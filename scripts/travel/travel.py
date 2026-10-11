"""travel-route 命令行入口（在项目目录运行，trip.json 放在项目目录）：

    python travel.py prep   trip.json                 # 下载 / 缓存数据（先征得用户同意）
    python travel.py web    trip.json [--serve 8765]  # 导出网页预览到 ./web/，可选起本地服务器
    python travel.py stills trip.json 2.4 8.2 13.4    # 关键帧静帧到 ./stills/
    python travel.py render trip.json out.mp4         # 成片（和网页预览一致）
"""
import os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def web(trip_path, serve=None):
    from PIL import Image
    from travel_core import Trip
    from travel_prep import CACHE
    Image.MAX_IMAGE_PIXELS = None
    trip = Trip(trip_path); out = os.path.join(trip.dir, 'web')
    trip.export_web(out)
    for f in ('index.html', 'player.js'): shutil.copy(os.path.join(HERE, 'player', f), os.path.join(out, f))
    for name, size in (('earth.jpg', (4096, 2048)), ('night.jpg', (2048, 1024)), ('clouds.jpg', None)):
        dst = os.path.join(out, name)
        if not os.path.exists(dst):
            im = Image.open(os.path.join(CACHE, name)); im = im.convert('L' if name == 'clouds.jpg' else 'RGB')
            (im.resize(size) if size else im).save(dst, quality=90)
    print('web preview:', out)
    if serve:
        print(f'http://localhost:{serve}  （?t=秒 跳到某一时刻，&play 自动播放）')
        subprocess.run([sys.executable, '-m', 'http.server', str(serve), '--directory', out])


def main():
    cmd, trip_path = sys.argv[1], sys.argv[2]
    if cmd == 'prep':
        from travel_prep import main as prep; prep(trip_path)
    elif cmd == 'web':
        web(trip_path, int(sys.argv[sys.argv.index('--serve') + 1]) if '--serve' in sys.argv else None)
    elif cmd in ('stills', 'render'):
        from travel_core import Trip
        from travel_render import Renderer
        R = Renderer(Trip(trip_path))
        if cmd == 'render': R.render(sys.argv[3])
        else:
            d = os.path.join(os.path.dirname(os.path.abspath(trip_path)), 'stills'); os.makedirs(d, exist_ok=True)
            for t in map(float, sys.argv[3:]):
                p = os.path.join(d, f't_{t:05.2f}.png'); R.still(t, p); print(p)


if __name__ == '__main__':
    main()
