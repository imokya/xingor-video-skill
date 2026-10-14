"""showcase · 作品宣传片 building blocks (size-agnostic; works for 16:9, 3:4 and 9:16).

Learned on the xingor promo (2026-10). Everything here is about presenting *existing footage* well:

    Clip            ffmpeg frame streamer: crop, rotation-aware probe, cover / fit, speed, holds the last frame
    clip_info       duration + display size of a file (use it to keep a clip inside its source: no blank tails)
    pick_start      first bright, non-empty start time from a list of candidates (avoids black frames)
    card3d          floating 3D card: rounded corners, shadow, ambient colour spill, *3D-mirrored* floor reflection,
                    rim light, optional light sweep (turn the sweep off on light / paper cards or text washes out)
    vcard           a vertical (9:16) clip as an animated 3D flip card - never letterbox portrait footage
    push_blur       zoom-through transition between two rendered scene images, with a light streak at the cut
    tilted_list     long lists (components, features) on a tilted, scrolling 3D plane that fades into the dark
    timeline_title  a wordmark built by an editing timeline: the playhead reaches a clip, its letter lands
    grain, vignette film finish
    fit_font        largest font size whose text fits a width (no text ever leaves its box)
    safe_overlay    draws the safe-area guides on a test still (titles / cards must stay between them)
"""
import math, os, re, subprocess
import numpy as np
import skia

from kit.motion import clamp, P, eo, eio, eob, eexp, lerp, spring

LIN = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)
FFMPEG = os.environ.get('XINGOR_FFMPEG', 'ffmpeg')


def CI(rgb, a=1.0): return skia.ColorSetARGB(int(clamp(a) * 255), *rgb)


def _paint(rgb, a=1.0, stroke=0, blur=0):
    p = skia.Paint(AntiAlias=True); p.setColor(CI(rgb, a))
    if stroke: p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


# ---------------------------------------------------------------- footage
def clip_info(path, ffmpeg=None):
    """(duration_s, display_w, display_h) - honours the rotation side-data phones write (a 1080x1920 'raw' that is
    really landscape)."""
    out = subprocess.run([ffmpeg or FFMPEG, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', out); w, h = int(m.group(1)), int(m.group(2))
    if re.search(r'rotation of -?90', out): w, h = h, w
    return dur, w, h


class Clip:
    """Streams RGBA frames of `path` scaled to (w, h). crop=(x, y, w, h) in display pixels removes window frames,
    player UI, cursors, hands. fit='cover' fills, fit='fit' keeps the whole frame (w/h become the fitted size).
    t0 = when the clip starts in the edit; speed < 1 slows it down (use it to stay inside a short source)."""
    def __init__(self, path, start=0.0, w=1920, h=1080, fit='cover', speed=1.0, t0=0.0, crop=None, fps=30, ffmpeg=None):
        self.path, self.start, self.w, self.h, self.fit, self.speed, self.t0, self.crop, self.fps = path, start, w, h, fit, speed, t0, crop, fps
        self.ff = ffmpeg or FFMPEG
        self.proc = None; self.idx = -1; self.img = None; self.arr = None; self.ok = os.path.exists(path)
        if fit == 'fit' and self.ok:
            vw, vh = (crop[2], crop[3]) if crop else clip_info(path, self.ff)[1:]
            s = min(w / vw, h / vh); self.w, self.h = int(vw * s) // 2 * 2, int(vh * s) // 2 * 2

    def _open(self, i):
        if self.proc: self.proc.kill()
        ss = self.start + i / self.fps * self.speed
        vf = f'setpts=(PTS-STARTPTS)/{self.speed},fps={self.fps},'
        if self.crop: vf += 'crop={2}:{3}:{0}:{1},'.format(*self.crop)
        vf += (f'scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}' if self.fit == 'cover'
               else f'scale={self.w}:{self.h}') + ',format=rgba'
        cmd = [self.ff, '-v', 'error', '-ss', f'{ss:.3f}', '-i', self.path, '-an', '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgba', '-']
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.idx = i - 1

    def frame(self, t):
        if not self.ok: return None
        i = max(0, int(round((t - self.t0) * self.fps)))
        if i == self.idx and self.img is not None: return self.img
        if self.proc is None or i < self.idx or i > self.idx + 45: self._open(i)
        n = self.w * self.h * 4
        while self.idx < i:
            buf = self.proc.stdout.read(n)
            if len(buf) < n: self.idx = i; return self.img          # past the end: hold the last frame
            self.idx += 1
            if self.idx == i:
                self.arr = np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 4).copy()
                self.img = skia.Image.fromarray(self.arr, colorType=skia.kRGBA_8888_ColorType)
        return self.img


def pick_start(path, candidates, need=3.0, min_mean=30.0, ffmpeg=None):
    """first candidate start time that is bright enough and leaves `need` seconds of footage after it."""
    dur = clip_info(path, ffmpeg)[0]
    for s in candidates:
        if s + need > dur: continue
        raw = subprocess.run([ffmpeg or FFMPEG, '-v', 'error', '-ss', f'{s}', '-i', path, '-frames:v', '1', '-vf', 'scale=96:-2',
                              '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
        if raw and np.frombuffer(raw, np.uint8).mean() >= min_mean: return s
    return max(0.0, min(candidates[0], dur - need))


# ---------------------------------------------------------------- 3D cards
def rot_pts3(w, h, rx=0.0, ry=0.0):
    out = []
    for (u, v) in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        x, y, z = u * w / 2, v * h / 2, 0.0
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
        out.append((x, y, z))
    return out


def proj3(p, cx, cy, z0=0.0, cam=1900):
    x, y, z = p; s = cam / (cam + z + z0); return (cx + x * s, cy + y * s)


def rot_quad3(cx, cy, w, h, rx=0.0, ry=0.0, z0=0.0, cam=1900):
    return [proj3(p, cx, cy, z0, cam) for p in rot_pts3(w, h, rx, ry)]


def refl_quad3(cx, cy, w, h, rx=0.0, ry=0.0, z0=0.0, gap=14.0, cam=1900):
    """mirror the card in 3D about a floor plane under its bottom edge, then project. Flipping the 2D quad instead
    gives reflections that tilt the wrong way as soon as the card turns."""
    pts = rot_pts3(w, h, rx, ry); yb = max(pts[2][1], pts[3][1]) + gap
    return [proj3((x, 2 * yb - y, z), cx, cy, z0, cam) for (x, y, z) in pts]


def _quad_matrix(img, q):
    m = skia.Matrix(); w, h = img.width(), img.height()
    ok = m.setPolyToPoly([skia.Point(0, 0), skia.Point(w, 0), skia.Point(w, h), skia.Point(0, h)], [skia.Point(*v) for v in q])
    return m if ok else None


def ambient(c, img, cx, cy, w, h, a=.3):
    """colour spill of the footage around a card: blurred, radial-masked (no hard rectangle)."""
    if img is None or a <= 0: return
    r = skia.Rect.MakeXYWH(cx - w * .9, cy - h * .85, w * 1.8, h * 1.7)
    c.saveLayer(r, None)
    p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a)); p.setImageFilter(skia.ImageFilters.Blur(60, 60, skia.TileMode.kDecal, None))
    c.drawImageRect(img, skia.Rect.MakeXYWH(cx - w * .7, cy - h * .65, w * 1.4, h * 1.3), LIN, p)
    g = skia.GradientShader.MakeRadial((cx, cy), max(w, h) * .85, [CI((0, 0, 0), 1), CI((0, 0, 0), .5), CI((0, 0, 0), 0)], [0, .5, 1])
    pp = skia.Paint(Shader=g); pp.setBlendMode(skia.BlendMode.kDstIn); c.drawRect(r, pp)
    c.restore()


def card3d(c, img, cx, cy, w, h, t, rx=0.0, ry=0.0, z0=0.0, a=1.0, seed=0, refl=True, edge=(158, 196, 255),
           amb=True, sweep=True, radius=22, canvas_w=1920):
    """floating 3D card. radius is in output pixels; the reflection is clipped to the same rounded corners."""
    if a <= 0 or img is None: return None
    q = rot_quad3(cx, cy, w, h, rx, ry, z0)
    if amb: ambient(c, img, cx, cy, w, h, .3 * a)
    w0, h0 = img.width(), img.height(); rr = radius * w0 / max(1, w)
    m = _quad_matrix(img, q)
    rpath = skia.Path(); rpath.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeWH(w0, h0), rr, rr))
    pth = skia.Path(rpath); pth.transform(m) if m else None
    shp = skia.Path(pth); shp.offset(0, 40); c.drawPath(shp, _paint((0, 0, 0), .5 * a, blur=46))
    if refl:
        rq = refl_quad3(cx, cy, w, h, rx, ry, z0); mr = _quad_matrix(img, rq)
        if mr:
            c.saveLayer(None, None)
            c.save(); c.concat(mr); p = skia.Paint(AntiAlias=True); p.setAlphaf(.22 * a); c.clipPath(rpath, doAntiAlias=True)
            c.drawImage(img, 0, 0, LIN, p); c.restore()
            ys = [v[1] for v in rq]; y0, y1 = min(ys), max(ys)
            g = skia.GradientShader.MakeLinear([(0, y0), (0, y0 + (y1 - y0) * .5)], [CI((0, 0, 0), 1), CI((0, 0, 0), 0)])
            pp = skia.Paint(Shader=g); pp.setBlendMode(skia.BlendMode.kDstIn); c.drawRect(skia.Rect.MakeLTRB(0, y0, canvas_w * 4, y1 + 2), pp)
            c.restore()
    if m:
        c.save(); c.concat(m); p = skia.Paint(AntiAlias=True); p.setAlphaf(clamp(a)); c.clipPath(rpath, doAntiAlias=True)
        c.drawImage(img, 0, 0, LIN, p); c.restore()
    g = skia.GradientShader.MakeLinear([q[0], q[2]], [CI((255, 255, 255), .45 * a), CI((255, 255, 255), .08 * a), CI(edge, .25 * a)])
    rp = skia.Paint(AntiAlias=True, Shader=g); rp.setStyle(skia.Paint.kStroke_Style); rp.setStrokeWidth(1.2); c.drawPath(pth, rp)
    u = ((t * .35 + seed * .37) % 1.8) / 1.8
    if sweep and u < .6:
        xs = [v[0] for v in q]; sx = lerp(min(xs) - 300, max(xs) + 300, u / .6)
        sh = skia.GradientShader.MakeLinear([(sx - 120, 0), (sx + 120, 0)], [CI((255, 255, 255), 0), CI((255, 255, 255), .16 * a), CI((255, 255, 255), 0)])
        c.save(); c.clipPath(pth, doAntiAlias=True); c.drawPaint(skia.Paint(Shader=sh)); c.restore()
    return q


def vcard(c, clip, cx, cy, h, t, t0, side=1.0, ry_rest=.22, d=1.0, a=1.0, seed=0, refl=True, out_t=None, **kw):
    """vertical clip as a 3D card that flips in from `side`, floats, and optionally flies out at out_t."""
    if t < t0: return None
    img = clip.frame(t); w = h * clip.w / clip.h
    k = spring(P(t, t0, d)); e = eexp(P(t, t0, d * .8))
    ko = eio(P(t, out_t, .45)) if out_t is not None else 0
    ry = lerp(1.25 * side, ry_rest, k) + .05 * math.sin(t * .7 + seed) - ko * 1.1 * side
    rx = .05 * math.sin(t * .55 + seed * 2) + .25 * (1 - e)
    yy = cy + (1 - e) * 140 + 8 * math.sin(t * .9 + seed) - ko * 60
    return card3d(c, img, cx + ko * 300 * side, yy, w, h, t, rx, ry, (1 - e) * 500 + ko * 700, a * clamp(e * 1.4) * (1 - ko), seed, refl, **kw)


# ---------------------------------------------------------------- transitions / finish
def push_blur(c, A, B, u, W, H, accent=(158, 196, 255)):
    """zoom-through between scene images A (outgoing) and B (incoming); u in 0..1 across the cut."""
    ea = eio(u)
    for img, s, bl, al in ((A, 1 + .16 * ea, 34 * ea ** 1.5, 1 - clamp((u - .3) / .4)), (B, 1.14 - .14 * ea, 34 * (1 - ea) ** 1.5, clamp((u - .3) / .4))):
        if al <= 0: continue
        p = skia.Paint(AntiAlias=True); p.setAlphaf(al)
        if bl > .5: p.setImageFilter(skia.ImageFilters.Blur(bl, bl * .35, skia.TileMode.kClamp, None))
        c.save(); c.translate(W / 2, H / 2); c.scale(s, s); c.translate(-W / 2, -H / 2); c.drawImageRect(img, skia.Rect.MakeWH(W, H), LIN, p); c.restore()
    k = math.sin(math.pi * u)
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 160, W, 320), _paint(accent, .10 * k, blur=90))
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 2, W, 4), _paint((255, 255, 255), .5 * k ** 3, blur=6))


_grain = []


def grain(c, t, W, H, a=1.0, fps=30):
    if not _grain:
        r = np.random.RandomState(4)
        for _ in range(4):
            g = np.zeros((540, 960, 4), np.uint8); g[..., :3] = 255; g[..., 3] = (r.rand(540, 960) ** 6 * 26).astype(np.uint8)
            _grain.append(skia.Image.fromarray(g, colorType=skia.kRGBA_8888_ColorType))
    p = skia.Paint(); p.setAlphaf(.5 * a)
    c.drawImageRect(_grain[int(t * fps) % 4], skia.Rect.MakeWH(W, H), skia.SamplingOptions(), p)


def vignette(c, W, H, s=.45):
    sh = skia.GradientShader.MakeRadial((W / 2, H / 2), max(W, H) * .75, [CI((0, 0, 0), 0), CI((0, 0, 0), 0), CI((0, 0, 0), s)], [0, .5, 1])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))


def font(family, weight, size):
    f = skia.Font(skia.Typeface(family, skia.FontStyle(weight, 5, skia.FontStyle.kUpright_Slant)), size)
    f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); return f


def fit_font(s, family, weight, size, maxw, minsize=12):
    while size > minsize and font(family, weight, size).measureText(s) > maxw: size -= 1
    return font(family, weight, size)


# ---------------------------------------------------------------- long lists on a tilted plane
def tilted_list(c, items, t, W, top_y, bot_y, far_w, near_w, cols=4, cell_w=340, row_h=74, speed=95, accent=(158, 196, 255),
                ink=(9, 9, 11), a=1.0, label_font=('PingFang SC', 400)):
    """many names (components, features) as a perspective plane scrolling away from the viewer. Viewers do not need
    to read them all - they need to feel 'a lot, and alive'. A few cells light up in the accent colour."""
    order = items + items[len(items) // 3:] + items[:len(items) // 3]
    rows = (len(order) + cols - 1) // cols; TW, TH = cols * cell_w, rows * row_h
    surf = skia.Surface(TW, TH); cc = surf.getCanvas(); cc.clear(skia.ColorTRANSPARENT)
    for i, s in enumerate(order):
        col, row = i % cols, i // cols; x, y, w, h = col * cell_w + 10, row * row_h + 8, cell_w - 20, row_h - 16
        hot = (i * 13 + int(t * 4)) % 9 == 0
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 12, 12)
        cc.drawRRect(rr, _paint(accent if hot else (255, 255, 255), .9 if hot else .06))
        if not hot: cc.drawRRect(rr, _paint((255, 255, 255), .14, stroke=1))
        f = fit_font(s, label_font[0], label_font[1], 28, w - 30); tw = f.measureText(s)
        cc.drawString(s, x + w / 2 - tw / 2, y + h / 2 + 10, f, _paint(ink if hot else (255, 255, 255), 1 if hot else .8))
    view_h = min(TH - 1, (bot_y - top_y) * 1.5)
    sy = (t * speed + 40) % max(1, TH - view_h)
    cx = W / 2; dst = [(cx - far_w / 2, top_y), (cx + far_w / 2, top_y), (cx + near_w / 2, bot_y), (cx - near_w / 2, bot_y)]
    m = skia.Matrix()
    if not m.setPolyToPoly([skia.Point(0, 0), skia.Point(TW, 0), skia.Point(TW, view_h), skia.Point(0, view_h)], [skia.Point(*v) for v in dst]): return
    clip = skia.Path(); clip.moveTo(*dst[0]); [clip.lineTo(*v) for v in dst[1:]]; clip.close()
    c.saveLayer(None, None)
    c.save(); c.clipPath(clip, doAntiAlias=True); c.concat(m); p = skia.Paint(AntiAlias=True); p.setAlphaf(a)
    c.drawImageRect(surf.makeImageSnapshot(), skia.Rect.MakeXYWH(0, sy, TW, view_h), skia.Rect.MakeWH(TW, view_h), LIN, p); c.restore()
    hgt = bot_y - top_y          # alpha fade (DstIn) - a dark overlay would show a hard band on a glowing background
    g = skia.GradientShader.MakeLinear([(0, top_y), (0, bot_y)], [CI((0, 0, 0), 0), CI((0, 0, 0), 1), CI((0, 0, 0), 1), CI((0, 0, 0), .15)],
                                       [0, .38, 1 - 130 / hgt, 1])
    gp = skia.Paint(Shader=g); gp.setBlendMode(skia.BlendMode.kDstIn); c.drawRect(skia.Rect.MakeLTRB(0, top_y - 2, W, bot_y + 2), gp)
    c.restore()


# ---------------------------------------------------------------- the timeline title
def timeline_title(c, t, t0, word, clips, names, W, cy, panel, accent=(158, 196, 255), size=300,
                   family=('Avenir Next', 400), spacing=24):
    """a wordmark assembled by an editing timeline. panel=(x, y, w, h). Each clip block sits on the video track; when
    the playhead reaches it, the matching letter lands (small scale + blur), shows that clip for ~0.15 s, then melts
    into a white→ice→mist gradient. The playhead keeps looping, so the final frame stays alive. Elegant > heavy:
    thin type with a cold gradient reads better than footage-filled letters (those blend into the background)."""
    lt = t - t0; TF = font(family[0], family[1], size)
    px, py0, pw, ph = panel; kp = eexp(P(lt, 0, .8)); py = py0 + (1 - kp) * 120
    x0, x1 = px + 110, px + pw - 24; n = len(word); gap = 10
    bw = (x1 - x0 - gap * (n - 1)) / n; blocks = [(x0 + i * (bw + gap), bw) for i in range(n)]
    def head(u): return lerp(x0, x1, eio(P(u, .45, 2.0))) if u < 2.6 else lerp(x0, x1, ((u - 2.6) / 4.0) % 1)
    land = []
    for (bx, _) in blocks:
        tt = .45
        while head(tt) < bx + 18 and tt < 2.6: tt += 1 / 120
        land.append(tt)
    # panel
    r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(px, py, pw, ph), 22, 22)
    c.drawRRect(r, _paint((22, 24, 30), .88 * kp)); c.drawRRect(r, _paint((255, 255, 255), .14 * kp, stroke=1))
    vy, vh = py + 68, 74
    for i, (bx, bwid) in enumerate(blocks):
        k = spring(P(lt, .2 + i * .07, .5))
        if k <= 0 or clips[i] is None: continue
        hh = vh * k; yy = vy + (vh - hh) / 2; img = clips[i].frame(t)
        if img is not None:
            c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(bx, yy, bwid, hh), 8, 8), True)
            p = skia.Paint(AntiAlias=True); p.setAlphaf(kp); c.drawImageRect(img, skia.Rect.MakeXYWH(bx, yy, bwid, hh), LIN, p); c.restore()
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(bx, yy, bwid, hh), 8, 8), _paint(accent if lt >= land[i] else (255, 255, 255), (.9 if lt >= land[i] else .25) * kp, stroke=1.2))
    ay = vy + vh + 40; nb = 140; bwd = (x1 - x0) / nb; phx = head(lt)
    for i in range(nb):
        ph_ = i * .37; v = (.25 + .75 * abs(math.sin(lt * 5.3 + ph_) * math.sin(lt * 2.1 + ph_ * .7))) * (.5 + .5 * math.sin(i * .19) ** 2)
        bh = max(2, 34 * v); xx = x0 + i * bwd
        c.drawRect(skia.Rect.MakeXYWH(xx, ay - bh / 2, bwd * .55, bh), _paint(accent if xx < phx else (255, 255, 255), (.75 if xx < phx else .25) * kp))
    if lt > .45:
        c.drawLine(phx, vy - 20, phx, py + ph - 12, _paint(accent, kp, stroke=2))
    # wordmark
    tws = [TF.measureText(ch) for ch in word]; x = W / 2 - (sum(tws) + spacing * (n - 1)) / 2
    for i, ch in enumerate(word):
        cw = tws[i]; k = P(lt, land[i], .35); e = eexp(k)
        if k > 0:
            s = lerp(1.12, 1, e); cxl = x + cw / 2
            c.save(); c.translate(cxl, cy - size / 3); c.scale(s, s); c.translate(-cxl, -(cy - size / 3))
            c.saveLayer(None, skia.Paint(Alphaf=clamp(e * 1.6)))
            g = skia.GradientShader.MakeLinear([(0, cy - size * .75), (0, cy + 10)], [CI((255, 255, 255)), CI((222, 232, 248)), CI((160, 184, 222))], [0, .55, 1])
            p = skia.Paint(AntiAlias=True, Shader=g)
            if e < .97: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, (1 - e) * 8 + .01))
            c.drawString(ch, x, cy, TF, p)
            va = 1 - eio(clamp((lt - land[i] - .15) / .4))
            if va > 0 and clips[i] is not None and clips[i].img is not None:
                pp = skia.Paint(AntiAlias=True); pp.setBlendMode(skia.BlendMode.kSrcATop); pp.setAlphaf(va)
                c.drawImageRect(clips[i].img, skia.Rect.MakeXYWH(x - 30, cy - size * .85, cw + 60, size * 1.1), LIN, pp)
            u = ((lt - 2.8) / 2.2) % 1 if lt > 2.8 else -1
            if 0 <= u < 1:
                sx = lerp(W / 2 - 600, W / 2 + 600, u)
                sh = skia.GradientShader.MakeLinear([(sx - 90, 0), (sx + 90, 0)], [CI(accent, 0), CI((120, 170, 255), .6), CI(accent, 0)])
                sp = skia.Paint(Shader=sh); sp.setBlendMode(skia.BlendMode.kSrcATop); c.drawRect(skia.Rect.MakeXYWH(x - 10, cy - size, cw + 20, size * 1.3), sp)
            c.restore(); c.restore()
            fl = 1 - clamp((lt - land[i]) / .25)
            if fl > 0:
                bx, bwid = blocks[i]; c.drawLine(bx + bwid / 2, vy - 2, x + cw / 2, cy + size * .2, _paint(accent, .6 * fl, stroke=1.5))
        x += cw + spacing
    return land


# ---------------------------------------------------------------- QA
def safe_overlay(img_path, top=None, bottom=None, out=None):
    """draw the safe-area lines on a test still (defaults: 9 % from the top, subtitles band from 90 % down)."""
    from PIL import Image, ImageDraw
    im = Image.open(img_path).convert('RGB'); w, h = im.size; d = ImageDraw.Draw(im)
    top = top or int(h * .09); bottom = bottom or int(h * .9)
    d.line([(0, top), (w, top)], fill=(255, 0, 0), width=3); d.line([(0, bottom), (w, bottom)], fill=(255, 0, 0), width=3)
    im.save(out or img_path); return out or img_path
