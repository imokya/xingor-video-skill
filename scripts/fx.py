"""Drawing helpers on top of skia-python."""
import math, random
import numpy as np
import skia

W, H = 1920, 1080

# ---- palette: "NEON LAB" ----
LIME = (198, 255, 46)
BLUE = (64, 120, 255)
VIOLET = (150, 92, 255)
INK = (5, 7, 13)
WHITE = (255, 255, 255)
GREY = (150, 158, 175)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def P(t, t0, d=0.4):
    """normalized progress of an animation starting at t0 lasting d."""
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def eo(x):  # ease out cubic
    x = clamp(x); return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def eob(x, s=1.9):  # ease out back
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def eexp(x):
    x = clamp(x); return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def window(t, t0, t1, fi=0.25, fo=0.25):
    """1 inside [t0,t1] with fades."""
    return clamp(min((t - t0) / fi if fi else 1, (t1 - t) / fo if fo else 1))


def lerp(a, b, x):
    return a + (b - a) * x


def C(rgb, a=1.0):
    return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


def CI(rgb, a=1.0):
    return skia.ColorSetARGB(int(clamp(a) * 255), *rgb)


_fonts = {}
FAM = {
    'heavy': ('Lantinghei SC', 800, False),
    'bold': ('PingFang SC', 600, False),
    'med': ('PingFang SC', 500, False),
    'reg': ('PingFang SC', 400, False),
    'disp': ('Avenir Next Condensed', 800, True),
    'dispu': ('Avenir Next Condensed', 800, False),
    'mono': ('Menlo', 700, False),
    'monor': ('Menlo', 400, False),
    'num': ('DIN Condensed', 700, False),
}


def F(kind, size):
    key = (kind, int(size * 4))
    f = _fonts.get(key)
    if f is None:
        fam, w, it = FAM[kind]
        tf = skia.Typeface(fam, skia.FontStyle(w, skia.FontStyle.kNormal_Width,
                                                skia.FontStyle.kItalic_Slant if it else skia.FontStyle.kUpright_Slant))
        f = skia.Font(tf, size)
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        _fonts[key] = f
    return f


def paint(rgb=WHITE, a=1.0, stroke=0, blur=0, shader=None):
    p = skia.Paint(AntiAlias=True)
    p.setColor4f(C(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
    return p


NOCJK = {'Menlo', 'DIN Condensed', 'Avenir Next Condensed'}


def runs(s, f):
    if f.getTypeface().getFamilyName() not in NOCJK or all(ord(ch) < 0x2000 for ch in s):
        return [(s, f)]
    fb = F('bold', f.getSize() * 0.95)
    out = []
    for ch in s:
        ff = f if ord(ch) < 0x2000 else fb
        if out and out[-1][1] is ff:
            out[-1] = (out[-1][0] + ch, ff)
        else:
            out.append((ch, ff))
    return out


def tw(s, f):
    return sum(ff.measureText(r) for r, ff in runs(s, f))


def text(c, s, x, y, f, rgb=WHITE, a=1.0, align='l', glow=0, glow_rgb=None, stroke=0, spacing=0):
    if a <= 0.003 or not s:
        return 0
    rs = runs(s, f)
    if spacing:
        items = [(ch, ff) for r, ff in rs for ch in r]
        w = sum(ff.measureText(ch) for ch, ff in items) + spacing * (len(items) - 1)
    else:
        items = rs
        w = sum(ff.measureText(r) for r, ff in rs)
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w

    def _draw(p):
        xx = x
        for r, ff in items:
            c.drawString(r, xx, y, ff, p); xx += ff.measureText(r) + spacing
    if glow:
        _draw(paint(glow_rgb or rgb, a * 0.8, blur=glow))
    if stroke:
        _draw(paint(rgb, a, stroke=stroke))
    else:
        _draw(paint(rgb, a))
    return w


def rrect(c, x, y, w, h, r, rgb=WHITE, a=1.0, stroke=0, blur=0, shader=None):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(rgb, a, stroke, blur, shader))


def glass(c, x, y, w, h, r=18, a=1.0, edge=LIME, edge_a=0.35):
    """dark translucent card with gradient edge."""
    if a <= 0: return
    rrect(c, x, y + 14, w, h, r, (0, 0, 0), 0.45 * a, blur=24)
    sh = skia.GradientShader.MakeLinear([(x, y), (x, y + h)], [CI((24, 30, 46), 0.86 * a), CI((10, 13, 22), 0.9 * a)])
    rrect(c, x, y, w, h, r, shader=sh)
    sh2 = skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [CI(edge, edge_a * a), CI(WHITE, 0.06 * a), CI(edge, 0.12 * a)])
    rrect(c, x + .5, y + .5, w - 1, h - 1, r, stroke=1.5, shader=sh2)


def line(c, x0, y0, x1, y1, rgb=WHITE, a=1.0, w=2, blur=0):
    c.drawLine(x0, y0, x1, y1, paint(rgb, a, stroke=w, blur=blur))


def circle(c, x, y, r, rgb=WHITE, a=1.0, stroke=0, blur=0):
    c.drawCircle(x, y, r, paint(rgb, a, stroke, blur))


def partial_path(path, t0, t1):
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    dst = skia.Path()
    if t1 > t0:
        pm.getSegment(L * t0, L * t1, dst, True)
    return dst


def path_pos(path, t):
    pm = skia.PathMeasure(path, False)
    return pm.getPosTan(pm.getLength() * clamp(t))


def glow_path(c, path, rgb=LIME, a=1.0, w=3, glow=10):
    c.drawPath(path, paint(rgb, a * 0.7, stroke=w * 2.5, blur=glow))
    c.drawPath(path, paint(rgb, a, stroke=w))


def corners(c, x, y, w, h, L=28, rgb=LIME, a=1.0, sw=3):
    p = skia.Path()
    for (px, py, dx, dy) in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]:
        p.moveTo(px + dx * L, py); p.lineTo(px, py); p.lineTo(px, py + dy * L)
    c.drawPath(p, paint(rgb, a, stroke=sw))


def chip(c, s, x, y, f, rgb=LIME, a=1.0, fg=INK, pad=14, h=None, align='l', fill=True):
    w = tw(s, f) + pad * 2
    h = h or f.getSize() * 1.55
    if align == 'c': x -= w / 2
    if align == 'r': x -= w
    if fill:
        rrect(c, x, y, w, h, 6, rgb, a)
        text(c, s, x + pad, y + h * 0.5 + f.getSize() * 0.36, f, fg, a)
    else:
        rrect(c, x, y, w, h, 6, rgb, a, stroke=2)
        text(c, s, x + pad, y + h * 0.5 + f.getSize() * 0.36, f, rgb, a)
    return w


def wave_bars(c, x, y, w, h, t, n=48, rgb=LIME, a=1.0, seed=0, amp=None):
    bw = w / n
    for i in range(n):
        v = 0.5 + 0.5 * math.sin(t * 9 + i * 0.7 + seed) * math.sin(t * 5.3 + i * 0.31 + seed * 2)
        env = math.sin(math.pi * (i + .5) / n) ** 0.6
        v = (0.15 + 0.85 * abs(v)) * env * (amp if amp is not None else 1)
        bh = max(3, h * v)
        rrect(c, x + i * bw + bw * .2, y - bh / 2, bw * .6, bh, bw * .3, rgb, a)


def typed(s, t, t0, cps=18):
    n = int(max(0, (t - t0) * cps))
    return s[:n]


class Particles:
    def __init__(self, n=120, seed=3):
        r = np.random.RandomState(seed)
        self.x = r.rand(n) * W; self.y = r.rand(n) * H
        self.vx = (r.rand(n) - .5) * 20; self.vy = -r.rand(n) * 30 - 6
        self.s = r.rand(n) * 2.2 + .6; self.ph = r.rand(n) * 6.28
        self.col = r.rand(n)

    def draw(self, c, t, a=1.0):
        for i in range(len(self.x)):
            x = (self.x[i] + self.vx[i] * t) % W
            y = (self.y[i] + self.vy[i] * t) % H
            tw_ = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 2 + self.ph[i]))
            rgb = LIME if self.col[i] < .45 else BLUE if self.col[i] < .8 else WHITE
            circle(c, x, y, self.s[i], rgb, a * tw_ * 0.55)


PARTS = Particles()


def dark_bg(c, t, a=1.0):
    sh = skia.GradientShader.MakeRadial((W * .42, H * .42), W * .75, [CI((16, 22, 40)), CI((7, 9, 17)), CI((3, 4, 8))], [0, .55, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    # floor perspective grid
    hy = 700
    p = paint(BLUE, 0.13 * a, stroke=1.2)
    for i in range(-14, 15):
        c.drawLine(W / 2 + i * 40, hy, W / 2 + i * 260, H + 20, p)
    off = (t * 40) % 60
    k = 0
    while True:
        yy = hy + ((k * 60 + off) / 400) ** 2 * 400 * 0.9
        if yy > H: break
        c.drawLine(0, yy, W, yy, paint(BLUE, 0.13 * a * clamp((yy - hy) / 120), stroke=1.2)); k += 1
    sh = skia.GradientShader.MakeLinear([(0, hy - 40), (0, hy + 120)], [CI((3, 4, 8), 1), CI((3, 4, 8), 0)])
    c.drawRect(skia.Rect.MakeXYWH(0, hy - 40, W, 160), skia.Paint(Shader=sh))
    # dot grid
    dp = paint(WHITE, 0.05 * a)
    for gx in range(40, W, 64):
        for gy in range(40, hy - 40, 64):
            c.drawCircle(gx, gy, 1.2, dp)
    # aurora blobs
    for (bx, by, r, rgb, ph) in [(300, 200, 420, BLUE, 0), (1500, 260, 380, VIOLET, 2), (900, 900, 500, LIME, 4)]:
        bx += math.sin(t * .3 + ph) * 60; by += math.cos(t * .25 + ph) * 40
        sh = skia.GradientShader.MakeRadial((bx, by), r, [CI(rgb, 0.10 * a), CI(rgb, 0)])
        c.drawCircle(bx, by, r, skia.Paint(Shader=sh))
    PARTS.draw(c, t, a)


def vignette(c, s=0.55):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), W * .72, [CI((0, 0, 0), 0), CI((0, 0, 0), 0), CI((0, 0, 0), s)], [0, .55, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


def side_shade(c, a=0.6, x1=900, side='l'):
    if side == 'l':
        sh = skia.GradientShader.MakeLinear([(0, 0), (x1, 0)], [CI((2, 3, 8), a), CI((2, 3, 8), a * .6), CI((2, 3, 8), 0)], [0, .5, 1])
    else:
        sh = skia.GradientShader.MakeLinear([(W, 0), (W - x1, 0)], [CI((2, 3, 8), a), CI((2, 3, 8), a * .6), CI((2, 3, 8), 0)], [0, .5, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


def hud_label(c, s, x, y, a=1.0, rgb=LIME):
    """small mono label with a leading square"""
    rrect(c, x, y - 11, 10, 10, 1, rgb, a)
    text(c, s, x + 18, y, F('mono', 15), rgb, a, spacing=1.5)
