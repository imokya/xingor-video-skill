"""poetry-ink · 诗墨国风 theme.

Xuan-paper backgrounds, indigo ink type (Songti / Kaiti / Xingkai), cinnabar seal accents and slow, natural
ink-wash motion: characters bleed into the paper, landscapes wash in, mist drifts, seals stamp, petals fall and
scenes dissolve through spreading ink. A project selects it with  THEME = 'poetry-ink'  in scenes.py;
render.py then swaps grading, captions, transitions, the hook look and the sound palette.
"""
import math
import numpy as np
import skia
from fx import *
from components import Scene, PERSON, full_xf, dark_xf, mix_xf, spring

# ---- palette: "POETRY INK" ----
XUAN = (241, 238, 230)     # 宣纸 paper
XUAN_L = (248, 246, 240)   # lighter paper: cards, halos, caption halo
MO = (22, 44, 96)          # 青黛 indigo ink: headlines, captions
DAI = (92, 112, 148)       # 淡墨 diluted ink: ghost characters, near hills, hairlines
QIAN = (170, 181, 200)     # 浅 pale wash: far mountains, moon
ZHU = (200, 70, 40)        # 朱砂 cinnabar: seals, dots, keywords (the only warm accent)
HUI = (100, 104, 114)      # grey body text
NUMS = '壹贰叁肆伍陆柒捌玖拾'
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)

# ------------------------------------------------------------------ textures (built once, lazily)
_TEX = {}


def _noise(w, h, cx, cy, seed):
    """smooth value noise in [-.5, .5]; cx/cy = feature size in px (cx >> cy gives horizontal fibres)."""
    from PIL import Image
    r = np.random.RandomState(seed)
    sm = (r.rand(h // cy + 3, w // cx + 3) * 255).astype(np.uint8)
    im = Image.fromarray(sm).resize(((w // cx + 3) * cx, (h // cy + 3) * cy), Image.BICUBIC)
    return np.asarray(im, np.float32)[cy:cy + h, cx:cx + w] / 255 - .5


def paper_img():
    """1920x1080 xuan paper: soft blotches, fibres, grain and slightly aged edges."""
    if 'paper' not in _TEX:
        r = np.random.RandomState(5)
        lum = _noise(W, H, 260, 260, 1) * 12 + _noise(W, H, 60, 60, 2) * 6 + _noise(W, H, 90, 6, 3) * 5 + (r.rand(H, W) - .5) * 6
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        lum -= ((xx / W - .5) ** 2 * 1.2 + (yy / H - .5) ** 2) * 22
        rgb = np.array(XUAN, np.float32) + lum[..., None] * np.array([1.0, .98, .9], np.float32)
        arr = np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
        surf = skia.Surface(W, H); c = surf.getCanvas()
        c.drawImage(skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType), 0, 0)
        for _ in range(900):
            x, y = r.rand() * W, r.rand() * H; L = r.uniform(8, 40); ang = r.uniform(0, math.pi)
            p = skia.Path(); p.moveTo(x, y)
            p.quadTo(x + math.cos(ang) * L * .5 + r.uniform(-5, 5), y + math.sin(ang) * L * .5 + r.uniform(-5, 5),
                     x + math.cos(ang) * L, y + math.sin(ang) * L)
            c.drawPath(p, paint((150, 140, 120) if r.rand() < .6 else WHITE, r.uniform(.04, .1), stroke=r.uniform(.6, 1.3)))
        _TEX['paper'] = surf.makeImageSnapshot()
    return _TEX['paper']


def brush_img():
    """alpha mask with streaky gaps: multiplied into ghost characters / hills for a dry-brush (飞白) texture."""
    if 'brush' not in _TEX:
        r = np.random.RandomState(9)
        n = _noise(W, H, 90, 5, 4) * .7 + _noise(W, H, 12, 12, 5) * .5 + (r.rand(H, W) - .5) * .9
        al = (np.clip(.86 + n * 1.1, 0, 1) * 255).astype(np.uint8)
        arr = np.dstack([np.full((H, W, 3), 255, np.uint8), al])
        _TEX['brush'] = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType,
                                             alphaType=skia.kUnpremul_AlphaType)
    return _TEX['brush']


def stipple_img():
    """alpha mask of fine stippled dots: worn letterpress / rubbing texture (the reference's 苏轼)."""
    if 'stipple' not in _TEX:
        r = np.random.RandomState(13)
        n = _noise(W, H, 40, 40, 6) * .9 + (r.rand(H, W) - .5) * 1.25
        al = (np.clip((n + .5) * 3.0, 0, 1) * 255).astype(np.uint8)
        arr = np.dstack([np.full((H, W, 3), 255, np.uint8), al])
        _TEX['stipple'] = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType,
                                               alphaType=skia.kUnpremul_AlphaType)
    return _TEX['stipple']


def dry(c, tex='brush'):
    """apply a texture mask to the current layer (call inside saveLayer): 'brush' (飞白) or 'stipple' (拓印)."""
    img = stipple_img() if tex == 'stipple' else brush_img()
    c.drawImage(img, 0, 0, SAMP, skia.Paint(BlendMode=skia.BlendMode.kDstIn))


# ------------------------------------------------------------------ backgrounds & atmosphere
BACKDROP = None      # image path: a painted page background (cover-fit, slow drift) instead of procedural paper
SAFE = None          # (x0, x1) fractions: where paper-layout (P*) content lives, e.g. (0, .62) keeps a painting's
                     # subject on the right clear; content is laid out as if that box were the whole frame
VEIL = .6            # strength of the paper veil over SAFE that keeps text readable on the painting
_SCENERY_OFF = False # set while drawing P* content on a backdrop: generated hills / water / landscapes are skipped


def backdrop_img(path=None):
    path = path or BACKDROP
    if ('backdrop', path) not in _TEX:
        from PIL import Image
        im = Image.open(path).convert('RGB')
        k = max(W / im.width, H / im.height) * 1.1          # cover-fit with room to drift
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        arr = np.dstack([np.asarray(im), np.full((im.height, im.width), 255, np.uint8)])
        _TEX[('backdrop', path)] = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)
    return _TEX[('backdrop', path)]


def backdrop_bg(c, t, a=1.0, path=None, safe=None, veil=None):
    """the painting, drifting very slowly, with mist over it and a paper veil on the safe band.
    a < 1 lays it faintly onto the paper (a faded background)."""
    safe = safe if safe is not None else SAFE
    veil = VEIL if veil is None else veil
    if a < 1: ink_bg(c, t)
    img = backdrop_img(path)
    s_ = 1.0 + .03 * (.5 + .5 * math.sin(t * .06))
    dx = (img.width() * s_ - W) / 2 + math.sin(t * .045) * 12
    dy = (img.height() * s_ - H) / 2 + math.cos(t * .05) * 6
    c.save(); c.translate(-dx, -dy); c.scale(s_, s_); c.drawImage(img, 0, 0, SAMP, skia.Paint(Alphaf=a)); c.restore()
    mist(c, t, H * .55, H * .75, .35 * a, 77, 4)
    if safe and veil > 0:
        x0, x1 = safe[0] * W, safe[1] * W
        x2 = x1 + W * .08
        sh = skia.GradientShader.MakeLinear([(x0, 0), (x2, 0)], [CI(XUAN_L, veil), CI(XUAN_L, veil * .75), CI(XUAN_L, 0)],
                                            [0, (x1 - x0) / (x2 - x0) * .85, 1])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
def ink_bg(c, t, a=1.0):
    c.drawImage(paper_img(), 0, 0)
    if a < 1: c.drawRect(skia.Rect.MakeWH(W, H), paint(XUAN, 1 - a))


def mist(c, t, y0, y1, a=.7, seed=0, n=4, rgb=XUAN_L):
    """wide drifting cloud bands (云雾)."""
    r = np.random.RandomState(seed)
    for _ in range(n):
        w = r.uniform(520, 950); h = r.uniform(40, 95)
        x = (r.uniform(-300, W) + t * r.uniform(8, 22)) % (W + 900) - 450
        y = r.uniform(y0, y1) + math.sin(t * .3 + r.rand() * 6) * 8
        c.drawOval(skia.Rect.MakeXYWH(x - w / 2, y - h / 2, w, h), paint(rgb, a * r.uniform(.5, 1), blur=h * .6))


def bottom_mist(c, a=.75, y0=None):
    """paper fog rising from the bottom edge: grounds the cutout and carries the captions."""
    y0 = H - 230 if y0 is None else y0
    sh = skia.GradientShader.MakeLinear([(0, y0), (0, H)], [CI(XUAN_L, 0), CI(XUAN_L, a * .75), CI(XUAN_L, a)], [0, .55, 1])
    c.drawRect(skia.Rect.MakeLTRB(0, y0, W, H), skia.Paint(Shader=sh))


def left_mist(c, t, a=.85, x1=1150):
    """paper fog from the left over real video, so ink type stays legible (留白)."""
    if a <= 0: return
    sh = skia.GradientShader.MakeLinear([(0, 0), (x1, 0)], [CI(XUAN_L, a), CI(XUAN_L, a * .85), CI(XUAN_L, 0)], [0, .5, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    for i in range(3):
        y = 180 + i * 280 + math.sin(t * .35 + i * 2) * 40
        c.drawOval(skia.Rect.MakeXYWH(x1 * .45 + math.sin(t * .2 + i) * 60, y - 120, x1 * .5, 240), paint(XUAN_L, a * .35, blur=60))


class Petals:
    """falling plum petals: slow, sparse, swaying."""

    def __init__(self, n=40, seed=8):
        r = np.random.RandomState(seed)
        self.x = r.rand(n) * W; self.y = r.rand(n) * H
        self.vx = r.uniform(10, 30, n); self.vy = r.uniform(16, 36, n)
        self.ph = r.rand(n) * 6.28; self.rs = r.uniform(-1.5, 1.5, n); self.s = r.uniform(.7, 1.3, n)
        self.col = r.rand(n)

    def draw(self, c, t, n, a=1.0):
        for i in range(min(n, len(self.x))):
            x = (self.x[i] + self.vx[i] * t + math.sin(t * .9 + self.ph[i]) * 30) % (W + 40) - 20
            y = (self.y[i] + self.vy[i] * t) % (H + 40) - 20
            c.save(); c.translate(x, y); c.rotate(math.degrees(self.ph[i] + t * self.rs[i]))
            c.scale(self.s[i], self.s[i] * (.55 + .45 * abs(math.sin(t * 1.3 + self.ph[i]))))
            rgb = ZHU if self.col[i] < .35 else (226, 150, 140)
            c.drawOval(skia.Rect.MakeXYWH(-7, -4, 14, 8), paint(rgb, a * (.3 + .25 * self.col[i])))
            c.restore()


PETALS = Petals()


# ------------------------------------------------------------------ ink type
# ------------------------------------------------------------------ ink diffusion (晕染)
# Ink is modelled with an arrival-time map: 0 where the brush first touches (a few drop points), growing with
# distance plus multi-scale paper-fibre noise. A frame at progress p shows everything the ink has reached, with a
# darker wet front and a feathered halo that soaks past the strokes and dries to a faint water mark (水痕).
INK_SLOW = 1.0        # pace multiplier for text / ghost entrances
INK_TEXT = 'fade'     # 'fade' = clean, restrained entrance (default) | 'diffuse' = characters soak in like ink
INK_BLOOM = False     # ink drops behind punch words (off by default: ink is kept for the page turns)
TURN = 'ink'          # page turns between scenes: 'ink' (水墨晕开) | 'punch' (quick push-in + paper flash) | 'cut'
                      # use 'punch' when the footage shown already has its own ink turns (don't stack two)
FIELD_MAX = 300       # glyph fields are computed at most this many px tall, then scaled up
_FIELD = {}


def _blur(a, r):
    from PIL import Image, ImageFilter
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255


def _arrival(h, w, seeds, seed, rough=.2):
    """ink arrival time in px: distance from the drop points (x, y, radius) + paper-fibre noise."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.full((h, w), 1e9, np.float32)
    for sx, sy, r0 in seeds:
        d = np.minimum(d, np.hypot(xx - sx, yy - sy) - r0)
    d = np.maximum(d, 0)
    S = max(h, w)
    n = (_noise(w, h, max(2, S // 5), max(2, S // 5), seed) + _noise(w, h, max(2, S // 16), max(2, S // 16), seed + 1) * .6
         + _noise(w, h, max(2, S // 45), max(2, S // 45), seed + 2) * .45)
    return d + n * rough * S, n


def _img(alpha, rgb):
    arr = np.empty(alpha.shape + (4,), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    arr[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


def _glyph_field(ch, f):
    tf = f.getTypeface(); size = f.getSize()
    key = (ch, tf.getFamilyName(), tf.fontStyle().weight(), round(size, 1))
    if key in _FIELD: return _FIELD[key]
    k = min(1.0, FIELD_MAX / size)
    m = f.getMetrics()
    pad = int(size * k * .28) + 4
    asc, desc = int(math.ceil(-m.fAscent * k)), int(math.ceil(m.fDescent * k))
    w, h = int(f.measureText(ch) * k) + 2 * pad, asc + desc + 2 * pad
    surf = skia.Surface(w, h); cc = surf.getCanvas(); cc.clear(skia.ColorTRANSPARENT)
    cc.translate(pad, pad + asc); cc.scale(k, k)
    cc.drawString(ch, 0, 0, f, paint(WHITE))
    G = surf.makeImageSnapshot().toarray()[..., 3].astype(np.float32) / 255
    ys, xs = np.where(G > .5)
    if len(xs) == 0:
        _FIELD[key] = None; return None
    sd = (ord(ch) * 7919) % 100003
    r = np.random.RandomState(sd)
    idx = r.choice(len(xs), min(len(xs), 2 + r.randint(0, 3)), replace=False)
    A, n = _arrival(h, w, [(xs[i], ys[i], size * k * r.uniform(.02, .06)) for i in idx], sd % 997, rough=.16)
    A /= max(1e-3, A[G > .3].max())
    halo = np.clip(_blur(G, max(2, size * k * .09)) * 2.2, 0, 1)
    fib = np.clip(.5 + _noise(w, h, 4, 4, sd % 991 + 5) * 1.6 + n * .7, 0, 1)    # capillary feathering
    grain = .84 + .16 * np.clip(_noise(w, h, 3, 3, sd % 983 + 7) * 2 + .5, 0, 1)
    fd = dict(G=G, A=A, H=halo * fib, grain=grain, k=k, pad=pad, asc=asc)
    _FIELD[key] = fd
    return fd


def _glyph_alpha(fd, p):
    """wet ink first spills softly past the strokes from the drop points, then settles and sharpens into the
    character as it dries, leaving a faint water mark."""
    x = p * 1.25 - fd['A']
    G = fd['G']
    core = G * np.clip(x / .12, 0, 1)
    r = fd['G'].shape[0] * .035 * (1 - p) ** 1.3
    if r > .6: core = np.clip(_blur(core, r) * 1.15, 0, 1)
    core *= lerp(fd['grain'], 1.0, p ** 3) * lerp(.7, 1, p)
    reach = np.clip(x / .16, 0, 1)
    spill = fd['H'] * reach * (.5 * (1 - p) ** .8 + .16)
    band = fd['H'] * np.exp(-((x - .03) / .07) ** 2) * .35 * (1 - p)
    return 1 - (1 - core) * (1 - spill) * (1 - band)


def _glyph(c, ch, x, y, f, rgb, a, p, rise=10):
    """one character entering: a clean fade with a slight rise and a short soft-focus (INK_TEXT='fade'), or
    soaking into the paper from a few drop points (INK_TEXT='diffuse')."""
    if p <= 0 or a <= 0: return
    if INK_TEXT == 'diffuse': return _glyph_diffuse(c, ch, x, y, f, rgb, a, p)
    e = eo(p)
    blur = 6 * (1 - e) ** 2
    c.drawString(ch, x, y + rise * (1 - e), f, paint(rgb, a * e, blur=blur if blur > .3 else 0))


def _glyph_diffuse(c, ch, x, y, f, rgb, a, p):
    """one character soaking into the paper from a few drop points (see the diffusion notes above)."""
    if p <= 0 or a <= 0: return
    fd = _glyph_field(ch, f)
    if fd is None:
        c.drawString(ch, x, y, f, paint(rgb, a * clamp(p * 2))); return
    k = fd['k']
    c.save(); c.translate(x - fd['pad'] / k, y - (fd['pad'] + fd['asc']) / k); c.scale(1 / k, 1 / k)
    if p >= 1:   # dry: cached water mark + crisp vector glyph
        hk = ('halo', rgb)
        if hk not in fd: fd[hk] = _img(fd['H'] * .16, rgb)
        c.drawImage(fd[hk], 0, 0, SAMP, skia.Paint(Alphaf=a))
        c.restore()
        c.drawString(ch, x, y, f, paint(rgb, a))
        return
    c.drawImage(_img(_glyph_alpha(fd, p), rgb), 0, 0, SAMP, skia.Paint(Alphaf=a))
    c.restore()


def ink_text(c, s, x, y, f, t, t0, rgb=MO, a=1.0, stagger=.08, dur=.9, align='l', spacing=0):
    """horizontal ink-bleed text, one character after another. Returns the width."""
    ws = [f.measureText(ch) for ch in s]
    total = sum(ws) + spacing * max(0, len(s) - 1)
    if align == 'c': x -= total / 2
    elif align == 'r': x -= total
    xx = x
    for i, ch in enumerate(s):
        if ch != ' ': _glyph(c, ch, xx, y, f, rgb, a, P(t, t0 + i * stagger, dur * INK_SLOW))
        xx += ws[i] + spacing
    return total


def ink_vtext(c, s, x, y, f, t, t0, rgb=MO, a=1.0, stagger=.12, dur=1.0, step=None):
    """vertical (竖排) text, top to bottom, centred on column x; y = first baseline. Spaces leave half a gap."""
    step = step or f.getSize() * 1.18
    yy = y; k = 0
    for ch in s:
        if ch == ' ':
            yy += step * .5; continue
        _glyph(c, ch, x - f.measureText(ch) / 2, yy, f, rgb, a, P(t, t0 + k * stagger, dur * INK_SLOW))
        yy += step; k += 1
    return yy - y


def ghost(c, ch, x, y, size, t, t0, rgb=DAI, a=.45, font='song', dur=2.0, tex='brush'):
    """huge, pale dry-brush character half off the frame (the reference's 美 / 感)."""
    p = P(t, t0, dur * INK_SLOW)
    if p <= 0 or a <= 0: return
    f = F(font, size)
    w = f.measureText(ch)
    c.saveLayer(skia.Rect.MakeLTRB(x - 80, y - size * 1.1, x + w + 80, y + size * .35))
    _glyph(c, ch, x, y, f, rgb, a, p, rise=0)
    dry(c, tex)
    c.restore()


def ink_label(c, s, x, y, a=1.0, rgb=MO, size=24, dot=True, spacing=6, font='songr'):
    """small letter-spaced label with a cinnabar dot (● AI 赋能表达)."""
    if a <= 0: return 0
    if dot: circle(c, x + 6, y - size * .36, 6, ZHU, a)
    return text(c, s, x + (26 if dot else 0), y, F(font, size), rgb, a, spacing=spacing)


def ink_title(c, t, t0, label, title, x=120, a=1.0):
    if label: ink_label(c, label, x, 160, a * eo(P(t, t0, .6)))
    if title: ink_text(c, title, x, 250, F('song', 66), t, t0 + .15, MO, a, stagger=.06)


# ------------------------------------------------------------------ marks: seal, brush, bloom, blob
def seal(c, s, cx, cy, size, t, t0, a=1.0, rgb=ZHU, font='kai', seed=0, rot=-3):
    """cinnabar seal (印章, 阴文: paper-coloured characters cut into red) that stamps down."""
    p = P(t, t0, .35)
    if p <= 0 or a <= 0: return
    k = eo(p); al = a * clamp(p * 2.5)
    c.save(); c.translate(cx, cy); c.rotate(rot); sc = lerp(1.5, 1, k); c.scale(sc, sc)
    h = size / 2
    rrect(c, -h, -h, size, size, size * .1, rgb, al * .92)
    n = len(s)
    if n == 1:
        pos, fs = [(0, 0)], size * .7
    elif n == 2:
        pos, fs = [(0, -size * .22), (0, size * .22)], size * .4
    else:
        pos, fs = [(size * .22, -size * .22), (size * .22, size * .22), (-size * .22, -size * .22), (-size * .22, size * .22)][:n], size * .38
    f = F(font, fs)
    for ch, (px, py) in zip(s, pos):
        text(c, ch, px - f.measureText(ch) / 2, py + fs * .36, f, XUAN_L, al)
    r = np.random.RandomState(seed)
    for _ in range(int(size * .7)):  # weathering: paper showing through
        u, v = r.uniform(-h, h), r.uniform(-h, h)
        if r.rand() < .5: u = math.copysign(h - r.uniform(0, size * .06), u)
        circle(c, u, v, r.uniform(.6, 1.8) * size / 60, XUAN_L, al * r.uniform(.3, .8))
    c.restore()


def brush_stroke(c, x0, y0, x1, y1, w=10, rgb=ZHU, a=1.0, prog=1.0, seed=0, bend=.04):
    """a single tapered brush stroke made of bristles, with dry gaps on the outer hairs; prog draws it on."""
    if prog <= 0 or a <= 0: return
    r = np.random.RandomState(seed)
    dx, dy = x1 - x0, y1 - y0
    L = max(1e-3, math.hypot(dx, dy)); nx, ny = -dy / L, dx / L
    mx, my = (x0 + x1) / 2 + nx * bend * L, (y0 + y1) / 2 + ny * bend * L
    n = max(6, int(w * 1.2))
    for i in range(n):
        o = (i / (n - 1) - .5) * w
        edge = abs(o) / (w / 2)
        st = r.rand() * .05 * edge
        en = prog * (1 - r.rand() * .2 * edge)
        if en <= st: continue
        pth = skia.Path(); pth.moveTo(x0 + nx * o * .6, y0 + ny * o * .6)
        pth.quadTo(mx + nx * o, my + ny * o, x1 + nx * o * .35, y1 + ny * o * .35)
        p = paint(rgb, a * (.55 + .45 * r.rand()), stroke=max(1.2, w / n * 1.9))
        if edge > .5:
            p.setPathEffect(skia.DashPathEffect.Make([r.uniform(20, 70), r.uniform(2, 10)], r.uniform(0, 40)))
        c.drawPath(partial_path(pth, st, en), p)


def blob_path(cx, cy, R, seed=0, rough=.12, t=0.0, n=120):
    """organic ink-spread outline."""
    r = np.random.RandomState(seed)
    ks = [3, 5, 7, 11, 17]; ph = r.rand(len(ks)) * 6.28
    pth = skia.Path()
    for i in range(n + 1):
        th = i / n * 2 * math.pi
        rr = R * (1 + sum(rough / (1 + j * .6) * math.sin(k * th + ph[j] + t * .5) for j, k in enumerate(ks)))
        x, y = cx + rr * math.cos(th), cy + rr * math.sin(th)
        if i == 0: pth.moveTo(x, y)
        else: pth.lineTo(x, y)
    pth.close()
    return pth


def _bloom_field(seed):
    key = ('bloom', seed)
    if key not in _FIELD:
        S = 240; r = np.random.RandomState(seed + 300)
        seeds = [(S / 2, S / 2, S * .04)] + [(S / 2 + r.uniform(-1, 1) * S * .16, S / 2 + r.uniform(-1, 1) * S * .16, S * .015)
                                             for _ in range(2)]
        A, n = _arrival(S, S, seeds, seed + 301, rough=.3)
        A /= S * .5
        fib = np.clip(.6 + _noise(S, S, 4, 4, seed + 302) * 1.2 + n * .6, 0, 1)
        yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
        win = np.clip((1 - np.hypot(xx - S / 2, yy - S / 2) / (S / 2)) / .15, 0, 1)   # round, never the sprite edge
        _FIELD[key] = dict(A=A, fib=fib, S=S, win=win)
    return _FIELD[key]


def ink_bloom(c, cx, cy, t, t0, R=180, rgb=MO, a=.28, seed=0, dur=1.8):
    """an ink drop landing on wet paper: it creeps outward along the fibres with a darker wet rim, then dries
    into a lighter stain that stays (墨滴晕开)."""
    if not INK_BLOOM: return
    p = P(t, t0, dur * INK_SLOW)
    if p <= 0 or a <= 0: return
    fd = _bloom_field(seed)
    if p >= 1 and ('dry', rgb) in fd:
        img = fd[('dry', rgb)]
    else:
        x = eo(p) * .95 - fd['A']
        edge = lerp(fd['fib'], 1.0, np.clip(x / .25, 0, 1))          # fibrous only where it is still spreading
        stain = np.clip(x / .1, 0, 1) * (.3 + .7 * np.clip(1 - fd['A'], 0, 1) ** 1.5) * edge
        band = np.exp(-((x - .02) / .06) ** 2) * fd['fib'] * (1 - p) * .6
        al = _blur(np.clip(stain * lerp(1, .5, clamp((p - .5) / .5)) + band, 0, 1) * fd['win'], 1.2)
        img = _img(al, rgb)
        if p >= 1: fd[('dry', rgb)] = img
    S = fd['S']; sc = 2 * R / S * 1.15
    c.save(); c.translate(cx - S * sc / 2, cy - S * sc / 2); c.scale(sc, sc)
    c.drawImage(img, 0, 0, SAMP, skia.Paint(Alphaf=clamp(a * 2.2)))
    c.restore()


def chamfer(x, y, w, h, k=24):
    p = skia.Path()
    p.moveTo(x + k, y); p.lineTo(x + w - k, y); p.lineTo(x + w, y + k); p.lineTo(x + w, y + h - k)
    p.lineTo(x + w - k, y + h); p.lineTo(x + k, y + h); p.lineTo(x, y + h - k); p.lineTo(x, y + k); p.close()
    return p


def paper_card(c, x, y, w, h, a=1.0, k=24):
    """lighter paper sheet with cut corners and a soft drop shadow."""
    if a <= 0: return
    pth = chamfer(x, y, w, h, k)
    sh = chamfer(x + 8, y + 22, w - 16, h - 10, k)
    c.drawPath(sh, paint((60, 60, 70), .16 * a, blur=26))
    c.drawPath(pth, paint(XUAN_L, .9 * a))
    c.drawPath(pth, paint(WHITE, .8 * a, stroke=2))
    c.drawPath(pth, paint(MO, .06 * a, stroke=1))


def wash_mask(c, x0, x1, y0, y1, p, soft=380, seed=0):
    """inside a saveLayer: reveal the layer left -> right behind a soft edge (call after drawing)."""
    edge = x0 - 20 + (x1 - x0 + soft + 40) * eio(clamp(p))
    sh = skia.GradientShader.MakeLinear([(edge - soft, 0), (edge, 0)], [CI(WHITE, 1), CI(WHITE, 0)])
    c.drawRect(skia.Rect.MakeLTRB(x0 - 400, y0 - 400, x1 + 400, y1 + 400), skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kDstIn))


# ------------------------------------------------------------------ torn paper (撕纸)
def torn_points(x0, y0, x1, y1, seed=0, rough=12, step=6):
    """ragged points from (x0,y0) to (x1,y1): a smoothed random walk + fine jags, like a hand tear."""
    r = np.random.RandomState(seed)
    L = max(1.0, math.hypot(x1 - x0, y1 - y0)); n = max(2, int(L / step))
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    pts, off = [], 0.0
    for i in range(n + 1):
        u = i / n
        off = .85 * off + r.uniform(-1, 1) * rough * .45
        d = (off + r.uniform(-1, 1) * rough * .3) * math.sin(math.pi * u) ** .15
        pts.append((x0 + (x1 - x0) * u + nx * d, y0 + (y1 - y0) * u + ny * d))
    return pts


def torn_rect(x, y, w, h, sides='trbl', seed=0, rough=12):
    """rectangle whose listed sides (t, r, b, l) are torn."""
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pth = skia.Path(); pth.moveTo(*corners[0])
    for k, side in enumerate('trbl'):
        a_, b_ = corners[k], corners[(k + 1) % 4]
        if side in sides:
            for px, py in torn_points(a_[0], a_[1], b_[0], b_[1], seed + k * 7, rough)[1:]: pth.lineTo(px, py)
        else:
            pth.lineTo(*b_)
    pth.close()
    return pth


def paper_piece(c, pth, a=1.0, rgb=XUAN_L, shadow=.22, fiber=True, seed=0):
    """a piece of xuan paper with a soft shadow and the white fibrous rim a real tear leaves."""
    if a <= 0: return
    if shadow:
        sh = skia.Path(pth); sh.offset(7, 12)
        c.drawPath(sh, paint((40, 40, 50), shadow * a, blur=14))
    b = pth.computeTightBounds()
    c.save(); c.clipPath(pth, skia.ClipOp.kIntersect, True)
    c.drawPath(pth, paint(XUAN, a))
    c.drawImage(paper_img(), b.left(), b.top(), SAMP, skia.Paint(Alphaf=a))
    c.drawPath(pth, paint(rgb, .55 * a))
    c.restore()
    if fiber:
        r = np.random.RandomState(seed)
        c.drawPath(pth, paint(WHITE, .95 * a, stroke=4, blur=1.2))
        p = paint(WHITE, .75 * a, stroke=9, blur=2.5)
        p.setPathEffect(skia.DashPathEffect.Make([r.uniform(6, 30), r.uniform(4, 22)], r.uniform(0, 20)))
        c.drawPath(pth, p)
        c.drawPath(pth, paint((150, 140, 125), .18 * a, stroke=1))


# ------------------------------------------------------------------ landscape (山水)
def mountain_layer(c, peaks, base, rgb, a, seed=0, x0=-100, x1=W + 100, detail=.05, blur=2.0, depth=180):
    """peaks = [(cx, height, width)]. Ridge = summed bumps + jagged detail; ink fades downward into mist."""
    if _SCENERY_OFF: return
    if a <= 0: return
    r = np.random.RandomState(seed)
    xs = np.linspace(x0, x1, 260)
    ys = np.zeros_like(xs)
    for cx, h, w in peaks: ys += h * np.exp(-((xs - cx) / w) ** 2)
    det = sum(np.sin(xs / (22 + k * 26) + r.rand() * 6.28) / (k + 1) for k in range(5)) + .25 * np.sin(xs / 6 + r.rand() * 6.28)
    top = base - ys * (1 + detail * det)
    pth = skia.Path(); pth.moveTo(xs[0], base + depth)
    for x, y in zip(xs, top): pth.lineTo(float(x), float(y))
    pth.lineTo(xs[-1], base + depth); pth.close()
    sh = skia.GradientShader.MakeLinear([(0, float(top.min())), (0, base + depth)], [CI(rgb, a), CI(rgb, a * .5), CI(rgb, 0)], [0, .45, 1])
    pp = skia.Paint(AntiAlias=True, Shader=sh)
    if blur: pp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawPath(pth, pp)
    rp = skia.Path(); rp.moveTo(float(xs[0]), float(top[0]))
    for x, y in zip(xs[1:], top[1:]): rp.lineTo(float(x), float(y))
    c.drawPath(rp, paint(rgb, a * .45, stroke=2.2, blur=1.2))


def boat(c, x, y, s=1.0, a=1.0, rgb=MO):
    """a fisherman's skiff (孤舟) with its reflection."""
    if a <= 0: return
    for flip, al in [(1, a), (-1, a * .14)]:
        c.save(); c.translate(x, y); c.scale(s, s * flip)
        hull = skia.Path(); hull.moveTo(-44, -2); hull.quadTo(0, 16, 48, -7); hull.quadTo(0, 7, -44, -2); hull.close()
        c.drawPath(hull, paint(rgb, al))
        line(c, 4, -18, 2, -3, rgb, al, 5)
        hat = skia.Path(); hat.moveTo(-11, -19); hat.lineTo(4, -27); hat.lineTo(19, -19); hat.close()
        c.drawPath(hat, paint(rgb, al))
        line(c, 8, -12, 46, -52, rgb, al * .8, 1.4)
        c.restore()


def birds(c, t, x, y, n=4, a=1.0, seed=0, rgb=MO):
    r = np.random.RandomState(seed)
    for i in range(n):
        bx = x + r.uniform(-90, 90) + t * r.uniform(12, 24) % 600
        by = y + r.uniform(-40, 40) + math.sin(t * .8 + i) * 8
        f = .3 + .7 * abs(math.sin(t * 5 + r.rand() * 6))
        sc = r.uniform(.7, 1.2)
        p = skia.Path(); p.moveTo(bx - 9 * sc, by - 5 * f * sc); p.quadTo(bx - 4 * sc, by - 2 * sc, bx, by)
        p.quadTo(bx + 4 * sc, by - 2 * sc, bx + 9 * sc, by - 5 * f * sc)
        c.drawPath(p, paint(rgb, a * .7, stroke=1.6))


def water(c, t, x0, x1, y0, y1, a=1.0, seed=0):
    """faint horizontal brush lines that drift: still water."""
    if _SCENERY_OFF: return
    r = np.random.RandomState(seed)
    for _ in range(16):
        y = r.uniform(y0, y1); L = r.uniform(30, 160)
        x = x0 + ((r.uniform(0, x1 - x0) + t * r.uniform(3, 9)) % (x1 - x0))
        line(c, x, y, x + L, y, DAI, a * r.uniform(.12, .3), r.uniform(1, 2))


def landscape(c, t, x0, x1, horizon, a=1.0, seed=0, scale=1.0, boat_x=.42, has_birds=True):
    """layered ink mountains + mist + water + boat + birds between x0..x1, standing on `horizon`."""
    if _SCENERY_OFF: return
    if a <= 0: return
    span = x1 - x0; s = scale
    mountain_layer(c, [(x0 + span * .22, 150 * s, span * .11), (x0 + span * .42, 215 * s, span * .09), (x0 + span * .68, 125 * s, span * .14)],
                   horizon, QIAN, .6 * a, seed, x0, x1, blur=3)
    mist(c, t, horizon - 110 * s, horizon - 40 * s, .55 * a, seed + 3, 3)
    mountain_layer(c, [(x0 + span * .12, 105 * s, span * .09), (x0 + span * .55, 135 * s, span * .1), (x0 + span * .92, 175 * s, span * .07)],
                   horizon + 12, DAI, .55 * a, seed + 1, x0, x1, blur=1.5, depth=120)
    mist(c, t, horizon - 30, horizon + 20, .5 * a, seed + 5, 3)
    water(c, t, x0, x1, horizon + 22, horizon + 110, a, seed + 2)
    if boat_x is not None:
        boat(c, x0 + span * boat_x + math.sin(t * .15) * 30 + t * 3, horizon + 62, .8 * s, .85 * a)
    if has_birds:
        birds(c, t, x0 + span * .55, horizon - 230 * s, 4, a, seed + 4)


def ripples(c, cx, cy, r0, r1, t, a=1.0):
    """embossed concentric rings pressed into the paper (the reference's top-right card motif)."""
    if a <= 0: return
    off = (t * 8) % 16
    r = r0 + off
    while r < r1:
        k = 1 - (r - r0) / (r1 - r0)
        circle(c, cx - 1, cy - 1, r, WHITE, a * .55 * k, stroke=1.4)
        circle(c, cx + 1, cy + 1, r, (150, 145, 135), a * .16 * k, stroke=1.2)
        r += 16


def orbit(c, cx, cy, rx, ry, rot, a=1.0, prog=1.0, rgb=DAI):
    if a <= 0 or prog <= 0: return
    p = skia.Path(); p.addOval(skia.Rect.MakeLTRB(cx - rx, cy - ry, cx + rx, cy + ry))
    c.save(); c.translate(cx, cy); c.rotate(rot); c.translate(-cx, -cy)
    c.drawPath(partial_path(p, 0, prog), paint(rgb, a, stroke=1.4))
    c.restore()


def dot_grid(c, x0, y0, cols, rows, step=16, a=1.0, rgb=DAI):
    """halftone dot field fading toward its lower-left."""
    if a <= 0: return
    for i in range(cols):
        for j in range(rows):
            k = (i / max(1, cols - 1)) * .6 + (1 - j / max(1, rows - 1)) * .4
            circle(c, x0 + i * step, y0 + j * step, 1.2 + 1.2 * k, rgb, a * (.15 + .6 * k))


# ------------------------------------------------------------------ the cutout, the video, captions
def tone_filter():
    """duotone: luminance -> indigo ink .. light paper (人物水墨化)."""
    L = (.299, .587, .114)
    I = [v / 255 for v in MO]; Pp = [v / 255 for v in XUAN_L]
    rows = []
    for ch in range(3):
        d = Pp[ch] - I[ch]
        rows += [d * L[0], d * L[1], d * L[2], 0, I[ch]]
    rows += [0, 0, 0, 1, 0]
    return skia.ColorFilters.Matrix(rows)


_PAPER_F = np.array(XUAN, np.float32)


def grade_np(fr):
    """soft, desaturated, paper-lifted grade (淡雅) for the real video."""
    f = fr.astype(np.float32)
    y = (f[..., 0] * .299 + f[..., 1] * .587 + f[..., 2] * .114)[..., None]
    f = y + (f - y) * .78
    f = f * .88 + _PAPER_F * .12
    return np.clip(f, 0, 255).astype(np.uint8)


def caption(c, st, caps, split_kw, min_start=-1e9):
    """ink subtitles: indigo Songti on a paper halo, keywords in cinnabar, bleeding in."""
    for s0, s1, txt in caps:
        if s0 <= st < s1 and s0 >= min_start:
            p = eo(P(st, s0, .28))
            f = F('songb', 48)
            parts = split_kw(txt)
            total = sum(tw(p_, f) for p_, _ in parts)
            x = W / 2 - total / 2; y = H - 68 + 4 * (1 - p)
            for ptxt, hl in parts:
                text(c, ptxt, x, y, f, XUAN_L, .8 * p, glow=12)
                text(c, ptxt, x, y, f, XUAN_L, .95 * p, stroke=9)
                c.drawString(ptxt, x, y, f, paint(ZHU if hl else MO, p, blur=6 * (1 - p) if p < .95 else 0))
                x += tw(ptxt, f)
            return


def _fbm(w, h, seed, base, octaves=4):
    """fractal noise in about [-.5, .5]; base = largest feature size in px."""
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        cs = max(2, int(base / 2 ** o))
        out += _noise(w, h, cs, cs, seed + o * 13) * amp; tot += amp; amp *= .55
    return out / tot


def _cover_field(seed):
    """ink-spread field for one page turn, at 1/3 resolution: several drops landing one after another, each
    spreading like real diffusion (fast, then slowing), on a domain-warped distance so the edge grows tendrils."""
    key = ('cover', seed, W, H)
    if key not in _FIELD:
        w, h = W // 3, H // 3; S = max(w, h)
        r = np.random.RandomState(seed + 500)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        wx = _fbm(w, h, seed + 510, S * .35) * S * .22          # domain warp -> 墨丝 tendrils
        wy = _fbm(w, h, seed + 520, S * .35) * S * .22
        X, Y = xx + wx, yy + wy
        ox, oy = [(.3, .3), (.7, .28), (.5, .5), (.3, .72), (.7, .7)][seed % 5]
        drops = [(ox * w, oy * h, 0.0)]
        for k in range(3):   # later, smaller drops nearby and further out
            ang = r.uniform(0, 6.28); dist = r.uniform(.18, .42) * S
            drops.append((ox * w + math.cos(ang) * dist, oy * h + math.sin(ang) * dist, r.uniform(.12, .32)))
        A = np.full((h, w), 9.0, np.float32)
        for dx, dy, delay in drops:
            dd = np.hypot(X - dx, Y - dy) / S
            A = np.minimum(A, delay + dd ** 1.6 * 1.25)               # radius ~ t^(1/1.6): fast, then slowing
        A += _fbm(w, h, seed + 530, S * .06, 3) * .07               # fine fibrous edge
        A = (A - A.min()) / (np.percentile(A, 99.7) - A.min())
        tex = np.clip(_fbm(w, h, seed + 540, S * .18) + .5, 0, 1)    # cloudy ink density
        tex2 = np.clip(_fbm(w, h, seed + 550, S * .05, 3) + .5, 0, 1)
        _FIELD[key] = (A, tex, tex2)
    return _FIELD[key]


def _ss(x, w):
    x = np.clip(x / w, 0, 1); return x * x * (3 - 2 * x)


def ink_cover(c, d, dur, seed, origin=None):
    """page turn, inside a saveLayer holding the incoming scene: mask it to where the ink has already cleared.
    d = seconds relative to the cut (-dur .. dur). Returns (state, u) for ink_edge."""
    u = clamp((d + dur) / (2 * dur))
    A, tex, tex2 = _cover_field(seed)
    T = 1.32 * eio(u) - .02
    reveal = _ss(T - .3 - A + .12 * (tex - .5), .22)       # the new page clears out of the ink centre
    c.drawImageRect(_img(_blur(reveal, 1.5), WHITE), skia.Rect.MakeWH(W, H), SAMP, skia.Paint(BlendMode=skia.BlendMode.kDstIn))
    return (A, tex, tex2, T, reveal), u


def ink_edge(c, st, u):
    """the ink itself: a cloudy indigo wash spreading ahead of the reveal, densest at its rim (ink pools at the
    edge as it dries), with wispy fibres; it thins out as the new page clears."""
    A, tex, tex2, T, reveal = st
    x = T - A
    cov = _ss(x + .015 * (tex2 - .5), .05)
    rim = np.exp(-((x - .035) / .045) ** 2)
    dens = cov * (.3 + .5 * tex ** 1.3 + .2 * tex2) + rim * (.12 + .22 * tex2)
    dens *= (1 - reveal) ** 1.4
    fade = clamp((1 - u) / .15)                            # nothing left once the page has turned
    c.drawImageRect(_img(_blur(np.clip(dens * .88 * fade, 0, 1), 1.6), MO), skia.Rect.MakeWH(W, H), SAMP, skia.Paint())


# ------------------------------------------------------------------ sound: gentle, acoustic-ish
KINDS = {'pluck', 'bell', 'drop', 'breeze', 'brush', 'seal', 'gliss', 'tear'}
SFX_MAP = {'whoosh': 'breeze', 'swish': 'brush', 'pop': 'pluck', 'impact': 'bell', 'riser': 'gliss', 'glitch': 'drop'}
SR = 48000
PENTA = [293.66, 329.63, 369.99, 440.0, 493.88, 587.33]   # D gong pentatonic (宫商角徵羽)


def _reverb(x, wet=.28, tail=1.4, seed=3):
    r = np.random.RandomState(seed)
    n = int(tail * SR); tt = np.arange(n) / SR
    ir = r.randn(n) * np.exp(-tt / .38)
    ir = np.convolve(ir, np.ones(12) / 12, 'same'); ir /= np.abs(ir).sum() / 6
    L = len(x) + n
    nf = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[:L]
    out = np.concatenate([x, np.zeros(n)]) + y * wet
    return out / (np.abs(out).max() + 1e-9)


def _band(d, f0, f1, seed, nb=20):
    r = np.random.RandomState(seed)
    n = int(d * SR); noise = r.randn(n); out = np.zeros(n)
    blk = max(64, n // nb * 2); hop = blk // 2; win = np.hanning(blk)
    for b in range(nb * 2):
        i0 = b * hop
        if i0 + blk > n: break
        Fq = np.fft.rfft(noise[i0:i0 + blk] * win); fr = np.fft.rfftfreq(blk, 1 / SR)
        fc = f0 * (f1 / f0) ** (b / (nb * 2))
        Fq *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * .45 ** 2))
        out[i0:i0 + blk] += np.fft.irfft(Fq, blk)
    return out / (np.abs(out).max() + 1e-9)


def _ks(freq, d, seed, damp=.996):
    """Karplus-Strong plucked string (古琴-ish when low and slow)."""
    r = np.random.RandomState(seed)
    N = int(SR / freq); n = int(d * SR)
    buf = r.uniform(-1, 1, N); buf = np.convolve(buf, np.ones(3) / 3, 'same')
    out = np.zeros(n)
    for i in range(n):
        j = i % N
        out[i] = buf[j]
        buf[j] = damp * .5 * (buf[j] + buf[(j + 1) % N])
    return out


def synth(kind, var=0):
    tt = lambda d: np.arange(int(d * SR)) / SR
    if kind == 'pluck':
        f = PENTA[var % len(PENTA)]
        x = _ks(f, 1.6, var) * .8 + _ks(f / 2, 1.6, var + 9, .997) * .35
        t = tt(1.6); x *= np.minimum(1, t / .004) * np.exp(-t * 1.6)
        return _reverb(x, .3) * .5
    if kind == 'bell':   # 磬 / small temple bell: inharmonic partials
        t = tt(3.2); f = [520, 780][var % 2]
        x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / dd) for m, a, dd in [(1, 1, 1.4), (2.76, .5, .7), (5.4, .25, .35), (8.93, .12, .18)])
        x *= np.minimum(1, t / .003)
        return _reverb(x, .35) * .42
    if kind == 'drop':   # water drop
        t = tt(.35)
        fq = 700 + 1500 * (1 - np.exp(-t * 90))
        x = np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-t * 28)
        return _reverb(x, .4) * .45
    if kind == 'breeze':
        x = _band(1.2, 220, 1300, var + 20); t = np.linspace(0, 1, len(x))
        return x * np.sin(np.pi * t) ** 2 * .32
    if kind == 'brush':
        x = _band(.45, 900, 3200, var + 40); t = np.linspace(0, 1, len(x))
        return x * (t ** .4) * (1 - t) ** 1.5 * 1.1 * .45
    if kind == 'gliss':  # rising breeze + a pentatonic run
        x = _band(1.4, 260, 2600, var + 60); t = np.linspace(0, 1, len(x))
        x = x * t ** 1.5 * .3
        for k, f in enumerate(PENTA[:4]):
            i0 = int((.55 + k * .18) * SR)
            pl = _ks(f * 2, .6, k) * np.exp(-np.arange(int(.6 * SR)) / SR * 5) * .22
            x[i0:i0 + len(pl)] += pl[:max(0, len(x) - i0)]
        return _reverb(x, .3) * .8
    if kind == 'tear':   # paper tearing: a crackle of fibre snaps over a dry rustle
        r = np.random.RandomState(var + 70)
        d = .55; n = int(d * SR); x = _band(d, 1200, 4200, var + 80) * .25
        t = np.linspace(0, 1, n); x *= np.sin(np.pi * t) ** .6
        k = 0.0
        while k < d - .02:
            i0 = int(k * SR); L = int(r.uniform(.002, .006) * SR)
            x[i0:i0 + L] += r.randn(L) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(.3, .9)
            k += r.uniform(.004, .02) * (1.3 - t[min(n - 1, i0)])
        x = np.convolve(x, [.5, .5], 'same')
        return x / (np.abs(x).max() + 1e-9) * .5
    if kind == 'seal':   # soft wooden press
        t = tt(.4)
        body = np.sin(2 * np.pi * np.cumsum(90 + 80 * np.exp(-t * 30)) / SR) * np.exp(-t * 14)
        r = np.random.RandomState(var)
        click = np.convolve(r.randn(len(t)) * np.exp(-t * 90), np.ones(24) / 24, 'same') * 2
        return np.tanh((body + click) * 1.2) * .6
    raise ValueError(kind)


# =============================================================== TEMPLATES
class ScrollScene(Scene):
    """Paper 'scroll' scene: the person, cut out, stands on xuan paper at the right (like the scholar in the
    reference), with a soft paper halo; content lives on the left (x 110-1150).
    ink_person: 0 = natural colour .. 1 = fully ink-toned duotone.  petals: number of falling petals."""
    mode = 'scroll'
    scale = .74
    cx = 1540
    enter_from = None
    ink_person = 0.0
    rim = .9
    rim_rgb = XUAN_L
    rim_blur = 26
    petals = 0

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .9))
        return mix_xf(self.enter_from or full_xf(1.05), dark_xf(self.scale, self.cx), k)

    backdrop = None      # per page: image path for a painted background (overrides ink.BACKDROP)
    fade = 1.0           # per page: backdrop opacity on the paper (e.g. .4 = faded background)
    safe = None          # per page: (x0, x1) band for P* content (overrides ink.SAFE)

    def draw_bg(self, c, t, ctx):
        bd = self.backdrop or BACKDROP
        if bd: backdrop_bg(c, t, self.fade, bd, self.safe, VEIL * self.fade)
        else: ink_bg(c, t)

    def ambient(self, c, t):
        if self.petals: PETALS.draw(c, t, self.petals, self.a(t))


class InkCover(ScrollScene):
    """封面 / opening: the reference layout. Ghost characters, an orbit hairline, a cut-corner paper card with an
    embossed ripple, a landscape that washes in, a three-line Songti title, cinnabar stroke + dot, a spaced
    subtitle, a vertical motto with a seal, and a corner motto.
    lines=[(t, '用GPT'), (t, '生成中文'), (t, '美感PPT')]  sub=(t, '封面设计 / AI视觉排版')
    ghost=('美', '感')  vertical=('让想法被看见', '让表达更有美感')  seal='雅'  corner=('AI 赋能表达', '设计提升价值')"""
    lines = []
    size = 112
    sub = None
    ghost = ('诗', '韵')
    ghost_t = None
    vertical = None
    vertical_t = None
    seal = '雅'
    seal_t = None
    corner = None
    corner_t = None
    landscape_t = None
    card = (110, 196, 1150, 640)
    petals = 6

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        gt = self.ghost_t if self.ghost_t is not None else self.t0 + .1
        x, y, w, h = self.card
        orbit(c, x + w * .55, y + h * .52, w * .68, h * .74, -8 + t * .6, a * .3, eo(P(t, gt + .3, 2.6)))
        fade = eo(P(t, gt + .6, 1.2))
        dot_grid(c, 930, 70, 13, 8, 15, a * .5 * fade)
        dot_grid(c, 30, 860, 7, 4, 15, a * .4 * fade)
        if self.ghost:
            ghost(c, self.ghost[0], -60 + math.sin(t * .25) * 6, 420, 480, t, gt, DAI, .42 * a)
            if len(self.ghost) > 1:
                ghost(c, self.ghost[1], 1390 + math.sin(t * .2 + 1) * 6, 1200, 480, t, gt + .5, DAI, .36 * a)
        cp = eo(P(t, self.t0 + .25, 1.0))
        yy = y + 30 * (1 - cp)
        paper_card(c, x, yy, w, h, a * cp)
        c.save(); c.clipPath(chamfer(x, yy, w, h), skia.ClipOp.kIntersect, True)
        ripples(c, x + w - 130, yy + 120, 30, 250, t, a * cp)
        lt = self.landscape_t if self.landscape_t is not None else self.t0 + .7
        c.saveLayer(skia.Rect.MakeXYWH(x, yy, w, h))
        landscape(c, t, x + w * .32, x + w + 60, yy + h * .8, a * cp, seed=3)
        wash_mask(c, x + w * .32, x + w, yy, yy + h, P(t, lt, 2.8))
        c.restore()
        c.restore()
        f = F('song', self.size)
        lh = self.size * 1.14
        for i, (t0, s) in enumerate(self.lines):
            ink_text(c, s, x + 120, yy + 205 + i * lh, f, t, t0, MO, a, stagger=.07)
        ny = yy + 205 + (len(self.lines) - 1) * lh + 72
        if self.sub:
            st, s = self.sub
            brush_stroke(c, x + 122, ny, x + 300, ny + 1, 7, ZHU, a, eo(P(t, st - .35, .6)), seed=2)
            circle(c, x + 334, ny, 7 * clamp(eob(P(t, st, .4))), ZHU, a)
            text(c, s, x + 122, ny + 74, F('songb', 30), MO, a * eo(P(t, st + .1, .7)), spacing=9)
        if self.vertical:
            vt = self.vertical_t if self.vertical_t is not None else self.t0 + 1.2
            vx = x + w - 110
            seal(c, self.seal, vx, yy + 120, 40, t, vt, a, seed=4)
            ink_vtext(c, '  '.join(self.vertical), vx, yy + 190, F('songr', 26), t, vt + .3, MO, a * .9, stagger=.07, step=32)

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.corner:
            ct = self.corner_t if self.corner_t is not None else self.t0 + 1.0
            circle(c, 1680, 92, 6, ZHU, a * eo(P(t, ct, .4)))
            for i, s in enumerate(self.corner):
                text(c, s, 1676, 136 + i * 36, F('songr', 24), MO, a * eo(P(t, ct + .15 + i * .2, .7)), spacing=6)
        self.ambient(c, t)

    def events(self):
        gt = self.ghost_t if self.ghost_t is not None else self.t0 + .1
        lt = self.landscape_t if self.landscape_t is not None else self.t0 + .7
        ev = [(gt, 'bell', .6), (lt, 'breeze', .7)] + [(t0, 'pluck', .55) for t0, _ in self.lines]
        if self.sub: ev.append((self.sub[0] - .35, 'brush', .6))
        if self.vertical: ev.append((self.vertical_t if self.vertical_t is not None else self.t0 + 1.2, 'seal', .8))
        return ev


class InkBehind(Scene):
    """Full frame. Big Songti/Kaiti/Xingkai characters bleed into a paper mist BEHIND the person — the ink
    version of BehindText. Optional ink-drop bloom, cinnabar seal after the word, spaced sub line.
    text, text_t, x/y/size, font='song'|'kai'|'xing', mist=.85, seal=('诗', t), sub=(t, '一句诗一幅画')"""
    text = '诗意'
    text_t = 0
    x, y, size = 70, 640, 230
    font = 'song'
    rgb = MO
    zoom = 1.08
    mist = .85
    stagger = .12
    bloom = True
    seal = None
    sub = None

    def xf(self, t):
        return full_xf(lerp(self.zoom, self.zoom + .03, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        left_mist(c, t, self.mist * a)
        f = F(self.font, self.size)
        if self.bloom:
            ink_bloom(c, self.x + self.size * .5, self.y - self.size * .35, t, self.text_t - .05, self.size * .9, MO, .2 * a, seed=3)
        if t > self.text_t + .6:
            k = eo(P(t, self.text_t + .6, 1.6))
            c.saveLayer(skia.Rect.MakeWH(W, H))
            text(c, self.text, self.x + 10 * k, self.y + 10 * k, f, DAI, .22 * a * k)
            dry(c)
            c.restore()
        self._w = ink_text(c, self.text, self.x, self.y, f, t, self.text_t, self.rgb, a * .97, stagger=self.stagger, dur=1.0)

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.seal:
            s, st = self.seal
            w = getattr(self, '_w', 0) or tw(self.text, F(self.font, self.size))
            sx = self.x + w + 50
            if sx + 40 > PERSON['head_x'] - 260:   # would land on the face: leading seal (引首章) above the first character
                seal(c, s, self.x + 40, self.y - self.size * 1.05 - 30, 56, t, st, a, seed=1)
            else:
                seal(c, s, sx, self.y - self.size * .75, 64, t, st, a, seed=1)
        if self.sub:
            st, s = self.sub
            brush_stroke(c, self.x + 6, self.y + 62, self.x + 160, self.y + 63, 6, ZHU, a, eo(P(t, st - .3, .6)), seed=5)
            text(c, s, self.x + 190, self.y + 72, F('songb', 32), MO, a * eo(P(t, st, .7)), spacing=8)

    def events(self):
        ev = [(self.text_t - .05, 'drop' if self.bloom else 'bell', .8), (self.text_t + .1, 'bell', .45)]
        if self.seal: ev.append((self.seal[1], 'seal', .9))
        if self.sub: ev.append((self.sub[0] - .3, 'brush', .5))
        return ev


class PoemColumn(ScrollScene):
    """竖排诗句: verses written top-down, right to left, each character bleeding in as it is spoken, between
    faint column rules, under a pale moon over far mountains; author + seal close the poem.
    lines=[(t, '床前明月光')] or [(t0, t1, '床前明月光')] (chars spread evenly over t0..t1)
    author=(t, '李白 · 静夜思')  seal=(t, '太白')  font='kai'|'song'|'xing'  label='诗 · 意'"""
    lines = []
    author = None
    seal = None
    font = 'kai'
    size = 84
    stagger = .14
    x0 = 1010
    col_gap = 140
    y0 = 250
    moon = True
    label = None
    petals = 10

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        if self.moon:
            mp = eo(P(t, self.t0 + .2, 2.4))
            mx, my = 330, 300 + 30 * (1 - mp)
            circle(c, mx, my, 160, WHITE, a * mp * .7, blur=45)
            circle(c, mx, my, 84, (232, 230, 222), a * mp, blur=1.5)
            circle(c, mx, my, 84, QIAN, a * mp * .5, stroke=2, blur=1)
            circle(c, mx - 22, my + 12, 30, QIAN, a * mp * .12, blur=10)
            ripples(c, mx, my, 100, 230, t, a * mp * .7)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        mountain_layer(c, [(250, 150, 220), (640, 210, 200), (1050, 130, 260)], 880, QIAN, .55 * a, 11, -100, 1500, blur=3)
        mountain_layer(c, [(120, 90, 160), (820, 120, 180)], 900, DAI, .4 * a, 12, -100, 1500, blur=1.5)
        mist(c, t, 760, 860, .6 * a, 13, 4)
        wash_mask(c, -100, 1500, 500, H, P(t, self.t0 + .1, 3.0))
        c.restore()
        if self.label: ink_label(c, self.label, 120, 150, a * eo(P(t, self.t0 + .3, .6)))
        f = F(self.font, self.size)
        step = self.size * 1.16
        maxlen = max([len(l[-1]) for l in self.lines] or [1])
        for i, ln in enumerate(self.lines):
            t0, s = ln[0], ln[-1]
            stg = (ln[1] - ln[0]) / max(1, len(s)) if len(ln) == 3 else self.stagger
            x = self.x0 - i * self.col_gap
            rp = eo(P(t, t0 - .4, 1.0))
            line(c, x + self.col_gap / 2, self.y0 - self.size, x + self.col_gap / 2, self.y0 - self.size + (maxlen * step + 40) * rp, DAI, .16 * a, 1)
            ink_vtext(c, s, x, self.y0, f, t, t0, MO, a, stagger=stg, dur=1.1, step=step)
        xa = self.x0 - len(self.lines) * self.col_gap + 20
        if self.author:
            at, s = self.author
            ink_vtext(c, s, xa, self.y0 + 20, F('songr', 32), t, at, HUI, a, stagger=.06, step=38)
            if self.seal:
                st, ss = self.seal
                seal(c, ss, xa, self.y0 + 60 + len(s) * 38, 58, t, st, a, seed=6)
        elif self.seal:
            st, ss = self.seal
            seal(c, ss, xa, self.y0 + 40, 58, t, st, a, seed=6)

    def front(self, c, t, ctx):
        self.ambient(c, t)

    def ready_t(self):
        """when the last verse character has been readable for 1 s (used to time the page turn)."""
        return max([(ln[1] if len(ln) == 3 else ln[0] + len(ln[-1]) * .14) + 1.0 for ln in self.lines] or [0])

    def events(self):
        ev = [(self.t0 + .1, 'breeze', .6)] + [(ln[0], 'pluck', .55) for ln in self.lines]
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


class InkLandscape(ScrollScene):
    """山水长卷: a whole landscape washes in left -> right under a cinnabar sun, mist drifts, a skiff glides, birds
    cross; a headline and sub line sit top-left. lines=[(t, '一叶扁舟')]  sub=(t, '烟波江上')  sun=True"""
    lines = []
    size = 96
    sub = None
    sun = True
    reveal_t = None
    petals = 0

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        rt = self.reveal_t if self.reveal_t is not None else self.t0 + .1
        if self.sun:
            sp = eo(P(t, rt + .8, 2.2))
            sy = 330 + 70 * (1 - sp)
            circle(c, 1010, sy, 110, ZHU, a * sp * .12, blur=40)
            circle(c, 1010, sy, 58, ZHU, a * sp * .82, blur=1)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        landscape(c, t, -80, 1560, 770, a, seed=7, scale=1.45, boat_x=.36)
        wash_mask(c, -80, 1560, 300, H, P(t, rt, 3.2))
        c.restore()
        f = F('song', self.size)
        for i, (t0, s) in enumerate(self.lines):
            ink_text(c, s, 120, 250 + i * self.size * 1.15, f, t, t0, MO, a, stagger=.09)
        if self.sub:
            st, s = self.sub
            ny = 250 + (len(self.lines) - 1) * self.size * 1.15 + 66
            brush_stroke(c, 122, ny, 260, ny + 1, 6, ZHU, a, eo(P(t, st - .3, .6)), seed=8)
            text(c, s, 290, ny + 10, F('songb', 30), MO, a * eo(P(t, st, .7)), spacing=8)

    def front(self, c, t, ctx):
        self.ambient(c, t)

    def events(self):
        rt = self.reveal_t if self.reveal_t is not None else self.t0 + .1
        ev = [(rt, 'gliss', .7)] + [(t0, 'pluck', .5) for t0, _ in self.lines]
        if self.sub: ev.append((self.sub[0] - .3, 'brush', .5))
        return ev


class InkList(ScrollScene):
    """A list / steps / key points on paper: cinnabar numeral seals (壹 贰 叁), Songti titles bleeding in, spaced
    grey notes, dry-brush rules drawn under each row. label='方法 · 三步'  title='三步写出诗意'
    items=[(t, '读懂内容', '先理解每一句')]"""
    label = None
    title = None
    title_t = None
    items = []
    petals = 0

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        tt = self.title_t if self.title_t is not None else self.t0 + .2
        ink_title(c, t, tt, self.label, self.title, 120, a)
        n = max(1, len(self.items))
        step = min(122, 500 / n)
        y0 = 380 if self.title else 260
        for i, (t0, s, note) in enumerate(self.items):
            y = y0 + i * step
            seal(c, NUMS[i], 150, y - 18, 56, t, t0, a, font='song', seed=10 + i, rot=-2)
            w = ink_text(c, s, 212, y, F('song', 50), t, t0 + .08, MO, a, stagger=.06)
            if note:
                text(c, note, 212 + w + 34, y - 4, F('songr', 26), HUI, a * eo(P(t, t0 + .4, .7)), spacing=4)
            brush_stroke(c, 120, y + 40, 1060, y + 42, 3, DAI, a * .35, eo(P(t, t0 + .1, .9)), seed=20 + i, bend=.003)

    def front(self, c, t, ctx):
        self.ambient(c, t)

    def events(self):
        tt = self.title_t if self.title_t is not None else self.t0 + .2
        return [(tt, 'pluck', .5)] + [(t0, 'seal', .7) for t0, _, _ in self.items] + [(t0 + .1, 'brush', .4) for t0, _, _ in self.items]


class InkEnd(ScrollScene):
    """Closing / CTA in ink: an ink drop spreads, the big line bleeds in with a cinnabar stroke under it, small
    paper chips pop in, a seal stamps, a vertical farewell line, petals fall.
    big=(t, '评论区见')  items=[(t, '点赞'), (t, '关注')]  seal=(t, '关注')  farewell=(t, '山水有相逢')"""
    big = None
    size = 150
    items = []
    seal = None
    farewell = None
    petals = 22

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        if self.farewell:
            ft, s = self.farewell
            ink_vtext(c, s, 1110, 230, F('kai', 40), t, ft, HUI, a, stagger=.12, step=50)
        if self.big:
            bt, s = self.big
            ink_bloom(c, 120 + self.size * 1.2, 420, t, bt - .1, 300, MO, .16 * a, seed=2, dur=2.4)
            w = ink_text(c, s, 120, 500, F('song', self.size), t, bt, MO, a, stagger=.1)
            brush_stroke(c, 126, 560, 126 + w * .62, 562, 10, ZHU, a, eo(P(t, bt + .5, .7)), seed=3)
            if self.seal:
                st, ss = self.seal
                seal(c, ss, min(120 + w + 70, 1080), 410, 78, t, st, a, seed=7)
        xx = 124
        for t0, s in self.items:
            p = eob(P(t, t0, .5), 1.3)
            if p <= 0:
                xx += tw(s, F('songb', 30)) + 110; continue
            f = F('songb', 30); w = tw(s, f) + 72
            al = a * clamp(p * 2)
            yy = 640 + 20 * (1 - p)
            rrect(c, xx, yy + 10, w, 64, 10, (60, 60, 70), .12 * al, blur=14)
            rrect(c, xx, yy, w, 64, 10, XUAN_L, al)
            circle(c, xx + 26, yy + 32, 6, ZHU, al)
            text(c, s, xx + 44, yy + 43, f, MO, al)
            xx += w + 38

    def front(self, c, t, ctx):
        self.ambient(c, t)

    def events(self):
        ev = []
        if self.big: ev += [(self.big[0] - .1, 'drop', .8), (self.big[0] + .5, 'brush', .6)]
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        ev += [(t0, 'pluck', .5) for t0, _ in self.items]
        if self.farewell: ev.append((self.farewell[0], 'bell', .5))
        return ev


class TornText(Scene):
    """大字撕纸: big characters on torn xuan paper, BEHIND the person, over the real video.
    style='sheet'  - a torn sheet slides in from the left; at text_t its top layer tears open along a ragged
                     line and the two halves peel away, revealing the characters (tear=False: they bleed in).
    style='scraps' - each character slaps in on its own torn paper scrap, slightly rotated (collage).
    text, text_t, size, font='song'|'kai'|'xing', tex='stipple'|'brush'|None (print texture on the characters),
    seal=('苏', t), sub=(t, '北宋文豪的一生')"""
    text = '撕纸'
    text_t = 0
    style = 'sheet'
    tear = True
    size = 230
    font = 'song'
    rgb = MO
    tex = 'stipple'
    x, y = 90, 640
    zoom = 1.06
    seal = None
    sub = None
    sheet_w = 1000
    stagger = .16

    def xf(self, t):
        return full_xf(lerp(self.zoom, self.zoom + .03, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def _pieces(self):
        if not hasattr(self, '_pc'):
            x0, y0, w, h = -60, 150, self.sheet_w + 60, 700
            sheet = torn_rect(x0, y0, w, h, 'trb', seed=31, rough=14)
            mid = self.x + tw(self.text, F(self.font, self.size)) * .48
            line_ = torn_points(mid + 40, y0 - 40, mid - 50, y0 + h + 40, seed=37, rough=18, step=5)
            left = skia.Path(); left.moveTo(-400, y0 - 40)
            for px, py in line_: left.lineTo(px, py)
            left.lineTo(-400, y0 + h + 40); left.close()
            right = skia.Path(); right.moveTo(W + 400, y0 - 40)
            for px, py in line_: right.lineTo(px, py)
            right.lineTo(W + 400, y0 + h + 40); right.close()
            self._pc = (sheet, skia.Op(sheet, left, skia.PathOp.kIntersect_PathOp), skia.Op(sheet, right, skia.PathOp.kIntersect_PathOp))
        return self._pc

    def _chars(self, c, t, a, t0, instant):
        f = F(self.font, self.size)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        if instant:
            text(c, self.text, self.x, self.y, f, self.rgb, a)
        else:
            ink_text(c, self.text, self.x, self.y, f, t, t0, self.rgb, a, stagger=self.stagger, dur=.8)
        if self.tex: dry(c, self.tex)
        c.restore()

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        if self.style == 'scraps':
            return self._scraps(c, t, a)
        sheet, left, right = self._pieces()
        k = eo(P(t, self.t0 + .05, .7))
        c.save(); c.translate(-self.sheet_w * 1.1 * (1 - k), 0)
        c.rotate(lerp(-5, -1.2, k))
        paper_piece(c, sheet, a, seed=1)
        self._chars(c, t, a, self.text_t, self.tear)
        if self.tear:
            tp = eo(P(t, self.text_t, .75))
            if tp <= 0:
                paper_piece(c, sheet, a, shadow=0, seed=1)   # untorn cover: no seam yet
            elif tp < 1:
                for pc, sgn in ((left, -1), (right, 1)):
                    c.save()
                    c.translate(sgn * 420 * tp, -60 * tp * (1 if sgn > 0 else .3))
                    c.rotate(sgn * 9 * tp)
                    paper_piece(c, pc, a * (1 - tp ** 2), seed=2 + sgn)
                    c.restore()
        c.restore()

    def _scraps(self, c, t, a):
        f = F(self.font, self.size)
        r = np.random.RandomState(41)
        xx = self.x
        for i, ch in enumerate(self.text):
            w = f.measureText(ch)
            p = P(t, self.text_t + i * self.stagger, .4)
            rot = r.uniform(-7, 7); dx, dy = r.uniform(-8, 8), r.uniform(-14, 14)
            if p > 0:
                k = eob(p, 1.2)
                s = self.size * 1.22
                cx, cy = xx + w / 2 + dx, self.y - self.size * .36 + dy
                c.save(); c.translate(cx, cy); c.rotate(rot * lerp(2.2, 1, eo(p))); sc = lerp(1.35, 1, k); c.scale(sc, sc)
                paper_piece(c, torn_rect(-s / 2, -s / 2, s, s, 'trbl', seed=50 + i, rough=10), a * clamp(p * 3), seed=i)
                c.saveLayer(skia.Rect.MakeXYWH(-s, -s, 2 * s, 2 * s))
                text(c, ch, -w / 2, self.size * .36, f, self.rgb, a * clamp(p * 3))
                c.restore()
                c.restore()
            xx += w + self.size * .12

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.seal:
            s, st = self.seal
            seal(c, s, self.x + 40, self.y - self.size * 1.05 - 30, 56, t, st, a, seed=1)
        if self.sub:
            st, s = self.sub
            brush_stroke(c, self.x + 6, self.y + 66, self.x + 160, self.y + 67, 6, ZHU, a, eo(P(t, st - .3, .6)), seed=5)
            text(c, s, self.x + 190, self.y + 76, F('songb', 32), MO, a * eo(P(t, st, .7)), spacing=8)

    def events(self):
        ev = [(self.t0 + .05, 'breeze', .6)] if self.style == 'sheet' else []
        if self.style == 'scraps':
            ev += [(self.text_t + i * self.stagger, 'tear' if i == 0 else 'brush', .6) for i in range(len(self.text))]
        else:
            ev.append((self.text_t, 'tear' if self.tear else 'bell', .9))
        if self.seal: ev.append((self.seal[1], 'seal', .9))
        if self.sub: ev.append((self.sub[0] - .3, 'brush', .5))
        return ev



# =============================================================== PAPER LAYOUTS (no presenter, any aspect)
# For narration audio (analyze.py <audio> --size 1080x1440) or any scene where the person should not appear.
# Everything is placed relative to W, H, so the same templates work for 3:4, 9:16 and 16:9.
def paper_halo(c, x, y, w, h, a=1.0):
    """soft patch of clean paper so small text / seals stay legible over ghost characters and hills."""
    if a > 0: c.drawOval(skia.Rect.MakeXYWH(x, y, w, h), paint(XUAN_L, .88 * a, blur=min(w, h) * .25))


def credit(c, s_, x, y, t, t0, a=1.0, size=None, step=None):
    """vertical attribution (作者 · 篇名) in indigo on a paper halo — always readable."""
    U = min(W, H); size = size or U * .036; step = step or size * 1.22
    k = eo(P(t, t0, .6))
    if k <= 0: return 0
    hgt = sum(step if ch != ' ' else step * .5 for ch in s_)
    paper_halo(c, x - size * 1.1, y - size * 1.4, size * 2.2, hgt + size * 1.4, a * k)
    ink_vtext(c, s_, x, y, F('songb', size), t, t0, MO, a * .9, stagger=.05, step=step)
    return hgt


def _boxed(fn):
    """run a P* draw method with the frame narrowed to SAFE (and generated scenery off on a backdrop)."""
    def run(self, c, t, ctx):
        global W, _SCENERY_OFF
        safe, bd = self.safe or SAFE, self.backdrop or BACKDROP
        if not safe and not bd: return fn(self, c, t, ctx)
        W0, off0 = W, _SCENERY_OFF
        x0, x1 = safe or (0, 1)
        _SCENERY_OFF = bool(bd)
        c.save(); c.translate(x0 * W0, 0); W = int((x1 - x0) * W0)
        try: return fn(self, c, t, ctx)
        finally:
            c.restore(); W, _SCENERY_OFF = W0, off0
    return run


class PaperScene(ScrollScene):
    """paper scene without a presenter (the cutout, if any, is hidden). With ink.SAFE set, content is laid out
    inside that part of the frame; with ink.BACKDROP set, the painting replaces the paper and generated scenery."""

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        for name in ('behind', 'front'):
            if name in cls.__dict__: setattr(cls, name, _boxed(cls.__dict__[name]))

    rim = 0.0
    show_person = False
    frame = True

    def xf(self, t):
        return (1e-4, -W, -H) if not self.show_person else ScrollScene.xf(self, t)

    def hold_t(self):
        """time at which a waiting page is held (its end state, before any fade)."""
        return self.t1 + .04

    def a(self, t):
        """stay fully visible through the cut; the ink transition (which still draws this scene for ~0.3-0.5 s
        after t1) covers it, so the page never dips to empty."""
        return window(t, self.t0, self.t1 + .45, .01, .4)

    def decor(self, c, t, a):
        if self.frame:
            rrect(c, 28, 28, W - 56, H - 56, 2, MO, .18 * a, stroke=1.2)

    def front(self, c, t, ctx):
        self.ambient(c, t)


def wave_lines(c, t, x0, x1, y0, y1, a=1.0, seed=0, n=9):
    """flowing river: sinuous brush lines drifting downstream."""
    if _SCENERY_OFF: return
    r = np.random.RandomState(seed)
    for i in range(n):
        y = y0 + (y1 - y0) * i / max(1, n - 1); ph = r.rand() * 6.28; amp = r.uniform(6, 16); sp = r.uniform(.6, 1.2)
        L = r.uniform(.35, .7) * (x1 - x0); xs = x0 + ((r.rand() * (x1 - x0) + t * 40 * sp) % (x1 - x0 + L)) - L
        p = skia.Path(); first = True
        for k in range(41):
            x = xs + L * k / 40
            yy = y + amp * math.sin(x / 70 + ph + t * 1.2 * sp)
            if first: p.moveTo(x, yy); first = False
            else: p.lineTo(x, yy)
        c.drawPath(p, paint(DAI, a * (.18 + .25 * i / n), stroke=1.4 + 1.6 * i / n))


def moon(c, t, x, y, r, a=1.0, t0=0.0):
    mp = eo(P(t, t0, 2.4))
    if mp <= 0: return
    yy = y + 40 * (1 - mp)
    circle(c, x, yy, r * 1.9, WHITE, a * mp * .7, blur=r * .55)
    circle(c, x, yy, r, (234, 232, 224), a * mp, blur=1.5)
    circle(c, x, yy, r, QIAN, a * mp * .5, stroke=2, blur=1)
    circle(c, x - r * .25, yy + r * .15, r * .35, QIAN, a * mp * .12, blur=10)
    ripples(c, x, yy, r * 1.2, r * 2.7, t, a * mp * .7)


class PCover(PaperScene):
    """3:4 / vertical cover after the 苏轼 reference: pale stippled ghost characters, a torn paper sidebar with a
    vertical label, a cut-corner card holding the title, a cinnabar stroke, a spaced sub line, a note line, an
    ink landscape washing in at the card's foot, a corner motto and a seal.
    lines=[(t, '苏轼的一生')]  sub=(t, '才华横溢 · 几度被贬')  note=(t, '1037 — 1101')  ghost=('苏', '轼')
    sidebar='人物 · 诗词'  corner=('北宋 · 文豪', '东坡居士')  seal=(t, '东坡')"""
    lines = []
    size = 120
    sub = None
    note = None
    ghost = None
    sidebar = None
    corner = None
    seal = None
    petals = 6

    def behind(self, c, t, ctx):
        a = self.a(t)
        gt = self.t0 + .05
        dot_grid(c, W * .62, H * .05, 12, 7, 15, a * .45 * eo(P(t, gt + .5, 1.2)))
        orbit(c, W * .55, H * .52, W * .52, H * .3, -10 + t * .5, a * .28, eo(P(t, gt + .3, 2.6)))
        if self.ghost:
            ghost(c, self.ghost[0], W * .06, H * .36 if H > W else H * .62, min(W, H) * .56, t, gt, DAI, .38 * a, tex='stipple')
            if len(self.ghost) > 1: ghost(c, self.ghost[1], W * .5 if H > W else W * .72, H * 1.0, min(W, H) * .56, t, gt + .4, DAI, .32 * a, tex='stipple')
        if H > W: x, w = W * .15, W * .79; h = min(H * .42, w * .78); y = H * .34
        else: x, w, y, h = W * .1, W * .8, H * .2, H * .54
        cp = eo(P(t, self.t0 + .2, 1.0)); yy = y + 30 * (1 - cp)
        self._card = (x, yy, w, h)
        paper_card(c, x, yy, w, h, a * cp)
        c.save(); c.clipPath(chamfer(x, yy, w, h), skia.ClipOp.kIntersect, True)
        ripples(c, x + w - 90, yy + 90, 24, 200, t, a * cp)
        c.saveLayer(skia.Rect.MakeXYWH(x, yy, w, h))
        landscape(c, t, x + w * .25, x + w + 40, yy + h * .86, a * cp * .9, seed=5, scale=.75, boat_x=.5)
        wash_mask(c, x + w * .25, x + w, yy, yy + h, P(t, self.t0 + .6, 2.8))
        c.restore(); c.restore()
        size = self.size if H > W else min(w * .7 / max(len(s_) for _, s_ in self.lines or [(0, 'x')]), h * .26)
        f = F('song', size)
        lh = size * 1.14
        for i, (t0, s_) in enumerate(self.lines):
            ink_text(c, s_, x + w * .09, yy + h * .3 + i * lh, f, t, t0, MO, a, stagger=.08)
        ny = yy + h * .3 + (len(self.lines) - 1) * lh + size * .5
        if self.sub:
            st, s_ = self.sub
            brush_stroke(c, x + w * .09, ny, x + w * .09 + 150, ny + 1, 7, ZHU, a, eo(P(t, st - .35, .6)), seed=2)
            circle(c, x + w * .09 + 180, ny, 7 * clamp(eob(P(t, st, .4))), ZHU, a)
            text(c, s_, x + w * .09, ny + 70, F('songb', 34 if H > W else 40), MO, a * eo(P(t, st + .1, .7)), spacing=8)
        if self.note:
            st, s_ = self.note
            k = eo(P(t, st, .8))
            line(c, x + w * .09, ny + 120, x + w * .09 + (w * .7) * k, ny + 120, MO, .5 * a, 1.2)
            circle(c, x + w * .09 + w * .7 * k, ny + 120, 5, MO, a * k)
            text(c, s_, x + w * .09, ny + 172, F('songr', 30 if H > W else 34), HUI, a * k, spacing=4)

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.sidebar:
            sp = eo(P(t, self.t0, .8))
            c.save(); c.translate(-140 * (1 - sp), 0)
            paper_piece(c, torn_rect(-30, -30, 140, H + 60, 'r', seed=61, rough=9), a, seed=3)
            circle(c, 55, H * .12, 5, ZHU, a)
            ink_vtext(c, self.sidebar, 55, H * .17, F('songr', 26), t, self.t0 + .4, MO, a, stagger=.06, step=34)
            if self.seal: seal(c, self.seal[1], 55, H * .74, min(W, H) * .07, t, self.seal[0], a, seed=9)
            c.restore()
        if self.corner and W > H and hasattr(self, '_card'):   # wide: a vertical motto inside the card's right edge
            ct = self.t0 + .9
            x, yy, w, h = self._card
            fs = F('songr', 30); step = 38
            cx_ = x + w - 64
            circle(c, cx_, yy + 56, 6, ZHU, a * eo(P(t, ct, .4)))
            ink_vtext(c, '  '.join(self.corner), cx_, yy + 108, fs, t, ct + .15, MO, a * .9, stagger=.05, step=step)
        elif self.corner:
            ct = self.t0 + .9
            circle(c, W * .74, H * .085, 6, ZHU, a * eo(P(t, ct, .4)))
            for i, s_ in enumerate(self.corner):
                text(c, s_, W * .74 - 4, H * .085 + 46 + i * 38, F('songr', 26), MO, a * eo(P(t, ct + .15 + i * .2, .7)), spacing=6)
        self.ambient(c, t)

    def events(self):
        ev = [(self.t0 + .05, 'bell', .6), (self.t0 + .6, 'breeze', .6)] + [(t0, 'pluck', .55) for t0, _ in self.lines]
        if self.sub: ev.append((self.sub[0] - .35, 'brush', .6))
        if self.seal: ev.append((self.seal[0], 'seal', .8))
        return ev


class PRoute(PaperScene):
    """a journey drawn as an ink route down the scroll: stops appear on their spoken word with an ink drop,
    a seal-ringed dot, the place name and a small note; a skiff travels to the latest stop.
    title=(t, '一路南迁')  stops=[(t, '黄州', '1080')]  ghost='贬'"""
    title = None
    stops = []
    ghost = None
    petals = 4

    def _pts(self):
        n = len(self.stops)
        return [(W * (.3 if i % 2 == 0 else .68), H * (.26 + .56 * i / max(1, n - 1))) for i in range(n)]

    def behind(self, c, t, ctx):
        a = self.a(t)
        if self.ghost: ghost(c, self.ghost, W * .2 if H > W else W * .55, H * .78 if H > W else H * .9, min(W, H) * .72, t, self.t0, DAI, .16 * a, tex='stipple')
        c.saveLayer(skia.Rect.MakeWH(W, H))
        mountain_layer(c, [(W * .2, H * .12, W * .2), (W * .7, H * .16, W * .22)], H * .9, QIAN, .5 * a, 21, -50, W + 50, blur=3)
        wave_lines(c, t, 0, W, H * .86, H * .93, a * .7, 3, 5)
        wash_mask(c, -50, W + 50, 0, H, P(t, self.t0, 2.5))
        c.restore()
        if self.title:
            tt, s_ = self.title
            ink_label(c, s_, W * .09, H * .1, a * eo(P(t, tt, .6)), size=30, spacing=10)
        pts = self._pts()
        pth = skia.Path(); pth.moveTo(*pts[0])
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            pth.cubicTo(x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, x1, y1)
        times = [st[0] for st in self.stops]
        n = len(pts); prog = 0.0
        for i in range(1, n):
            prog = (i - 1 + eio(P(t, times[i] - .45, .5))) / (n - 1) if t >= times[i] - .45 else prog
        if prog > 0:
            pp = paint(MO, .55 * a, stroke=3)
            pp.setPathEffect(skia.DashPathEffect.Make([14, 10], -t * 20))
            c.drawPath(partial_path(pth, 0, prog), pp)
            (bx, by), _ = path_pos(pth, prog)
            boat(c, bx + 6, by - 8, .75, a)
        for i, (st, name, note) in enumerate(self.stops):
            x, y = pts[i]
            ink_bloom(c, x, y, t, st - .05, 90, MO, .22 * a, seed=i)
            k = eob(P(t, st, .45))
            if k > 0:
                circle(c, x, y, 26 * k, ZHU, .9 * a, stroke=3)
                circle(c, x, y, 9 * k, MO, a)
            right = i % 2 == 0
            tx = x + (48 if right else -48)
            ink_text(c, name, tx, y + 24, F('song', 78), t, st, MO, a, stagger=.08, align='l' if right else 'r')
            if note: text(c, note, tx, y + 76, F('songr', 28), HUI, a * eo(P(t, st + .3, .6)), align='l' if right else 'r', spacing=4)

    def events(self):
        return [(self.t0 + .05, 'breeze', .6)] + [(st, 'drop' if i else 'pluck', .7) for i, (st, _, _) in enumerate(self.stops)]


class PTorn(PaperScene):
    """大字撕纸 on paper: a torn sheet printed with one word (cover) tears open and peels apart to reveal
    another underneath. cover=(t, '困境')  text='乐趣'  text_t=tear time  seal=(t, '趣')  kicker=(t, '...')"""
    cover = None
    text = '乐趣'
    text_t = 0
    size = None
    seal = None
    kicker = None
    petals = 6

    def _geom(self):
        if not hasattr(self, '_g'):
            w, h = min(W * .84, H * 1.25), H * (.38 if H > W else .48)
            x0, y0 = (W - w) / 2, H * (.3 if H > W else .22)
            sheet = torn_rect(x0, y0, w, h, 'trbl', seed=71, rough=13)
            mid = W / 2
            ln = torn_points(mid + 50, y0 - 40, mid - 40, y0 + h + 40, seed=73, rough=18, step=5)
            L = skia.Path(); L.moveTo(-200, y0 - 40)
            for p_ in ln: L.lineTo(*p_)
            L.lineTo(-200, y0 + h + 40); L.close()
            R = skia.Path(); R.moveTo(W + 200, y0 - 40)
            for p_ in ln: R.lineTo(*p_)
            R.lineTo(W + 200, y0 + h + 40); R.close()
            self._g = (sheet, skia.Op(sheet, L, skia.PathOp.kIntersect_PathOp), skia.Op(sheet, R, skia.PathOp.kIntersect_PathOp), (x0, y0, w, h))
        return self._g

    def _word(self, c, s_, rgb, a, t=None, t0=None):
        x0, y0, w, h = self._geom()[3]
        sz = self.size or min(w * .8 / max(1, len(s_)), h * .62)
        f = F('song', sz)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        if t is None: text(c, s_, W / 2, y0 + h / 2 + sz * .36, f, rgb, a, align='c')
        else: ink_text(c, s_, W / 2, y0 + h / 2 + sz * .36, f, t, t0, rgb, a, stagger=.12, align='c')
        dry(c, 'stipple')
        c.restore()

    def behind(self, c, t, ctx):
        a = self.a(t)
        sheet, left, right, _ = self._geom()
        k = eo(P(t, self.t0 + .05, .8))
        if a * clamp(k * 2) <= 0: return
        c.saveLayer(None, skia.Paint(Alphaf=a * clamp(k * 2)))   # one layer: the hidden word never shows through
        c.save(); c.translate(0, 60 * (1 - k)); c.rotate(lerp(-4, -1, k))
        paper_piece(c, sheet, 1, seed=1)
        tp = eo(P(t, self.text_t, .8))
        if tp > 0: self._word(c, self.text, MO, 1)
        if tp < 1:
            pieces = [(sheet, 0)] if tp <= 0 else [(left, -1), (right, 1)]
            for pc, sg in pieces:
                c.save(); c.translate(sg * W * .45 * tp, -H * .05 * tp * (1 if sg > 0 else .4)); c.rotate(sg * 10 * tp)
                paper_piece(c, pc, 1 - tp ** 2, shadow=.22 if sg else 0, seed=2 + sg)
                c.save(); c.clipPath(pc, skia.ClipOp.kIntersect, True)
                if self.cover: self._word(c, self.cover[1], DAI, 1 - tp ** 2, t, self.cover[0])
                c.restore(); c.restore()
        c.restore()
        c.restore()
        if self.kicker:   # always clear above the sheet
            kt, s_ = self.kicker
            x0, y0 = self._geom()[3][:2]
            ink_label(c, s_, x0 + 6, min(H * .2, y0 - 46), a * eo(P(t, kt, .6)), size=30, spacing=10)

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.seal:
            x0, y0, w, h = self._geom()[3]
            seal(c, self.seal[1], x0 + w - 70, y0 + h - 40, 70, t, self.seal[0], a, seed=4)
        self.ambient(c, t)

    def events(self):
        ev = [(self.t0 + .05, 'brush', .5), (self.text_t, 'tear', 1.0)]
        if self.cover: ev.append((self.cover[0], 'pluck', .5))
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


class PPoem(PaperScene):
    """vertical verses centred on the page (right to left), each character bleeding in as spoken; author column
    + seal; kicker label top-left; background 'river' (cliffs + flowing waves) or 'moon' (rising moon, ripples).
    lines=[(t0, t1, '大江东去')]  author=(t, '苏轼 · 念奴娇')  seal=(t, '东坡')  kicker=(t, '被贬黄州')  bg='river'|'moon'
    ghost='江' (huge pale character behind)"""
    lines = []
    author = None
    seal = None
    kicker = None
    bg = 'moon'
    font = 'kai'
    size = 112
    ghost = None
    petals = 8

    def behind(self, c, t, ctx):
        a = self.a(t)
        if self.ghost: ghost(c, self.ghost, W * .3 if H > W else W * .62, H * .74 if H > W else H * .9, min(W, H) * .68, t, self.t0, DAI, .13 * a, tex='stipple')
        if self.bg == 'moon':
            moon(c, t, W * .74, H * .2, W * .1, a, self.t0 + .1)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        if self.bg == 'river':
            mountain_layer(c, [(W * .05, H * .3, W * .14), (W * .25, H * .18, W * .1)], H * .86, DAI, .55 * a, 31, -50, W * .6, blur=1.5, depth=200)
            mountain_layer(c, [(W * .95, H * .24, W * .12)], H * .88, MO, .4 * a, 32, W * .5, W + 50, blur=1.2, depth=200)
            wave_lines(c, t, 0, W, H * .8, H * .9, a, 7, 11)
            mist(c, t, H * .74, H * .82, .55 * a, 33, 3)
        else:
            mountain_layer(c, [(W * .2, H * .1, W * .2), (W * .65, H * .14, W * .2)], H * .88, QIAN, .55 * a, 34, -50, W + 50, blur=3)
            mist(c, t, H * .8, H * .87, .6 * a, 35, 3)
            water(c, t, 0, W, H * .89, H * .94, a, 36)
        wash_mask(c, -50, W + 50, 0, H, P(t, self.t0 + .05, 2.6))
        c.restore()
        if self.kicker:
            kt, s_ = self.kicker
            ink_label(c, s_, W * .09, H * .1, a * eo(P(t, kt, .6)), size=30, spacing=10)
        n = len(self.lines)
        gap = self.size * 1.5
        cols = n + (1 if self.author else 0)
        xs = [W / 2 + (cols - 1) / 2 * gap - i * gap for i in range(cols)]
        step = self.size * 1.14
        y0 = H * .24
        f = F(self.font, self.size)
        maxlen = max([len(l[-1]) for l in self.lines] or [1])
        for i, ln in enumerate(self.lines):
            t0, s_ = ln[0], ln[-1]
            stg = (ln[1] - ln[0]) / max(1, len(s_)) if len(ln) == 3 else .14
            rp = eo(P(t, t0 - .4, 1.0))
            lx = xs[i] - gap / 2
            line(c, lx, y0 - self.size, lx, y0 - self.size + (maxlen * step + 30) * rp, DAI, .18 * a, 1)
            ink_vtext(c, s_, xs[i], y0, f, t, t0, MO, a, stagger=stg, dur=1.0, step=step)
        if self.author:
            at, s_ = self.author
            ax = xs[-1] + gap * .2
            hgt = credit(c, s_, ax, y0 + 10, t, at, a)
            if self.seal:
                sz = min(W, H) * .075
                seal(c, self.seal[1], ax, y0 + hgt + sz * .5 + 10, sz, t, self.seal[0], a, seed=6)

    def ready_t(self):
        """when the last verse character has been readable for 1 s (used to time the page turn)."""
        return max([(ln[1] if len(ln) == 3 else ln[0] + len(ln[-1]) * .14) + 1.0 for ln in self.lines] or [0])

    def events(self):
        ev = [(self.t0 + .05, 'breeze', .6)] + [(ln[0], 'pluck', .6) for ln in self.lines]
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


class PWords(PaperScene):
    """a short lead line, then key words land one by one on torn paper scraps in a 2-column grid; the last one can
    carry a seal. lead=(t, '别人看到的是诗意')  head=(t, '苏轼看到的却是')  words=[(t, '江风'), ...]  seal_last='生'"""
    lead = None
    head = None
    words = []
    seal_last = None
    petals = 8

    def behind(self, c, t, ctx):
        a = self.a(t)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        landscape(c, t, -40, W + 40, H * .9, a * .7, seed=41, scale=.9, boat_x=.7, has_birds=False)
        wash_mask(c, -40, W + 40, 0, H, P(t, self.t0, 2.6))
        c.restore()
        if self.lead:
            lt, s_ = self.lead
            k = eo(P(t, lt, .7))
            text(c, s_, W * .09, H * .13, F('songr', 36), HUI, a * k, spacing=6)
            if self.head:   # strike the lead through as the head line answers it
                sk = eo(P(t, self.head[0] + .4, .5))
                if sk > 0:
                    lw = tw(s_, F('songr', 36)) + 6 * len(s_) + 12
                    line(c, W * .09 - 6, H * .13 - 13, W * .09 - 6 + lw * sk, H * .13 - 13, ZHU, a * .8, 2.5)
        if self.head:
            ht, s_ = self.head
            ink_text(c, s_, W * .09, H * .22, F('song', 74), t, ht, MO, a, stagger=.07)
        r = np.random.RandomState(5)
        wide = W > H * 1.2
        cw, ch_ = (W * .2, H * .27) if wide else (W * .38, H * .17)
        for i, (wt, s_) in enumerate(self.words):
            col, row = i % 2, i // 2
            if wide: cx, cy = W * (.17 + .22 * i) + r.uniform(-10, 10), H * .56 + r.uniform(-18, 18)
            else: cx, cy = W * (.29 if col == 0 else .71) + r.uniform(-14, 14), H * .38 + row * H * .21 + r.uniform(-10, 10)
            rot = r.uniform(-5, 5)
            p = P(t, wt, .45)
            if p <= 0: continue
            k = eob(p, 1.2)
            c.save(); c.translate(cx, cy); c.rotate(rot * lerp(2.5, 1, eo(p))); sc = lerp(1.3, 1, k); c.scale(sc, sc)
            paper_piece(c, torn_rect(-cw / 2, -ch_ / 2, cw, ch_, 'trbl', seed=80 + i, rough=9), a * clamp(p * 3), seed=i)
            f = F('song', min(ch_ * .58, cw * .8 / max(1, len(s_))))
            c.saveLayer(skia.Rect.MakeXYWH(-cw, -ch_, 2 * cw, 2 * ch_))
            text(c, s_, 0, f.getSize() * .36, f, MO, a * clamp(p * 3), align='c')
            dry(c, 'stipple')
            c.restore()
            if self.seal_last and i == len(self.words) - 1:
                seal(c, self.seal_last, cw / 2 - 30, ch_ / 2 - 26, 48, t, wt + .35, a, seed=12)
            c.restore()

    def events(self):
        ev = [(self.t0 + .05, 'breeze', .5)] + [(wt, 'tear' if i % 2 == 0 else 'brush', .55) for i, (wt, _) in enumerate(self.words)]
        if self.head: ev.append((self.head[0], 'pluck', .5))
        if self.seal_last and self.words: ev.append((self.words[-1][0] + .35, 'seal', .8))
        return ev


class PBig(PaperScene):
    """two big lines bleeding in at the centre over a huge pale stippled character, with an ink drop and a seal.
    lines=[(t, '千年之后'), (t, '依然喜欢')]  ghost='苏'  seal=(t, '东坡')  label=(t, '千年')"""
    lines = []
    ghost = None
    seal = None
    label = None
    size = None
    petals = 10

    def behind(self, c, t, ctx):
        a = self.a(t)
        wide = W > H * 1.2
        if self.ghost:   # off to the side, never behind the lines
            ghost(c, self.ghost, W * .14 if not wide else W * .74, H * .7 if not wide else H * .96, min(W, H) * .8, t, self.t0,
                  DAI, .18 * a, tex='stipple')
        moon(c, t, W * (.8 if not wide else .17), H * .14 if not wide else H * .2, min(W, H) * .06 if not wide else H * .08, a * .8, self.t0)
        sz = self.size or min(W * .8 / max(len(s_) for _, s_ in self.lines), 170)
        f = F('song', sz)
        y = H * .42
        if self.lines: ink_bloom(c, W / 2, y - sz * .4, t, self.lines[0][0] - .05, W * .3, MO, .16 * a, seed=8, dur=2.2)
        for i, (t0, s_) in enumerate(self.lines):
            ink_text(c, s_, W / 2, y + i * sz * 1.3, f, t, t0, MO if i == 0 else MO, a, stagger=.1, align='c')
        if self.label:
            lt, s_ = self.label
            ink_label(c, s_, W * .09, H * .1, a * eo(P(t, lt, .6)), size=30, spacing=10)
        if self.seal:
            bw = max(tw(s_, f) for _, s_ in self.lines)
            ssz = min(W, H) * .08
            sx = min(W / 2 + bw / 2 + ssz * .9, W - ssz)
            sy = min(y + (len(self.lines) - 1) * sz * 1.3 - sz * .3, H - 230 - ssz)
            paper_halo(c, sx - ssz, sy - ssz, ssz * 2, ssz * 2, a)
            seal(c, self.seal[1], sx, sy, ssz, t, self.seal[0], a, seed=3)

    def events(self):
        ev = [(t0, 'drop' if i == 0 else 'pluck', .7) for i, (t0, _) in enumerate(self.lines)]
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


class PEnd(PaperScene):
    """closing: a lead line, ink rain sweeping across on the 'storm' word, then the big answer bleeding in with a
    cinnabar stroke, and a vertical quote with its source and a seal.
    lead=(t, '人生可以有风雨')  rain=(t0, t1)  big=[(t, '豁达'), (t, '浪漫')]  quote=(t, '一蓑烟雨任平生')
    source='苏轼《定风波》'  seal=(t, '东坡')"""
    lead = None
    rain = None
    big = []
    quote = None
    source = None
    seal = None
    petals = 18

    def behind(self, c, t, ctx):
        a = self.a(t)
        c.saveLayer(skia.Rect.MakeWH(W, H))
        landscape(c, t, -40, W + 40, H * .9, a * .8, seed=51, scale=.9, boat_x=.3)
        wash_mask(c, -40, W + 40, 0, H, P(t, self.t0, 2.4))
        c.restore()
        if self.rain:
            r0, r1 = self.rain
            ra = window(t, r0, r1, .4, .8) * a
            if ra > 0:
                rr = np.random.RandomState(3)
                for _ in range(90):
                    x = rr.rand() * (W + 300); sp = rr.uniform(900, 1500); L = rr.uniform(30, 80)
                    y = (rr.rand() * H + t * sp) % (H + 100) - 50
                    line(c, x - y * .25, y, x - (y + L) * .25, y + L, DAI, ra * rr.uniform(.2, .5), 1.4)
        if W > H * 1.2: return self._wide(c, t, a)
        if self.lead:
            lt, s_ = self.lead
            ink_text(c, s_, W * .09, H * .16, F('songb', 58), t, lt, MO, a, stagger=.07)
        sz = min(W * .34, 230)
        for i, (bt, s_) in enumerate(self.big):
            y = H * .4 + i * sz * 1.15
            ink_bloom(c, W * .09 + sz, y - sz * .4, t, bt - .05, sz * 1.1, MO, .14 * a, seed=20 + i)
            w = ink_text(c, s_, W * .09, y, F('song', sz), t, bt, MO, a, stagger=.12)
            brush_stroke(c, W * .09 + 6, y + 40, W * .09 + w * .55, y + 41, 8, ZHU, a, eo(P(t, bt + .45, .6)), seed=30 + i)
        if self.quote:
            qt, s_ = self.quote
            qx = W * .84
            ink_vtext(c, s_, qx, H * .3, F('kai', 58), t, qt, MO, a, stagger=.12, step=68)
            if self.source:
                credit(c, self.source, qx - 78, H * .32, t, qt + .6, a, size=min(W, H) * .03)
            if self.seal:
                sz = min(W, H) * .07
                paper_halo(c, qx - sz, H * .3 + len(s_) * 68 + 30 - sz, sz * 2, sz * 2, a)
                seal(c, self.seal[1], qx, H * .3 + len(s_) * 68 + 30, sz, t, self.seal[0], a, seed=14)

    def _wide(self, c, t, a):
        """16:9: answer words on the left, the quote inside a round paper window (圆窗) centre-right."""
        x0 = W * .08
        if self.lead:
            lt, s_ = self.lead
            ink_text(c, s_, x0, H * .2, F('songb', 56), t, lt, MO, a, stagger=.07)
        sz = min(H * .25, W * .16)
        for i, (bt, s_) in enumerate(self.big):
            y = H * .45 + i * sz * 1.18
            w = ink_text(c, s_, x0, y, F('song', sz), t, bt, MO, a, stagger=.12)
            brush_stroke(c, x0 + 6, y + 36, x0 + w * .55, y + 37, 8, ZHU, a, eo(P(t, bt + .45, .6)), seed=30 + i)
        if not self.quote: return
        qt, s_ = self.quote
        cx_, cy_, R = W * .64, H * .45, H * .33
        k = eo(P(t, qt - .3, 1.0))
        ghost(c, '雨', W * .66, H * 1.02, H * .95, t, qt - .3, DAI, .12 * a, tex='stipple')
        if k > 0:
            circle(c, cx_, cy_ + 14, R * lerp(.94, 1, k), (60, 60, 70), .1 * a * k, blur=26)
            circle(c, cx_, cy_, R * lerp(.94, 1, k), XUAN_L, .9 * a * k)
            circle(c, cx_, cy_, R * lerp(.94, 1, k), DAI, .4 * a * k, stroke=2)
            circle(c, cx_, cy_, R * lerp(.94, 1, k) - 14, DAI, .18 * a * k, stroke=1)
            c.save(); c.clipPath(blob_path(cx_, cy_, R - 16, 0, 0), skia.ClipOp.kIntersect, True)
            mountain_layer(c, [(cx_ - R * .5, R * .35, R * .4), (cx_ + R * .4, R * .5, R * .35)], cy_ + R * .9, QIAN, .45 * a * k, 61,
                           cx_ - R, cx_ + R, blur=2.5)
            c.restore()
        step = R * 1.34 / max(1, len(s_))
        fs = F('kai', min(step * .9, 66))
        qx = cx_ + R * .14
        ink_vtext(c, s_, qx, cy_ - R * .62 + fs.getSize(), fs, t, qt, MO, a, stagger=.12, step=step)
        if self.source:
            credit(c, self.source, qx - fs.getSize() * 1.6, cy_ - R * .5 + 40, t, qt + .6, a, size=min(W, H) * .03)
        if self.seal:
            ssz = min(W, H) * .075
            sx, sy = cx_ + R * .72, cy_ + R * .62
            paper_halo(c, sx - ssz, sy - ssz, ssz * 2, ssz * 2, a)
            seal(c, self.seal[1], sx, sy, ssz, t, self.seal[0], a, seed=14)

    def events(self):
        ev = []
        if self.rain: ev.append((self.rain[0], 'breeze', .9))
        if self.lead: ev.append((self.lead[0], 'pluck', .5))
        ev += [(bt, 'bell' if i == 0 else 'drop', .7) for i, (bt, _) in enumerate(self.big)]
        if self.quote: ev.append((self.quote[0], 'brush', .5))
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


# =============================================================== presenter + footage (poetry-ink)
class BRollReader:
    """sequential frame reader for footage shown inside a scene (seeks only when time jumps)."""

    def __init__(self, path, fps=25, size=(960, 540), crop=None):
        self.path, self.fps, self.size, self.crop = path, fps, size, crop   # crop = (x, y, w, h) fractions of the source
        self.p = None; self.idx = -10; self.img = None

    def _open(self, t):
        import subprocess
        w, h = self.size
        if self.p: self.p.kill()
        pre = ''
        if self.crop:
            cx, cy, cw, ch = self.crop
            pre = f'crop=iw*{cw}:ih*{ch}:iw*{cx}:ih*{cy},'
        self.p = subprocess.Popen(['./ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.3f}', '-i', self.path, '-vf',
                                   f'{pre}scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={self.fps}',
                                   '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.idx = int(round(max(0, t) * self.fps)) - 1

    def at(self, t):
        want = int(round(max(0, t) * self.fps))
        if want == self.idx and self.img is not None: return self.img
        if not (self.p and 0 < want - self.idx <= 3): self._open(want / self.fps)
        w, h = self.size
        b = None
        while self.idx < want:
            b = self.p.stdout.read(w * h * 3); self.idx += 1
            if len(b) < w * h * 3: b = None; break
        if b:
            arr = np.dstack([np.frombuffer(b, np.uint8).reshape(h, w, 3), np.full((h, w), 255, np.uint8)])
            self.img = skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)
        return self.img


def hanging_scroll(c, x, y, w, h, p, a=1.0):
    """mounted hanging scroll (立轴): silk border + wooden rods; p = how far it has unrolled (0..1).
    Returns the inner picture rect (x, y, w, h) and its current visible clip (top, bottom)."""
    cy = y + h / 2
    half = (h / 2 + 34) * eio(p)
    top, bot = cy - half, cy + half
    if a <= 0 or p <= 0: return (x, y, w, h), (cy, cy)
    c.drawRect(skia.Rect.MakeLTRB(x - 26, top + 10, x + w + 26, bot + 24), paint((40, 40, 50), .18 * a, blur=18))
    c.drawRect(skia.Rect.MakeLTRB(x - 26, top, x + w + 26, bot), paint((214, 206, 188), a))          # silk mount
    c.drawRect(skia.Rect.MakeLTRB(x - 14, top + 12, x + w + 14, bot - 12), paint(XUAN_L, a))
    for yy in (top, bot):   # rods with knobs
        rrect(c, x - 44, yy - 9, w + 88, 18, 9, (78, 56, 42), a)
        rrect(c, x - 44, yy - 9, w + 88, 6, 3, (120, 92, 70), .6 * a)
        for xx in (x - 52, x + w + 36):
            rrect(c, xx, yy - 12, 16, 24, 6, (58, 40, 30), a)
    return (x, y, w, h), (top + 14, bot - 14)


class InkScroll(Scene):
    """Full frame with the presenter; footage (e.g. the finished result) plays inside a hanging scroll that
    unrolls on the left, over a paper mist. broll='../result.mp4', b0=start time in the footage,
    kicker=(t, '刚才这段 · 苏轼'), label=(t, 'xingor-video-skill'), seal=(t, '诗墨'), rect=(x, y, w, h)"""
    broll = None
    b0 = 0.0
    kicker = None
    label = None
    seal = None
    rect = (90, 210, 640, 360)
    zoom = 1.06

    def xf(self, t):
        return full_xf(lerp(self.zoom, self.zoom + .03, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .3)
        left_mist(c, t, .8 * a, x1=1050)
        x, y, w, h = self.rect
        p = P(t, self.t0 + .15, 1.1)
        _, (top, bot) = hanging_scroll(c, x, y, w, h, p, a)
        if self.broll and bot > top:
            if not hasattr(self, '_rd'): self._rd = BRollReader(self.broll, ctx.fps, (int(w), int(h)))
            img = self._rd.at(self.b0 + max(0, t - self.t0))
            if img is not None:
                c.save(); c.clipRect(skia.Rect.MakeLTRB(x, max(y, top), x + w, min(y + h, bot)))
                c.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), SAMP, skia.Paint(Alphaf=a))
                c.restore()
                c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint(MO, .25 * a * clamp(p * 2), stroke=1.2))

    def front(self, c, t, ctx):
        a = self.a(t)
        x, y, w, h = self.rect
        if self.kicker:
            kt, s_ = self.kicker
            ink_label(c, s_, x - 10, y - 70, a * eo(P(t, kt, .6)), size=28, spacing=8)
        if self.label:
            lt, s_ = self.label
            k = eo(P(t, lt, .6))
            f = F('songb', 34)
            ly = y + h + 96
            if k > 0:
                paper_halo(c, x - 30, ly - 60, tw(s_, f) + 200, 100, a * k)
                text(c, s_, x + 70, ly + 4 * (1 - k), f, MO, a * k, spacing=2)
                brush_stroke(c, x + 72, ly + 22, x + 72 + tw(s_, f) * .5, ly + 23, 6, ZHU, a, eo(P(t, lt + .3, .6)), seed=9)
        if self.seal:
            st, s_ = self.seal
            seal(c, s_, x + 26, y + h + 84, 56, t, st, a, seed=21)

    def events(self):
        ev = [(self.t0 + .15, 'gliss', .6)]
        if self.label: ev.append((self.label[0], 'brush', .6))
        if self.seal: ev.append((self.seal[0], 'seal', .9))
        return ev


class InkPrompt(ScrollScene):
    """The presenter on paper at the right; on the left, numbered steps, then a letter sheet (信笺, with cinnabar
    rules) on which the prompt is written character by character in step with the speech.
    label=(t, '只需一句话')  steps=[(t, '安装 Skill'), (t, '告诉 AI')]  prompt=(t0, t1, '用 Poetry Ink 风格，…')"""
    label = None
    steps = []
    prompt = None
    petals = 6

    def behind(self, c, t, ctx):
        a = self.a(t)
        if self.label:
            lt, s_ = self.label
            ink_label(c, s_, 120, 150, a * eo(P(t, lt, .6)), size=28, spacing=8)
        for i, (st, s_) in enumerate(self.steps):
            x = 120 + i * 420
            seal(c, NUMS[i], x + 28, 236, 56, t, st, a, font='song', seed=40 + i)
            ink_text(c, s_, x + 76, 256, F('song', 50), t, st + .05, MO, a, stagger=.06)
            if i: brush_stroke(c, x - 110, 238, x - 40, 239, 3, DAI, a * .5, eo(P(t, st - .2, .5)), seed=50 + i)
        if self.prompt:
            p0, p1, s_ = self.prompt
            x, y, w, h = 110, 340, 990, 470
            k = eo(P(t, p0 - .6, .8))
            if k <= 0: return
            paper_card(c, x, y + 20 * (1 - k), w, h, a * k)
            yy = y + 20 * (1 - k)
            text(c, '提示词', x + 40, yy + 58, F('songr', 24), HUI, a * k, spacing=10)
            LH = 92
            for i in range(4):   # 八行笺-style cinnabar rules
                ly = yy + 172 + i * LH
                line(c, x + 36, ly, x + w - 36, ly, ZHU, .2 * a * k, 1.2)
            f = F('kai', 62)
            n = len(s_); xx, row = x + 50, 0
            for i, ch in enumerate(s_):
                cw = f.measureText(ch)
                if xx + cw > x + w - 50: xx, row = x + 50, row + 1
                tt = p0 + (p1 - p0) * i / max(1, n - 1)
                _glyph(c, ch, xx, yy + 156 + row * LH, f, MO, a * k, P(t, tt, .45), rise=4)
                xx += cw
            # brush tip that follows the writing
            if p0 <= t <= p1 + .3:
                i = min(n - 1, int((t - p0) / max(.01, p1 - p0) * (n - 1)))
                xx, row = x + 50, 0
                for ch in s_[:i + 1]:
                    cw = f.measureText(ch)
                    if xx + cw > x + w - 50: xx, row = x + 50, row + 1
                    xx += cw
                circle(c, xx + 8, yy + 156 + row * LH - 22, 6, MO, .6 * a)

    def front(self, c, t, ctx):
        self.ambient(c, t)

    def events(self):
        ev = [(st, 'seal', .7) for st, _ in self.steps]
        if self.prompt: ev += [(self.prompt[0] - .6, 'brush', .5), (self.prompt[1], 'pluck', .6)]
        return ev


class InkShowcase(Scene):
    """Footage-first page: the footage (e.g. the finished result) plays large on xuan paper inside a thin indigo
    frame, the presenter sits in a round, face-tracked avatar at the lower right, and what is being said appears
    beside it (headline + tag chips in the right margin) or on a paper strip over the footage (a typed prompt).
    broll, b0 = footage time at this scene's t0 (keep b0 = t0 - start of the first showcase for one continuous play)
    headline=(t, '只需一句话')  tags=[(t, '安装 Skill'), ...]  strip=(t0, t1, '用 Poetry Ink 风格，…')
    seal=(t, '墨')  name='阿星 · 口播'.  Use smooth_in=True on consecutive showcases so the footage never cuts."""
    mode = 'talk'
    broll = None
    b0 = 0.0
    headline = None
    tags = []
    strip = None
    seal = None
    name = '口播'
    crop = (.06, 0, .88, .88)   # drop the footage's own burned-in subtitles (bottom ~12%) so only ours show
    layout = 'frame'            # 'frame' = inset picture on paper with a margin column | 'full' = footage fills the frame
    avatar_in = None            # 'full': the presenter's full frame shrinks into the avatar at t0 (use as the transition)
    avatar_big = None           # (t, (cx, cy, r)): the avatar springs to a bigger circle (e.g. for the ending)
    cta = None                  # (t, '评论区见'): big paper card slammed in, footage dims behind it
    s_first = None              # time the continuous footage section started (for a steady push across scenes)
    motion = False              # full layout: slow push + zoom bumps on keywords (off = footage shown still and whole)
    side = 'column'             # full layout overlay: 'column' (calm vertical inscription, 题款) | 'banner' (hanging banner + chips)
    cover_subs = True           # full layout: a soft paper band hides the footage's own subtitle line; ours sit on it
    smooth_in = False
    _readers = {}

    def _rects(self):
        if self.layout == 'full':
            return (0, 0, W, H), (W - 170, H - 330, 128)
        fw, fh = W * .8, H * .8
        return (56, 40, fw, fh), (W - 170, H - 330, 128)

    def _beats(self):
        bs = [tt for tt, _ in self.tags]
        if self.headline: bs.append(self.headline[0])
        if self.cta: bs.append(self.cta[0])
        return bs

    def draw_bg(self, c, t, ctx):
        if self.layout == 'full':
            (fx, fy, fw, fh), _ = self._rects()
            key = (self.broll, int(fw), int(fh), self.crop)
            if self.broll:
                rd = InkShowcase._readers.get(key)
                if rd is None: rd = InkShowcase._readers[key] = BRollReader(self.broll, ctx.fps, (int(fw), int(fh)), self.crop)
                img = rd.at(self.b0 + max(0, t - self.t0))
                if img is not None:   # optional slow push + a small zoom bump on every keyword
                    z = 1.0
                    if self.motion:
                        z += .0016 * (t - (self.s_first if self.s_first is not None else self.t0))
                        z += sum(.022 * math.exp(-((t - b - .12) / .22) ** 2) for b in self._beats())
                    c.save(); c.translate(W / 2, H * .45); c.scale(z, z); c.translate(-W / 2, -H * .45)
                    c.drawImageRect(img, skia.Rect.MakeXYWH(fx, fy, fw, fh), SAMP, skia.Paint())
                    c.restore()
            else: ink_bg(c, t)
            if self.cta:
                c.drawRect(skia.Rect.MakeWH(W, H), paint(XUAN_L, .88 * eio(P(t, self.cta[0] - .5, 1.0))))
            if self.cover_subs:   # hide the footage's own subtitle line under a soft paper band
                sh = skia.GradientShader.MakeLinear([(0, H - 150), (0, H)], [CI(XUAN_L, 0), CI(XUAN_L, .97), CI(XUAN_L, .97), CI(XUAN_L, .9)],
                                                    [0, .3, .8, 1])
                c.drawRect(skia.Rect.MakeLTRB(0, H - 150, W, H), skia.Paint(Shader=sh))
            return
        ink_bg(c, t)
        (fx, fy, fw, fh), _ = self._rects()
        c.drawRect(skia.Rect.MakeXYWH(fx + 8, fy + 20, fw - 16, fh - 8), paint((40, 40, 50), .2, blur=22))
        key = (self.broll, int(fw), int(fh), self.crop)
        if self.broll:
            rd = InkShowcase._readers.get(key)
            if rd is None: rd = InkShowcase._readers[key] = BRollReader(self.broll, ctx.fps, (int(fw), int(fh)), self.crop)
            img = rd.at(self.b0 + max(0, t - self.t0))
            if img is not None: c.drawImageRect(img, skia.Rect.MakeXYWH(fx, fy, fw, fh), SAMP, skia.Paint())
        c.drawRect(skia.Rect.MakeXYWH(fx - 10, fy - 10, fw + 20, fh + 20), paint(MO, .45, stroke=1.4))

    def _avatar(self, c, t, ctx):
        _, (cx, cy, r) = self._rects()
        if self.avatar_big:
            bt, (bx, by, br) = self.avatar_big
            k = spring(P(t, bt, .8)) if self.motion else eio(P(t, bt, 1.3))
            cx, cy, r = lerp(cx, bx, k), lerp(cy, by, k), lerp(r, br, k)
        if self.avatar_in == 'full':
            k = spring(P(t, self.t0, .75)) if self.motion else eio(P(t, self.t0, 1.1))
            if k < 1:   # the presenter's full frame shrinks into the circle
                x0, y0, w0, h0, rr = lerp(0, cx - r, k), lerp(0, cy - r, k), lerp(W, 2 * r, k), lerp(H, 2 * r, k), lerp(0, r, k)
                hx, fy, side = ctx.head_x, PERSON['face_y'] - 40, 560
                sx = clamp(hx - side / 2, 0, W - side); sy = clamp(fy - side * .5, 0, H - side)
                q = clamp(k * 1.15)
                src = skia.Rect.MakeXYWH(lerp(0, sx, q), lerp(0, sy, q), lerp(W, side, q), lerp(H, side, q))
                rect = skia.Rect.MakeXYWH(x0, y0, w0, h0)
                c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y0 + 14, w0, h0), rr, rr), paint((40, 40, 50), .25 * k, blur=18))
                c.save(); c.clipRRect(skia.RRect.MakeRectXY(rect, rr, rr), skia.ClipOp.kIntersect, True)
                c.drawImageRect(ctx.img, src, rect, SAMP, skia.Paint())
                c.restore()
                c.drawRRect(skia.RRect.MakeRectXY(rect, rr, rr), paint(XUAN_L, k, stroke=7 * k))
                return
        r *= 1 + .012 * math.sin(t * 2.2)
        c.drawCircle(cx, cy + 10, r + 8, paint((40, 40, 50), .25, blur=16))
        hx, fy, side = ctx.head_x, PERSON['face_y'] - 40, 560
        src = skia.Rect.MakeXYWH(clamp(hx - side / 2, 0, W - side), clamp(fy - side * .5, 0, H - side), side, side)
        pth = skia.Path(); pth.addCircle(cx, cy, r)
        c.save(); c.clipPath(pth, skia.ClipOp.kIntersect, True)
        c.drawImageRect(ctx.img, src, skia.Rect.MakeXYWH(cx - r, cy - r, 2 * r, 2 * r), SAMP, skia.Paint())
        c.restore()
        circle(c, cx, cy, r, XUAN_L, 1, stroke=7)
        circle(c, cx, cy, r + 9, MO, .35, stroke=1.2)
        ring = skia.Path(); ring.addCircle(cx, cy, r + 18)
        p = paint(ZHU, .45, stroke=1.6); p.setPathEffect(skia.DashPathEffect.Make([10, 16], -t * (30 if self.motion else 6))); c.drawPath(ring, p)
        f = F('songb', 22); w = tw(self.name, f) + 54
        rrect(c, cx - w / 2, cy + r + 26, w, 40, 6, XUAN_L, .95)
        circle(c, cx - w / 2 + 20, cy + r + 46, 5, ZHU, .6 + .4 * math.sin(t * 3))
        text(c, self.name, cx - w / 2 + 34, cy + r + 53, f, MO, 1)

    def front(self, c, t, ctx):
        a = self.a(t)
        (fx, fy, fw, fh), _ = self._rects()
        full = self.layout == 'full'
        mx = W - 330 if full else fx + fw + 36
        if full:
            self._full_front(c, t, ctx, a)
            self._avatar(c, t, ctx)
            return
        if self.headline:
            ht, s_ = self.headline
            k = eo(P(t, ht, .6))
            circle(c, mx + 6, 92, 6, ZHU, a * k)
            ink_text(c, s_, mx, 150, F('song', min(46, (W - mx - 30) / max(1, len(s_)))), t, ht, MO, a, stagger=.06)
        for i, (tt, s_) in enumerate(self.tags):
            p = eob(P(t, tt, .45), 1.3)
            if p <= 0: continue
            f = F('songb', 28); w = tw(s_, f) + 60; y = 200 + i * 70
            al = a * clamp(p * 2)
            rrect(c, mx, y + 8 + 10 * (1 - p), w, 52, 8, (60, 60, 70), .1 * al, blur=10)
            rrect(c, mx, y + 10 * (1 - p), w, 52, 8, XUAN_L, al)
            rrect(c, mx, y + 12 + 10 * (1 - p), 4, 28, 2, ZHU, al)
            text(c, s_, mx + 24, y + 36 + 10 * (1 - p), f, MO, al)
        if self.strip:
            s0, s1, s_ = self.strip
            k = eo(P(t, s0 - .5, .6)) * a
            if k > 0:
                f = F('kai', 50)
                sh_, sy = 150, (H - 410 if full else fy + fh - 190) + 20 * (1 - k)
                paper_piece(c, torn_rect(fx + 60, sy, fw - 120, sh_, 'tb', seed=88, rough=7), k, seed=5)
                text(c, '提示词', fx + 96, sy + 40, F('songr', 22), HUI, k, spacing=8)
                xx, n = fx + 96, len(s_)
                for i, ch in enumerate(s_):
                    tt = s0 + (s1 - s0) * i / max(1, n - 1)
                    _glyph(c, ch, xx, sy + 108, f, MO, k, P(t, tt, .4), rise=4)
                    xx += f.measureText(ch)
        if self.seal:
            st, s_ = self.seal
            seal(c, s_, fx + fw - 40, fy + 50, 62, t, st, a, seed=31)
        self._avatar(c, t, ctx)

    def _column(self, c, t, a):
        """calm inscription (题款) at the top right: the headline as one large vertical line, keywords as thinner
        columns to its left appearing on their words (Latin set sideways), a soft paper patch behind for legibility."""
        if not (self.headline or self.tags): return
        hs, ts = 66, 34; hstep, tstep = 78, 42
        x0 = W - 120
        cols = [(self.headline[0], self.headline[1], True)] if self.headline else []
        cols += [(tt, s_, False) for tt, s_ in self.tags]
        first = min(c_[0] for c_ in cols)
        k = eo(P(t, first - .2, .8))
        tall = max((len(s_) * (hstep if big else tstep) if not s_.isascii() else tw(s_, F('songb', ts))) for _, s_, big in cols)
        width = 110 + 58 * (len(cols) - 1)
        paper_halo(c, x0 - width - 40, 20, width + 140, tall + 170, a * k * .97)
        x = x0
        for i, (tt, s_, big) in enumerate(cols):
            if big:
                ink_vtext(c, s_, x, 70 + hs, F('song', hs), t, tt, MO, a, stagger=.09, dur=.8, step=hstep)
                x -= 92
            else:
                p = eo(P(t, tt, .7))
                if p <= 0: x -= 58; continue
                if s_.isascii():   # Latin runs sideways in a vertical layout
                    c.save(); c.translate(x - 12, 80 + 8 * (1 - p)); c.rotate(90)
                    text(c, s_, 0, 0, F('songb', ts), MO, a * p * .9, spacing=2)
                    c.restore()
                else:
                    ink_vtext(c, s_, x, 80 + ts, F('songb', ts), t, tt, MO, a * .9, stagger=.06, dur=.6, step=tstep)
                if i == 1: circle(c, x, 60, 4, ZHU, a * p)
                x -= 58

    def _full_front(self, c, t, ctx, a):
        """full layout: overlay (calm inscription column, or banner + chips), an optional typed prompt strip and
        an optional CTA card."""
        bx = W - 236
        if self.side == 'column':
            self._column(c, t, a)
        if self.side == 'banner' and self.headline:
            ht, s_ = self.headline
            k = eob(P(t, ht - .05, .55), 1.4)
            if k > 0:
                fs = F('song', 84); step = 96
                bh = len(s_) * step + 110
                yoff = -bh * (1 - k)
                c.save(); c.translate(0, yoff)
                paper_piece(c, torn_rect(bx, -30, 156, bh + 30, 'lrb', seed=91, rough=8), a, seed=4)
                rrect(c, bx - 6, -30, 168, 22, 6, (78, 56, 42), a)     # top rod
                ink_vtext(c, s_, bx + 78, 74, fs, t, ht + .15, MO, a, stagger=.07, dur=.5, step=step)
                c.restore()
        for i, (tt, s_) in enumerate(self.tags if self.side == 'banner' else []):
            p = spring(P(t, tt, .5))
            if p <= 0: continue
            f = F('songb', 32); w = tw(s_, f) + 64; y = 70 + i * 78
            x = bx - 30 - w + 60 * (1 - p)
            al = a * clamp(p * 3)
            rrect(c, x, y + 8, w, 58, 8, (40, 40, 50), .16 * al, blur=12)
            rrect(c, x, y, w, 58, 8, XUAN_L, .96 * al)
            rrect(c, x, y + 14, 5, 30, 2, ZHU, al)
            text(c, s_, x + 26, y + 41, f, MO, al)
        if self.strip:
            s0, s1, s_ = self.strip
            k = eo(P(t, s0 - .6, .45 if self.motion else .9)) * a
            if k > 0:
                f = F('kai', 52)
                sw_ = min(W - 520, sum(f.measureText(ch) for ch in s_) + 120)
                sx = 60 - ((sw_ + 80) * (1 - k) if self.motion else 0); sy = H - 400 + (0 if self.motion else 16 * (1 - k))
                c.saveLayer(None, skia.Paint(Alphaf=1 if self.motion else k))
                paper_piece(c, torn_rect(sx, sy, sw_, 150, 'trb', seed=88, rough=7), 1, seed=5)
                text(c, '提示词', sx + 50, sy + 40, F('songr', 22), HUI, 1, spacing=8)
                xx, n = sx + 50, len(s_)
                for i, ch in enumerate(s_):
                    _glyph(c, ch, xx, sy + 110, f, MO, 1, P(t, s0 + (s1 - s0) * i / max(1, n - 1), .35), rise=4)
                    xx += f.measureText(ch)
                c.restore()
        if self.cta:
            ct, s_ = self.cta
            k = eob(P(t, ct - .05, .45), 1.5) if self.motion else eo(P(t, ct - .25, 1.0))
            if k > 0:
                f = F('song', 170); w = tw(s_, f)
                cw, chh = w + 200, 330
                cx0, cy0 = W * .36 - cw / 2, H * .44 - chh / 2
                c.save(); c.translate(W * .36, H * .44); sc = lerp(1.25 if self.motion else 1.03, 1, k); c.scale(sc, sc)
                if self.motion: c.rotate(-2 * (1 - k))
                c.translate(-W * .36, -H * .44)
                paper_piece(c, torn_rect(cx0, cy0, cw, chh, 'trbl', seed=97, rough=9), clamp(k * 2) * a, seed=6)
                text(c, s_, cx0 + 100, cy0 + chh / 2 + 62, f, MO, clamp(k * 2) * a)
                brush_stroke(c, cx0 + 104, cy0 + chh - 48, cx0 + 104 + w * .6, cy0 + chh - 46, 10, ZHU, a, eo(P(t, ct + .35, .5)), seed=12)
                c.restore()
        if self.seal:
            st, s_ = self.seal
            if self.cta:
                f = F('song', 170); w = tw(self.cta[1], f)
                seal(c, s_, W * .36 + (w + 200) / 2 - 30, H * .44 - 165 + 20, 84, t, st, a, seed=31)
            elif self.side == 'banner':
                seal(c, s_, bx + 78, (len(self.headline[1]) * 96 + 150) if self.headline else 120, 64, t, st, a, seed=31)
            else:
                seal(c, s_, W - 120, 70 + (len(self.headline[1]) * 78 if self.headline else 0) + 70, 56, t, st, a, seed=31)

    def events(self):
        ev = [(tt, 'pluck', .5) for tt, _ in self.tags]
        if self.headline: ev.append((self.headline[0], 'bell' if self.layout == 'full' else 'brush', .6))
        if self.cta: ev.append((self.cta[0], 'bell', .9))
        if self.avatar_in == 'full': ev.append((self.t0, 'breeze', .8))
        if self.avatar_big: ev.append((self.avatar_big[0], 'brush', .6))
        if self.strip: ev += [(self.strip[0] - .5, 'brush', .5), (self.strip[1], 'pluck', .6)]
        if self.seal: ev.append((self.seal[0], 'seal', .8))
        return ev
