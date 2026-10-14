"""EXAMPLE — the xingor-video-skill promo, 3:4 (1080x1440), as shipped on 小红书 (2026-10).
Copied from the project that produced it; asset paths (ROOT, V(...)) point at that machine — swap them for yours.
Reusable pieces now live in scripts/kit/showcase.py (Clip, card3d, vcard, push_blur, tilted_list, timeline_title, …)
and scripts/kit/music.py; read references/showcase.md first.
"""
"""xingor-video-skill promo v7 (v6 motion, v2 look: black/ice, thin type, grain, rounded cards) — 16:9, 1920x1080, 30 fps.
v1's energy (heavy kinetic type, glows, glass, HUD, wipes, glitch) in an electric cyan/violet palette, Chinese on screen,
travel chapter first, 3D carousel for the creative reel, follow.mp4 tail.

    python promo34.py test 3.2 9.5 ...
    python promo34.py full out.mp4
"""
import math, os, re, subprocess, sys, wave, json
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', 'skill', 'scripts')))
from kit.motion import clamp, P, eo, eio, eob, eexp, window, lerp, spring   # noqa: E402
from kit import sfx as SFX                                                   # noqa: E402

W, H, FPS = 1080, 1440, 30
ROOT = os.environ.get('PROMO_ROOT', os.path.expanduser('~/Desktop/vibemotion'))   # folder holding the source clips
FFMPEG = os.path.join(HERE, 'ffmpeg')

# ---------------------------------------------------------------- palette / type
INK = (9, 9, 11)
ACC = (158, 196, 255)       # ice — the only accent
ACC2 = (206, 222, 255)
BLUE = (60, 64, 74)
WHITE = (242, 242, 244)
GREY = (132, 134, 142)
DIMG = (66, 68, 76)
CORAL = (255, 72, 96)
PAPER = (241, 238, 230)
DARK = (20, 22, 30)
DEEP = (40, 80, 160)        # accent on light pages


def C4(rgb, a=1.0): return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))
def CI(rgb, a=1.0): return skia.ColorSetARGB(int(clamp(a) * 255), *rgb)


FAM = {'heavy': ('PingFang SC', 300, False), 'bold': ('PingFang SC', 400, False), 'med': ('PingFang SC', 400, False),
       'reg': ('PingFang SC', 400, False), 'light': ('PingFang SC', 300, False),
       'disp': ('Helvetica Neue', 100, False), 'dispu': ('Helvetica Neue', 300, False),
       'mono': ('Menlo', 700, False), 'monor': ('Menlo', 400, False), 'num': ('Helvetica Neue', 300, False),
       'song': ('Songti SC', 900, False)}
_fc = {}


def F(kind, size):
    k = (kind, round(size * 4))
    if k not in _fc:
        fam, w, it = FAM[kind]
        tf = skia.Typeface(fam, skia.FontStyle(w, 5, skia.FontStyle.kItalic_Slant if it else skia.FontStyle.kUpright_Slant))
        f = skia.Font(tf, size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); _fc[k] = f
    return _fc[k]


LATIN_ONLY = {'Menlo', 'Helvetica Neue'}


def runs(s, f):
    if f.getTypeface().getFamilyName() not in LATIN_ONLY or all(ord(ch) < 0x2000 for ch in s):
        return [(s, f)]
    fb = F('heavy', f.getSize() * .9); out = []
    for ch in s:
        ff = f if ord(ch) < 0x2000 else fb
        if out and out[-1][1] is ff: out[-1] = (out[-1][0] + ch, ff)
        else: out.append((ch, ff))
    return out


def tw(s, f, sp=0): return sum(ff.measureText(r) for r, ff in runs(s, f)) + sp * max(0, len(s) - 1)


def fit(s, kind, size, maxw, sp=0, minsize=12):
    while size > minsize and tw(s, F(kind, size), sp) > maxw: size -= 1
    return F(kind, size)


def paint(rgb=WHITE, a=1.0, stroke=0, blur=0, shader=None):
    p = skia.Paint(AntiAlias=True); p.setColor4f(C4(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None: p.setShader(shader); p.setAlphaf(clamp(a))
    return p


def text(c, s, x, y, f, rgb=WHITE, a=1.0, align='l', sp=0, glow=0, glow_rgb=None, shader=None):
    if a <= .003 or not s: return 0
    w = tw(s, f, sp)
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w

    def draw(p):
        xx = x
        for r, ff in runs(s, f):
            if sp:
                for ch in r: c.drawString(ch, xx, y, ff, p); xx += ff.measureText(ch) + sp
            else: c.drawString(r, xx, y, ff, p); xx += ff.measureText(r)
    if glow and False: draw(paint(glow_rgb or rgb, a * .22, blur=glow))
    draw(paint(rgb, a, shader=shader))
    return w


def slide_text(c, s, x, y, f, t, t0, rgb=WHITE, a=1.0, align='l', stagger=.035, d=.45, sp=0, glow=0, glow_rgb=None):
    """letters slide up + fade in one after another (motion-blurred while moving)."""
    w = tw(s, f, sp)
    if t < t0 or a <= 0: return w
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w
    dy = f.getSize() * .55; xx = x
    for i, ch in enumerate(s):
        ff = runs(ch, f)[0][1]; k = eexp(P(t, t0 + i * stagger, d * 1.6))
        if k > 0:
            yy = y + dy * (1 - k)
            pass
            p = paint(rgb, a * k)
            if k < .98: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, (1 - k) * 6 + .01))
            c.drawString(ch, xx, yy, ff, p)
        xx += ff.measureText(ch) + sp
    return w


def rrect(c, x, y, w, h, r, rgb=WHITE, a=1.0, stroke=0, blur=0, shader=None):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), paint(rgb, a, stroke, blur, shader))


def circle(c, x, y, r, rgb=WHITE, a=1.0, stroke=0, blur=0): c.drawCircle(x, y, r, paint(rgb, a, stroke, blur))
def line(c, x0, y0, x1, y1, rgb=WHITE, a=1.0, w=2, blur=0): c.drawLine(x0, y0, x1, y1, paint(rgb, a, stroke=w, blur=blur))


def corners(c, x, y, w, h, L=28, rgb=ACC, a=1.0, sw=3):
    p = skia.Path()
    for (px, py, dx, dy) in [(x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)]:
        p.moveTo(px + dx * L, py); p.lineTo(px, py); p.lineTo(px, py + dy * L)
    c.drawPath(p, paint(rgb, a, stroke=sw))


def chip(c, s, x, y, f, bg=ACC, fg=INK, a=1.0, pad=16, h=None, align='l', fill=True, r=None, maxw=None):
    if maxw: f = fit(s, 'bold' if f.getTypeface().getFamilyName() == 'PingFang SC' else 'mono', f.getSize(), maxw - pad * 2)
    w = tw(s, f) + pad * 2; h = h or f.getSize() * 1.7
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w
    r = h / 2 if r is None else r
    hot = fill and bg == ACC
    rrect(c, x, y, w, h, r, WHITE, (.10 if hot else .05) * a)
    rrect(c, x + .5, y + .5, w - 1, h - 1, r, ACC if hot else WHITE, (.7 if hot else .22) * a, stroke=1)
    text(c, s, x + pad, y + h / 2 + f.getSize() * .36, f, ACC if hot else WHITE, a)
    return w


def glass(c, x, y, w, h, r=24, a=1.0, edge=ACC, edge_a=.4, fill=((24, 25, 30), (13, 14, 17))):
    if a <= 0: return
    light = fill[0][0] > 200
    rrect(c, x, y + 20, w, h, r, (0, 0, 0), (.12 if light else .45) * a, blur=36)
    sh = skia.GradientShader.MakeLinear([(x, y), (x, y + h)], [CI(fill[0], (1 if light else .82) * a), CI(fill[1], (1 if light else .9) * a)])
    rrect(c, x, y, w, h, r, shader=sh)
    sh2 = skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [CI(WHITE, .22 * a), CI(WHITE, .05 * a), CI(ACC, .18 * a)]) if not light else \
        skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [CI((0, 0, 0), .12 * a), CI((0, 0, 0), .06 * a)])
    rrect(c, x + .5, y + .5, w - 1, h - 1, r, stroke=1, shader=sh2)


def metal_shader(y0, y1):
    return skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [CI(WHITE), CI((236, 240, 246)), CI((196, 204, 216)), CI((246, 248, 252)), CI((214, 220, 230))],
                                          [0, .38, .52, .7, 1])


def tick_ring(c, x, y, r, t, a=1.0, rgb=WHITE, n=120, speed=8):
    c.save(); c.translate(x, y); c.rotate(t * speed)
    for i in range(n):
        L = 22 if i % 10 == 0 else 9; ang = 2 * math.pi * i / n
        line(c, math.cos(ang) * r, math.sin(ang) * r, math.cos(ang) * (r - L), math.sin(ang) * (r - L), rgb, a * (.6 if i % 10 == 0 else .25), 2)
    c.restore()


class Particles:
    def __init__(self, n=60, seed=3):
        r = np.random.RandomState(seed)
        self.x = r.rand(n) * W; self.y = r.rand(n) * H; self.vx = (r.rand(n) - .5) * 20; self.vy = -r.rand(n) * 30 - 6
        self.s = r.rand(n) * 2.2 + .6; self.ph = r.rand(n) * 6.28; self.col = r.rand(n)

    def draw(self, c, t, a=1.0):
        for i in range(len(self.x)):
            x = (self.x[i] + self.vx[i] * t) % W; y = (self.y[i] + self.vy[i] * t) % H
            k = .35 + .65 * (.5 + .5 * math.sin(t * 2 + self.ph[i]))
            circle(c, x, y, self.s[i] * .8, ACC if self.col[i] < .3 else WHITE, a * k * .3)


PARTS = Particles()


def dot_grid(c, a=.05, step=56, rgb=WHITE, y1=H):
    p = paint(rgb, a)
    for gx in range(step // 2, W, step):
        for gy in range(step // 2, y1, step): c.drawCircle(gx, gy, 1.2, p)


_dust = np.random.RandomState(12).rand(46, 5)


def bg_dark(c, t, a=1.0, accent=ACC, floor=True):
    c.clear(CI(INK))
    tint = (40, 44, 56) if accent in (ACC, BLUE) else tuple(int(v * .22 + 30) for v in accent)
    gx = W * .5 + math.sin(t * .23) * 90; gy = H * .42 + math.cos(t * .19) * 50
    sh = skia.GradientShader.MakeRadial((gx, gy), W * .7, [CI(tint, .9), CI(INK, 0)])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    bx = ((t * 60) % (W + 1600)) - 800
    pth = skia.Path(); pth.moveTo(bx, -50); pth.lineTo(bx + 260, -50); pth.lineTo(bx - 340, H + 50); pth.lineTo(bx - 600, H + 50); pth.close()
    c.drawPath(pth, paint(ACC, .022 * a, blur=60))
    for i in range(len(_dust)):
        x0, y0, r, sp, ph = _dust[i]
        x = (x0 * W + t * (8 + sp * 18)) % W; y = (y0 * H - t * (6 + sp * 10)) % H
        k = .5 + .5 * math.sin(t * (.6 + sp) + ph * 6); rad = 2 + r * 9
        c.drawCircle(x, y, rad, paint(ACC if i % 3 == 0 else WHITE, (.05 + .08 * k) * (1 - r * .5) * a, blur=rad * .9))


def bg_paper(c, t):
    c.clear(CI((234, 234, 236)))
    sh = skia.GradientShader.MakeRadial((W * .5 + math.sin(t * .3) * 80, H * .4), W * .8, [CI((248, 248, 250)), CI((234, 234, 236), 0)])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


def vignette(c, s=.5):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), W * .72, [CI((0, 0, 0), 0), CI((0, 0, 0), 0), CI((0, 0, 0), s)], [0, .55, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


_grain = []


def grain(c, t, a=1.0):
    if not _grain:
        r = np.random.RandomState(4)
        for _ in range(4):
            g = np.zeros((540, 960, 4), np.uint8); g[..., :3] = 255; g[..., 3] = (r.rand(540, 960) ** 6 * 26).astype(np.uint8)
            _grain.append(skia.Image.fromarray(g, colorType=skia.kRGBA_8888_ColorType))
    p = skia.Paint(); p.setAlphaf(.5 * a)
    c.drawImageRect(_grain[int(t * FPS) % 4], skia.Rect.MakeWH(W, H), skia.SamplingOptions(), p)


def vignette(c, s_=.45):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), W * .75, [CI((0, 0, 0), 0), CI((0, 0, 0), 0), CI((0, 0, 0), s_)], [0, .5, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


def hud(c, t, label, a=1.0, rgb=ACC, idx=None, dark=True):
    if a <= 0: return
    col = GREY if dark else (120, 120, 126)
    circle(c, 66, 58, 3.5, rgb if dark else DARK, a)
    text(c, label, 82, 64, F('reg', 18), col, a, sp=3)
    if idx: text(c, idx, W - 64, 64, F('dispu', 18), col, a, 'r', sp=3)


# ---------------------------------------------------------------- video
class Clip:
    def __init__(self, path, start=0.0, w=W, h=H, fit='cover', speed=1.0, t0=0.0, crop=None):
        self.path, self.start, self.w, self.h, self.fit, self.speed, self.t0, self.crop = path, start, w, h, fit, speed, t0, crop
        self.proc = None; self.idx = -1; self.img = None; self.ok = os.path.exists(path)
        if fit == 'fit' and self.ok:
            vw, vh = (crop[2], crop[3]) if crop else self._probe()
            s = min(w / vw, h / vh); self.w, self.h = int(vw * s) // 2 * 2, int(vh * s) // 2 * 2

    def _probe(self):
        out = subprocess.run([FFMPEG, '-hide_banner', '-i', self.path], capture_output=True, text=True).stderr
        m = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', out); vw, vh = int(m.group(1)), int(m.group(2))
        if re.search(r'rotation of -?90', out): vw, vh = vh, vw
        return vw, vh

    def _open(self, i):
        if self.proc: self.proc.kill()
        ss = self.start + i / FPS * self.speed
        vf = f'setpts=(PTS-STARTPTS)/{self.speed},fps={FPS},'
        if self.crop: vf += 'crop={2}:{3}:{0}:{1},'.format(*self.crop)
        vf += (f'scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}' if self.fit == 'cover'
               else f'scale={self.w}:{self.h}') + ',format=rgba'
        cmd = [FFMPEG, '-v', 'error', '-ss', f'{ss:.3f}', '-i', self.path, '-an', '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-']
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.idx = i - 1

    def frame(self, t):
        if not self.ok: return None
        i = max(0, int(round((t - self.t0) * FPS)))
        if i == self.idx and self.img is not None: return self.img
        if self.proc is None or i < self.idx or i > self.idx + 45: self._open(i)
        n = self.w * self.h * 4
        while self.idx < i:
            buf = self.proc.stdout.read(n)
            if len(buf) < n: self.idx = i; return self.img
            self.idx += 1
            if self.idx == i:
                self.img = skia.Image.fromarray(np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 4).copy(), colorType=skia.kRGBA_8888_ColorType)
        return self.img


LIN = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def draw_img(c, img, x, y, w, h, a=1.0, r=0, blur=0):
    if img is None: rrect(c, x, y, w, h, r, (30, 34, 50), a); return
    p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a))
    if blur: p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp, None))
    c.save()
    if r: c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), LIN, p); c.restore()


def card(c, img, x, y, w, h, a=1.0, r=20, rot=0, scale=1.0, edge=ACC, glow=True):
    if a <= 0: return
    c.save(); c.translate(x, y); c.rotate(rot); c.scale(scale, scale)
    rrect(c, -w / 2, -h / 2 + 30, w, h, r, (0, 0, 0), .55 * a, blur=40)
    draw_img(c, img, -w / 2, -h / 2, w, h, a, r)
    rrect(c, -w / 2 + .5, -h / 2 + .5, w - 1, h - 1, r, WHITE, .18 * a, stroke=1)
    c.restore()


def quad_path(q):
    p = skia.Path(); p.moveTo(*q[0])
    for v in q[1:]: p.lineTo(*v)
    p.close(); return p


def quad_img(c, img, q, a=1.0, r=16):
    if img is None or a <= 0: return
    w, h = img.width(), img.height(); m = skia.Matrix()
    if not m.setPolyToPoly([skia.Point(0, 0), skia.Point(w, 0), skia.Point(w, h), skia.Point(0, h)], [skia.Point(*v) for v in q]): return
    c.save(); c.concat(m); p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a))
    c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(w, h), r, r), True); c.drawImage(img, 0, 0, LIN, p); c.restore()


def rot_pts3(w, h, rx=0.0, ry=0.0):
    """card corners (TL, TR, BR, BL) in 3D, relative to the card centre."""
    out = []
    for (u, v) in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        x, y, z = u * w / 2, v * h / 2, 0.0
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        out.append((x, y, z))
    return out


def proj3(p, cx, cy, z0=0.0, cam=1900):
    x, y, z = p; s_ = cam / (cam + z + z0); return (cx + x * s_, cy + y * s_)


def rot_quad3(cx, cy, w, h, rx=0.0, ry=0.0, z0=0.0, cam=1900):
    return [proj3(p, cx, cy, z0, cam) for p in rot_pts3(w, h, rx, ry)]


def refl_quad3(cx, cy, w, h, rx=0.0, ry=0.0, z0=0.0, gap=14.0, cam=1900):
    """the card mirrored in 3D about a floor plane just under its bottom edge, then projected (correct perspective)."""
    pts = rot_pts3(w, h, rx, ry); yb = max(pts[2][1], pts[3][1]) + gap
    return [proj3((x, 2 * yb - y, z), cx, cy, z0, cam) for (x, y, z) in pts]


def ambient(c, img, cx, cy, w, h, a=.3):
    """colour spill of the footage around a card (soft, radial)."""
    if img is None or a <= 0: return
    r = skia.Rect.MakeXYWH(cx - w * .9, cy - h * .85, w * 1.8, h * 1.7)
    c.saveLayer(r, None)
    p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a)); p.setImageFilter(skia.ImageFilters.Blur(60, 60, skia.TileMode.kDecal, None))
    c.drawImageRect(img, skia.Rect.MakeXYWH(cx - w * .7, cy - h * .65, w * 1.4, h * 1.3), LIN, p)
    g = skia.GradientShader.MakeRadial((cx, cy), max(w, h) * .85, [CI((0, 0, 0), 1), CI((0, 0, 0), .5), CI((0, 0, 0), 0)], [0, .5, 1])
    pp = skia.Paint(Shader=g); pp.setBlendMode(skia.BlendMode.kDstIn); c.drawRect(r, pp)
    c.restore()


def card3d(c, img, cx, cy, w, h, t, rx=0.0, ry=0.0, z0=0.0, a=1.0, seed=0, refl=True, edge=ACC, amb=True, sweep=True):
    """floating 3D card: ambient light, shadow, floor reflection, rim light, light sweep."""
    if a <= 0 or img is None: return None
    q = rot_quad3(cx, cy, w, h, rx, ry, z0)
    if amb: ambient(c, img, cx, cy, w, h, .3 * a)
    pth = quad_path(q); shp = skia.Path(pth); shp.offset(0, 40); c.drawPath(shp, paint((0, 0, 0), .5 * a, blur=46))
    if refl:
        rq = refl_quad3(cx, cy, w, h, rx, ry, z0)          # TL', TR', BR', BL' (image top maps to the far side)
        m = skia.Matrix(); w0, h0 = img.width(), img.height()
        if m.setPolyToPoly([skia.Point(0, 0), skia.Point(w0, 0), skia.Point(w0, h0), skia.Point(0, h0)], [skia.Point(*v) for v in rq]):
            c.saveLayer(None, None)
            rr0 = 22 * w0 / max(1, w)
            c.save(); c.concat(m); p = skia.Paint(AntiAlias=True); p.setAlphaf(.22 * a)
            c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(w0, h0), rr0, rr0), True); c.drawImage(img, 0, 0, LIN, p); c.restore()
            ys = [v[1] for v in rq]; y0, y1 = min(ys), max(ys)
            g = skia.GradientShader.MakeLinear([(0, y0), (0, y0 + (y1 - y0) * .5)], [CI((0, 0, 0), 1), CI((0, 0, 0), 0)])
            pp = skia.Paint(Shader=g); pp.setBlendMode(skia.BlendMode.kDstIn); c.drawRect(skia.Rect.MakeLTRB(0, y0, W, y1 + 2), pp)
            c.restore()
    quad_img(c, img, q, a, 22 * img.width() / max(1, w))
    rr = 22 * img.width() / max(1, w); m2 = skia.Matrix(); w0, h0 = img.width(), img.height()
    if m2.setPolyToPoly([skia.Point(0, 0), skia.Point(w0, 0), skia.Point(w0, h0), skia.Point(0, h0)], [skia.Point(*v) for v in q]):
        rp = skia.Path(); rp.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(w0, h0), rr, rr)); rp.transform(m2); pth = rp
    g = skia.GradientShader.MakeLinear([q[0], q[2]], [CI(WHITE, .45 * a), CI(WHITE, .08 * a), CI(ACC, .25 * a)])
    rp_ = skia.Paint(AntiAlias=True, Shader=g); rp_.setStyle(skia.Paint.kStroke_Style); rp_.setStrokeWidth(1.2); c.drawPath(pth, rp_)
    u = ((t * .35 + seed * .37) % 1.8) / 1.8
    if sweep and u < .6:
        xs = [v[0] for v in q]; sx = lerp(min(xs) - 300, max(xs) + 300, u / .6)
        sh = skia.GradientShader.MakeLinear([(sx - 120, 0), (sx + 120, 0)], [CI(WHITE, 0), CI(WHITE, .16 * a), CI(WHITE, 0)])
        c.save(); c.clipPath(pth, doAntiAlias=True); c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh)); c.restore()
    return q


def vcard(c, clip, cx, cy, h, t, t0, side=1.0, ry_rest=.22, d=1.0, a=1.0, seed=0, refl=True, out_t=None):
    """a vertical clip as an animated 3D card: flips in from the side, floats, can fly out."""
    if t < t0: return
    img = clip.frame(t); w = h * clip.w / clip.h
    k = spring(P(t, t0, d)); e = eexp(P(t, t0, d * .8))
    ko = eio(P(t, out_t, .45)) if out_t is not None else 0
    ry = lerp(1.25 * side, ry_rest, k) + .05 * math.sin(t * .7 + seed) - ko * 1.1 * side
    rx = .05 * math.sin(t * .55 + seed * 2) + .25 * (1 - e)
    yy = cy + (1 - e) * 140 + 8 * math.sin(t * .9 + seed) - ko * 60
    return card3d(c, img, cx + ko * 300 * side, yy, w, h, t, rx, ry, (1 - e) * 500 + ko * 700, a * clamp(e * 1.4) * (1 - ko), seed, refl)


def V(rel): return os.path.join(ROOT, rel)


TRIP1 = V('promo/trip_hrb_34/travel.mp4'); TRIP2 = V('promo/trip_qqhr_34/travel.mp4')
HRB_CHURCH = V('travel/哈尔滨/微信视频2026-10-12_225920_886.mp4'); HRB_RIVER = V('travel/哈尔滨/微信视频2026-10-12_225945_278.mp4')
QQ_FLOCK = V('travel/齐齐哈尔/8dbd4f1952ad466785e678f02be7cdfd_raw.mp4'); QQ_WALK = V('travel/齐齐哈尔/ba1975d171c831db18aa1fdc9c3c2e2c.mp4')
FOLLOW = V('关注.mp4')
FISH = V('creative/fish.mp4'); SDGT = V('creative/水调歌头4.mp4'); ARTURA = V('creative/artura-hd.mp4')
DUCK = V('creative/rubber-duck.mp4'); DUCK2 = V('creative/rubber2.mp4'); SUSHI = V('苏轼简介_诗墨_16x9_v5.mp4')
SXD = V('documentary/三星堆.mp4'); SZL = V('documentary/丝绸之路16x9.mp4'); SZL34 = V('documentary/丝绸之路.mp4')
CROP = {'fish': (100, 120, 3508, 1940), 'sdgt': (150, 130, 3366, 1900), 'artura': (60, 60, 1770, 960),
        'sushi': (0, 4, 1920, 1076), 'qq': (266, 0, 1387, 780), 'follow': (320, 140, 3200, 1800)}

CUES = []
def cue(t, kind, g=1.0): CUES.append((t, kind, g))


SCENES = []
def scene(t0, t1):
    def deco(fn): SCENES.append((t0, t1, fn)); return fn
    return deco


# ======================================================= 1. HOOK 0–7  (sentence → wall of results → hero → claim)
from PIL import Image as _PILImage
_stills = {}


def still(name, w=600):
    if name not in _stills:
        im = _PILImage.open(os.path.join(HERE, 'cover', name + '.png')).convert('RGBA')
        im = im.resize((w, int(im.height * w / im.width)), _PILImage.LANCZOS)
        _stills[name] = skia.Image.fromarray(np.ascontiguousarray(np.array(im)), colorType=skia.kRGBA_8888_ColorType)
    return _stills[name]


def crop_ar(img, ar):
    w, h = img.width(), img.height()
    if w / h > ar: nw = int(h * ar); r = skia.IRect.MakeXYWH((w - nw) // 2, 0, nw, h)
    else: nh = int(w / ar); r = skia.IRect.MakeXYWH(0, (h - nh) // 2, w, nh)
    return img.makeSubset(r)


def prompt_box(c, x, y, w, s, t, t0, cps=16, a=1.0, sent_t=None, light=False, h=84):
    fill = ((255, 255, 255), (244, 246, 250)) if light else ((26, 32, 56), (12, 15, 30))
    glass(c, x, y, w, h, h / 2, a, edge=ACC if not light else (200, 205, 215), edge_a=.6 if not light else .9, fill=fill)
    n = int(max(0, (t - t0) * cps)); f = F('med', 30); fg = DARK if light else WHITE; tx = x + 40
    w_ = text(c, s[:n], tx, y + h / 2 + 11, f, fg, a)
    if (sent_t is None or t < sent_t) and int(t * 2.4) % 2 == 0: rrect(c, tx + w_ + 4, y + h / 2 - 18, 3, 36, 1, ACC if not light else DEEP, a)
    bx, by = x + w - h / 2, y + h / 2; done = n >= len(s)
    circle(c, bx, by, h / 2 - 12, (ACC if not light else DEEP) if done else (70, 76, 96), a)
    pth = skia.Path(); pth.moveTo(bx - 9, by + 2); pth.lineTo(bx, by - 9); pth.lineTo(bx + 9, by + 2); pth.moveTo(bx, by - 9); pth.lineTo(bx, by + 10)
    c.drawPath(pth, paint(INK if not light else WHITE, a, stroke=3.2))
    k = P(t, sent_t, .3) if sent_t is not None else 0
    if 0 < k < 1: circle(c, bx, by, (h / 2) * (1 + k * 2), ACC if not light else DEEP, a * (1 - k) * .8, stroke=3)


PROMPT = '帮我做一支宣传片'
HT0, BEAT = 1.3, .45
WALL_CW, WALL_GAP = 300, 24
WALL = [[('globe', 'L'), ('river', 'V'), ('silk', 'L')], [('sxd', 'V'), ('taxi', 'L'), ('duck', 'L')],
        [('sushi', 'L'), ('car', 'L'), ('church', 'V')], [('sdgt2', 'L'), ('crane', 'V'), ('globe', 'L')],
        [('river', 'V'), ('sdgt', 'L'), ('sushi', 'L')], [('car', 'L'), ('silk', 'L'), ('sxd', 'V')],
        [('church', 'V'), ('duck', 'L'), ('taxi', 'L')]]
WALL_OFF = [-120, -330, -40, -260, -380, -90, -300]
# beats: (column, row, live clip, style, title)
BEATS = [(0, 0, (TRIP1, 2.2, None), '旅行路线', '上海 → 哈尔滨'), (1, 0, (SXD, 4.0, None), '文物纪录片', '三星堆'),
         (2, 0, (SUSHI, 1.5, 'sushi'), '诗墨国风', '苏轼的一生'), (3, 0, (SDGT, 30.0, 'sdgt'), '3D 创意', '水调歌头'),
         (4, 0, (HRB_RIVER, 6.0, None), '旅行实拍', '松花江日落'), (5, 0, (ARTURA, 1.0, 'artura'), '3D 创意', '超跑展厅'),
         (6, 0, (HRB_CHURCH, 4.0, None), '旅行实拍', '哈尔滨老教堂')]
HERO_T0, HERO_T1 = HT0 + len(BEATS) * BEAT, 5.0
HERO = Clip(TRIP1, 3.4, W, H, 'cover', t0=HERO_T0)


def wall_cells():
    cells = []; x0 = -(len(WALL) * WALL_CW + (len(WALL) - 1) * WALL_GAP) / 2
    for i, col in enumerate(WALL):
        x = x0 + i * (WALL_CW + WALL_GAP) + WALL_CW / 2; y = WALL_OFF[i]
        for j, (name, kind) in enumerate(col):
            h = WALL_CW * (16 / 9 if kind == 'V' else 9 / 16)
            cells.append(dict(i=i, j=j, name=name, kind=kind, x=x, y=y + h / 2, w=WALL_CW, h=h)); y += h + WALL_GAP
    return cells


CELLS = wall_cells()
BEAT_CLIPS = []
for b, (ci, cj, (p, s, k), lab, sub) in enumerate(BEATS):
    cell = next(cl for cl in CELLS if cl['i'] == ci and cl['j'] == cj)
    vw, vh = (600, 1067) if cell['kind'] == 'V' else (640, 360)
    BEAT_CLIPS.append(Clip(p, s, vw, vh, 'cover', t0=HT0 + b * BEAT, crop=CROP.get(k)))
    cue(HT0 + b * BEAT, 'swish' if b % 2 else 'pop', .4)


@scene(0, 7)
def s_hook(c, t):
    bg_dark(c, t)
    if t < HT0:                                       # 1. an AI composer: type one sentence, press send
        ent = eexp(P(t, 0, .45)); out = eio(P(t, 1.02, .28))
        px, py, pw, ph = 60, 430, 960, 330
        c.save(); s_ = lerp(.94, 1, ent) * (1 + .12 * out); c.translate(W / 2, py + ph / 2); c.scale(s_, s_); c.translate(-W / 2, -(py + ph / 2))
        al = ent * (1 - out)
        text(c, '输入一句话', W / 2, py - 46, F('reg', 24), GREY, al, 'c', sp=10)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(px - 30, py - 30, pw + 60, ph + 60), 60, 60), paint(ACC, .10 * al, blur=50))
        glass(c, px, py, pw, ph, 34, al, fill=((26, 30, 40), (14, 16, 22)))
        sw = skia.GradientShader.MakeSweep(W / 2, py + ph / 2, [CI(ACC, 0), CI(ACC, .9), CI(WHITE, .9), CI(ACC, 0), CI(ACC, 0)], [0, .12, .18, .3, 1],
                                           localMatrix=skia.Matrix.RotateDeg(t * 220, (W / 2, py + ph / 2)))
        rp = skia.Paint(AntiAlias=True, Shader=sw); rp.setStyle(skia.Paint.kStroke_Style); rp.setStrokeWidth(2); rp.setAlphaf(al)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(px + 1, py + 1, pw - 2, ph - 2), 33, 33), rp)
        # header row
        circle(c, px + 44, py + 52, 6, ACC, al)
        hf = skia.Font(skia.Typeface('Avenir Next', skia.FontStyle(500, 5, skia.FontStyle.kUpright_Slant)), 26)
        wx = text(c, 'xingor', px + 62, py + 61, hf, WHITE, al)
        text(c, '·  新建视频任务', px + 74 + wx, py + 61, F('reg', 24), GREY, al)
        chip(c, '3:4 竖屏', px + pw - 36, py + 32, F('reg', 20), WHITE, INK, al, pad=14, align='r', fill=False)
        line(c, px + 30, py + 92, px + pw - 30, py + 92, WHITE, .08 * al, 1)
        # the sentence, typed with a little pop per character
        f = F('heavy', 76); n = int(max(0, (t - .15) * 12)); x = px + 44; y = py + 196
        for i, ch in enumerate(PROMPT[:n]):
            ff = runs(ch, f)[0][1]; k = eo(P(t, .15 + i / 12, .12)); cw = ff.measureText(ch)
            c.save(); c.translate(x + cw / 2, y - 26); c.scale(lerp(1.3, 1, k), lerp(1.3, 1, k)); c.translate(-(x + cw / 2), -(y - 26))
            c.drawString(ch, x, y, ff, paint(WHITE, al * k)); c.restore(); x += cw + 2
        if n < len(PROMPT) or int(t * 3) % 2 == 0:
            rrect(c, x + 6, y - 62, 4, 74, 2, ACC, al); rrect(c, x + 6, y - 62, 4, 74, 2, ACC, .6 * al, blur=8)
        # toolbar
        tf_ = F('reg', 22); tx = px + 40; ty = py + ph - 78
        for j, s in enumerate(['素材 · 12 个文件', '画幅 3:4', '配音 · 行歌']):
            kk = eo(P(t, .3 + j * .1, .3)); tx += chip(c, s, tx, ty, tf_, WHITE, INK, al * kk, pad=18, h=46, fill=False) + 14
        bx, by = px + pw - 70, py + ph - 55
        press = P(t, .95, .12); rel = P(t, 1.07, .15)
        bs = 1 - .18 * eo(press) + .18 * eo(rel)
        ready = n >= len(PROMPT)
        circle(c, bx, by, 36 * bs, ACC if ready else (70, 76, 96), al)
        if ready: circle(c, bx, by, 36 * bs, ACC, .45 * al, blur=14)
        arw = skia.Path(); arw.moveTo(bx - 11, by + 3); arw.lineTo(bx, by - 11); arw.lineTo(bx + 11, by + 3); arw.moveTo(bx, by - 11); arw.lineTo(bx, by + 13)
        c.drawPath(arw, paint(INK, al, stroke=3.5))
        for j in range(2):
            r_ = P(t, .98 + j * .08, .35)
            if 0 < r_ < 1: circle(c, bx, by, 36 + 90 * eo(r_), ACC, (1 - r_) * .8, stroke=2)
        c.restore()
        if out > 0:                                   # light streak as the request is sent
            c.drawRect(skia.Rect.MakeXYWH(0, py + ph / 2 - 3, W, 6), paint(WHITE, .7 * math.sin(math.pi * out), blur=10))
            c.drawRect(skia.Rect.MakeWH(W, H), paint(WHITE, .18 * math.sin(math.pi * out)))
        return
    if t < HERO_T1:                                   # 2. wall of results; each beat lifts a card and plays it
        b = min(len(BEATS) - 1, int((t - HT0) / BEAT)); lt = t - (HT0 + b * BEAT)
        cur = next(cl for cl in CELLS if cl['i'] == BEATS[b][0] and cl['j'] == BEATS[b][1])
        prv = next(cl for cl in CELLS if cl['i'] == BEATS[max(0, b - 1)][0] and cl['j'] == BEATS[max(0, b - 1)][1])
        e = eio(clamp(lt / .3)) if b else 1
        camx = lerp(prv['x'], cur['x'], e); camy = lerp(prv['y'], cur['y'], e) * .35
        ent = eexp(P(t, HT0, .7)); z = lerp(1.6, 1.08, ent) + .06 * (t - HT0) / 3.6
        hero = eio(P(t, HERO_T0, .4))
        c.save(); c.translate(W / 2, H / 2 + 20); c.rotate(-11); c.scale(z, z); c.translate(-camx, -camy)
        for cl in CELLS:
            if cl is cur and t < HERO_T0: continue
            img = crop_ar(still(cl['name']), 9 / 16 if cl['kind'] == 'V' else 16 / 9)
            card(c, img, cl['x'], cl['y'], cl['w'], cl['h'], .55 * ent * (1 - hero), 16)
        if t < HERO_T0:                               # the live card pops forward
            k = spring(P(lt, 0, .5)); s_ = 1 + .55 * k
            cl = cur; img = BEAT_CLIPS[b].frame(t)
            rrect(c, cl['x'] - cl['w'] * s_ / 2, cl['y'] - cl['h'] * s_ / 2, cl['w'] * s_, cl['h'] * s_, 18, ACC, .35 * k, blur=30)
            card(c, img, cl['x'], cl['y'], cl['w'], cl['h'], 1, 16, 0, s_)
            rrect(c, cl['x'] - cl['w'] * s_ / 2, cl['y'] - cl['h'] * s_ / 2, cl['w'] * s_, cl['h'] * s_, 16 * s_, ACC, .8 * k, stroke=1.5 / s_ * s_)
        c.restore()
        if t >= HERO_T0:                              # 3. the travel animation takes the whole frame
            k = eio(P(t, HERO_T0, .35)); s_ = lerp(.3, 1, k)
            c.save(); c.translate(W / 2, H / 2); c.scale(s_, s_); c.rotate(-11 * (1 - k)); c.translate(-W / 2, -H / 2)
            rr = lerp(40, 0, k); draw_img(c, HERO.frame(t), 0, 0, W, H, 1, rr); c.restore()
            lab, sub = '旅行路线', '一个行程文件 → 整段路线动画'
        else:
            lab, sub = BEATS[b][3], BEATS[b][4]
        sh = skia.GradientShader.MakeLinear([(0, H - 360), (0, H)], [CI(INK, 0), CI(INK, .85)])
        c.drawRect(skia.Rect.MakeXYWH(0, H - 360, W, 360), skia.Paint(Shader=sh))
        kk = eo(P(lt if t < HERO_T0 else t - HERO_T0, 0, .2))
        chip(c, lab, 80, H - 300 + (1 - kk) * 14, F('bold', 22), ACC, INK, kk)
        text(c, sub, 80, H - 190, F('heavy', 72), WHITE, kk)
        hud(c, t, '作品集', 1, idx=f'{min(b + 1, len(BEATS)):02d} / {len(BEATS):02d}')
        for j in range(len(BEATS)):
            x0 = W - 80 - (len(BEATS) - j) * 66; fk = 1 if j < b or t >= HERO_T0 else (lt / BEAT if j == b else 0)
            rrect(c, x0, 100, 58, 3, 1.5, WHITE, .25); rrect(c, x0, 100, 58 * fk, 3, 1.5, ACC, 1)
        return
    slide_text(c, '你只说一句话', W / 2, 590, F('heavy', 124), t, 5.05, WHITE, align='c', stagger=.05)
    e = eexp(P(t, 5.5, .9)); line(c, W / 2 - 300 * e, 650, W / 2 + 300 * e, 650, WHITE, .25, 1); circle(c, W / 2 + 300 * e, 650, 4, ACC, e)
    slide_text(c, '剩下的，交给它剪', W / 2, 740, F('heavy', 56), t, 5.75, ACC, align='c', stagger=.045, sp=6)


cue(1.05, 'impact', .4); cue(HERO_T0, 'whoosh', .5); cue(5.05, 'impact', .45); cue(5.75, 'whoosh', .35)


# ======================================================= 2. TITLE 7–12  (an editing timeline builds the wordmark)
TL_CLIPS = [Clip(TRIP1, 0.4, 480, 480, 'cover', speed=.45, t0=7.0), Clip(SXD, 6.0, 480, 480, 'cover', t0=7.0),
            Clip(SDGT, 30.0, 480, 480, 'cover', t0=7.0, crop=CROP['sdgt']), Clip(HRB_CHURCH, 18.0, 480, 480, 'cover', t0=7.0),
            Clip(HRB_RIVER, 8.0, 480, 480, 'cover', t0=7.0), Clip(ARTURA, 2.5, 480, 480, 'cover', t0=7.0, crop=CROP['artura'])]
TL_NAMES = ['旅行路线', '文物纪录片', '3D 创意', '老城教堂', '松花江', '超跑展厅']
TF = skia.Font(skia.Typeface('Avenir Next', skia.FontStyle(400, 5, skia.FontStyle.kUpright_Slant)), 220); TF.setSubpixel(True)
TWORD, TSP = 'xingor', 16
PX0, PY0, PW_, PH_ = 50, 860, 980, 236                   # timeline panel
TRK_X0, TRK_X1 = PX0 + 110, PX0 + PW_ - 24
BLK_W = [146, 124, 152, 140, 130, 144]


def blocks():
    out = []; x = TRK_X0; gap = (TRK_X1 - TRK_X0 - sum(BLK_W)) / (len(BLK_W) - 1)
    for w in BLK_W: out.append((x, w)); x += w + gap
    return out


BLKS = blocks()


def playhead(lt):
    if lt < 2.6: return lerp(TRK_X0, TRK_X1, eio(P(lt, .45, 2.0)))
    return lerp(TRK_X0, TRK_X1, ((lt - 2.6) / 4.0) % 1)      # keeps playing, slower


LAND = []
for (bx, bw) in BLKS:                                         # when the playhead reaches each clip
    tt = .45
    while playhead(tt) < bx + 18 and tt < 2.6: tt += 1 / 120
    LAND.append(tt)


def letter_pos():
    x = W / 2 - tw(TWORD, TF, TSP) / 2; out = []
    for ch in TWORD: out.append((x, TF.measureText(ch))); x += TF.measureText(ch) + TSP
    return out


LPOS = letter_pos()
BASE_Y = 560


@scene(7, 12)
def s_title(c, t):
    bg_dark(c, t); lt = t - 7
    # soft glow of the footage behind the word
    c.drawOval(skia.Rect.MakeXYWH(W / 2 - 520, BASE_Y - 280, 1040, 380), paint(ACC, .07 * eexp(P(lt, .4, 1.5)), blur=110))
    # ---------------- the timeline panel
    kp = eexp(P(lt, 0, .8)); py = PY0 + (1 - kp) * 120
    glass(c, PX0, py, PW_, PH_, 22, kp)
    text(c, '时间线', PX0 + 26, py + 34, F('reg', 18), GREY, kp, sp=4)
    fr = int((lt * 30)) ; tc = f'00:00:{int(lt) % 60:02d}:{fr % 30:02d}'
    text(c, tc, PX0 + PW_ - 26, py + 34, F('mono', 17), WHITE, kp * .8, 'r')
    ry = py + 56                                                 # ruler
    for i, x in enumerate(range(int(TRK_X0), int(TRK_X1) + 1, 22)):
        L = 9 if i % 5 == 0 else 4; line(c, x, ry - L, x, ry, WHITE, .22 * kp, 1)
    rows = [('视频', ry + 12, 74), ('字幕', ry + 96, 24), ('音效', ry + 128, 34)]
    for name, y, h in rows: text(c, name, PX0 + 26, y + h / 2 + 7, F('reg', 18), GREY, kp, sp=2)
    vy, vh = rows[0][1], rows[0][2]
    for i, (bx, bw) in enumerate(BLKS):                         # clip thumbnails pop in
        k = spring(P(lt, .2 + i * .07, .5))
        if k <= 0: continue
        hh = vh * k; yy = vy + (vh - hh) / 2
        draw_img(c, TL_CLIPS[i].frame(t), bx, yy, bw, hh, kp, 8)
        on = lt >= LAND[i]
        rrect(c, bx + .5, yy + .5, bw - 1, hh - 1, 8, ACC if on else WHITE, (.9 if on else .25) * kp, stroke=1.2)
        text(c, TL_NAMES[i], bx + 10, yy + hh - 9, F('med', 15), WHITE, kp * clamp(k * 1.5))
    sy, sh_ = rows[1][1], rows[1][2]                             # subtitle track: the four inputs → output
    subs = [('口播', .02, .16), ('旁白', .2, .16), ('一个主题', .4, .24), ('成片', .7, .28)]
    for j, (s, a0, ww) in enumerate(subs):
        k = eexp(P(lt, .5 + j * .12, .5))
        if k <= 0: continue
        x = TRK_X0 + (TRK_X1 - TRK_X0) * a0; w = (TRK_X1 - TRK_X0) * ww * k
        rrect(c, x, sy, w, sh_, sh_ / 2, ACC if j == 3 else WHITE, (.35 if j == 3 else .12) * kp)
        text(c, s, x + 12, sy + sh_ / 2 + 6, F('med', 15), ACC if j == 3 else WHITE, kp * k)
    ay, ah = rows[2][1], rows[2][2]                              # waveform
    n = 140; bwid = (TRK_X1 - TRK_X0) / n
    for i in range(n):
        ph = i * .37
        v = (.25 + .75 * abs(math.sin(lt * 5.3 + ph) * math.sin(lt * 2.1 + ph * .7))) * (.5 + .5 * math.sin(i * .19) ** 2)
        k = eexp(P(lt, .3 + i * .004, .4)); bh = max(2, ah * v * k)
        xx = TRK_X0 + i * bwid
        rrect(c, xx, ay + ah / 2 - bh / 2, bwid * .55, bh, 1, ACC if xx < playhead(lt) else WHITE, (.75 if xx < playhead(lt) else .25) * kp)
    phx = playhead(lt)                                           # playhead
    if lt > .45:
        line(c, phx, ry - 14, phx, py + PH_ - 12, ACC, kp, 2)
        tri = skia.Path(); tri.moveTo(phx - 8, ry - 22); tri.lineTo(phx + 8, ry - 22); tri.lineTo(phx, ry - 10); tri.close()
        c.drawPath(tri, paint(ACC, kp)); c.drawRect(skia.Rect.MakeXYWH(phx - 1, ry - 14, 2, PH_ - 60), paint(ACC, .4 * kp, blur=6))
    # ---------------- the wordmark: each letter lands when the playhead reaches its clip
    for i, ch in enumerate(TWORD):
        x, cw = LPOS[i]; k = P(lt, LAND[i], .35); e = eexp(k)
        if k <= 0: continue
        s_ = lerp(1.12, 1, e); cxl = x + cw / 2; cyl = BASE_Y - 100
        c.save(); c.translate(cxl, cyl); c.scale(s_, s_); c.translate(-cxl, -cyl)
        c.saveLayer(None, skia.Paint(Alphaf=clamp(e * 1.6)))
        gfill = skia.GradientShader.MakeLinear([(0, BASE_Y - 165), (0, BASE_Y + 10)],
                                               [CI((255, 255, 255)), CI((222, 232, 248)), CI((160, 184, 222))], [0, .55, 1])
        p = paint(WHITE, 1, shader=gfill)                             # white → ice → mist blue, like cold metal
        if e < .97: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, (1 - e) * 8 + .01))
        c.drawString(ch, x, BASE_Y, TF, p)
        fl = 1 - clamp((lt - LAND[i]) / .25)                     # used by the clip → letter link line
        va = 1 - eio(clamp((lt - LAND[i] - .15) / .4))              # the clip flashes inside the letter, then melts into the gradient
        if va > 0:
            pp = skia.Paint(AntiAlias=True); pp.setBlendMode(skia.BlendMode.kSrcATop); pp.setAlphaf(va)
            c.drawImageRect(TL_CLIPS[i].frame(t), skia.Rect.MakeXYWH(x - 30, BASE_Y - 200, cw + 60, 260), LIN, pp)
        u = ((lt - 2.8) / 2.2) % 1 if lt > 2.8 else -1           # slow ice shimmer, once the word is complete
        if 0 <= u < 1:
            sx = lerp(LPOS[0][0] - 200, LPOS[-1][0] + LPOS[-1][1] + 200, u)
            sh = skia.GradientShader.MakeLinear([(sx - 90, 0), (sx + 90, 0)], [CI(ACC, 0), CI((120, 170, 255), .6), CI(ACC, 0)])
            sp = skia.Paint(Shader=sh); sp.setBlendMode(skia.BlendMode.kSrcATop); c.drawRect(skia.Rect.MakeXYWH(x - 10, BASE_Y - 260, cw + 20, 340), sp)
        c.restore(); c.restore()
        c.drawString(ch, x, BASE_Y, TF, paint(WHITE, .5 * e, stroke=1.1))       # hairline outline
        if fl > 0:                                               # link: clip on the timeline → its letter
            bx, bw = BLKS[i]
            line(c, bx + bw / 2, vy - 2, x + cw / 2, BASE_Y + 64, ACC, .6 * fl, 1.5)
            circle(c, bx + bw / 2, vy - 2, 4, ACC, fl)
    # ---------------- under the word
    yv = BASE_Y + 104
    kk = eexp(P(lt, 2.5, .8))
    text(c, 'VIDEO SKILL', W / 2, yv, skia.Font(skia.Typeface('Avenir Next', skia.FontStyle(500, 5, skia.FontStyle.kUpright_Slant)), 24), ACC, kk, 'c', sp=20)
    slide_text(c, '会剪片的 AI 技能', W / 2, yv + 64, F('heavy', 36), lt, 2.7, WHITE, align='c', stagger=.04, sp=10)
    hud(c, t, '开源 · 视频技能', eo(P(lt, .3, .6)), idx='01 / 10')


cue(7.0, 'whoosh', .35)
for i, tl in enumerate(LAND): cue(7.0 + tl, 'impact' if i == len(LAND) - 1 else 'pop', .3 if i < len(LAND) - 1 else .45)
for i in range(6): cue(7.2 + i * .07, 'swish', .08)


# ======================================================= 3. TRAVEL 12–47.5
T_IN, L1_IN, L1_OUT, L2_IN, L2_OUT, T_OUT = 12.0, 16.0, 29.0, 33.5, 42.5, 47.5
L1 = Clip(TRIP1, 0.0, W, H, 'cover', speed=16.25 / (L1_OUT - L1_IN), t0=L1_IN)
L2_SRC0 = 4.6
L2 = Clip(TRIP2, L2_SRC0, W, H, 'cover', speed=(16.25 - L2_SRC0) / (L2_OUT - L2_IN), t0=L2_IN)
TEASER = Clip(V('promo/trip_hrb/travel.mp4'), 1.2, 860, 484, 'cover', t0=T_IN)
HRB = [Clip(HRB_CHURCH, 1.0, 405, 720, 'cover', t0=L1_OUT), Clip(HRB_RIVER, 5.0, 405, 720, 'cover', t0=L1_OUT),
       Clip(HRB_CHURCH, 17.0, 405, 720, 'cover', t0=L1_OUT)]
QQ = Clip(QQ_WALK, 0.0, W, H, 'cover', t0=L2_OUT)
QQ2 = Clip(QQ_FLOCK, 4.5, 860, 484, 'cover', t0=L2_OUT, crop=CROP['qq'])


def chapter(c, t, t0, num, zh, en, desc, rgb=ACC, dark=True, x=120, y=430):
    lt = t - t0; fg = WHITE if dark else DARK; k = eo(P(lt, 0, .5))
    text(c, num, x, y - 130, F('disp', 130), rgb, k, glow=18)
    line(c, x + 170, y - 172, x + 170 + 280 * eo(P(lt, .2, .6)), y - 172, rgb, .85, 2)
    text(c, en, x + 172, y - 138, F('bold', 22), rgb, eo(P(lt, .3, .4)), sp=6)
    slide_text(c, zh, x, y, F('heavy', 110), lt, .1, fg, stagger=.05, glow=14 if dark else 0, glow_rgb=rgb)
    for i, d in enumerate(desc):
        kk = eo(P(lt, .6 + i * .15, .4))
        text(c, d, x + (1 - kk) * -20, y + 84 + i * 50, fit(d, 'med', 30, 700), GREY if dark else (90, 92, 100), kk)


def lower_third(c, t, t0, city, sub, leg):
    k = eo(P(t, t0, .5))
    if k <= 0: return
    x = 80; y = H - 470
    rrect(c, x, y, 8, 170 * k, 4, ACC, 1); rrect(c, x, y, 8, 170 * k, 4, ACC, .6, blur=10)
    text(c, leg, x + 34, y + 32, F('bold', 22), ACC, k, sp=6)
    slide_text(c, city, x + 30, y + 124, F('heavy', 96), t, t0 + .1, WHITE, stagger=.05, glow=14, glow_rgb=ACC)
    text(c, sub, x + 34, y + 176, fit(sub, 'med', 30, 700), WHITE, eo(P(t, t0 + .45, .4)) * .85)


def leg_chip(c, t, t0, t1, s):
    k = window(t, t0 + .3, t1 - .2, .4, .3)
    if k > 0:
        chip(c, s, W - 80, 56, F('bold', 26), ACC, INK, k, align='r')


@scene(12, 47.5)
def s_travel(c, t):
    if t < L1_IN:
        lt = t - T_IN; bg_dark(c, t, accent=BLUE)
        hud(c, t, '第一章 · 旅行路线', 1, idx='02 / 10')
        chapter(c, t, T_IN, '01', '旅行路线', '一个行程文件', ['给它写一个行程文件', '它画出整段路线动画'], y=380)
        if False:
          steps = ['地球', '航线', '地图', '登机牌', '飞行', '打车', '落点']
          pass
        kc = spring(P(lt, .2, .9))
        card(c, TEASER.frame(t), lerp(1700, 540, kc), 790, 800, 450, 1, 20, lerp(8, -2, kc))
        # itinerary glass card
        k = spring(P(lt, .8, .9)); gx, gy = 140, 1052
        if k > 0:
            c.save(); c.translate(0, (1 - k) * 300)
            glass(c, gx, gy, 800, 236, 22, clamp(k * 1.4))
            text(c, '行程', gx + 34, gy + 44, F('bold', 20), ACC, clamp(k), sp=6)
            stops = [('上海', '出发'), ('哈尔滨', '第一站 · 松花江'), ('齐齐哈尔', '第二站 · 扎龙湿地')]
            e = eio(P(lt, 1.1, 1.2)); line(c, gx + 52, gy + 84, gx + 52, gy + 84 + 116 * e, ACC, .7, 2)
            for i, (city, sub) in enumerate(stops):
                kk = eo(P(lt, 1.1 + i * .35, .4)); yy = gy + 84 + i * 58
                circle(c, gx + 52, yy, 9 * kk, ACC, 1); circle(c, gx + 52, yy, 20 * kk, ACC, .4 * kk, blur=8)
                text(c, city, gx + 88, yy + 12, F('heavy', 34), WHITE, kk)
                text(c, sub, gx + 340, yy + 10, fit(sub, 'med', 24, 420), GREY, kk)
            c.restore()
        return
    if t < L1_OUT:
        draw_img(c, L1.frame(t), 0, 0, W, H); leg_chip(c, t, L1_IN, L1_OUT, '第一程 · 上海 → 哈尔滨'); return
    if t < L2_IN:
        st = t - L1_OUT; bg_dark(c, t, accent=CORAL)
        orbit = math.sin(st * .5)
        for i in (0, 2, 1):
            side = i - 1
            vcard(c, HRB[i], 540 + side * 310 + orbit * 20 * side, 560, 600 if side == 0 else 500, t, L1_OUT + .15 + abs(side) * .25,
                  side=side if side else -1, ry_rest=.42 * side, seed=i, out_t=L2_IN - .5 + i * .05)
        sh = skia.GradientShader.MakeLinear([(0, H - 460), (0, H)], [CI(INK, 0), CI(INK, .92)])
        c.drawRect(skia.Rect.MakeXYWH(0, H - 460, W, 460), skia.Paint(Shader=sh))
        lower_third(c, t, L1_OUT + .4, '哈尔滨', '松花江日落 · 老城教堂', '第一站')
        hud(c, t, '旅行 · 实拍', 1, idx='02 / 10')
        return
    if t < L2_OUT:
        draw_img(c, L2.frame(t), 0, 0, W, H); leg_chip(c, t, L2_IN, L2_OUT, '第二程 · 哈尔滨 → 齐齐哈尔'); return
    st = t - L2_OUT
    z = 1.1 - .07 * st / 5
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2); draw_img(c, QQ.frame(t), 0, 0, W, H); c.restore()
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, 700)], [CI(INK, .55), CI(INK, 0)])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    e = eexp(P(st, .3, 1.0)); kq = spring(P(st, .3, 1.3))
    card3d(c, QQ2.frame(t), 540, 420 + 8 * math.sin(t * .8), 860, 484, t, .06, lerp(-1.0, -.18, kq), (1 - e) * 500, e, 7, False)
    sh = skia.GradientShader.MakeLinear([(0, H - 460), (0, H)], [CI(INK, 0), CI(INK, .9)])
    c.drawRect(skia.Rect.MakeXYWH(0, H - 460, W, 460), skia.Paint(Shader=sh))
    lower_third(c, t, L2_OUT + .4, '齐齐哈尔', '扎龙湿地 · 丹顶鹤', '第二站')
    hud(c, t, '旅行 · 实拍', 1, idx='02 / 10')


cue(T_IN, 'impact', .4)
for i in range(7): cue(T_IN + .6 + i * .18, 'pop', .3)
cue(L1_IN, 'whoosh', .5); cue(L1_OUT, 'whoosh', .5)
for i in range(3): cue(L1_OUT + i * .15, 'swish', .35)
cue(L2_IN, 'whoosh', .5); cue(L2_OUT, 'whoosh', .5); cue(L2_OUT + .2, 'swish', .35)


# ======================================================= 4. INPUT 47.5–55
PREVIEW = Clip(SZL, 26.0, 432, 243, 'cover', t0=47.5)


@scene(47.5, 55)
def s_input(c, t):
    bg_dark(c, t, accent=BLUE); lt = t - 47.5
    hud(c, t, '第二章 · 工作流', 1, idx='03 / 10')
    slide_text(c, '丢给它任何一种素材', W / 2, 200, F('heavy', 72), lt, 0, WHITE, align='c', stagger=.04)
    # three inputs in a row
    items = [('口播视频', '一段出镜讲解'), ('旁白音频', '只有声音也行'), ('一个主题', '比如「三星堆」')]
    cw_, ch_, gap = 300, 150, 30; x0 = (W - 3 * cw_ - 2 * gap) / 2; y = 270
    cx, cy = W / 2, 640
    for i, (a1, a2) in enumerate(items):
        k = spring(P(lt, .3 + i * .25, .8)); x = x0 + i * (cw_ + gap); yy = y + (1 - k) * 80; ka = clamp(k * 1.5)
        glass(c, x, yy, cw_, ch_, 20, ka)
        rrect(c, x + 22, yy + 22, 52, 52, 12, ACC, .9 * ka); text(c, f'0{i + 1}', x + 48, yy + 59, F('num', 30), INK, ka, 'c')
        text(c, a1, x + 22, yy + 112, fit(a1, 'heavy', 36, cw_ - 44), WHITE, ka)
        text(c, a2, x + 22, yy + 138, fit(a2, 'med', 20, cw_ - 44), GREY, ka)
        kw = eio(P(lt, 1.3 + i * .12, .7))                       # streams down into the core
        if kw > 0:
            sx, sy = x + cw_ / 2, y + ch_
            pth = skia.Path(); pth.moveTo(sx, sy); pth.cubicTo(sx, sy + 90, cx, cy - 200, cx, cy - 130)
            pm = skia.PathMeasure(pth, False); L = pm.getLength(); seg = skia.Path(); pm.getSegment(0, L * kw, seg, True)
            c.drawPath(seg, paint(ACC, .3, stroke=6, blur=6)); c.drawPath(seg, paint(ACC, .9, stroke=2.2))
            if kw >= 1:
                pos, _ = pm.getPosTan(L * ((lt * .8 + i * .3) % 1)); circle(c, pos.x(), pos.y(), 6, WHITE, .9); circle(c, pos.x(), pos.y(), 14, ACC, .5, blur=8)
    kc = eob(P(lt, 1.9, .6))
    if kc > 0:
        pulse = 1 + .04 * math.sin(lt * math.pi * 4)
        circle(c, cx, cy, 170 * kc, ACC, .12, blur=50); tick_ring(c, cx, cy, 135 * kc * pulse, t, .7)
        c.save(); c.translate(cx, cy); c.rotate(-t * 40)
        c.drawArc(skia.Rect.MakeXYWH(-108, -108, 216, 216), 0, 250, False, paint(ACC, .9 * kc, stroke=4)); c.restore()
        circle(c, cx, cy, 86 * kc, INK, 1); circle(c, cx, cy, 86 * kc, ACC, .6, stroke=2)
        text(c, '技能', cx, cy + 14, F('heavy', 40 * kc), WHITE, kc, 'c')
    ko = spring(P(lt, 2.8, .8))
    if ko > 0:                                                    # output card below the core
        ox, oy, ow, oh = 110, 830, 860, 300
        line(c, cx, cy + 140, cx, lerp(cy + 140, oy, eio(P(lt, 2.6, .4))), ACC, .9, 2.5)
        c.save(); c.translate(W / 2, oy + oh / 2); s_ = .8 + .2 * ko; c.scale(s_, s_); c.translate(-W / 2, -(oy + oh / 2))
        a = clamp(ko * 1.5); glass(c, ox, oy, ow, oh, 24, a, edge_a=.7)
        draw_img(c, PREVIEW.frame(t), ox + 24, oy + 26, 440, 248, a, 12)
        rx_ = ox + 500
        text(c, '成片', rx_, oy + 100, F('heavy', 52), WHITE, a)
        text(c, '横屏 · 竖屏 · 小红书', rx_, oy + 150, F('bold', 24), ACC, a, sp=1)
        rrect(c, rx_, oy + 190, 330, 6, 3, WHITE, .15); rrect(c, rx_, oy + 190, 330 * eio(P(lt, 3.0, 3.0)), 6, 3, ACC, .95)
        c.restore()
    feats = ['逐字字幕', '动效模板', '合成音效', '开头钩子', '转场']
    f2 = F('bold', 24); ws = [tw(s, f2) + 32 for s in feats]; gap2 = 14
    x = (W - sum(ws) - gap2 * 4) / 2
    for i, s in enumerate(feats):
        k = eob(P(lt, 4.0 + i * .2, .4))
        if k > 0:
            c.save(); c.translate(x + ws[i] / 2, 1185); c.scale(k, k)
            chip(c, s, -ws[i] / 2, -20, f2, ACC if i % 2 == 0 else WHITE, INK, clamp(k)); c.restore()
        x += ws[i] + gap2


for i in range(3): cue(47.8 + i * .4, 'whoosh', .3)
cue(49.5, 'impact', .4); cue(50.5, 'swish', .45)
for i in range(5): cue(51.7 + i * .25, 'pop', .35)


# ======================================================= 5. PIPELINE (light) 55–62
TOTAL_FRAMES = 0


@scene(55, 62)
def s_pipe(c, t):
    bg_paper(c, t); lt = t - 55
    rrect(c, 64, 52, 10, 10, 1, DEEP, 1); text(c, '第二章 · 工作流', 84, 63, F('bold', 17), DARK, 1, sp=3)
    slide_text(c, '说出你想要的', 70, 220, F('heavy', 80), lt, 0, DARK, stagger=.04)
    slide_text(c, '它自己跑完整条流水线', 70, 315, F('heavy', 80), lt, .3, DEEP, stagger=.04)
    prompt_box(c, 60, 395, 960, '把我的东北之旅做成旅行路线动画', t, 55.5, 16, eo(P(lt, .2, .4)), sent_t=57.6, light=True)
    steps = [('01', '分析', '转写 · 抠像 · 静音点'), ('02', '钩子', '挑出最精彩的几秒'), ('03', '分镜', '每个词触发一个动效'), ('04', '渲染', '字幕 · 音效 · 成片')]
    x0, y0, sh_ = 100, 600, 175
    kl = eio(P(lt, 2.8, 3.0)); line(c, x0 + 40, y0 + 60, x0 + 40, y0 + 60 + sh_ * 3 * kl, DARK, .9, 3)
    for i, (n, a, d) in enumerate(steps):
        ts = 2.8 + i * .8; k = spring(P(lt, ts, .6)); on = lt > ts + .3; x = x0; y = y0 + i * sh_ - 60
        if k <= 0: continue
        c.save(); c.translate(x + 40, y + 60); c.scale(k, k); c.translate(-(x + 40), -(y + 60))
        if on: circle(c, x + 40, y + 60, 48, DEEP, .25, blur=14)
        circle(c, x + 40, y + 60, 40, DEEP if on else DARK, 1); text(c, n, x + 40, y + 72, F('num', 34), WHITE, 1, 'c'); c.restore()
        ka = clamp(k * 1.4)
        text(c, a, x + 120, y + 76, F('heavy', 56), DARK, ka)
        text(c, d, x + 120, y + 120, fit(d, 'med', 28, 700), (90, 92, 104), ka)
    kp = P(lt, 5.4, 1.2)
    if kp > 0: text(c, f'渲染 {int(TOTAL_FRAMES * eio(kp)):04d} / {TOTAL_FRAMES} 帧', W - 70, 1240, F('mono', 24), DARK, 1, 'r')


cue(57.6, 'pop', .6)
for i in range(4): cue(57.8 + i * .8, 'pop', .45)


# ======================================================= 6. NUMBERS 62–68.5
STYLES = ['科技口播 · 霓虹实验室', '诗墨国风 · 水墨诗词', '文物纪录片 · 无人出镜', '撞色测评 · 纯配音', '旅行路线 · 行程动画']
COMPS = ['人脸追踪开场', '逐字标题', '金属标题', '水墨封面', '竖版封面', '人物身后大字', '身后打字机', '纸雾晕字', '双词分列', '撕纸大字',
         '撕纸卡片字', '推镜大标题', '居中大字', '竖向步骤', '清单划掉', '印章要点', '浮动标签', '撕纸关键词', '编号列表', '数据卡片',
         '数字跳动', '对比表', '快慢对比', '点阵分屏', '符号替换', '竖排诗句', '竖版诗句', '口播小窗', '山水长卷', '节点流程', '技能核心',
         '素材分析', '路线图', '输入框打字', '信笺书写', '截图标注', '素材主画面', '挂轴播放', '抠像展示', '本片时间线', '评论引导',
         '水墨结尾', '竖版结尾', '中性结尾']
assert len(COMPS) == 44


@scene(62, 68.5)
def s_numbers(c, t):
    bg_dark(c, t); lt = t - 62
    hud(c, t, '第三章 · 风格与组件', 1, idx='04 / 10')
    blocks = [(5, '种风格', 0.0), (44, '个组件', 2.2), (3, '种画幅', 4.4)]
    for i, (n, unit, ts) in enumerate(blocks):
        if lt < ts: continue
        age = lt - ts; k = eo(P(age, 0, .5))
        m = eo(P(age, 2.2, .45)) if i < 2 else 0
        y = lerp(470, 200, m); size = lerp(300, 90, m); a = lerp(1, .45, m)
        val = int(round(n * eo(P(age, .05, .7)))); f = F('disp', size); x = lerp(80, 80 + i * 300, m) + (1 - k) * -60
        w = text(c, f'{val}', x, y, f, ACC if m < .5 else WHITE, a * k, glow=24 if m < .5 else 0)
        text(c, unit, x + w + 22, y - size * .06, F('heavy', size * .3), WHITE, a * k)
    px, py = 80, 560
    if lt < 2.2:
        for i, s in enumerate(STYLES):
            k = eo(P(lt, .25 + i * .15, .4)); xx = px + (1 - k) * 80; yy = py + i * 118
            glass(c, xx, yy, 920, 96, 16, k)
            text(c, f'0{i + 1}', xx + 30, yy + 62, F('num', 40), ACC, k)
            text(c, s, xx + 100, yy + 62, fit(s, 'bold', 34, 780), WHITE, k)
        text(c, '+ 不指定时，按内容自动设计一套', px, py + 5 * 118 + 40, F('med', 26), ACC, eo(P(lt, 1.2, .4)))
    elif lt < 4.4:
        a2 = lt - 2.2; cols, cw, ch = 4, 232, 46
        for i, s in enumerate(COMPS):
            col, row = i % cols, i // cols; k = eo(P(a2, i * .02, .3))
            hl = (int(a2 * 12) + i * 7) % 11 == 0
            x = px - 20 + col * cw; y = 540 + row * (ch + 12)
            rrect(c, x, y, cw - 14, ch, 8, ACC if hl else WHITE, (.95 if hl else .07) * k)
            if hl: rrect(c, x, y, cw - 14, ch, 8, ACC, .5 * k, blur=10)
            text(c, s, x + (cw - 14) / 2, y + 32, fit(s, 'med', 20, cw - 34), INK if hl else WHITE, k, 'c')
    else:
        a3 = lt - 4.4; x = 80
        for i, (rw, rh, lab) in enumerate([(16, 9, '横屏 16:9'), (3, 4, '小红书 3:4'), (9, 16, '竖屏 9:16')]):
            k = spring(P(a3, i * .2, .6)); hh = 320; ww = hh * rw / rh
            if ww > 400: ww = 400; hh = ww * rh / rw
            y = 600 + (320 - hh) / 2
            if k > 0:
                c.save(); c.translate(x + ww / 2, y + hh / 2); c.scale(k, k); c.translate(-(x + ww / 2), -(y + hh / 2))
                rrect(c, x, y, ww, hh, 14, ACC, .08); rrect(c, x, y, ww, hh, 14, ACC, .5, stroke=6, blur=8); rrect(c, x, y, ww, hh, 14, ACC, .95, stroke=3)
                c.restore(); text(c, lab, x + ww / 2, 990, fit(lab, 'bold', 28, ww + 40), WHITE, clamp(k), 'c')
            x += ww + 50


for ts in (62, 64.2, 66.4): cue(ts, 'impact', .4)
for i in range(5): cue(62.25 + i * .15, 'pop', .25)
for i in range(3): cue(66.4 + i * .2, 'pop', .35)


# ======================================================= 7. POETRY 68.5–74.5
SU1 = Clip(SUSHI, 14.5, 1000, 562, 'cover', t0=68.5, crop=CROP['sushi'])
SU2 = Clip(SUSHI, 33.8, 420, 236, 'cover', speed=.6, t0=68.5, crop=CROP['sushi'])   # stays inside the clip (ends at 38.4 s)
VERM = (200, 70, 40)


@scene(68.5, 74.5)
def s_poetry(c, t):
    bg_dark(c, t, accent=VERM); lt = t - 68.5
    hud(c, t, '风格 01 · 诗墨国风', 1, VERM, idx='06 / 10')
    k = eob(P(lt, 1.0, .35))
    if k > 0:
        c.save(); c.translate(880, 250); c.scale(1.6 - .6 * k, 1.6 - .6 * k); c.rotate(-6)
        rrect(c, -48, -48, 96, 96, 8, VERM, clamp(k)); text(c, '诗墨', 0, 14, F('song', 38), PAPER, clamp(k), 'c'); c.restore()
    chapter(c, t, 68.5, '02', '诗墨国风', '水墨诗词', ['宣纸 · 水墨晕开 · 朱砂印章', '诗句跟着朗读逐字出现', '只给一段旁白也能出片'], VERM, dark=True, y=380)
    kc = spring(P(lt, .3, 1.3)); k2 = spring(P(lt, .9, 1.3)); e = eexp(P(lt, .3, 1.0)); e2 = eexp(P(lt, .9, 1.0))
    card3d(c, SU1.frame(t), 540, 830 + 8 * math.sin(t * .8), 900, 506, t, .06 + .03 * math.sin(t * .6), lerp(-1.0, -.24, kc), (1 - e) * 500, e, 1,
           edge=(200, 70, 40), amb=False, sweep=False)
    card3d(c, SU2.frame(t), 790, 1090 + 6 * math.sin(t), 400, 225, t, .05, lerp(-1.1, -.34, k2), (1 - e2) * 400 - 120, e2, 2, False,
           edge=(200, 70, 40), amb=False, sweep=False)


cue(68.5, 'impact', .3); cue(68.8, 'whoosh', .45); cue(69.5, 'pop', .6)


# ======================================================= 8. DOC 74.5–80
SX = [Clip(SXD, s, 340, 604, 'cover', t0=74.5) for s in (2.0, 48.0, 95.0)]
SZ169 = Clip(SZL, 30.0, 820, 461, 'cover', t0=77.4)
SZ34 = Clip(SZL34, 30.0, 300, 400, 'cover', t0=77.4)
GOLD = (222, 184, 110)


@scene(74.5, 80)
def s_doc(c, t):
    bg_dark(c, t, accent=GOLD); lt = t - 74.5
    hud(c, t, '风格 02 · 文物纪录片', 1, GOLD, idx='05 / 10')
    chapter(c, t, 74.5, '03', '文物纪录片', '无人出镜', ['给一个主题，自动找图、抠图', '配音、配乐，出横竖两版'], GOLD, y=380)
    if lt < 3.2:
        for i in (0, 2, 1):
            side = i - 1
            vcard(c, SX[i], 540 + side * 300, 800, 540 if side == 0 else 460, t, 74.5 + .2 + abs(side) * .2, side=side if side else 1,
                  ry_rest=.45 * side, seed=i + 3, out_t=77.0 + i * .05)
    else:
        a2 = lt - 3.2; k = spring(P(a2, 0, 1.2)); k2 = spring(P(a2, .2, 1.2))
        e = eexp(P(a2, 0, 1.0)); e2 = eexp(P(a2, .25, 1.0))
        card3d(c, SZ169.frame(t), 540, 820 + 8 * math.sin(t * .8), 880, 495, t, .06, lerp(-1.0, -.24, k), (1 - e) * 500, e, 4, edge=GOLD)
        card3d(c, SZ34.frame(t), 850, 1090 + 6 * math.sin(t), 270, 360, t, .05, lerp(-1.1, -.3, k2), (1 - e2) * 400 - 120, e2, 5, False, edge=GOLD)
        chip(c, '横屏', 100, 545, F('bold', 22), GOLD, INK, eo(P(a2, .6, .3)), r=6)
        chip(c, '竖版', 690, 885, F('bold', 22), GOLD, INK, eo(P(a2, .8, .3)), r=6)


cue(74.5, 'whoosh', .45)
for i in range(3): cue(74.7 + i * .18, 'swish', .35)
cue(77.4, 'whoosh', .5)


# ======================================================= 9. CREATIVE — 3D carousel 80–87
CR_T0, CR_T1 = 80.0, 87.0
CRE = [(Clip(FISH, 30.0, 800, 450, 'cover', t0=CR_T0, crop=CROP['fish']), '深海鱼群'),
       (Clip(ARTURA, 1.5, 800, 450, 'cover', t0=CR_T0, crop=CROP['artura']), '超跑展厅'),
       (Clip(DUCK, 4.0, 800, 450, 'cover', t0=CR_T0), '小黄鸭星球'),
       (Clip(SDGT, 100.0, 800, 450, 'cover', t0=CR_T0, crop=CROP['sdgt']), '水调歌头'),
       (Clip(DUCK2, 6.0, 800, 450, 'cover', t0=CR_T0), '鸭群爆发'),
       (Clip(SDGT, 40.0, 800, 450, 'cover', t0=CR_T0, crop=CROP['sdgt']), '月下楼阁')]
FINAL = Clip(FISH, 52.0, W, H, 'cover', t0=CR_T0, crop=CROP['fish'])
FOC = 1500.0


CAM = dict(cy=-150.0, oy=-80.0)


def proj(X, Y, Z, cam_z):
    z = Z - cam_z
    if z < 50: z = 50
    s = FOC / z
    return (W / 2 + X * s, H / 2 + CAM['oy'] + (Y - CAM['cy']) * s), s


@scene(CR_T0, CR_T1)
def s_creative(c, t):
    lt = t - CR_T0
    bg_dark(c, t, accent=ACC2, floor=False)
    # light rays from above
    for j in range(5):
        x0 = 120 + j * 220 + math.sin(t * .4 + j) * 50
        pth = skia.Path(); pth.moveTo(x0 - 30, -20); pth.lineTo(x0 + 30, -20); pth.lineTo(x0 + 260, H); pth.lineTo(x0 - 160, H); pth.close()
        c.drawPath(pth, paint(ACC if j % 2 else ACC2, .045, blur=30))
    hud(c, t, '更多 · 3D 创意动效', 1, ACC2, idx='08 / 10')
    # carousel: N cards on a ring, spinning, camera dolly; at the end fly through the front card
    N = len(CRE); R = 760.0; cw, chh = 560.0, 315.0
    def spin_at(u): return -u * .55 - 2.2 * eexp(P(u, 0, 1.6))
    off = -2 * math.pi * 1 - spin_at(5.6)                 # card 0 is dead centre when the fly-through starts
    spin = spin_at(min(lt, 5.6)) + off
    fly = eio(P(lt, 5.6, 1.4))
    base_z = lerp(-R - 1700, -R - 1200, eo(P(lt, 0, 3.5)))
    cam_z = lerp(base_z, -R - 330, fly)
    Y0 = 60.0
    CAM['cy'] = lerp(-150.0, Y0, fly); CAM['oy'] = lerp(-150.0, 0.0, fly)
    floor_y = Y0 + chh / 2 + 60
    items = []
    for i, (cl, lab) in enumerate(CRE):
        th = spin + i * 2 * math.pi / N
        X = R * math.sin(th); Z = -R * math.cos(th)
        items.append((Z, i, cl, lab, X, th, math.cos(th), math.sin(th)))
    items.sort(key=lambda v: -v[0])
    ka = eexp(P(lt, 0, 1.0))
    geo = []
    for (Z, i, cl, lab, X, th, tx, tz) in items:
        c3 = [(X - tx * cw / 2, Y0 - chh / 2, Z - tz * cw / 2), (X + tx * cw / 2, Y0 - chh / 2, Z + tz * cw / 2),
              (X + tx * cw / 2, Y0 + chh / 2, Z + tz * cw / 2), (X - tx * cw / 2, Y0 + chh / 2, Z - tz * cw / 2)]
        depth = clamp((R - Z) / (2 * R))
        a = ka * (.25 + .75 * depth) * (1 - .6 * fly * (i != 0))
        geo.append((Z, i, cl, lab, X, th, c3, a, depth, cl.frame(t)))
    # pass 1: reflections on the glossy floor, then the floor fade
    for (Z, i, cl, lab, X, th, c3, a, depth, img) in geo:
        rq = [proj(v[0], 2 * floor_y - v[1], v[2], cam_z)[0] for v in c3]
        quad_img(c, img, rq, a * .28)
    (fx_, fy), _ = proj(0, floor_y, -R, cam_z)
    (_, fy_back), _ = proj(0, floor_y, R, cam_z)
    sh = skia.GradientShader.MakeLinear([(0, fy_back), (0, H)], [CI(INK, .55), CI(INK, .35), CI(INK, .92)], [0, .3, 1])
    c.drawRect(skia.Rect.MakeLTRB(0, fy_back, W, H), skia.Paint(Shader=sh))
    line(c, 0, fy_back, W, fy_back, ACC, .22 * ka, 1.5)
    # pass 2: cards back to front
    for (Z, i, cl, lab, X, th, c3, a, depth, img) in geo:
        q = [proj(*v, cam_z)[0] for v in c3]; facing = math.cos(th)
        pth = quad_path(q)
        c.drawPath(pth, paint(ACC if i % 2 == 0 else ACC2, .35 * a * depth, blur=30))
        quad_img(c, img, q, a)
        c.drawPath(pth, paint(WHITE, .5 * a, stroke=1.5))
        if facing > .6 and img is not None:
            u = ((lt * .5 + i * .37) % 1.6) / 1.6
            sx = lerp(q[0][0] - 200, q[1][0] + 200, u)
            sh = skia.GradientShader.MakeLinear([(sx - 90, 0), (sx + 90, 0)], [CI(WHITE, 0), CI(WHITE, .22 * a), CI(WHITE, 0)])
            c.save(); c.clipPath(pth, doAntiAlias=True); c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh)); c.restore()
        if facing > .85 and fly < .2:
            (bx, by), s_ = proj(X, Y0 - chh / 2 - 40, Z, cam_z)
            chip(c, lab, bx, by - 30, F('bold', 26), ACC, INK, a * (facing - .85) / .15, align='c')
    # headline
    hk = 1 - fly
    slide_text(c, '模板之外，', 70, 220, F('heavy', 72), lt, 0, WHITE, a=hk, stagger=.05, glow=14, glow_rgb=ACC2)
    slide_text(c, '还能一起玩 3D 创意动效', 70, 310, F('heavy', 56), lt, .35, ACC, a=hk, stagger=.045, glow=14)
    # fly-through: the front video fills the screen, then flash
    if fly > 0:
        k = eio(P(lt, 6.1, .7))
        if k > 0:
            c.save(); s = lerp(.55, 1.0, k); c.translate(W / 2, H / 2); c.scale(s, s); c.translate(-W / 2, -H / 2)
            draw_img(c, FINAL.frame(t), 0, 0, W, H, k); c.restore()
        fl = P(lt, 6.05, .25)
        if 0 < fl < 1: c.drawRect(skia.Rect.MakeWH(W, H), paint(WHITE, (1 - fl) * .7))


cue(CR_T0, 'whoosh', .5); cue(CR_T0 + .1, 'riser', .35)
for i in range(6): cue(CR_T0 + .3 + i * .22, 'swish', .25)
cue(CR_T0 + 5.6, 'riser', .5); cue(CR_T0 + 6.05, 'impact', .55)


WALL_GEOM = (420, 1290, 520, 1500, 900)
WALL_TITLE_Y = 230
# ======================================================= 10. WALL 87–91  (component names on a tilted, scrolling 3D plane)
WALL_COLS, WALL_CW, WALL_RH = 4, 340, 74
WALL_TW = WALL_COLS * WALL_CW
_wall_order = COMPS + COMPS[17:] + COMPS[:17] + COMPS[29:] + COMPS[:29]      # repeat (shuffled) so the scroll never runs out
WALL_ROWS = (len(_wall_order) + WALL_COLS - 1) // WALL_COLS
WALL_TH = WALL_ROWS * WALL_RH


def wall_texture(lt):
    surf = skia.Surface(WALL_TW, WALL_TH); c = surf.getCanvas(); c.clear(skia.ColorTRANSPARENT)
    f = F('reg', 28)
    for i, s in enumerate(_wall_order):
        col, row = i % WALL_COLS, i // WALL_COLS
        x = col * WALL_CW + 10; y = row * WALL_RH + 8; w = WALL_CW - 20; h = WALL_RH - 16
        hot = (i * 13 + int(lt * 4)) % 9 == 0
        rrect(c, x, y, w, h, 12, ACC if hot else WHITE, .9 if hot else .06)
        if not hot: rrect(c, x + .5, y + .5, w - 1, h - 1, 12, WHITE, .14, stroke=1)
        text(c, s, x + w / 2, y + h / 2 + 10, fit(s, 'reg', 28, w - 30), INK if hot else WHITE, 1 if hot else .8, 'c')
    return surf.makeImageSnapshot()


def wall_plane(c, lt, top_y, bot_y, far_w, near_w, view_h, a=1.0):
    img = wall_texture(lt)
    sy = (lt * 95 + 40) % (WALL_TH - view_h)
    cx = W / 2
    dst = [(cx - far_w / 2, top_y), (cx + far_w / 2, top_y), (cx + near_w / 2, bot_y), (cx - near_w / 2, bot_y)]
    m = skia.Matrix()
    if not m.setPolyToPoly([skia.Point(0, 0), skia.Point(WALL_TW, 0), skia.Point(WALL_TW, view_h), skia.Point(0, view_h)], [skia.Point(*v) for v in dst]): return
    clip = skia.Path(); clip.moveTo(*dst[0])
    for v in dst[1:]: clip.lineTo(*v)
    clip.close()
    c.saveLayer(None, None)
    c.save(); c.clipPath(clip, doAntiAlias=True); c.concat(m)
    p = skia.Paint(AntiAlias=True); p.setAlphaf(a)
    c.drawImageRect(img, skia.Rect.MakeXYWH(0, sy, WALL_TW, view_h), skia.Rect.MakeWH(WALL_TW, view_h), LIN, p)
    c.restore()
    hgt = bot_y - top_y
    g = skia.GradientShader.MakeLinear([(0, top_y), (0, bot_y)],
                                       [CI((0, 0, 0), 0), CI((0, 0, 0), 1), CI((0, 0, 0), 1), CI((0, 0, 0), .15)], [0, .38, 1 - 130 / hgt, 1])
    gp = skia.Paint(Shader=g); gp.setBlendMode(skia.BlendMode.kDstIn)        # alpha fade: far end dissolves into the background
    c.drawRect(skia.Rect.MakeLTRB(0, top_y - 2, W, bot_y + 2), gp)
    c.restore()


@scene(87, 91)
def s_wall(c, t):
    bg_dark(c, t); lt = t - 87
    hud(c, t, '四十四个组件 · 跟随主题', 1, idx='09 / 10')
    k = eexp(P(lt, 0, 1.0))
    wall_plane(c, lt, *WALL_GEOM, a=k)
    tsz = 64 if W < H else 70
    slide_text(c, '四十四个组件，跟着主题自动换装', W / 2, WALL_TITLE_Y, fit('四十四个组件，跟着主题自动换装', 'heavy', tsz, W - 120), lt, 0, WHITE, align='c', stagger=.03)


for i in range(8): cue(87.6 + i * .3, 'pop', .12)


# ======================================================= 11. CTA 91–99
CMD = 'git clone https://github.com/imokya/xingor-video-skill.git ~/.claude/skills/xingor-video-skill'
CTA_T0, END_T, CTA_T1 = 91.0, 95.4, 99.0


@scene(91, 99)
def s_cta(c, t):
    lt = t - CTA_T0; bg_dark(c, t)
    if t < END_T:
        hud(c, t, '第四章 · 安装', 1, idx='10 / 10')
        k = spring(P(lt, 0, .7)); x, y, w, h = 50, 220 + (1 - k) * 200, 980, 300
        glass(c, x, y, w, h, 18, clamp(k * 1.4), edge_a=.5)
        for i, col in enumerate([(255, 95, 87), (254, 188, 46), (40, 200, 64)]): circle(c, x + 32 + i * 26, y + 30, 8, col, clamp(k))
        text(c, '终端', x + w / 2, y + 38, F('med', 18), GREY, clamp(k), 'c', sp=4)
        n = int(max(0, (lt - .4) * 52)); s = CMD[:n]; f = F('mono', 25)
        text(c, '$', x + 36, y + 120, f, ACC, clamp(k)); tx = x + 70; l1, l2 = s, ''
        while tw(l1, f) > w - 110: l2 = l1[-1] + l2; l1 = l1[:-1]
        text(c, l1, tx, y + 120, f, WHITE, clamp(k)); text(c, l2, tx, y + 162, f, WHITE, clamp(k))
        if int(lt * 2.4) % 2 == 0 and n < len(CMD):
            cx_ = tx + tw(l2 or l1, f); cy_ = y + (162 if l2 else 120); rrect(c, cx_ + 2, cy_ - 24, 13, 30, 2, ACC, 1)
        if n >= len(CMD): text(c, '安装完成', tx, y + 236, F('bold', 24), ACC, eo(P(lt, .4 + len(CMD) / 52 + .2, .3)), glow=8)
        slide_text(c, '装好之后，对它说一句：', 60, 680, F('heavy', 56), lt, 2.4, WHITE, stagger=.035, glow=12, glow_rgb=ACC)
        asks = ['帮我把口播视频剪一下，加字幕和特效', '做一个关于三星堆的文物纪录片', '把我的东北之旅做成旅行路线动画']
        for i, a in enumerate(asks):
            kk = spring(P(lt, 2.9 + i * .35, .6))
            if kk > 0:
                c.save(); c.translate(60, 740 + i * 96); c.scale(clamp(.6 + .4 * kk), clamp(.6 + .4 * kk))
                chip(c, '“' + a + '”', 0, 0, F('bold', 32), ACC if i == 2 else WHITE, INK, clamp(kk), 26, 70, maxw=960); c.restore()
        return
    a2 = t - END_T; k = eo(P(a2, 0, .6))
    tick_ring(c, W / 2, 600, 440, t, .45 * k); tick_ring(c, W / 2, 600, 380, -t, .3 * k, ACC, 60, -12)
    circle(c, W / 2, 600, 300, ACC, .07 * k, blur=90)
    f = F('disp', 210); y = H / 2 + 10
    e = eexp(P(a2, 0, 1.4)); y = 660
    ly = y + 26
    line(c, W / 2 - 400 * e, ly, W / 2 + 400 * e, ly, WHITE, .3, 1); circle(c, W / 2 + 400 * e, ly, 3.5, ACC, e)
    c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 0, W, ly - 2))
    f = F('disp', 200); word = 'xingor'; x = W / 2 - tw(word, f, 6) / 2
    for i, ch in enumerate(word):
        kk = eexp(P(a2, .1 + i * .06, 1.0)); p = paint(WHITE, 1)
        if kk < .98: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, (1 - kk) * 14 + .01))
        c.drawString(ch, x, y - 44 + (1 - kk) * 190, f, p); x += f.measureText(ch) + 6
    c.restore()
    y += 30
    slide_text(c, '会剪片的 AI 技能', W / 2, y + 84, F('heavy', 46), a2, .6, WHITE, align='c', stagger=.04, sp=8)
    kk = eexp(P(a2, 1.0, .8)); wbox = 760
    rrect(c, W / 2 - wbox / 2, y + 128, wbox, 64, 32, WHITE, .05 * kk); rrect(c, W / 2 - wbox / 2 + .5, y + 128.5, wbox - 1, 63, 32, ACC, .5 * kk, stroke=1)
    text(c, 'github.com/imokya/xingor-video-skill', W / 2, y + 169, fit('github.com/imokya/xingor-video-skill', 'mono', 26, wbox - 60), WHITE, kk, 'c')
    text(c, '开源　·　本地渲染　·　一句话出片', W / 2, y + 250, F('reg', 24), GREY, eexp(P(a2, 1.3, .8)), 'c', sp=3)
    fo = P(t, CTA_T1 - .6, .6)
    if fo > 0: c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), fo))


cue(91.4, 'swish', .3); cue(END_T, 'impact', .5)
for i in range(3): cue(93.9 + i * .35, 'pop', .4)


# ======================================================= 12. FOLLOW 99–end
FOLLOW_T0 = 99.0; FOLLOW_DUR = 4.2
FOL = Clip(FOLLOW, 0.0, W, H, 'fit', t0=FOLLOW_T0)             # whole 3:4 frame, no crop


@scene(99, 99 + FOLLOW_DUR)
def s_follow(c, t):
    c.clear(CI((0, 0, 0)))
    k = eo(P(t, FOLLOW_T0, .35)); fo = P(t, DUR_ - .5, .5)
    draw_img(c, FOL.frame(t), W / 2 - FOL.w / 2, H / 2 - FOL.h / 2, FOL.w, FOL.h, k * (1 - fo))


DUR = FOLLOW_T0 + FOLLOW_DUR
DUR_ = DUR

# ---------------------------------------------------------------- transitions: push-blur (zoom through + light streak)
TRANS = [7.0, 12.0, 16.0, 29.0, 33.5, 42.5, 47.5, 55.0, 62.0, 68.5, 74.5, 80.0, 87.0, 91.0, 99.0]
TD = .28
GLITCH = [16.0, 33.5]          # v1's RGB-split / row-offset glitch where the globe comes in
TRANS = [x for x in TRANS if x not in GLITCH]
for tb in GLITCH: cue(tb - .05, 'glitch', .55)


def post_glitch(arr, t):
    for tb in GLITCH:
        if -.1 <= t - tb < .14:
            r = np.random.RandomState(int(t * 1000)); sh = r.randint(14, 40); out = arr.copy()
            out[:, :, 0] = np.roll(arr[:, :, 0], sh, 1); out[:, :, 2] = np.roll(arr[:, :, 2], -sh, 1)
            for _ in range(7):
                y = r.randint(0, H - 60); hh = r.randint(8, 60); out[y:y + hh] = np.roll(out[y:y + hh], r.randint(-140, 140), 1)
            return out
    return arr
for tb in TRANS: cue(tb - .22, 'whoosh', .35)


# ---------------------------------------------------------------- voice-over + subtitles
VO_DIR = 'vo/full'
VO_AT = [1.2, 7.5, 12.3, 16.6, 29.3, 33.8, 42.8, 47.8, 55.3, 62.3, 68.8, 74.8, 80.3, 87.3, 91.4, 95.9]
VO = []
if os.path.exists(os.path.join(HERE, VO_DIR, 'vo.json')):
    for d, item in zip(VO_AT, json.load(open(os.path.join(HERE, VO_DIR, 'vo.json')))):
        VO.append(dict(t=d, dur=item['dur'], text=item['text'].replace('星哥儿', 'xingor'), file=os.path.join(HERE, VO_DIR, item['file'])))
KEYS = ['一句话', 'xingor video skill', 'AI 技能', '行程文件', '哈尔滨', '齐齐哈尔', '丹顶鹤', '成片', '五种风格', '四十四个组件',
        '三种画幅', '朱砂印章', '不用出镜', '3D 创意动效', '自动换装', '一句话就行', '去试试吧', '它画的']


def sub_chunks(item):
    chunks = []
    for sent in [x for x in re.split(r'[。！？]+', item['text']) if x.strip()]:
        cur = ''
        for p in [x for x in re.split(r'[，、；…]+', sent) if x.strip()]:
            if cur and len(cur) + len(p) <= 13: cur += ' ' + p
            else:
                if cur: chunks.append(cur)
                cur = p
        if cur: chunks.append(cur)
    n = sum(len(x) for x in chunks); t = item['t']; out = []
    for x in chunks:
        d = item['dur'] * len(x) / n; out.append((t, t + d, x)); t += d
    return out


SUBS = [ch for item in VO for ch in sub_chunks(item)]


def draw_subs(c, t):
    for (a, b, s) in SUBS:
        if a - .05 <= t < b + .05:
            f = fit(s, 'med', 46, W - 140); y = H - 80; w = tw(s, f); x = W / 2 - w / 2
            k = eo(P(t, a - .05, .12))
            rrect(c, x - 24, y - 50, w + 48, 68, 14, (0, 0, 0), .45 * k)
            spans = [(s.find(kw), s.find(kw) + len(kw)) for kw in KEYS if kw in s]; xx = x
            for i, ch in enumerate(s):
                ff = runs(ch, f)[0][1]; hl = any(a_ <= i < b_ for a_, b_ in spans)
                c.drawString(ch, xx, y, ff, paint(ACC if hl else WHITE, k)); xx += ff.measureText(ch)
            return


# ---------------------------------------------------------------- frame / audio / output
SCENES.sort(key=lambda x: x[0])
TOTAL_FRAMES = int(DUR * FPS)


def scene_at(t):
    for sc in SCENES:
        if sc[0] <= t < sc[1]: return sc
    return SCENES[-1]


def render_scene(t):
    surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(CI(INK))
    t0, t1, fn = scene_at(t)
    z = 1 + .025 * clamp((t - t0) / max(1e-3, t1 - t0)) if t < FOLLOW_T0 else 1      # slow camera push
    c.save(); c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-W / 2, -H / 2); fn(c, t); c.restore()
    return surf.makeImageSnapshot()


def push_blur(c, A, B, u):
    ea = eio(u)
    for img, s_, bl, al in ((A, 1 + .16 * ea, 34 * ea ** 1.5, 1 - clamp((u - .3) / .4)), (B, 1.14 - .14 * ea, 34 * (1 - ea) ** 1.5, clamp((u - .3) / .4))):
        if al <= 0: continue
        p = skia.Paint(AntiAlias=True); p.setAlphaf(al)
        if bl > .5: p.setImageFilter(skia.ImageFilters.Blur(bl, bl * .35, skia.TileMode.kClamp, None))
        c.save(); c.translate(W / 2, H / 2); c.scale(s_, s_); c.translate(-W / 2, -H / 2); c.drawImageRect(img, skia.Rect.MakeWH(W, H), LIN, p); c.restore()
    k = math.sin(math.pi * u)
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 160, W, 320), paint(ACC, .10 * k, blur=90))
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 2, W, 4), paint(WHITE, .5 * k ** 3, blur=6))


def render_frame(t):
    surf = skia.Surface(W, H); c = surf.getCanvas(); c.clear(CI(INK))
    tb = next((x for x in TRANS if abs(t - x) < TD), None)
    if tb is None: c.drawImage(render_scene(t), 0, 0)
    else: push_blur(c, render_scene(min(t, tb - 1 / FPS)), render_scene(max(t, tb)), (t - tb + TD) / (2 * TD))
    if t < FOLLOW_T0:
        vignette(c); grain(c, t); draw_subs(c, t); rrect(c, 0, H - 2, W * t / FOLLOW_T0, 2, 0, WHITE, .35)
    return post_glitch(surf.toarray(colorType=skia.kRGBA_8888_ColorType), t)


def read_wav(path):
    with wave.open(path) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32767
    return (x.reshape(-1, ch) if ch > 1 else x[:, None]), sr


def write_wav(path, x, sr):
    x = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.tobytes())


def resample(x, sr0, sr): return np.interp(np.arange(int(len(x) * sr / sr0)) / sr, np.arange(len(x)) / sr0, x) if sr0 != sr else x


def sfx_track(dur, sr):
    n = int(dur * sr) + sr * 2; out = np.zeros(n); cache = {}
    for (t, kind, g) in CUES:
        if kind not in cache: cache[kind] = resample(SFX.synth(kind), SFX.SR, sr)
        x = cache[kind]; i = int(t * sr)
        if 0 <= i < n: x = x[:n - i]; out[i:i + len(x)] += x * g
    r = np.random.RandomState(5); tt = np.arange(int(.02 * sr)) / sr
    for (t0, t1, cps) in [(.12, .9, 14), (55.5, 57.5, 16), (91.4, 93.2, 26)]:
        k = 0
        while t0 + k / cps < t1:
            i = int((t0 + k / cps) * sr); out[i:i + len(tt)] += r.randn(len(tt)) * np.exp(-tt * 400) * .1; k += 1
    return out[:int(dur * sr)]


def mix_audio(path):
    import music
    sr = music.SR; n = int(DUR * sr)
    secs = [(0, 'intro'), (7, 'groove'), (12, 'full'), (47.5, 'groove'), (68.5, 'break'), (80, 'full'), (87, 'build'), (91, 'outro')]
    bgm = music.make(FOLLOW_T0 + .3, secs, [7, 12, 80, 91])
    bgm = np.pad(bgm, ((0, max(0, n - len(bgm))), (0, 0)))[:n]
    sfx = sfx_track(DUR, sr); sfx = np.pad(sfx, (0, max(0, n - len(sfx))))[:n]
    vo = np.zeros(n); env = np.zeros(n)
    for item in VO:
        x, vsr = read_wav(item['file']); x = resample(x[:, 0], vsr, sr); i = int(item['t'] * sr); x = x[:n - i]; vo[i:i + len(x)] += x
        env[max(0, int((item['t'] - .15) * sr)):int((item['t'] + item['dur'] + .2) * sr)] = 1
    k = int(.25 * sr); env = np.convolve(env, np.ones(k) / k, 'same')
    vo = vo / (np.abs(vo).max() + 1e-9) * .9
    mix = bgm * (.5 * (1 - .55 * env))[:, None] + sfx[:, None] * .4 + vo[:, None]
    tmp = os.path.join(HERE, 'follow_audio.wav')
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', FOLLOW, '-vn', '-ac', '2', '-ar', str(sr), tmp], check=True)
    fa, _ = read_wav(tmp); i = int(FOLLOW_T0 * sr); fa = fa[:n - i]; mix[i:i + len(fa)] += fa / (np.abs(fa).max() + 1e-9) * .8
    mix = np.tanh(mix); write_wav(path, mix / (np.abs(mix).max() + 1e-9) * .95, sr)


def full(out):
    mix_audio(os.path.join(HERE, 'mix34.wav'))
    cmd = [FFMPEG, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', os.path.join(HERE, 'mix34.wav'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import time; t_start = time.time(); N = int(DUR * FPS)
    for i in range(N):
        p.stdin.write(render_frame(i / FPS).tobytes())
        if i % 300 == 0: print(f'{i}/{N}  {i / max(1e-3, time.time() - t_start):.1f} fps', flush=True)
    p.stdin.close(); p.wait(); print('done', out)


def test(times):
    os.makedirs(os.path.join(HERE, 'test'), exist_ok=True)
    from PIL import Image
    for tt in times:
        p = os.path.join(HERE, f'test/t_{tt:06.2f}.jpg'); Image.fromarray(render_frame(tt)[:, :, :3]).save(p, quality=86); print(p)


if __name__ == '__main__':
    if sys.argv[1] == 'full': full(sys.argv[2])
    else: test([float(x) for x in sys.argv[2:]])
