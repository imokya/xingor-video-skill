"""travel-route 核心：行程配置 → 地图图层 / 地名 / 航线 / 出租车路线 / 相机编排 / 逐帧状态。
网页预览（player/）和成片渲染（travel_render.py）都读这里算好的结果，两边的运动完全一致。

坐标：地面统一用墨卡托公里（原点 = 两座机场的中点），相机 Cam3 是针孔透视相机看地面：
    target 地面点、heading（0 = 北）、pitch（0 = 俯视；>0 斜看，画面下沿近）、dist（km）、F（焦距 px）、flip（卡片绕竖轴翻转）
时间轴（秒，默认 16.3 s）：
    0–1      地球全貌停留
    1–3.1    推近出发城市，飞线（向东弯的弧）从出发画到到达，镜头紧跟线头
    3.1–4.7  拉远看全程 → 朝出发机场拉近，地球 → 矢量地图交叉淡化（同比例尺交接）
    4.7–5.7  矢量地图继续拉近，卡片外的地图淡成背景，地图收成一张带厚边的卡片
    5.7–7.2  卡片顶部后倒（下沿近）、磨砂机票从模糊淡入、慢推
    7.2–8.4  加速冲进机票，穿过去落到跑道上的飞机（俯仰角一路增大，不翻转）
    8–12     飞行 4 秒：滑跑 → 爬升 → 巡航（相机拉高）→ 下降 → 着陆
    12–14.5  镜头飞到市区，出租车只开最后一段（约 3 km，2 秒），车头贴路线切线、按弯道刹车
    14.5–    终点图钉 + 地名
"""
import json, math, os, pickle, sys
import numpy as np

sys.setrecursionlimit(20000)
RE = 6371.0


# ================================================================ 工具
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def P(t, t0, d): return clamp((t - t0) / d)
def eio(x): x = clamp(x); return x * x * (3 - 2 * x)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def ei(x): x = clamp(x); return x ** 3
def eob(x, s=1.7): x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, k): return a + (b - a) * k
def logl(a, b, k): return math.exp(lerp(math.log(a), math.log(b), k))


def gauss_smooth(x, sigma):
    if sigma <= 0: return np.asarray(x, float)
    r = int(sigma * 3); k = np.exp(-.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    return np.convolve(np.pad(np.asarray(x, float), (r, r), mode='edge'), k, mode='valid')


def resample(pts, step):
    seg = np.hypot(*np.diff(pts, axis=0).T); cum = np.concatenate([[0], np.cumsum(seg)])
    ss = np.arange(0, cum[-1], step)
    return np.stack([np.interp(ss, cum, pts[:, 0]), np.interp(ss, cum, pts[:, 1])], 1)


def pchip(ts, vs):
    """单调三次插值（端点速度为 0），返回 f(t)"""
    ts, vs = np.asarray(ts, float), np.asarray(vs, float)
    h = np.diff(ts); d = np.diff(vs) / h; m = np.zeros_like(vs)
    for i in range(1, len(vs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    def f(t):
        if t <= ts[0]: return float(vs[0])
        if t >= ts[-1]: return float(vs[-1])
        i = int(np.searchsorted(ts, t) - 1); s = (t - ts[i]) / h[i]
        return float((2 * s ** 3 - 3 * s ** 2 + 1) * vs[i] + (s ** 3 - 2 * s ** 2 + s) * h[i] * m[i]
                     + (-2 * s ** 3 + 3 * s ** 2) * vs[i + 1] + (s ** 3 - s ** 2) * h[i] * m[i + 1])
    return f


def dp_simplify(pts, tol):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; ab = b - a; L = np.hypot(*ab)
    d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / L if L > 1e-9 else np.hypot(*(pts - a).T)
    i = int(np.argmax(d))
    if d[i] > tol: return np.vstack([dp_simplify(pts[:i + 1], tol)[:-1], dp_simplify(pts[i:], tol)])
    return np.array([a, b])


class Track:
    def __init__(self, pts):
        self.p = np.asarray(pts, float)
        self.cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(self.p, axis=0).T))]); self.L = float(self.cum[-1])

    def at(self, s):
        s = min(max(s, 0), self.L)
        return np.array([np.interp(s, self.cum, self.p[:, 0]), np.interp(s, self.cum, self.p[:, 1])])

    def heading(self, s, win):
        a, b = self.at(s - win), self.at(s + win)
        return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))


def vec3(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return np.array([math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)])


def arc_point(a, b, k, bow=.11):
    """地球飞线：球面二次曲线，控制点从中点向东侧移，飞线带弧度（player.js 的 arcPoint 与此一致）"""
    va, vb = vec3(*a), vec3(*b)
    m = va + vb; m /= np.linalg.norm(m)
    n = np.cross(va, vb); n /= np.linalg.norm(n)
    lm = math.atan2(m[1], m[0]); east = np.array([-math.sin(lm), math.cos(lm), 0.0])
    if np.dot(n, east) < 0: n = -n
    c = m + n * bow; c /= np.linalg.norm(c)
    v = (1 - k) ** 2 * va + 2 * k * (1 - k) * c + k ** 2 * vb
    return v / np.linalg.norm(v)


def ll_of(v): return math.degrees(math.atan2(v[1], v[0])), math.degrees(math.asin(clamp(float(v[2]), -1, 1)))


# ================================================================ 相机
class Cam3:
    def __init__(self, tx, ty, heading, pitch, dist, F=1500.0, cx=960, cy=600, flip=0.0):
        h, p = math.radians(heading), math.radians(pitch); hx, hy = math.sin(h), math.cos(h)
        self.f = np.array([hx * math.sin(p), hy * math.sin(p), -math.cos(p)])
        self.r = np.array([hy, -hx, 0.0]); self.u = np.cross(self.r, self.f)
        self.C = np.array([tx, ty, 0.0]) - self.f * dist
        self.F, self.cx, self.cy, self.dist, self.T, self.near = F, cx, cy, dist, (tx, ty), dist * .05
        self.fl = abs(flip) > 1e-4; self.fc, self.fs = math.cos(math.radians(flip)), math.sin(math.radians(flip))

    def proj(self, X, Y, Z=0.0):
        X, Y, Z = np.asarray(X, float), np.asarray(Y, float), np.asarray(Z, float)
        if self.fl:                                                   # 卡片绕自身竖直轴翻转
            ox = X - self.T[0]; X, Z = self.T[0] + ox * self.fc - Z * self.fs, ox * self.fs + Z * self.fc
        dx, dy, dz = X - self.C[0], Y - self.C[1], Z - self.C[2]
        xc = dx * self.r[0] + dy * self.r[1] + dz * self.r[2]
        yc = dx * self.u[0] + dy * self.u[1] + dz * self.u[2]
        zc = dx * self.f[0] + dy * self.f[1] + dz * self.f[2]
        zz = np.maximum(zc, 1e-6)
        return self.cx + self.F * xc / zz, self.cy - self.F * yc / zz, zc

    def front_line(self):
        if self.fl: return np.array([0.0, 0.0]), -1e18
        return self.f[:2], self.near + float(np.dot(self.f, self.C))

    def horizon_y(self):
        nrm = math.hypot(self.f[0], self.f[1])
        if nrm < 1e-6: return -1e9
        X = self.C[0] + self.f[0] / nrm * self.dist * 400; Y = self.C[1] + self.f[1] / nrm * self.dist * 400
        x, y, z = self.proj(X, Y); return float(y) if z > 0 else -1e9

    def homography(self):
        """地面平面 (X, Y, 1) → 屏幕的 3x3 射影矩阵"""
        f, r, u, C, F, cx, cy = self.f, self.r, self.u, self.C, self.F, self.cx, self.cy
        return np.array([[F * r[0] + cx * f[0], F * r[1] + cx * f[1], -F * r @ C - cx * f @ C],
                         [-F * u[0] + cy * f[0], -F * u[1] + cy * f[1], F * u @ C - cy * f @ C],
                         [f[0], f[1], -f @ C]])


def clip_halfplane(xs, ys, n, k):
    out = []; m = len(xs)
    for i in range(m):
        ax, ay, bx, by = xs[i - 1], ys[i - 1], xs[i], ys[i]
        da, db = n[0] * ax + n[1] * ay - k, n[0] * bx + n[1] * by - k
        if db >= 0:
            if da < 0: s = da / (da - db); out.append((ax + (bx - ax) * s, ay + (by - ay) * s))
            out.append((bx, by))
        elif da >= 0: s = da / (da - db); out.append((ax + (bx - ax) * s, ay + (by - ay) * s))
    return out


# ================================================================ 地图样式（高德风格）
SEA, LAND, URBAN = (170, 208, 240), (244, 242, 236), (236, 232, 226)
NE_ROAD, NE_ROAD_CASE, COAST = (255, 214, 140), (232, 184, 110), (150, 188, 222)
LAND_BG = (246, 244, 239)
BLUE, INK, MUTED = (38, 108, 255), (36, 40, 50), (110, 118, 130)
STY = {   # 类别: (填充 / 线色, 描边色, 线宽 km, 是否面)
    '_land': (LAND_BG, None, 0, True),
    'water': ((166, 206, 240), None, 0, True), 'park': ((197, 230, 186), None, 0, True),
    'apron': ((226, 226, 232), None, 0, True), 'building': ((233, 229, 222), (214, 208, 200), 0, True),
    'river': ((166, 206, 240), None, .06, False), 'rail': ((180, 180, 188), None, .006, False),
    'minor': ((255, 255, 255), (222, 222, 226), .012, False), 'secondary': ((255, 255, 255), (210, 210, 216), .02, False),
    'taxiway': ((205, 205, 214), None, .025, False), 'primary': ((255, 233, 160), (226, 196, 120), .028, False),
    'motorway': ((255, 200, 110), (222, 160, 70), .038, False), 'runway': ((178, 178, 190), (150, 150, 162), .06, False),
}
ORDER = ['_land', 'water', 'park', 'apron', 'building', 'river', 'rail', 'minor', 'secondary', 'taxiway', 'primary', 'motorway', 'runway']
AREAS = {'water', 'park', 'apron', 'building'}


def classify(tg):
    hw = tg.get('highway')
    if hw:
        if hw.startswith('motorway'): return 'motorway'
        if hw.startswith('trunk') or hw.startswith('primary'): return 'primary'
        if hw in ('secondary', 'tertiary'): return 'secondary'
        return 'minor'
    ae = tg.get('aeroway')
    if ae == 'runway': return 'runway'
    if ae == 'taxiway': return 'taxiway'
    if ae in ('apron', 'terminal'): return 'apron'
    if tg.get('natural') == 'water': return 'water'
    if tg.get('waterway') == 'river': return 'river'
    if tg.get('leisure') == 'park': return 'park'
    if 'building' in tg: return 'building'
    if tg.get('railway') == 'rail': return 'rail'
    return None


def stitch(segs):
    segs = [list(s) for s in segs if len(s) > 1]; rings = []
    while segs:
        cur = segs.pop(0); changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]: cur += s[1:]
                elif s[-1] == cur[-1]: cur += s[::-1][1:]
                elif s[-1] == cur[0]: cur = s[:-1] + cur
                elif s[0] == cur[0]: cur = s[::-1][:-1] + cur
                else: continue
                segs.pop(i); changed = True; break
        rings.append(cur)
    return rings


def is_foreign(nm): return any('Ѐ' <= ch <= 'ӿ' for ch in nm)


# ================================================================ 行程
class Trip:
    """读 trip.json + data/，算出一切静态数据和逐帧状态"""
    T = dict(hold=1.0, arc=(1.5, 1.6), zoom=(3.5, 1.2), xfade=(4.35, .35), phone=5.7, face=6.3, flyin=7.2,
             fly0=8.0, landed=12.0, taxi0=12.5, taxi1=14.5, dur=16.3)

    def __init__(self, trip_path, fps=60, size=(1920, 1080)):
        self.cfg = json.load(open(trip_path))
        self.dir = os.path.dirname(os.path.abspath(trip_path)); self.D = os.path.join(self.dir, 'data')
        self.W, self.H = self.cfg.get('size', size); self.fps = self.cfg.get('fps', fps)
        T = dict(self.T); T.update(self.cfg.get('timing', {})); self.T = T
        self.T['dive1'] = T['fly0'] + .4
        o, d = self.cfg['origin']['airport']['lonlat'], self.cfg['dest']['airport']['lonlat']
        self.lon0, self.lat0 = (o[0] + d[0]) / 2, (o[1] + d[1]) / 2
        self.y0 = RE * math.log(math.tan(math.pi / 4 + math.radians(self.lat0) / 2))
        self._layers(); self._airports(); self._tracks(); self._places(); self._models()
        self._cameras(); self._states()

    # ---------------- 投影
    def merc(self, lon, lat):
        lon, lat = np.asarray(lon, float), np.asarray(lat, float)
        return RE * np.radians(lon - self.lon0), RE * np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)) - self.y0

    def unmerc(self, x, y):
        return np.degrees(x / RE) + self.lon0, np.degrees(2 * np.arctan(np.exp((y + self.y0) / RE)) - np.pi / 2)

    def m2(self, ll): x, y = self.merc(*ll); return np.array([float(x), float(y)])

    # ---------------- 图层
    def _pack(self, rings, tol=0.0, meta=None):
        arrs = [dp_simplify(np.asarray(r, float), tol) if tol else np.asarray(r, float) for r in rings]
        arrs = [a for a in arrs if len(a) >= 2]
        pts = np.vstack(arrs) if arrs else np.zeros((0, 2)); offs = np.cumsum([0] + [len(a) for a in arrs])
        bb = np.array([[a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()] for a in arrs]) if arrs else np.zeros((0, 4))
        return dict(pts=pts, offs=offs, bb=bb, meta=meta if meta is not None else [None] * len(arrs))

    def _ll2m(self, rings): return [np.stack(self.merc(*np.array(r).T), 1) for r in rings if len(r) >= 2]

    def _layers(self):
        ne = pickle.load(open(os.path.join(self.D, 'ne_region.pkl'), 'rb'))
        rd = [r for r in ne['roads'] if len(r['p']) >= 2]
        self.base = {'land': self._pack(self._ll2m(ne['land']), .3), 'lakes': self._pack(self._ll2m(ne['lakes']), .2),
                     'rivers': self._pack(self._ll2m(ne['rivers']), .3), 'coast': self._pack(self._ll2m(ne['coastline']), .3),
                     'urban': self._pack(self._ll2m(ne['urban']), .1),
                     'roads': self._pack(self._ll2m([r['p'] for r in rd]), .3, [r['rank'] for r in rd])}
        self.ne_places = ne['places']
        cover = json.load(open(os.path.join(self.D, 'cover.json')))
        self.cities, self.cover, self.raw = {}, {}, {}
        for key in ('origin', 'dest'):
            d = json.load(open(os.path.join(self.D, f'osm_{key}.json')))
            out = {}
            for e in d['elements']:
                tg = e.get('tags', {}); cat = classify(tg)
                if cat is None: continue
                if e['type'] == 'way' and 'geometry' in e: rings = [[(g['lon'], g['lat']) for g in e['geometry']]]
                elif e['type'] == 'relation':
                    rings = stitch([[(g['lon'], g['lat']) for g in m['geometry']] for m in e.get('members', [])
                                    if m.get('type') == 'way' and 'geometry' in m and m.get('role', 'outer') == 'outer'])
                else: continue
                for r in rings:
                    if cat in AREAS and r[0] != r[-1]: continue
                    out.setdefault(cat, []).append(dict(xy=np.stack(self.merc(*np.array(r).T), 1), name=tg.get('name', '')))
            c = cover[key]; x0, y0 = self.m2((c[0], c[1])); x1, y1 = self.m2((c[2], c[3]))
            self.cover[key] = (float(x0), float(y0), float(x1), float(y1))
            out['_land'] = [dict(xy=np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), name='')]
            self.raw[key] = out
            self.cities[key] = {cat: self._pack([f['xy'] for f in fs]) for cat, fs in out.items()}

    # ---------------- 机场 / 跑道：选最长的跑道，方向朝着要去 / 来的方向
    def _runway(self, key, toward):
        rws = self.raw[key].get('runway', [])
        if not rws: raise RuntimeError(f'{key} 机场没有跑道数据')
        rw = max(rws, key=lambda f: np.hypot(*(f['xy'][-1] - f['xy'][0])))
        a, b = rw['xy'][0], rw['xy'][-1]
        return (a, b) if np.dot(b - a, toward) > 0 else (b, a)

    def _airports(self):
        cfg = self.cfg
        self.O_ll, self.D_ll = tuple(cfg['origin']['lonlat']), tuple(cfg['dest']['lonlat'])
        oa, da = self.m2(cfg['origin']['airport']['lonlat']), self.m2(cfg['dest']['airport']['lonlat'])
        self.TAKE0, self.TAKE1 = self._runway('origin', da - oa)            # 起飞朝着目的地
        self.LAND0, self.LAND1 = self._runway('dest', da - oa)              # 降落顺着来的方向
        self.PARK = self.m2(cfg['poi']['lonlat'])

    # ---------------- 航线 / 出租车路线
    def _tracks(self):
        d0 = (self.TAKE1 - self.TAKE0) / np.linalg.norm(self.TAKE1 - self.TAKE0)
        dl = (self.LAND1 - self.LAND0) / np.linalg.norm(self.LAND1 - self.LAND0)
        # 直线滑跑爬升 → 三次 Hermite 大弧线 → 对准跑道直线进近（航向变化平缓，没有急转）
        P0, P1 = self.TAKE1 + d0 * 25, self.LAND0 - dl * 40
        L = np.hypot(*(P1 - P0)); m0, m1 = d0 * L * .45, dl * L * .45
        ss = np.linspace(0, 1, 4000)[:, None]
        curve = (2 * ss ** 3 - 3 * ss ** 2 + 1) * P0 + (ss ** 3 - 2 * ss ** 2 + ss) * m0 + (-2 * ss ** 3 + 3 * ss ** 2) * P1 + (ss ** 3 - ss ** 2) * m1
        self.FLIGHT = Track(resample(np.vstack([self.TAKE0, self.TAKE1, curve, self.LAND0, self.LAND0 + dl * 2.8]), .05))
        self.LAND_S = float(self.FLIGHT.cum[np.argmin(np.hypot(*(self.FLIGHT.p - self.LAND0).T))])
        self.LIFT_S = float(self.FLIGHT.cum[np.argmin(np.hypot(*(self.FLIGHT.p - (self.TAKE0 + d0 * 3.0)).T))])
        self.FLIGHT_KM = RE * math.acos(clamp(float(np.dot(vec3(*self.cfg['origin']['airport']['lonlat']), vec3(*self.cfg['dest']['airport']['lonlat']))), -1, 1))
        T = self.T
        self.FLY_S = pchip([T['fly0'], T['fly0'] + .7, T['fly0'] + 1.2, T['landed'] - 1.4, T['landed'] - .55, T['landed']],
                           [0, 3.4, 30, self.LAND_S - 70, self.LAND_S, self.FLIGHT.L])
        # 出租车：OSRM 路线，路口磨成半径 0.2 km 的圆弧；只开最后约 4.5 墨卡托 km（约 3 km）
        route = json.load(open(os.path.join(self.D, 'route.json')))['routes'][0]
        raw = np.stack(self.merc(*np.array(route['geometry']['coordinates']).T), 1)
        self.TAXI = Track(self.round_corners(raw, .2))
        self.TAXI_S0 = max(0.0, self.TAXI.L - self.cfg.get('taxi_tail_km', 4.5))
        self.TAXI_SUB = Track(self.TAXI.p[self.TAXI.cum >= self.TAXI_S0])
        self.TAXI_KM, self.TAXI_MIN = route['distance'] / 1000, route['duration'] / 60
        self._TC = self.taxi_time_map()

    @staticmethod
    def round_corners(pts, radius_km=.07):
        """沿弧长做高斯平滑，把路口直角磨成圆弧；车头严格沿这条线的切线"""
        q = resample(pts, .005); sig = radius_km / .005; r = int(sig * 3)
        k = np.exp(-.5 * (np.arange(-r, r + 1) / sig) ** 2); k /= k.sum()
        pad = np.vstack([np.repeat(q[:1], r, 0), q, np.repeat(q[-1:], r, 0)])
        return resample(np.stack([np.convolve(pad[:, 0], k, 'valid'), np.convolve(pad[:, 1], k, 'valid')], 1), .01)

    def taxi_time_map(self, yaw_max=170.0):
        """像真车一样开：按弯道曲率限速（转向 ≤ yaw_max 度/秒），前后各扫一遍限制加速度（提前刹车、出弯加速），
        起步 / 到达从低速开始；直路最高速度二分求解，让总时长正好等于出租车段时长。"""
        total = self.T['taxi1'] - self.T['taxi0']
        d = np.diff(self.TAXI_SUB.p, axis=0); ds = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
        curv = gauss_smooth(np.abs(np.gradient(np.unwrap(np.arctan2(d[:, 0], d[:, 1])))) / ds, 4)
        om = math.radians(yaw_max)

        def profile(vs):
            acc = vs * 1.6
            v = np.concatenate([[vs * .03], np.minimum(vs, om / np.maximum(curv, 1e-6))]); v[-1] = min(v[-1], vs * .03)
            for i in range(1, len(v)): v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * acc * ds[i - 1]))
            for i in range(len(v) - 2, -1, -1): v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * acc * ds[i]))
            return v
        lo, hi = .05, 500.0
        for _ in range(60):
            mid = math.sqrt(lo * hi); v = profile(mid)
            if np.sum(2 * ds / (v[:-1] + v[1:])) > total: lo = mid
            else: hi = mid
        v = profile(hi); tc = np.concatenate([[0], np.cumsum(2 * ds / (v[:-1] + v[1:]))])
        return tc / tc[-1]

    def taxi_s(self, t):
        u = P(t, self.T['taxi0'], self.T['taxi1'] - self.T['taxi0'])
        return float(self.TAXI_S0 + np.interp(u, self._TC, self.TAXI_SUB.cum))

    def alt_frac(self, s):
        return eio(min(clamp((s - self.LIFT_S) / 55), clamp((self.LAND_S - s) / 45)))

    # ---------------- 地名 / 路名
    def _places(self):
        cfg = self.cfg; poi = cfg['poi']['name']; out = []
        for p in self.ne_places:
            nm = p['name'] or ''
            if not nm or is_foreign(nm) or nm in (cfg['origin']['name'], cfg['dest']['name']): continue
            lvl = 0 if p['rank'] <= 2 else 1 if p['rank'] <= 5 else 2
            x, y = self.m2(p['ll']); out.append((x, y, nm, lvl, {0: 3000, 1: 900, 2: 300}[lvl]))
        for key in ('origin', 'dest'):
            x, y = self.m2(cfg[key]['lonlat']); out.append((x, y, cfg[key]['name'], 0, 5000))
        for e in json.load(open(os.path.join(self.D, 'osm_places.json')))['elements']:
            tg = e['tags']; nm = tg.get('name', ''); pl = tg.get('place')
            if not nm or is_foreign(nm) or len(nm) > 9 or nm == poi or pl == 'city': continue
            x, y = self.m2((e['lon'], e['lat']))
            if pl in ('suburb', 'town'): out.append((x, y, nm, 2, 60))
            elif pl in ('quarter', 'neighbourhood'): out.append((x, y, nm, 3, 14))
            elif 'tourism' in tg: out.append((x, y, nm, 4, 9))
        for key, pt in (('origin', self.TAKE1), ('dest', self.LAND1)):
            out.append((float(pt[0]), float(pt[1]), cfg[key]['airport']['name'], 1, 120))
        self.PLACES = [(float(x), float(y), nm, lvl, vis) for x, y, nm, lvl, vis in out]
        roads = []
        for key in ('origin', 'dest'):
            best = {}
            for cat, rank in (('motorway', 0), ('primary', 1), ('secondary', 2)):
                for f in self.raw[key].get(cat, []):
                    nm = f['name']
                    if not nm or len(nm) > 8 or is_foreign(nm): continue
                    L = float(np.sum(np.hypot(*np.diff(f['xy'], axis=0).T)))
                    if L >= .25 and (nm not in best or L > best[nm][2]): best[nm] = (f['xy'], rank, L)
            roads += [(nm, xy, rk, L) for nm, (xy, rk, L) in best.items()]
        self.ROADNAMES = roads

    # ---------------- 3D 模型
    def _models(self):
        from travel_models import airliner, taxi
        self.PLANE, self.CAR = airliner(BLUE), taxi()

    # ---------------- 相机编排
    def _cameras(self):
        W, H, T = self.W, self.H, self.T
        self.PH_W, self.PH_H, self.PH_WG = 430, 900, 6.2
        self.KM_PER_PX = self.PH_WG / (self.PH_W - 32)
        mid_rw = (self.TAKE0 + self.TAKE1) / 2
        d0 = (self.TAKE1 - self.TAKE0) / np.linalg.norm(self.TAKE1 - self.TAKE0)
        self.PH_CENTER = mid_rw + d0 * 3.4                                 # 卡片露出的下半部正好是出发机场
        self.CARD_TGT = self.PH_CENTER + np.array([0.0, (450 - 760) * self.KM_PER_PX])
        self.TICKET_C = self.PH_CENTER + np.array([0.0, (450 - 680) * self.KM_PER_PX])
        self.CARD_LL = tuple(float(v) for v in self.unmerc(*self.CARD_TGT))
        self.LAT_SEC = 1 / math.cos(math.radians(self.CARD_LL[1]))
        self.D_XFADE = 600.0
        ts = np.arange(int(T['dur'] * self.fps)) / self.fps
        raw = [self.raw_cam(t) for t in ts]
        keys = ['tx', 'ty', 'head', 'pitch', 'dist', 'cx', 'cy', 'F', 'flip']
        arr = {k: np.array([r[k] for r in raw], float) for k in keys}
        arr['head'] = np.degrees(np.unwrap(np.radians(arr['head']))); arr['dist'] = np.log(arr['dist'])
        start = int(T['dive1'] * self.fps)                                 # 之前都是解析曲线，冲刺结束后才做时间平滑
        for k, sig in (('tx', 5), ('ty', 5), ('head', 24), ('pitch', 14), ('dist', 12)):
            arr[k][start:] = gauss_smooth(arr[k][start:], sig)
        arr['dist'] = np.exp(arr['dist'])
        self.CAMS = arr; self.N = len(ts)
        self.GLOBE = [self.globe_params(t) for t in ts[:int((T['xfade'][0] + T['xfade'][1] + .1) * self.fps)]]

    def cam(self, n):
        a = self.CAMS
        fs = self.W / 1920.0 if self.W < self.H else 1.0      # portrait frames: keep the horizontal field of view
        return Cam3(a['tx'][n], a['ty'][n], a['head'][n], a['pitch'][n], a['dist'][n], a['F'][n] * fs, a['cx'][n], a['cy'][n], a['flip'][n])

    def globe_params(self, t):
        """(中心经度, 中心纬度, 半径 px, cx, cy, 飞线进度)"""
        T, W, H = self.T, self.W, self.H
        k = eio(P(t, *T['arc'])); R_end = 6371 * 1500 / self.D_XFADE * self.LAT_SEC
        A, B = self.O_ll, self.D_ll
        head = ll_of(arc_point(A, B, max(0.0, k - .03)))
        start = ll_of(arc_point(A, B, .0)); c0 = (start[0] - 15, start[1] - 10)
        if t < T['hold']:
            h = t / T['hold']; return (lerp(c0[0] - 6, c0[0], h), lerp(c0[1] - 3, c0[1], h), 430.0, W / 2, H / 2, k)
        if t < T['arc'][0] + T['arc'][1]:
            e = eio(P(t, T['hold'], .9))
            return (lerp(c0[0], head[0], e), lerp(c0[1], head[1], e), logl(430, 2300, e), W / 2, H / 2, k)
        pb = eio(P(t, T['arc'][0] + T['arc'][1], T['zoom'][0] - T['arc'][0] - T['arc'][1]))
        mid, eh = ll_of(arc_point(A, B, .5)), ll_of(arc_point(A, B, .97))
        lon, lat, R = lerp(eh[0], mid[0], pb), lerp(eh[1], mid[1], pb), logl(2300, 1150, pb)
        if t < T['zoom'][0]: return (lon, lat, R, W / 2, H / 2, k)
        z = eio(P(t, *T['zoom']))
        return (lerp(mid[0], self.CARD_LL[0], z), lerp(mid[1], self.CARD_LL[1], z),
                logl(1150, R_end, ei(P(t, *T['zoom'])) * .3 + z * .7), W / 2, H / 2, k)

    def phone_cam(self, t):
        T, W, H = self.T, self.W, self.H
        xe = T['xfade'][0] + T['xfade'][1]
        if t < T['phone']:                                                 # 矢量地图俯视拉近到卡片
            k = eio(P(t, xe, T['phone'] - xe)); ppk = logl(1500 / self.D_XFADE, 900 / 4.4, k); F = lerp(1500, 900, k)
            return dict(tx=self.CARD_TGT[0], ty=self.CARD_TGT[1], head=0.0, pitch=0.0, dist=F / ppk, cx=W / 2, cy=lerp(H / 2, H * .45, k), F=F, flip=0.0)
        pitch = lerp(0, 34, eio(P(t, T['phone'] + .1, .45))) + lerp(0, 4, eio(P(t, T['phone'] + .55, T['flyin'] - T['phone'] - .55)))
        dist = 4.4 * lerp(1, .8, eio(P(t, T['phone'] + .55, T['flyin'] - T['phone'] - .55)))
        return dict(tx=self.CARD_TGT[0], ty=self.CARD_TGT[1], head=0.0, pitch=pitch, dist=dist, cx=W / 2, cy=H * .45, F=900.0, flip=0.0)

    def dive_u(self, t): return eio(P(t, self.T['flyin'], self.T['dive1'] - self.T['flyin']))

    def dive_cam(self, t):
        u = self.dive_u(t); a = self.phone_cam(self.T['flyin'])
        mid = dict(tx=self.TICKET_C[0], ty=self.TICKET_C[1] + .9, head=0.0, pitch=46.0, dist=.75, cx=self.W / 2, cy=self.H / 2, F=1100.0, flip=0.0)
        z = self.raw_flight(self.T['dive1'])
        return self.blend(a, mid, u / .5) if u < .5 else self.blend(mid, z, (u - .5) / .5)

    def raw_flight(self, t):
        s = self.FLY_S(t); alt = self.alt_frac(s)
        hd = self.FLIGHT.heading(s + 1, 2 + 60 * alt); dist = logl(2.3, 700, alt)
        ahead = self.FLIGHT.at(s + dist * .1)
        return dict(tx=ahead[0], ty=ahead[1], head=hd, pitch=lerp(60, 48, alt), dist=dist, cx=self.W / 2, cy=self.H * .56, F=1500.0, flip=0.0)

    def raw_taxi(self, t):
        T = self.T; s = self.taxi_s(t); pos = self.TAXI.at(s)
        hd = self.TAXI.heading(min(s + 2.0, self.TAXI.L), 6.0)              # 地图朝向只跟大方向，车自己转
        end = eio(P(t, T['taxi1'] - .3, 2.2))
        dist = lerp(logl(4.2, 3.4, P(t, T['taxi0'], T['taxi1'] - T['taxi0'])), 2.4, end)
        tx, ty = lerp(pos[0], self.PARK[0], end * .5), lerp(pos[1], self.PARK[1], end * .5)
        return dict(tx=tx, ty=ty, head=hd, pitch=lerp(52, 44, end), dist=dist, cx=self.W / 2, cy=self.H * .56, F=1500.0, flip=0.0)

    @staticmethod
    def blend(a, b, k):
        out = {}
        for key in a:
            if key == 'head': out[key] = a['head'] + ((b['head'] - a['head'] + 540) % 360 - 180) * k
            elif key == 'dist': out[key] = logl(a[key], b[key], k)
            else: out[key] = lerp(a[key], b[key], k)
        return out

    def raw_cam(self, t):
        T = self.T
        if t < T['flyin']: return self.phone_cam(t)
        if t < T['dive1']: return self.dive_cam(t)
        if t < T['landed']: return self.raw_flight(t)
        if t < T['taxi0'] + .5:
            return self.blend(self.raw_flight(T['landed']), self.raw_taxi(T['taxi0'] + .5), eio(P(t, T['landed'] - .2, T['taxi0'] + .7 - T['landed'])))
        return self.raw_taxi(t)

    def phone_state(self, t):
        """ui 机票透明度、bez 卡片厚边、open 卡片窗口展开程度（1 = 整幅地图）、blur_in 机票淡入时的模糊"""
        T = self.T; u = self.dive_u(t) if t >= T['flyin'] else 0.0
        fade_in = eo(P(t, T['phone'] + .3, .3)); card = eio(P(t, T['phone'] - .55, .55))
        return dict(u=u, ui=fade_in * (1 - eio((u - .40) / .16)), bez=card * (1 - eio((u - .25) / .3)),
                    open=eio((u - .30) / .3) if t >= T['flyin'] else 1 - card, blur_in=(1 - fade_in) * 12)

    # ---------------- 逐帧状态（飞机 / 出租车朝向逐帧平滑，车头贴路线切线）
    def _states(self):
        ts = np.arange(self.N) / self.fps
        ps = np.array([self.FLY_S(t) for t in ts]); alt = np.array([self.alt_frac(s) for s in ps])
        pos = np.array([self.FLIGHT.at(s) for s in ps])
        hd = gauss_smooth(np.degrees(np.unwrap(np.radians([self.FLIGHT.heading(s, .8 + 8 * a) for s, a in zip(ps, alt)]))), 14)
        bank = np.clip(gauss_smooth(np.gradient(hd) * self.fps, 10) * .9, -24, 22)
        LIFT, LAND = self.LIFT_S, self.LAND_S
        climb = gauss_smooth([7 * clamp((s - LIFT) / 6) * (1 - clamp((s - LIFT - 40) / 30)) - 3 * clamp((s - (LAND - 60)) / 20) * (1 - clamp((s - LAND + 3) / 3)) for s in ps], 12)
        cs = np.array([self.taxi_s(t) for t in ts]); cpos = np.array([self.TAXI.at(s) for s in cs])
        chd = gauss_smooth(np.degrees(np.unwrap(np.radians([self.TAXI.heading(s, .015) for s in cs]))), 1.5)
        self.ST = dict(plane=dict(x=pos[:, 0], y=pos[:, 1], alt=alt, head=hd, bank=bank, climb=climb, s=ps),
                       car=dict(x=cpos[:, 0], y=cpos[:, 1], head=chd, s=cs),
                       phone={k: np.array([self.phone_state(t)[k] for t in ts]) for k in ('u', 'ui', 'bez', 'open', 'blur_in')})

    # ---------------- 导出给网页
    def export_web(self, out_dir):
        r3 = lambda a: np.round(np.asarray(a, float), 3).ravel().tolist()
        def feats(layer):
            return [dict(bb=r3(layer['bb'][i]), p=r3(layer['pts'][layer['offs'][i]:layer['offs'][i + 1]]),
                         **({'m': layer['meta'][i]} if layer['meta'][i] is not None else {})) for i in range(len(layer['offs']) - 1)]
        cities = {}
        for key, data in self.cities.items():
            ls = []
            for cat in ORDER:
                if cat not in data: continue
                fill, case, w, area = STY[cat]
                ls.append(dict(cat=cat, fill=fill, case=case, w=w, area=area, f=feats(data[cat])))
            cities[key] = dict(cover=list(self.cover[key]), layers=ls)
        cfg = self.cfg
        data = dict(W=self.W, H=self.H, fps=self.fps, dur=self.T['dur'], n=self.N,
                    T=dict(xfade=list(self.T['xfade']), dive1=self.T['dive1'], phone=self.T['phone'], face=self.T['face'], flyin=self.T['flyin'],
                           fly0=self.T['fly0'], landed=self.T['landed'], taxi0=self.T['taxi0'], taxi1=self.T['taxi1']),
                    frames=dict(cam={k: r3(v) for k, v in self.CAMS.items()},
                                plane={k: r3(v) for k, v in self.ST['plane'].items()}, car={k: r3(v) for k, v in self.ST['car'].items()},
                                phone={k: r3(v) for k, v in self.ST['phone'].items()}, globe=np.round(np.array(self.GLOBE), 3).tolist()),
                    base={k: feats(v) for k, v in self.base.items()}, cities=cities,
                    places=[[round(p[0], 3), round(p[1], 3), p[2], p[3], p[4]] for p in self.PLACES],
                    roads=[[nm, r3(xy), rk, round(L, 2)] for nm, xy, rk, L in self.ROADNAMES],
                    flight=dict(p=r3(self.FLIGHT.p[::2]), cum=r3(self.FLIGHT.cum[::2]), L=self.FLIGHT.L, km=self.FLIGHT_KM),
                    taxi=dict(p=r3(self.TAXI.p[::3]), cum=r3(self.TAXI.cum[::3]), L=self.TAXI.L, km=self.TAXI_KM, min=self.TAXI_MIN),
                    park=r3(self.PARK),
                    phone=dict(center=r3(self.PH_CENTER), km_per_px=self.KM_PER_PX, w=self.PH_W, h=self.PH_H),
                    models=dict(plane=[[np.round(np.array(v), 4).ravel().tolist(), list(c)] for v, c in self.PLANE],
                                car=[[np.round(np.array(v), 4).ravel().tolist(), list(c)] for v, c in self.CAR]),
                    city_pts={cfg['origin']['name']: list(self.O_ll), cfg['dest']['name']: list(self.D_ll)},
                    trip=dict(origin=cfg['origin']['name'], dest=cfg['dest']['name'], poi=cfg['poi']['name'], poi_sub=cfg['poi'].get('sub', ''),
                              o_air=cfg['origin']['airport']['name'], d_air=cfg['dest']['airport']['name'],
                              o_code=cfg['origin']['airport'].get('code', ''), d_code=cfg['dest']['airport'].get('code', ''),
                              ticket=cfg.get('ticket', {})))
        os.makedirs(out_dir, exist_ok=True)
        json.dump(data, open(os.path.join(out_dir, 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        return os.path.join(out_dir, 'data.json')
