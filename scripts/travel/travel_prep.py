"""travel-route 数据准备：基础数据（缓存，多个项目共用）+ 本次行程的城市数据。

    python travel_prep.py trip.json            # 在项目目录运行；结果写到 ./data/

基础数据（只下载一次，缓存到 ~/.cache/xingor-travel/，公共领域）：
    Natural Earth 10m：陆地 / 海岸线 / 河流 / 湖泊 / 道路 / 城市点（带中文名）/ 建成区
    NASA：Blue Marble 地球贴图、云层、夜景灯光（WebGL 与 skia 地球都用）
本次行程（OpenStreetMap Overpass + OSRM）：
    出发机场：跑道 / 滑行道 / 停机坪 / 航站楼 + 周边主干道 / 水系 / 公园
    到达城市：到达机场 + 进近区域主干道 + 机场到终点一带的道路 / 水系 / 公园 / 铁路，终点附近的小路和建筑
    两地地名点（区 / 镇 / 街道 / 景点），出租车路线（OSRM，从到达机场航站楼到终点）
下载前要征得用户同意（说明来源、大小）。数据署名：© OpenStreetMap 贡献者、Natural Earth、NASA、OSRM。
"""
import json, math, os, pickle, struct, sys, time, urllib.parse, urllib.request, zipfile

CACHE = os.path.expanduser(os.environ.get('XINGOR_TRAVEL_CACHE', '~/.cache/xingor-travel'))
UA = {'User-Agent': 'xingor-video-skill travel-route/1.0'}
OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
            'https://overpass.kumi.systems/api/interpreter']   # 504s are common: the script retries and rotates
NE_FILES = {'land': 'physical/ne_10m_land', 'coastline': 'physical/ne_10m_coastline',
            'rivers': 'physical/ne_10m_rivers_lake_centerlines', 'lakes': 'physical/ne_10m_lakes',
            'roads': 'cultural/ne_10m_roads', 'places': 'cultural/ne_10m_populated_places', 'urban': 'cultural/ne_10m_urban_areas'}
NASA = {'earth.jpg': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/73000/73909/world.topo.bathy.200412.3x5400x2700.jpg',
        'clouds.jpg': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/cloud_combined_2048.jpg',
        'night.jpg': 'https://eoimages.gsfc.nasa.gov/images/imagerecords/144000/144898/BlackMarble_2016_01deg.jpg'}


def log(*a): print('[travel_prep]', *a, flush=True)


def fetch(url, path, data=None, timeout=300):
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(path + '.part', 'wb') as f:
        while True:
            b = r.read(1 << 20)
            if not b: break
            f.write(b)
    os.replace(path + '.part', path)


# ---------------------------------------------------------------- 基础数据（缓存）
def base_data():
    os.makedirs(os.path.join(CACHE, 'shp'), exist_ok=True)
    for key, rel in NE_FILES.items():
        name = os.path.basename(rel)
        if os.path.exists(os.path.join(CACHE, 'shp', name + '.shp')): continue
        z = os.path.join(CACHE, name + '.zip')
        log('下载 Natural Earth', name); fetch(f'https://naciscdn.org/naturalearth/10m/{rel}.zip', z)
        with zipfile.ZipFile(z) as zf:
            for m in zf.namelist():
                if m.endswith(('.shp', '.dbf')): zf.extract(m, os.path.join(CACHE, 'shp'))
        os.remove(z)
    for name, url in NASA.items():
        p = os.path.join(CACHE, name)
        if not os.path.exists(p):
            log('下载 NASA 贴图', name); fetch(url, p)


def read_shp(path):
    with open(path, 'rb') as f:
        f.seek(100)
        while True:
            hdr = f.read(8)
            if len(hdr) < 8: return
            _, length = struct.unpack('>ii', hdr); rec = f.read(length * 2)
            st = struct.unpack('<i', rec[:4])[0]
            if st == 1: yield [[struct.unpack('<2d', rec[4:20])]]; continue
            if st not in (3, 5): yield None; continue
            np_, npt = struct.unpack('<2i', rec[36:44])
            parts = list(struct.unpack(f'<{np_}i', rec[44:44 + 4 * np_])) + [npt]
            pts = struct.unpack(f'<{2 * npt}d', rec[44 + 4 * np_:44 + 4 * np_ + 16 * npt])
            yield [[(pts[2 * i], pts[2 * i + 1]) for i in range(a, b)] for a, b in zip(parts[:-1], parts[1:])]


def read_dbf(path):
    f = open(path, 'rb'); hdr = f.read(32)
    n, hlen, rlen = struct.unpack('<IHH', hdr[4:12]); fields = []
    while True:
        d = f.read(32)
        if d[0] == 0x0D: break
        fields.append((d[:11].split(b'\0')[0].decode(), d[11:12].decode(), d[16]))
    f.seek(hlen)
    for _ in range(n):
        rec = f.read(rlen); pos = 1; row = {}
        for name, typ, ln in fields:
            v = rec[pos:pos + ln].decode('utf-8', 'ignore').strip(); pos += ln
            if typ in 'NF':
                try: v = float(v)
                except ValueError: v = None
            row[name] = v
        yield row


def ne_region(box, out):
    """Natural Earth 按区域裁切（经纬度原样保存，墨卡托投影在 travel_core 里做）"""
    if os.path.exists(out): return
    shp = lambda n: os.path.join(CACHE, 'shp', os.path.basename(NE_FILES[n]) + '.shp')
    inbox = lambda r: any(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in r)
    res = {k: [] for k in ('land', 'coastline', 'rivers', 'lakes', 'roads', 'urban', 'places')}
    for k in ('land', 'coastline', 'rivers', 'lakes', 'urban'):
        for g in read_shp(shp(k)):
            if g: res[k] += [[(round(x, 4), round(y, 4)) for x, y in r] for r in g if inbox(r)]
    for g, row in zip(read_shp(shp('roads')), read_dbf(shp('roads')[:-4] + '.dbf')):
        if g: res['roads'] += [dict(p=[(round(x, 4), round(y, 4)) for x, y in r], rank=row.get('scalerank') or 10) for r in g if inbox(r)]
    for g, row in zip(read_shp(shp('places')), read_dbf(shp('places')[:-4] + '.dbf')):
        lo, la = g[0][0]
        if box[0] <= lo <= box[2] and box[1] <= la <= box[3]:
            res['places'].append(dict(ll=(lo, la), name=row.get('NAME_ZH') or row.get('NAME'), rank=row.get('SCALERANK') or 10))
    pickle.dump(res, open(out, 'wb'))
    log('Natural Earth 区域', {k: len(v) for k, v in res.items()})


# ---------------------------------------------------------------- OSM / OSRM
def overpass(query, path):
    if os.path.exists(path): return json.load(open(path))
    for attempt in range(6):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            fetch(url, path, data=urllib.parse.urlencode({'data': query}).encode(), timeout=400)
            d = json.load(open(path))
            log('Overpass', os.path.basename(path), len(d.get('elements', [])), '个要素')
            return d
        except Exception as e:
            log('Overpass 失败，重试', attempt + 1, e)
            if os.path.exists(path): os.remove(path)
            time.sleep(20 + attempt * 10)
    raise RuntimeError('Overpass 多次失败：' + path)


def bb(lon, lat, dlon, dlat): return f'{lat - dlat:.4f},{lon - dlon:.4f},{lat + dlat:.4f},{lon + dlon:.4f}'


def city_queries(trip):
    o, d, poi = trip['origin']['airport'], trip['dest']['airport'], trip['poi']
    ao, ad, pp = o['lonlat'], d['lonlat'], poi['lonlat']
    lon0, lon1 = min(ad[0], pp[0]) - .08, max(ad[0], pp[0]) + .08
    lat0, lat1 = min(ad[1], pp[1]) - .06, max(ad[1], pp[1]) + .06
    dest_box = f'{lat0:.4f},{lon0:.4f},{lat1:.4f},{lon1:.4f}'
    major = '^(motorway|trunk|primary|secondary|motorway_link|trunk_link|primary_link)$'
    q_origin = f'''[out:json][timeout:200];
(
  way["aeroway"~"^(runway|taxiway|apron|terminal)$"]({bb(*ao, .08, .07)});
  way["highway"~"{major}"]({bb(*ao, .30, .28)});
  way["natural"="water"]({bb(*ao, .30, .28)});
  way["waterway"="river"]({bb(*ao, .30, .28)});
  way["leisure"="park"]({bb(*ao, .15, .12)});
);
out geom;'''
    q_dest = f'''[out:json][timeout:200];
(
  way["aeroway"~"^(runway|taxiway|apron|terminal)$"]({bb(*ad, .08, .07)});
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link)$"]({dest_box});
  way["highway"~"{major}"]({bb(*ad, .40, .30)});
  way["highway"~"^(residential|unclassified|living_street|pedestrian)$"]({bb(*pp, .05, .03)});
  way["natural"="water"]({dest_box});
  relation["natural"="water"]({dest_box});
  way["waterway"="river"]({dest_box});
  way["leisure"="park"]({dest_box});
  relation["leisure"="park"]({dest_box});
  way["railway"="rail"]({dest_box});
  way["building"]({bb(*pp, .025, .013)});
);
out geom;'''
    q_places = f'''[out:json][timeout:120];
(
  node["place"~"^(city|town|suburb|quarter|neighbourhood)$"]["name"]({bb(*ao, .35, .3)});
  node["place"~"^(city|town|suburb|quarter|neighbourhood|village)$"]["name"]({dest_box});
  node["tourism"~"^(attraction|museum)$"]["name"]({bb(*pp, .04, .03)});
);
out;'''
    cover = {'origin': (ao[0] - .30, ao[1] - .28, ao[0] + .30, ao[1] + .28),
             'dest': (min(lon0, ad[0] - .40), min(lat0, ad[1] - .30), max(lon1, ad[0] + .40), max(lat1, ad[1] + .30))}
    return q_origin, q_dest, q_places, cover


def osrm(a, b, path):
    if os.path.exists(path): return json.load(open(path))
    url = f'https://router.project-osrm.org/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}?overview=full&geometries=geojson'
    fetch(url, path, timeout=60)
    r = json.load(open(path))
    log('OSRM', round(r['routes'][0]['distance'] / 1000, 1), 'km')
    return r


def main(trip_path):
    trip = json.load(open(trip_path))
    proj = os.path.dirname(os.path.abspath(trip_path)); D = os.path.join(proj, 'data'); os.makedirs(D, exist_ok=True)
    base_data()
    lons = [trip['origin']['lonlat'][0], trip['dest']['lonlat'][0]]; lats = [trip['origin']['lonlat'][1], trip['dest']['lonlat'][1]]
    box = (min(lons) - 10, min(lats) - 8, max(lons) + 10, max(lats) + 8)
    ne_region(box, os.path.join(D, 'ne_region.pkl'))
    q_o, q_d, q_p, cover = city_queries(trip)
    overpass(q_o, os.path.join(D, 'osm_origin.json'))
    overpass(q_d, os.path.join(D, 'osm_dest.json'))
    overpass(q_p, os.path.join(D, 'osm_places.json'))
    json.dump(cover, open(os.path.join(D, 'cover.json'), 'w'))
    term = trip['dest']['airport'].get('terminal') or trip['dest']['airport']['lonlat']
    end = trip['poi'].get('route_end') or trip['poi']['lonlat']
    osrm(term, end, os.path.join(D, 'route.json'))
    log('完成：', D)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'trip.json')
