"""documentary 风格渲染核心：PIL/numpy 逐帧绘制 + ffmpeg 编码（9:16 文物 / 历史解说短片）

项目目录约定（cwd 或 init(project) 指定）：
  img/<name>.jpg      照片素材（doc_fetch.py 下载）
  cut/<name>.png      抠图（doc_cutout.py 生成）
  audio/vo_XX.wav     逐句配音；vo.json 为 [{text, file, dur}]（doc_tts.py 生成）
  sfx/<id>.wav        Mixkit 音效（doc_audio.py sfx 下载）
  music/...           背景音乐（可选，doc_audio.py music 下载 / 分析）

项目的 scenes 文件：
  import doc_core as dc
  dc.init(".", lead=0.15, gap=0.42, tail=7.0, extra={0: 0.5})   # 先 init 再 import *
  from doc_core import *
  def shot_01(u, D): ...      # 每句旁白一个镜头，u = 镜头内时间，D = 镜头时长，返回 1080×1920 RGB
  SHOTS = [shot_01, ...]
  def sfx_events(): return [(mixkit_id, 峰值对齐时刻, 音量), ...]
  if __name__ == "__main__": dc.main(SHOTS, sfx_events)

命令行：--stills 1 2.5 ...（预览帧 -> preview/）  --demo SEC（只渲染前 SEC 秒）
        --music music/xxx.mp3（混入背景音乐）  --out ../成片.mp4  --ratio 3x4（小红书 1080×1440，背景铺满）
"""
import json, math, random, subprocess, sys, wave
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

Image.MAX_IMAGE_PIXELS = None
W, H, FPS = 1080, 1920, 30
SONG = "/System/Library/Fonts/Supplemental/Songti.ttc"   # Songti SC：0 Black / 1 Bold / 6 Regular
BLACK, BOLD, REG = 0, 1, 6
GOLD, GOLD_HI, PAPER, INK, CINNABAR = (217, 178, 106), (246, 220, 154), (242, 230, 207), (14, 10, 7), (184, 52, 40)
TEAL = (12, 26, 28)
XF = 0.40          # 镜头交叉淡化
PUNCT = "，。？！；：、——…"
BRONZE = (120, 170, 150)

# ---- 画幅：--ratio 3x4（小红书 1080×1440）----
# 9:16 画布照常绘制；3:4 时取画布 y 100–1600（1500 高）只缩 4% 铺满全高，背景铺满，
# 左右各约 20 px 用同画面拉伸模糊补齐；HUD 小字仍在顶部；字幕直接画在 3:4 画面上（顶边 1262）。
RATIO34 = "--ratio" in sys.argv and sys.argv[sys.argv.index("--ratio") + 1] == "3x4"
SRC_Y0, SRC_Y1 = 100, 1600
CONTENT = (21, 0, 1038, 1440)
OUT_H = 1440 if RATIO34 else 1920
SUB_Y = 1262 if RATIO34 else 1530
HUD_T, HUD_B = (178, 1560) if RATIO34 else (150, 1880)
HUD_TAG = "DOCUMENTARY"     # HUD 地点小字，项目里改：dc.HUD_TAG = "SANXINGDUI · 广汉"

# ---- 由 init() 设置 ----
R = Path(".")
LINES, SPANS, TOTAL = [], [], 0.0


def init(project=".", lead=0.15, gap=0.42, tail=6.0, extra=None, n_shots=None):
    """读取 vo.json 排时间轴：每句旁白一个镜头（镜头 k 从第 k 句前 0.15 s 开始）"""
    global R, LINES, SPANS, TOTAL
    R = Path(project).resolve()
    vo = json.loads((R / "vo.json").read_text())
    extra = extra or {}
    LINES, t = [], lead
    for i, v in enumerate(vo):
        LINES.append({"text": v["text"], "file": v["file"], "start": t, "dur": v["dur"]})
        t += v["dur"] + gap + extra.get(i, 0)
    TOTAL = t - gap + tail
    n = n_shots or len(LINES)
    SPANS = [(0.0 if k == 0 else S(k) - 0.15, TOTAL if k == n - 1 else S(k + 1) - 0.15 + XF) for k in range(n)]
    return LINES


def S(i):
    return LINES[i]["start"]


def E(i):
    return LINES[i]["start"] + LINES[i]["dur"]


def at_char(i, key):
    """第 i 句里关键词被念出的大致时刻（按字数比例）"""
    txt = LINES[i]["text"]
    return S(i) + LINES[i]["dur"] * txt.index(key) / len(txt)


# ================================================================ 绘图工具
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(1.0, max(0.0, x))
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, x):
    return a + (b - a) * x


def prog(u, a, b, f=None):
    f = f or ease
    return f((u - a) / (b - a)) if b > a else float(u >= a)


@lru_cache(None)
def font(size, idx=BOLD):
    return ImageFont.truetype(SONG, size, index=idx)


@lru_cache(None)
def load(name, tint=None):
    im = Image.open(R / "img" / f"{name}.jpg").convert("RGB")
    if tint == "sepia":  # 老照片：暖褐色调
        im = ImageOps.colorize(ImageOps.autocontrast(im.convert("L"), cutoff=1), black=(18, 11, 6), white=(246, 226, 188))
    elif tint == "paper":  # 线图：做旧纸色
        im = ImageOps.colorize(im.convert("L"), black=(60, 36, 20), white=(236, 222, 194))
    return im


@lru_cache(None)
def blur_bg(name, tint=None, dark=0.38):
    im = load(name, tint)
    bg = cover(im, 1.15)
    bg = bg.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(12)).resize((W, H), Image.BILINEAR)
    return Image.eval(bg, lambda v: int(v * dark))


def cover(im, s=1.0, fx=0.5, fy=0.5, size=(W, H)):
    """裁切铺满 size，s 为放大倍数，(fx,fy) 为焦点（0~1）"""
    ow, oh = size
    iw, ih = im.size
    s = max(1.0, s)
    base = max(ow / iw, oh / ih)
    cw, ch = ow / (base * s), oh / (base * s)
    x0 = max(0.0, min(max(fx * iw - cw / 2, 0), iw - cw))
    y0 = max(0.0, min(max(fy * ih - ch / 2, 0), ih - ch))
    return im.resize(size, Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


@lru_cache(None)
def vignette(strength=0.8):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H * 0.46) / (H * 0.55)) ** 2)
    a = np.clip((d - 0.55) / 0.6, 0, 1) ** 1.6 * 255 * strength
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


@lru_cache(None)
def scrim():
    """上下压暗，保证标签和字幕可读"""
    a = np.zeros(H)
    yy = np.arange(H)
    a += np.clip(1 - yy / 420, 0, 1) * 150
    a += np.clip((yy - 1260) / 560, 0, 1) * 215
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = np.clip(a, 0, 255).astype(np.uint8)[:, None]
    return Image.fromarray(v, "RGBA")


@lru_cache(None)
def grain(k):
    rng = np.random.default_rng(k)
    n = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
    g = np.zeros((H // 2, W // 2, 4), np.uint8)
    g[..., :3] = n[..., None]
    g[..., 3] = 14
    return Image.fromarray(g, "RGBA").resize((W, H), Image.NEAREST)


def over(base, layer):
    base.paste(layer, (0, 0), layer)


@lru_cache(None)
def text_img(text, size, color=PAPER, idx=BOLD, glow=None, shadow=True, spacing=0):
    """把一行文字渲染成带阴影的 RGBA 小图（缓存）"""
    f = font(size, idx)
    widths = [f.getlength(ch) for ch in text]
    tw = int(sum(widths) + spacing * max(0, len(text) - 1))
    asc, desc = f.getmetrics()
    pad = int(size * 0.5)
    im = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    def draw_at(d, fill, dx=0, dy=0):
        x = pad + dx
        for ch, w in zip(text, widths):
            d.text((x, pad + dy), ch, font=f, fill=fill)
            x += w + spacing
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw_at(ImageDraw.Draw(sh), (0, 0, 0, 230), 0, int(size * 0.05))
        im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(size * 0.12)))
    if glow:
        gl = Image.new("RGBA", im.size, (0, 0, 0, 0))
        draw_at(ImageDraw.Draw(gl), glow + (170,))
        im = Image.alpha_composite(im, gl.filter(ImageFilter.GaussianBlur(size * 0.25)))
    draw_at(ImageDraw.Draw(im), color + (255,))
    return im


def put(base, im, cx, cy, alpha=1.0, scale=1.0, anchor="mm"):
    if alpha <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    x = int(cx - im.width / 2) if anchor[0] == "m" else int(cx)
    y = int(cy - im.height / 2) if anchor[1] == "m" else int(cy)
    base.paste(im, (x, y), im)


def label(base, u, text, sub=None, y=230, at=0.3):
    a = prog(u, at, at + 0.5)
    put(base, text_img(f"——  {text}  ——", 40, GOLD_HI, BOLD, spacing=6), W / 2, y + (1 - a) * 18, a)
    if sub:
        put(base, text_img(sub, 30, PAPER, REG, spacing=4), W / 2, y + 62, a * 0.9)


@lru_cache(None)
def frame_border(fw, fh):
    pad = 24
    im = Image.new("RGBA", (fw + pad * 2, fh + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((pad, pad + 18, pad + fw, pad + fh + 18), fill=(0, 0, 0, 200))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(im)
    d.rectangle((pad - 10, pad - 10, pad + fw + 10, pad + fh + 10), outline=GOLD + (40,), width=8)
    d.rectangle((pad - 2, pad - 2, pad + fw + 1, pad + fh + 1), outline=GOLD + (255,), width=3)
    return im


def framed(name, u, D, box=(70, 400, 940, 1020), s=(1.0, 1.12), fx=(0.5, 0.5), fy=(0.5, 0.5), tint=None, src=None, bg=None, bright=1.0):
    """模糊铺底 + 金框主图，框内做推拉摇移"""
    im = src or load(name, tint)
    out = (bg or blur_bg(name, tint)).copy()
    bx, by, bw, bh = box
    iw, ih = im.size
    k = min(bw / iw, bh / ih)
    fw, fh = int(iw * k), int(ih * k)
    p = ease(u / D)
    sc = lerp(*s, p)
    cw, ch = iw / sc, ih / sc
    cx, cy = lerp(*fx, p) * iw, lerp(*fy, p) * ih
    x0 = min(max(cx - cw / 2, 0), iw - cw)
    y0 = min(max(cy - ch / 2, 0), ih - ch)
    fg = im.resize((fw, fh), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
    if bright != 1.0:
        fg = Image.eval(fg, lambda v: min(255, int(v * bright)))
    px, py = bx + (bw - fw) // 2, by + (bh - fh) // 2
    b = frame_border(fw, fh)
    out.paste(b, (px - 24, py - 24), b)
    out.paste(fg, (px, py))
    return out


def particles(base, u, n=40, color=GOLD_HI, seed=1, kind="dust", speed=1.0, area=(0, 0, W, H)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area
    for i in range(n):
        bx, by = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        sz, v, ph = rnd.uniform(2, 6), rnd.uniform(0.5, 1.5) * speed, rnd.uniform(0, 6.28)
        if kind == "ember":  # 余烬：上升、闪烁
            y = (by - u * 90 * v) % (y1 - y0) + y0
            x = bx + math.sin(u * 1.5 + ph) * 25
            a = int(200 * (0.4 + 0.6 * abs(math.sin(u * 3 + ph))))
            c = (255, int(120 + 80 * rnd.random()), 40)
        elif kind == "fall":  # 剥落碎屑
            y = (by + u * 120 * v) % (y1 - y0) + y0
            x = bx + math.sin(u + ph) * 15
            a, c = 170, color
        else:  # 浮尘
            y = (by - u * 25 * v) % (y1 - y0) + y0
            x = bx + math.sin(u * 0.7 + ph) * 30
            a = int(160 * (0.35 + 0.65 * abs(math.sin(u * 1.3 + ph))))
            c = color
        d.ellipse((x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2), fill=c + (a,))
    over(base, lay.filter(ImageFilter.GaussianBlur(1.2)))


def candle(base, u, amt=0.10):
    f = 0.5 + 0.5 * math.sin(u * 7.1) * math.sin(u * 3.3 + 1)
    put(base, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * amt * f))), W / 2, H / 2)


def red_glow(base, u, amt=1.0):
    """画面边缘泛起火光"""
    a = 0.5 + 0.5 * math.sin(u * 4) * math.sin(u * 2.3)
    g = edge_glow()
    if amt * (0.6 + 0.4 * a) < 1:
        g = g.copy(); g.putalpha(g.getchannel("A").point(lambda v: int(v * amt * (0.6 + 0.4 * a))))
    over(base, g)


@lru_cache(None)
def edge_glow():
    y, x = np.mgrid[0:H, 0:W]
    d = np.minimum.reduce([x, W - x, y * 0.7, (H - y) * 0.7]) / 260
    a = np.clip(1 - d, 0, 1) ** 2 * 170
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 0], v[..., 1], v[..., 2], v[..., 3] = 200, 70, 20, a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


@lru_cache(None)
def rock():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
    c = np.clip(1 - d * 1.6, 0, 1)[..., None]
    img = np.array(INK, float) + c * (np.array([52, 34, 20]) - np.array(INK))
    img += np.random.default_rng(1).normal(0, 3, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def bg_dark():
    return Image.new("RGB", (W, H), INK)


@lru_cache(None)
def shine_band():
    """斜向金属高光带（RGBA，宽于画面）"""
    w, h = W * 3, H * 3
    x = np.arange(w)[None, :]
    a = np.exp(-((x - w / 2) / 90.0) ** 2) * 150 + np.exp(-((x - w / 2) / 260.0) ** 2) * 60
    v = np.zeros((h, w, 4), np.uint8)
    v[..., 0], v[..., 1], v[..., 2] = 255, 240, 210
    v[..., 3] = np.clip(a, 0, 255).astype(np.uint8)
    return Image.fromarray(v, "RGBA").rotate(28, Image.BILINEAR)


def shine(im, p):
    """高光从左上扫到右下，p∈[0,1]"""
    if p <= 0 or p >= 1:
        return im
    b = shine_band()
    off = int(lerp(-W * 1.4, W * 1.4, p))
    rgb = im.convert("RGB")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.paste(b, (off - b.width // 2 + W // 2, -b.height // 2 + H // 2), b)
    from PIL import ImageChops
    add = Image.new("RGB", (W, H), (0, 0, 0))
    add.paste(lay.convert("RGB"), (0, 0), lay)
    return ImageChops.screen(rgb, add)


def flash(im, v, amt=0.8, color=(255, 246, 228)):
    if v < 0 or v > 0.4:
        return im
    k = v / 0.03 if v < 0.03 else max(0.0, 1 - (v - 0.03) / 0.37)
    return Image.blend(im, Image.new("RGB", im.size, color), k * amt) if k > 0.01 else im


def punch(u, a, dur=0.45):
    """切入时的镜头冲击：先放大后回弹"""
    v = (u - a) / dur
    return 1.0 + 0.10 * math.exp(-v * 4) if v >= 0 else 1.0


@lru_cache(None)
def sepia(name):
    return ImageOps.colorize(ImageOps.autocontrast(load(name).convert("L"), cutoff=1), black=(20, 14, 8), white=(240, 222, 186))


@lru_cache(None)
def seal_img(text, size=210):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((6, 6, size - 6, size - 6), 18, outline=CINNABAR + (240,), width=12)
    f = font(int(size * 0.36), BLACK)
    for k, ch in enumerate(text):
        d.text((size / 2, size * (0.3 + 0.4 * k)), ch, font=f, fill=CINNABAR + (240,), anchor="mm")
    return im.rotate(-12, Image.BICUBIC, expand=True)


def blur_from_img(im):
    return im.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)


@lru_cache(None)
def cut(name):
    im = Image.open(R / "cut" / f"{name}.png").convert("RGBA")
    return im.crop(im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox())


@lru_cache(None)
def cut_sized(name, h):
    im = cut(name)
    return im.resize((max(1, int(im.width * h / im.height)), h), Image.LANCZOS)


@lru_cache(None)
def rim_glow(name, h, color=(255, 196, 110), blur=26):
    im = cut_sized(name, h)
    pad = blur * 3
    a = Image.new("L", (im.width + pad * 2, im.height + pad * 2), 0)
    a.paste(im.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(blur))
    g = Image.new("RGBA", a.size, color + (0,))
    g.putalpha(a.point(lambda v: min(255, int(v * 1.5))))
    return g


def lit(im, k):
    """器物亮度（0=全黑剪影）"""
    if k >= 0.999:
        return im
    rgb = Image.eval(im.convert("RGB"), lambda v: int(v * k))
    rgb.putalpha(im.getchannel("A"))
    return rgb


def spot(im, y_frac):
    """自上而下的光：y_frac 以上被照亮"""
    w, h = im.size
    g = np.clip((y_frac * h - np.arange(h)) / (h * 0.25) + 0.15, 0.08, 1.0)[:, None]
    arr = np.array(im).astype(float)
    arr[..., :3] *= g[..., None]
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def find_coeffs(dst, src):
    A = []
    for (x, y), (X, Y) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -X * x, -X * y])
        A.append([0, 0, 0, x, y, 1, -Y * x, -Y * y])
    return np.linalg.solve(np.array(A, float), np.array(src, float).reshape(8))


def persp(im, ry=0.0, rx=0.0, f=1400.0):
    """绕 y / x 轴旋转的透视（度）"""
    w, h = im.size
    cx, cy = w / 2, h / 2
    a, b = math.radians(ry), math.radians(rx)
    pts = []
    for x, y in [(0, 0), (w, 0), (w, h), (0, h)]:
        X, Y, Z = x - cx, y - cy, 0.0
        X, Z = X * math.cos(a) + Z * math.sin(a), -X * math.sin(a) + Z * math.cos(a)
        Y, Z = Y * math.cos(b) - Z * math.sin(b), Y * math.sin(b) + Z * math.cos(b)
        s = f / (f + Z)
        pts.append((cx + X * s, cy + Y * s))
    minx, miny = min(p[0] for p in pts), min(p[1] for p in pts)
    pts = [(x - minx, y - miny) for x, y in pts]
    ow, oh = int(max(p[0] for p in pts)) + 1, int(max(p[1] for p in pts)) + 1
    c = find_coeffs(pts, [(0, 0), (w, 0), (w, h), (0, h)])
    return im.transform((ow, oh), Image.PERSPECTIVE, tuple(c), Image.BICUBIC)


@lru_cache(None)
def bg_grad():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.42) / H) ** 2)
    c = np.clip(1 - d * 1.7, 0, 1)[..., None]
    img = np.array([4, 6, 7], float) + c * (np.array([22, 44, 44]) - np.array([4, 6, 7]))
    img += np.random.default_rng(2).normal(0, 2.2, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def rings(base, u, cx=W / 2, cy=760, a=1.0, spin=6.0):
    """青铜纹样感的同心刻度环，缓慢旋转"""
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k, r in enumerate([300, 380, 470, 590]):
        al = int((60 - k * 10) * a)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD + (al,), width=2)
        n = 72 if k % 2 == 0 else 36
        rot = math.radians(u * spin * (1 if k % 2 else -1) * (1 + k * 0.3))
        for i in range(n):
            ang = rot + i * 2 * math.pi / n
            l = 14 if i % 6 == 0 else 6
            d.line((cx + math.cos(ang) * r, cy + math.sin(ang) * r, cx + math.cos(ang) * (r + l), cy + math.sin(ang) * (r + l)),
                   fill=GOLD + (int(al * 1.6),), width=2)
    over(base, lay)


def hud(base, u, a=1.0, tag=None):
    """四角框线 + 扫描线 + 顶部小字（地点标签与计时）"""
    if a <= 0.01:
        return
    tag = tag or HUD_TAG
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = GOLD + (int(170 * a),)
    for x, y, sx, sy in [(50, HUD_T, 1, 1), (W - 50, HUD_T, -1, 1), (50, HUD_B, 1, -1), (W - 50, HUD_B, -1, -1)]:
        d.line((x, y, x + 60 * sx, y), fill=c, width=3)
        d.line((x, y, x, y + 60 * sy), fill=c, width=3)
    yy = HUD_T + ((u * 160) % (HUD_B - HUD_T))
    d.line((50, yy, W - 50, yy), fill=(160, 230, 210, int(26 * a)), width=2)
    over(base, lay)
    ty = HUD_T - 40 if RATIO34 else HUD_T - 46
    put(base, text_img(tag, 22, GOLD, REG, shadow=False, spacing=4), 70, ty, a * 0.8, anchor="lt")
    put(base, text_img(f"T+{u:05.2f}", 22, GOLD, REG, shadow=False), W - 220, ty, a * 0.8, anchor="lt")


def god_rays2(base, u, cx, cy, a, color=(255, 214, 150)):
    if a <= 0.01:
        return base
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(16):
        ang = math.radians(62 + k * 3.6 + math.sin(u * 0.5 + k * 1.3) * 1.4)
        w_ = 0.012 + 0.01 * ((k * 7) % 3)
        d.polygon([(cx, cy), (cx + math.cos(ang) * 2600, cy + math.sin(ang) * 2600),
                   (cx + math.cos(ang + w_) * 2600, cy + math.sin(ang + w_) * 2600)], fill=color + (int(40 * a),))
    add = Image.new("RGB", (W, H), (0, 0, 0))
    add.paste(lay.convert("RGB"), (0, 0), lay.filter(ImageFilter.GaussianBlur(16)))
    return ImageChops.screen(base.convert("RGB"), add)


def glass(base, box, a=1.0, radius=28, tint=(255, 255, 255), border=GOLD):
    """磨砂玻璃卡片：取背后画面模糊 + 提亮 + 金边 + 顶部高光"""
    if a <= 0.01:
        return
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W, x1), min(H, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return
    reg = base.crop((x0, y0, x1, y1)).resize(((x1 - x0) // 4 + 1, (y1 - y0) // 4 + 1)).filter(ImageFilter.GaussianBlur(5)).resize((x1 - x0, y1 - y0))
    reg = Image.blend(reg.convert("RGB"), Image.new("RGB", reg.size, (30, 46, 46)), 0.45)
    m = Image.new("L", reg.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, reg.width - 1, reg.height - 1), radius, fill=int(255 * a))
    base.paste(reg, (x0, y0), m)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0, y0, x1, y1), radius, outline=border + (int(200 * a),), width=2)
    d.line((x0 + radius, y0 + 2, x1 - radius, y0 + 2), fill=(255, 255, 255, int(60 * a)), width=2)
    over(base, lay)


@lru_cache(None)
def metal_text(text, size, spacing=0, palette="gold"):
    t = text_img(text, size, (255, 255, 255), BLACK, shadow=False, spacing=spacing)
    w, h = t.size
    yy = np.linspace(0, 1, h)[:, None]
    if palette == "gold":
        top, mid, bot = np.array([255, 244, 205]), np.array([205, 150, 60]), np.array([255, 214, 130])
    else:
        top, mid, bot = np.array([215, 245, 235]), np.array([70, 120, 105]), np.array([170, 215, 200])
    g = np.where(yy < 0.55, top + (mid - top) * (yy / 0.55), mid + (bot - mid) * ((yy - 0.55) / 0.45))
    arr = np.broadcast_to(g[:, None, :] if g.ndim == 2 else g, (h, w, 3)).astype(np.uint8)
    out = Image.fromarray(arr.copy(), "RGB").convert("RGBA")
    out.putalpha(t.getchannel("A"))
    sh = text_img(text, size, (0, 0, 0), BLACK, shadow=True, glow=(246, 180, 90) if palette == "gold" else (120, 220, 190), spacing=spacing)
    base = Image.new("RGBA", sh.size, (0, 0, 0, 0))
    base.alpha_composite(sh)
    base.alpha_composite(out)
    return base


def metal_put(base, text, size, cx, cy, a, shine_p=None, spacing=0, scale=1.0, palette="gold"):
    im = metal_text(text, size, spacing, palette)
    if shine_p is not None and 0 < shine_p < 1:
        im = im.copy()
        w, h = im.size
        x = np.arange(w)[None, :] - (shine_p * (w + h) - h)
        band = np.clip(1 - np.abs(x - np.arange(h)[:, None] * 0.5) / 40, 0, 1)
        arr = np.array(im).astype(float)
        arr[..., :3] += band[..., None] * 140
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    put(base, im, cx, cy, a, scale)


def chars_in(base, text, size, cx, cy, u, at, step=0.07, color=PAPER, idx=BLACK, spacing=6):
    """逐字从模糊放大到清晰"""
    f = font(size, idx)
    ws = [f.getlength(c) + spacing for c in text]
    x = cx - sum(ws) / 2
    for c, w_ in zip(text, ws):
        k = prog(u, at, at + 0.35)
        if k > 0:
            ti = text_img(c, size, color, idx)
            if k < 1:
                ti = ti.filter(ImageFilter.GaussianBlur((1 - k) * 10))
            put(base, ti, x + w_ / 2, cy + (1 - k) * 30, k, 1.4 - 0.4 * k)
        x += w_
        at += step


@lru_cache(None)
def big_char(ch, size, color=(238, 228, 206)):
    """超大背景字：竖向渐变 + 柔光"""
    t = text_img(ch, size, (255, 255, 255), BLACK, shadow=False)
    w, h = t.size
    yy = np.linspace(0, 1, h)[:, None, None]
    top, bot = np.array(color, float), np.array(color, float) * 0.62
    g = np.broadcast_to(top + (bot - top) * yy, (h, w, 3)).astype(np.uint8)
    out = Image.fromarray(g.copy(), "RGB").convert("RGBA")
    out.putalpha(t.getchannel("A"))
    gl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl.putalpha(t.getchannel("A").filter(ImageFilter.GaussianBlur(size * 0.12)).point(lambda v: v // 2))
    gl = Image.composite(Image.new("RGBA", (w, h), (255, 200, 120, 255)), gl, gl.getchannel("A"))
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base.alpha_composite(gl)
    base.alpha_composite(out)
    return base


def type_behind(base, text, size, cx, cy, u, t0, step=0.13, cursor_until=None, alpha=0.95, spacing=0.02):
    """打字机效果：逐字弹出 + 闪烁光标（在主体之前绘制，即位于主体背后）"""
    f = font(size, BLACK)
    ws = [f.getlength(c) * (1 + spacing) for c in text]
    x = cx - sum(ws) / 2
    n_typed = 0
    for i, (c, w_) in enumerate(zip(text, ws)):
        ti = t0 + i * step
        k = prog(u, ti, ti + 0.12, lambda z: min(1, max(0, z)))
        if k > 0:
            n_typed = i + 1
            put(base, big_char(c, size), x + w_ / 2, cy, alpha * k, 1.18 - 0.18 * k)
        x += w_
    end = t0 + len(text) * step
    if u >= t0 - 0.3 and u < (cursor_until if cursor_until is not None else end + 0.9):
        cx_ = cx - sum(ws) / 2 + sum(ws[:n_typed]) + size * 0.06
        if int(u * 2.6) % 2 == 0 or u < end:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).rectangle((cx_, cy - size * 0.42, cx_ + size * 0.07, cy + size * 0.42), fill=(255, 220, 150, 235))
            over(base, lay)


def pulse_dot(base, x, y, u, a=1.0, color=GOLD_HI):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for k in range(2):
        ph = (u * 1.2 + k * 0.5) % 1
        r = 10 + ph * 46
        d.ellipse((x - r, y - r, x + r, y + r), outline=color + (int(220 * (1 - ph) * a),), width=3)
    d.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color + (int(255 * a),))
    over(base, lay)


def leader(base, p, pts, color=GOLD_HI):
    """折线引线，按进度绘制"""
    if p <= 0:
        return
    total = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    left = total * p
    for i in range(len(pts) - 1):
        seg = math.dist(pts[i], pts[i + 1])
        if left <= 0:
            break
        k = min(1, left / seg)
        d.line((pts[i], (lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k))), fill=color + (255,), width=3)
        left -= seg
    over(base, lay)


def float_obj(base, name, h, cx, cy, u, a=1.0, scale=1.0, ry=0.0, light=1.0, rim=True, rim_a=1.0, bob=8.0):
    """悬浮器物：轮廓光 + 轻微浮动 + 透视"""
    if a <= 0.01:
        return
    hh = int(h * scale)
    obj = cut_sized(name, hh)
    obj = lit(obj, light)
    if abs(ry) > 0.2:
        obj = persp(obj, ry)
    yb = math.sin(u * 1.3) * bob
    if rim:
        g = rim_glow(name, hh)
        put(base, g, cx, cy + yb, a * rim_a * (0.75 + 0.25 * math.sin(u * 2.2)))
    put(base, obj, cx, cy + yb, a)


@lru_cache(None)
def round_thumb(name, fx, fy, size=260):
    pic = cover(load(name), 1.0, fx, fy, (size, size)).convert("RGBA")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size, size), fill=255)
    pic.putalpha(m)
    ring = Image.new("RGBA", (size + 30, size + 30), (0, 0, 0, 0))
    g = Image.new("RGBA", ring.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((4, 4, size + 26, size + 26), outline=GOLD_HI + (255,), width=10)
    ring = Image.alpha_composite(ring, g.filter(ImageFilter.GaussianBlur(8)))
    ImageDraw.Draw(ring).ellipse((12, 12, size + 18, size + 18), outline=GOLD_HI + (255,), width=4)
    ring.paste(pic, (15, 15), pic)
    return ring


@lru_cache(None)
def photo_card(name, title, fx, fy, w=400, h=560):
    pic = cover(load(name), 1.0, fx, fy, (w, h - 90)).convert("RGBA")
    card = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 34, 20 + w, 34 + h), 26, fill=(0, 0, 0, 200))
    card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(14)))
    body = Image.new("RGBA", (w, h), (18, 30, 30, 255))
    body.paste(pic, (0, 0))
    d = ImageDraw.Draw(body)
    d.text((w / 2, h - 46), title, font=font(52, BLACK), fill=GOLD_HI, anchor="mm")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=255)
    body.putalpha(m)
    card.paste(body, (20, 20), body)
    ImageDraw.Draw(card).rounded_rectangle((20, 20, 20 + w - 1, 20 + h - 1), 26, outline=GOLD + (255,), width=3)
    return card


def lt(i, key):
    """第 i 句里关键词在本镜头内的局部时刻"""
    return at_char(i, key) - SPANS[i][0]


def stage(u, seed=0, rings_a=0.7, cy=860, tag="SANXINGDUI · 广汉"):
    im = bg_grad().copy()
    rings(im, u + seed, cy=cy, a=rings_a)
    return im


def finish(im, u, seed=0, vig=0.75):
    hud(im, u + seed)
    over(im, vignette(vig))
    return im


def cover_box(iw, ih, w, h, s, fx, fy):
    s = max(1.0, s)
    base = max(w / iw, h / ih)
    cw, ch = w / (base * s), h / (base * s)
    x0 = max(0.0, min(max(fx * iw - cw / 2, 0), iw - cw))
    y0 = max(0.0, min(max(fy * ih - ch / 2, 0), ih - ch))
    return x0, y0, base * s


def card_img(name, w, h, s=1.0, fx=0.5, fy=0.5, radius=26, src=None, dark=1.0, title=None):
    """照片卡：圆角 + 金边 + 投影（返回 RGBA，含 20px 外边距）"""
    im = src or load(name)
    pic = cover(im, s, fx, fy, (w, h))
    if dark != 1.0:
        pic = Image.eval(pic, lambda v: int(v * dark))
    card = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 32, 20 + w, 32 + h), radius, fill=(0, 0, 0, 210))
    card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(14)))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    card.paste(pic, (20, 20), m)
    d = ImageDraw.Draw(card)
    if title:
        d.rounded_rectangle((20, 20 + h - 80, 20 + w, 20 + h), radius, fill=(10, 18, 18, 200))
        d.rectangle((20, 20 + h - 80, 20 + w, 20 + h - 60), fill=(10, 18, 18, 200))
        d.text((20 + w / 2, 20 + h - 40), title, font=font(42, BLACK), fill=GOLD_HI, anchor="mm")
    d.rounded_rectangle((20, 20, 20 + w - 1, 20 + h - 1), radius, outline=GOLD + (255,), width=3)
    return card


@lru_cache(None)
def card_cached(name, w, h, s=1.0, fx=0.5, fy=0.5, dark=1.0, title=None, sepia_=False):
    return card_img(name, w, h, s, fx, fy, src=sepia(name) if sepia_ else None, dark=dark, title=title)


def put_card(base, card, cx, cy, a=1.0, ry=0.0, rot=0.0, scale=1.0):
    if a <= 0.01:
        return
    c = persp(card, ry) if abs(ry) > 0.2 else card
    if abs(rot) > 0.1:
        c = c.rotate(rot, Image.BICUBIC, expand=True)
    put(base, c, cx, cy, a, scale)


def chip(base, text, x, y, a, size=40, color=GOLD_HI):
    """玻璃小标签"""
    if a <= 0.01:
        return
    w = int(font(size, BLACK).getlength(text)) + 56
    yy = y + (1 - a) * 24
    glass(base, (x - w / 2, yy - size * 0.95, x + w / 2, yy + size * 0.95), a, radius=int(size * 0.95))
    put(base, text_img(text, size, color, BLACK, shadow=False), x, yy, a)


def stat_card(base, x, y, w, h, title, sub, a):
    if a <= 0.01:
        return
    xx = x + (1 - a) * 120
    glass(base, (xx - w / 2, y - h / 2, xx + w / 2, y + h / 2), a)
    put(base, text_img(title, 48, GOLD_HI, BLACK, shadow=False), xx, y - 22, a)
    put(base, text_img(sub, 28, PAPER, REG, shadow=False), xx, y + 32, a)


def rise_obj(base, name, h, cx, cy_end, u, t0=0.0, dur=1.4, rim_color=(255, 196, 110), bob=6):
    """抠图自下方升起，顶光由暗到亮"""
    k = prog(u, t0, t0 + dur, ease_io)
    obj = cut_sized(name, h)
    obj = spot(obj, lerp(0.0, 1.3, prog(u, t0 + 0.2, t0 + dur + 0.6, ease_io)))
    cy = lerp(cy_end + 500, cy_end, k) + math.sin(u * 1.2) * bob
    put(base, rim_glow(name, h, rim_color), cx, cy, k * 0.8)
    put(base, obj, cx, cy, min(1, k * 1.6))
    return cy


def pit_mouth(base, a, cy=1300, w=760, glow=True):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.polygon([(W / 2 - w / 2, cy - 60), (W / 2 + w / 2, cy - 60), (W / 2 + w / 2 - 70, cy + 120), (W / 2 - w / 2 + 70, cy + 120)],
              fill=(6, 8, 8, int(230 * a)), outline=GOLD_HI + (int(255 * a),))
    over(base, lay)
    if glow:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((W / 2 - w / 2, cy - 90, W / 2 + w / 2, cy - 30), fill=(255, 200, 120, int(120 * a)))
        over(base, g.filter(ImageFilter.GaussianBlur(30)))


def sub_chunks(text, maxw=940):
    """单行字幕切分：先按逗号/句号分句，句末必断；分句过宽再按顿号或正中断开；过短的片段并入相邻片段"""
    f = font(54, BOLD)
    clean = lambda x: x.rstrip("，。；：、").replace("——", "")
    width = lambda x: f.getlength(clean(x)) + 3 * len(x)
    parts, cur = [], ""
    for ch in text:
        cur += ch
        if ch in "，。？！；：":
            parts.append(cur); cur = ""
    if cur:
        parts.append(cur)
    fine = []
    for p_ in parts:
        if width(p_) <= maxw:
            fine.append(p_); continue
        segs, c = [], ""
        for ch in p_:
            c += ch
            if ch == "、":
                segs.append(c); c = ""
        if c:
            segs.append(c)
        cur = ""
        for sg in segs:
            if cur and width(cur + sg) > maxw:
                fine.append(cur); cur = sg
            else:
                cur += sg
        while width(cur) > maxw:
            fine.append(cur[: len(cur) // 2]); cur = cur[len(cur) // 2:]
        fine.append(cur)
    chunks, cur = [], ""
    for p_ in fine:
        tiny = len(clean(cur)) <= 3 or len(clean(p_)) <= 3
        if cur and (cur[-1] in "。？！；" or width(cur + p_) > (maxw + 40 if tiny else maxw)):
            chunks.append(cur); cur = p_
        else:
            cur += p_
    if cur:
        chunks.append(cur)
    return [clean(c) for c in chunks if clean(c)]


@lru_cache(None)
def sub_img(text):
    return text_img(text, 54, PAPER, BOLD, spacing=3)


@lru_cache(None)
def sub_timing(i):
    """第 i 句的单行字幕及各自起止时间（按字数比例）"""
    l = LINES[i]
    ch = sub_chunks(l["text"])
    n = [max(1, len([c for c in x if c not in PUNCT])) for x in ch]
    tot = sum(n)
    out, t0 = [], l["start"]
    for c, k in zip(ch, n):
        d = l["dur"] * k / tot
        out.append((c, t0, t0 + d)); t0 += d
    return out


def draw_subs(frame, t):
    for i, l in enumerate(LINES):
        if not (l["start"] - 0.05 <= t < l["start"] + l["dur"] + 0.35):
            continue
        segs = sub_timing(i)
        for j, (c, a0, a1) in enumerate(segs):
            end = a1 if j < len(segs) - 1 else a1 + 0.35
            if a0 - 0.05 <= t < end:
                a = min(1, (t - a0 + 0.05) / 0.12, (end - t) / 0.12)
                put(frame, sub_img(c), W / 2, SUB_Y, a, 1.0 + 0.04 * (1 - min(1, (t - a0 + 0.05) / 0.12)), anchor="mt")


@lru_cache(None)
def sfx(id_):
    import wave
    with wave.open(str(R / "sfx" / f"{id_}.wav")) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return x / (np.abs(x).max() + 1e-9), int(np.argmax(np.abs(x)))


# ================================================================ 合成一帧
def render_frame(n, shots):
    t = n / FPS
    frame = None
    for k, (a, b) in enumerate(SPANS):
        if a <= t < b:
            img = shots[k](t - a, b - a).convert("RGB")
            fi = 1.0 if k == 0 else min(1, (t - a) / XF)
            frame = img if frame is None else Image.blend(frame, img, ease(fi))
    frame = frame.convert("RGB")
    over(frame, scrim())
    if RATIO34:
        frame = to_34(frame)
        draw_subs(frame, t)
        over(frame, grain(n % 4).crop((0, 0, W, OUT_H)))
        return frame.tobytes()
    draw_subs(frame, t)
    over(frame, grain(n % 4))
    return frame.tobytes()


@lru_cache(None)
def _feather34():
    """左右两侧 24 px 羽化，上下不羽化（背景铺满）"""
    x, y, w, h = CONTENT
    m = np.ones((h, w), np.float32)
    r = np.arange(24) / 24
    m[:, :24] *= r[None, :]; m[:, -24:] *= r[::-1][None, :]
    return Image.fromarray((m * 255).astype(np.uint8))


@lru_cache(None)
def _scrim34():
    a = np.clip((np.arange(OUT_H) - 1120) / 220, 0, 1) * 210
    v = np.zeros((OUT_H, W, 4), np.uint8); v[..., 3] = a.astype(np.uint8)[:, None]
    return Image.fromarray(v, "RGBA")


def to_34(frame):
    """9:16 画布 -> 3:4：取 y 100–1600 只缩 4% 铺满全高，左右窄缝用同画面拉伸模糊补齐"""
    x, y, w, h = CONTENT
    region = frame.crop((0, SRC_Y0, W, SRC_Y1))
    bg = region.resize((W // 8, OUT_H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3)).resize((W, OUT_H), Image.BILINEAR)
    bg.paste(region.resize((w, h), Image.LANCZOS), (x, y), _feather34())
    over(bg, _scrim34())
    return bg


_SHOTS = None


def _worker(n):
    return render_frame(n, _SHOTS)


# ================================================================ 音频：人声 + 音效 + 背景音乐
def read_wav(p):
    with wave.open(str(p)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x if w.getnchannels() == 1 else x.reshape(-1, w.getnchannels()).mean(1)


def build_audio(end, events, music=None, music_db=-13.0, duck_db=6.0, sr=44100):
    """人声归一 → 音效按峰值对齐并在旁白处让位 → （可选）背景音乐削人声频段 + 自动压低 → 软限幅"""
    voice = np.zeros(int(end * sr) + sr, np.float32)
    for l in LINES:
        if l["start"] < end:
            x = read_wav(R / l["file"]); i = int(l["start"] * sr); voice[i:i + len(x)] += x[: len(voice) - i]
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.85
    act = (np.abs(voice) > 0.02).astype(np.float32)
    k = sr // 5
    act = np.clip(np.convolve(act, np.ones(k) / k, mode="same") * 3, 0, 1)
    fx = np.zeros_like(voice)
    for id_, t, g in events:
        x, pk = sfx(id_)
        i = int(t * sr) - pk
        a, b = max(0, i), min(len(fx), i + len(x))
        if b > a:
            fx[a:b] += x[a - i: b - i] * g
    fx *= 1 - 0.37 * act          # 旁白处音效让位约 4 dB
    mix = voice + fx * 0.8
    if music:
        import imageio_ffmpeg
        eq = R / "music" / "_eq.wav"
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(music), "-af",
                        "highpass=f=45,equalizer=f=2500:t=q:w=1.2:g=-5,equalizer=f=1200:t=q:w=1:g=-3", "-ac", "1", "-ar", str(sr), str(eq)], check=True)
        m = read_wav(eq)[: len(mix)]
        m = np.pad(m, (0, max(0, len(mix) - len(m))))
        rms = lambda a: np.sqrt((a[np.abs(a) > 1e-4] ** 2).mean())
        m *= rms(voice) / rms(m) * 10 ** (music_db / 20)
        k2 = int(0.4 * sr)
        m *= 1 - (1 - 10 ** (-duck_db / 20)) * np.convolve(act, np.ones(k2) / k2, mode="same")
        tt = np.arange(len(m)) / sr
        m *= np.clip(tt / 2.0, 0, 1) * np.clip((end - tt) / 4.0, 0, 1)
        mix = mix + m
    mix = np.tanh(mix * 1.05) / np.tanh(1.05)
    out = R / "audio_mix.wav"
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((mix[: int(end * sr)] * 32767).astype(np.int16).tobytes())
    return out


def _arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main(shots, sfx_events=lambda: []):
    """--stills t1 t2 … | [--demo SEC] [--music path] [--out path] [--crf 20]"""
    global _SHOTS
    import imageio_ffmpeg
    from multiprocessing import Pool
    _SHOTS = shots
    assert len(shots) == len(SPANS), f"镜头数 {len(shots)} ≠ 旁白句数 {len(SPANS)}"
    if "--stills" in sys.argv:
        (R / "preview").mkdir(exist_ok=True)
        for s in [a for a in sys.argv[sys.argv.index("--stills") + 1:] if not a.startswith("--")]:
            Image.frombytes("RGB", (W, OUT_H), render_frame(int(float(s) * FPS), shots)).resize((540, OUT_H // 2)).save(R / "preview" / f"t{float(s):06.1f}{'_34' if RATIO34 else ''}.jpg", quality=84)
        print("stills ->", R / "preview"); return
    end = float(_arg("--demo", TOTAL))
    audio = build_audio(end, sfx_events(), _arg("--music"))
    out = Path(_arg("--out", R.parent / f"{R.name}{'_3x4' if RATIO34 else ''}{'_样片' if '--demo' in sys.argv else ''}.mp4"))
    N = int(end * FPS)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{OUT_H}", "-r", str(FPS),
           "-i", "-", "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", _arg("--crf", "20"), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-t", f"{end:.3f}", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(8, initializer=_set_shots, initargs=(shots,)) as pool:
        for k, buf in enumerate(pool.imap(_worker, range(N), chunksize=4)):
            proc.stdin.write(buf)
            if k % 900 == 0:
                print(f"{k}/{N}", flush=True)
    proc.stdin.close(); proc.wait()
    print("done", out, f"{end:.1f}s")


def _set_shots(shots):
    global _SHOTS
    _SHOTS = shots
