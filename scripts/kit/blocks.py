"""Theme-driven components: drawing primitives and scene templates that take every colour, font and pace from the
active theme (kit.theme.ACTIVE, set by render.py from THEME). They work under any theme — presets or designed ones.

Primitives (draw inside a scene's behind()/front())
    kinetic_word   characters slide in with a motion trail and squash back; can fling out      (from 撞色测评)
    end_dot        a coloured full stop that pops in after a title                              (from 撞色测评)
    typewriter     characters pop in one by one with a blinking cursor                          (from 文物纪录片)
    metal_text     gradient-filled metallic type with a sweeping highlight                     (from 文物纪录片)
    counter        a number counting up to its value                                            (from 撞色测评)
    glass          frosted panel: the picture behind it, blurred, tinted, with an accent edge  (from 文物纪录片)
    rings          rotating tick rings                                                          (from 文物纪录片)
    hud            corner brackets, a scan line, a tag and a running timecode                   (from 文物纪录片)
    pulse_dot / leader   pulsing marker and a polyline that draws itself to a label             (from 文物纪录片)
    pointer / strike     a line that draws to a point / a strike-through                        (from 撞色测评)
    input_box      chat input box typing a prompt, send button pressed on time                  (from 撞色测评)
    table          comparison table: columns rise in, numbers count up, the winner highlighted (from 撞色测评)
    iris           a growing circle with a chromatic fringe (the 'iris' page turn)             (from 撞色测评)
Templates (Scene subclasses for scenes.py)
    Page           base: themed background ('paper' / 'dark' / 'plain'), presenter optional
    TitleCard      kicker + kinetic title with end dot + sub line (+ optional HUD)
    BigStat        up to three counters with labels
    CompareTable   a comparison table page
    PromptPage     a prompt typed into an input box, then reply lines appearing
    TypeBehind     typewriter text BEHIND the presenter over the real video
    MetalTitle     metallic title with a shine sweep over rotating rings
    Callouts       a screenshot / image card with pointer labels
"""
import math
import numpy as np
import skia
from fx import W, H, F, text, tw, paint, rrect, circle, line, CI, dark_bg
from kit.motion import clamp, P, eo, eio, eob, eexp, lerp, spring, window
import kit.theme as KT
from components import Scene, PERSON, full_xf, dark_xf, mix_xf

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def TH():
    return KT.ACTIVE


# ================================================================ primitives
def kinetic_word(c, s, x, y, f, t, t0, rgb, stagger=.05, dist=420, from_left=False, t_out=None, a=1.0):
    """characters slide in (exponential ease) with a short motion trail and a horizontal squash that springs back;
    after t_out they fling off to the left. Returns the end x (for an end_dot)."""
    cx = x
    for i, ch in enumerate(s):
        adv = tw(ch, f)
        p = P(t, t0 + i * stagger, .42)
        if p <= 0 or ch == ' ':
            cx += adv; continue
        e = eexp(p); sgn = -1 if from_left else 1
        off = (1 - e) * dist * sgn
        v = (eexp(clamp(p + .08)) - e) * dist * sgn
        al = a
        if t_out is not None and t >= t_out:
            q = P(t, t_out + i * .025, .32)
            if q >= 1: cx += adv; continue
            off = -(q ** 3) * 1400; v = -3 * q * q * 120; al = a * (1 - q)
        sq = 1 + .35 * (1 - e)
        for j in range(4, -1, -1):   # trail
            if j and abs(v) < 4: continue
            gx = cx + off + v * j * .35
            c.save(); c.translate(gx + adv / 2, y); c.scale(sq, 1); c.translate(-(gx + adv / 2), -y)
            text(c, ch, gx, y, f, rgb, al * (1 if j == 0 else .18 / j))
            c.restore()
        cx += adv
    return cx


def end_dot(c, x, y, t, t0, rgb, r=14):
    p = eob(P(t, t0, .3))
    if p > 0: circle(c, x, y, r * p, rgb, 1)


def typewriter(c, s, x, y, f, t, t0, rgb, step=.13, cursor=None, align='l', cursor_until=None, a=1.0):
    """characters pop in (1.18x -> 1) one per `step` s; a blinking cursor follows. cursor=None uses the theme accent."""
    ws = [tw(ch, f) for ch in s]; total = sum(ws)
    if align == 'c': x -= total / 2
    elif align == 'r': x -= total
    xx, n = x, 0
    for i, ch in enumerate(s):
        k = P(t, t0 + i * step, .12)
        if k > 0:
            n = i + 1
            sc = 1.18 - .18 * k; cxm = xx + ws[i] / 2
            c.save(); c.translate(cxm, y - f.getSize() * .35); c.scale(sc, sc); c.translate(-cxm, -(y - f.getSize() * .35))
            text(c, ch, xx, y, f, rgb, a * k)
            c.restore()
        xx += ws[i]
    end = t0 + len(s) * step
    if t >= t0 - .3 and t < (cursor_until if cursor_until is not None else end + .9) and (int(t * 2.6) % 2 == 0 or t < end):
        lx = x + sum(ws[:n]) + f.getSize() * .06; sz = f.getSize()
        rrect(c, lx, y - sz * .82, sz * .07, sz * .92, 2, cursor or TH().accent, a)


def metal_text(c, s, x, y, f, a=1.0, shine=None, palette=None, align='l', glow=True):
    """metallic type: a vertical gradient (light top, deep middle, bright bottom) from the theme accent, a soft glow
    behind, and a diagonal highlight sweeping across while 0 < shine < 1."""
    th = TH(); acc = th.accent
    top, mid, bot = palette or (KT.mix(acc, (255, 255, 255), .78), KT.mix(acc, (0, 0, 0), .25), KT.mix(acc, (255, 255, 255), .45))
    w = tw(s, f); sz = f.getSize()
    if align == 'c': x -= w / 2
    elif align == 'r': x -= w
    if a <= 0: return w
    if glow: text(c, s, x, y, f, acc, a * (.55 if KT.luminance(th.bg) < .3 else .18), glow=sz * (.12 if KT.luminance(th.bg) < .3 else .06))
    sh = skia.GradientShader.MakeLinear([(0, y - sz * .85), (0, y + sz * .12)], [CI(top, a), CI(mid, a), CI(bot, a)], [0, .55, 1])
    c.drawString(s, x, y, f, skia.Paint(AntiAlias=True, Shader=sh))
    if shine is not None and 0 < shine < 1:
        bx = x - sz + (w + 2 * sz) * shine
        band = skia.GradientShader.MakeLinear([(bx - sz * .5, y - sz), (bx + sz * .5, y)],
                                              [CI((255, 255, 255), 0), CI((255, 255, 255), .75 * a), CI((255, 255, 255), 0)], [0, .5, 1])
        c.drawString(s, x, y, f, skia.Paint(AntiAlias=True, Shader=band, BlendMode=skia.BlendMode.kPlus))
    return w


def counter(c, value, x, y, f, t, t0, rgb, dec=0, dur=.8, prefix='', suffix='', align='l', a=1.0):
    p = eexp(P(t, t0, dur))
    if p <= 0: return 0
    return text(c, f'{prefix}{value * p:.{dec}f}{suffix}', x, y, f, rgb, a * clamp(p * 3), align=align)


def glass(c, x, y, w, h, r=24, a=1.0, tint=None, border=None, blur=14):
    """frosted panel: the pixels already drawn behind it, blurred and tinted, with an accent edge and a top highlight."""
    if a <= 0: return
    th = TH(); tint = tint or th.surface; border = border or th.accent
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    sf = c.getSurface()
    ix, iy = max(0, int(x)), max(0, int(y))
    iw, ih = min(W, int(x + w)) - ix, min(H, int(y + h)) - iy
    if sf is not None and iw > 4 and ih > 4:
        img = sf.makeImageSnapshot(skia.IRect.MakeXYWH(ix, iy, iw, ih))
        c.save(); c.clipRRect(rr, skia.ClipOp.kIntersect, True)
        c.drawImage(img, ix, iy, SAMP, skia.Paint(ImageFilter=skia.ImageFilters.Blur(blur, blur), Alphaf=a))
        c.restore()
    c.drawRRect(rr, paint(tint, .42 * a))
    c.drawRRect(rr, paint(border, .7 * a, stroke=2))
    line(c, x + r, y + 2, x + w - r, y + 2, (255, 255, 255), .25 * a, 2)


def rings(c, cx, cy, t, rgb=None, a=1.0, radii=(300, 380, 470, 590), spin=6.0):
    if a <= .01: return
    rgb = rgb or TH().accent
    for k, r in enumerate(radii):
        al = (.24 - k * .04) * a
        circle(c, cx, cy, r, rgb, al, stroke=2)
        n = 72 if k % 2 == 0 else 36
        rot = math.radians(t * spin * (1 if k % 2 else -1) * (1 + k * .3))
        for i in range(n):
            ang = rot + i * 2 * math.pi / n; l = 14 if i % 6 == 0 else 6
            line(c, cx + math.cos(ang) * r, cy + math.sin(ang) * r, cx + math.cos(ang) * (r + l), cy + math.sin(ang) * (r + l), rgb, al * 1.6, 2)


def hud(c, t, a=1.0, tag='', rgb=None, box=None, clock=True):
    """corner brackets + slow scan line + tag (top-left) + running timecode (top-right)."""
    if a <= .01: return
    th = TH(); rgb = rgb or th.accent
    x0, y0, x1, y1 = box or (50, 70, W - 50, H - 190)
    for x, y, sx, sy in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        line(c, x, y, x + 60 * sx, y, rgb, .7 * a, 3); line(c, x, y, x, y + 60 * sy, rgb, .7 * a, 3)
    yy = y0 + ((t * 160) % (y1 - y0))
    line(c, x0, yy, x1, yy, rgb, .1 * a, 2)
    f = F(th.font('label'), 22)
    if tag: text(c, tag, x0 + 20, y0 - 18, f, rgb, .8 * a, spacing=4)
    if clock: text(c, f'T+{t:05.2f}', x1 - 20, y0 - 18, f, rgb, .8 * a, align='r')


def pulse_dot(c, x, y, t, rgb=None, a=1.0):
    rgb = rgb or TH().accent
    for k in range(2):
        ph = (t * 1.2 + k * .5) % 1
        circle(c, x, y, 10 + ph * 46, rgb, .86 * (1 - ph) * a, stroke=3)
    circle(c, x, y, 9, rgb, a)


def leader(c, pts, p, rgb=None, w=3, a=1.0):
    """polyline drawn to progress p (0..1)."""
    if p <= 0: return
    rgb = rgb or TH().accent
    pth = skia.Path(); pth.moveTo(*pts[0])
    for q in pts[1:]: pth.lineTo(*q)
    from fx import partial_path
    c.drawPath(partial_path(pth, 0, clamp(p)), paint(rgb, a, stroke=w))


def pointer(c, t, t0, x0, y0, x1, y1, rgb=None, w=3):
    rgb = rgb or TH().accent; p = eo(P(t, t0, .35))
    if p <= 0: return
    line(c, x0, y0, x0 + (x1 - x0) * p, y0 + (y1 - y0) * p, rgb, 1, w)
    if p >= 1: circle(c, x1, y1, 9, rgb, 1)


def strike(c, t, t0, x0, x1, y, rgb=None, w=8):
    rgb = rgb or TH().accent; p = eo(P(t, t0, .3))
    if p > 0: line(c, x0, y, x0 + (x1 - x0) * p, y, rgb, 1, w)


def wrap(s, f, width):
    lines, cur = [], ''
    for ch in s:
        if tw(cur + ch, f) > width and cur: lines.append(cur); cur = ch
        else: cur += ch
    return lines + [cur] if cur else lines or ['']


def input_box(c, t, x, y, w, prompt, t_type, t_send, a=1.0, size=42):
    """chat input box: the prompt types out over t_type=(start, end), the send button presses at t_send.
    Colours come from the theme: the box takes the ink colour (so it contrasts with the page), the send button the accent."""
    if a <= 0: return 0
    th = TH(); box = th.ink; fg = th.bg; f = F(th.font('body'), size); lh = size * 1.45
    n = int(len(prompt) * clamp((t - t_type[0]) / max(.01, t_type[1] - t_type[0])))
    shown = prompt[:n] if t < t_send else prompt
    full = wrap(prompt, f, w - 110); lines = wrap(shown, f, w - 110) if shown else ['']
    h = 40 + len(full) * lh + 96
    rrect(c, x, y + 12, w, h, 44, (0, 0, 0), .18 * a, blur=18)
    rrect(c, x, y, w, h, 44, box, a)
    cy = y + h - 52
    line(c, x + 38, cy, x + 66, cy, fg, .9 * a, 3); line(c, x + 52, cy - 14, x + 52, cy + 14, fg, .9 * a, 3)
    press = P(t, t_send, .12) * (1 - P(t, t_send + .12, .15))
    r = 32 * (1 - .15 * press); sx = x + w - 66
    circle(c, sx, cy, r, th.accent, a)
    on = max([th.bg, th.surface, th.ink, (255, 255, 255)], key=lambda q: KT.contrast(q, th.accent))
    line(c, sx, cy + 13, sx, cy - 13, on, a, 4); line(c, sx - 11, cy - 2, sx, cy - 13, on, a, 4); line(c, sx + 11, cy - 2, sx, cy - 13, on, a, 4)
    ty = y + 34 + size
    for i, ln in enumerate(lines): text(c, ln, x + 46, ty + i * lh, f, fg, a)
    if (t < t_send and int(t * 2.5) % 2 == 0) or t_type[0] <= t < t_type[1]:
        lx = x + 46 + tw(lines[-1], f); ly = ty + (len(lines) - 1) * lh
        rrect(c, lx + 4, ly - size * .85, 4, size * 1.05, 1, fg, a)
    return h


def table(c, t, cols, rows, t_cols, x0=120, x1=None, y0=300, colx=None, a=1.0):
    """cols=[(name, sub)]; rows=[(label, [values], t, best_col|None)]. Numbers count up; the best cell gets an accent block."""
    import re
    th = TH(); x1 = x1 or W - 120
    colx = colx or [x0 + (x1 - x0) * (.32 + .68 * i / max(1, len(cols))) for i in range(len(cols))]
    fh, fs, fr, fn = F(th.font('head'), 50), F(th.font('label'), 26), F(th.font('body'), 42), F(th.font('num'), 58)
    for i, (nm, sub) in enumerate(cols):
        p = eo(P(t, t_cols + i * .1, .35))
        if p <= 0: continue
        text(c, nm, colx[i], y0 + 20 * (1 - p), fh, th.ink, a * p)
        if sub: text(c, sub, colx[i], y0 + 46 + 20 * (1 - p), fs, th.muted, a * p)
    lp = eo(P(t, t_cols, .6))
    if lp > 0: line(c, x0, y0 + 80, x0 + (x1 - x0) * lp, y0 + 80, th.ink, a, 3)
    for r, (name, vals, t0, best) in enumerate(rows):
        y = y0 + 170 + r * 112
        p = eo(P(t, t0 - .05, .3))
        if p <= 0: continue
        text(c, name, x0, y, fr, th.ink, a * p)
        for i, v in enumerate(vals):
            q = P(t, t0 + .03 + i * .08, .5)
            if q <= 0: continue
            m = re.match(r'(\$?)([\d.]+)(\D*)', str(v))
            if m and q < 1:
                dec = len(m.group(2).split('.')[1]) if '.' in m.group(2) else 0
                s = f'{m.group(1)}{float(m.group(2)) * eexp(q):.{dec}f}{m.group(3)}'
            else: s = str(v)
            f = fn if m else fr
            if best == i and q >= 1:
                rrect(c, colx[i] - 14, y - f.getSize() * .9, tw(s, f) + 28, f.getSize() * 1.2, 8, th.accent, a)
                on = max([th.bg, th.ink, th.surface], key=lambda q_: KT.contrast(q_, th.accent))
                text(c, s, colx[i], y, f, on, a)
            else:
                text(c, s, colx[i], y, f, th.ink, a * (eo(q) if q < 1 else 1))
        lp2 = eo(P(t, t0, .5)); line(c, x0, y + 40, x0 + (x1 - x0) * lp2, y + 40, th.line, .6 * a, 1)


def iris(c, cx, cy, r, color, fringe=None):
    """a filled circle with a chromatic fringe (violet / cyan by default)."""
    if r <= 0: return
    for k, col in enumerate(fringe or [(150, 90, 255), (60, 200, 255)]):
        circle(c, cx, cy, r + (2 - k) * 9, col, 1)
    circle(c, cx, cy, r, color, 1)


# ================================================================ templates
class Page(Scene):
    """a themed page. background follows theme.background ('paper' texture / 'dark' gradient / 'plain' colour);
    show_person=True keeps the presenter cut out at the right (scale / cx like the dark scenes)."""
    mode = 'scroll'
    show_person = False
    scale = .74
    cx = 1540
    rim = 0.0
    enter_from = None

    def xf(self, t):
        if not self.show_person: return (1e-4, -W, -H)
        k = eio(P(t, self.t0 + .05, .9))
        return mix_xf(self.enter_from or full_xf(1.05), dark_xf(self.scale, self.cx), k)

    def draw_bg(self, c, t, ctx):
        th = TH()
        if th.background == 'paper':
            import ink
            ink.ink_bg(c, t)
        elif th.background == 'dark':
            dark_bg(c, t)
        else:
            c.drawRect(skia.Rect.MakeWH(W, H), paint(th.bg))

    def right(self):
        """usable right edge for content (keeps clear of the presenter)."""
        return 1150 if self.show_person else W - 110


class TitleCard(Page):
    """kicker (t, '第一章') + kinetic title (t, '标题') with an accent end dot + sub line (t, '…'); hud=True adds HUD."""
    kicker = None
    title = None
    sub = None
    hud = False
    tag = ''
    size = None

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t); x = 110
        if self.hud: hud(c, t, a, self.tag)
        if self.kicker:
            kt, s = self.kicker
            circle(c, x + 6, 312, 6, th.accent, a * eo(P(t, kt, .4)))
            text(c, s, x + 26, 320, F(th.font('label'), 30), th.muted, a * eo(P(t, kt, .5)), spacing=6)
        if self.title:
            tt, s = self.title
            size = self.size or min(170, (self.right() - x) / max(1, len(s)) * .95)
            end = kinetic_word(c, s, x, 360 + size * .85, F(th.font('display'), size), t, tt, th.ink, a=a)
            end_dot(c, end + size * .14, 360 + size * .78, t, tt + .45, th.accent, max(12, size // 9))
        if self.sub:
            st, s = self.sub
            text(c, s, x, 360 + (self.size or 150) * 1.35, F(th.font('body'), 40), th.muted, a * eo(P(t, st, th.dur)))

    def events(self):
        ev = []
        if self.title: ev.append((self.title[0], 'swish', .7))
        if self.kicker: ev.append((self.kicker[0], 'pop', .5))
        return ev


class BigStat(Page):
    """title (t, '…') + stats=[(t, value, '前缀', '后缀', '说明', dec)] counting up, side by side."""
    title = None
    stats = []

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t); x0 = 110; x1 = self.right()
        if self.title:
            tt, s = self.title
            kinetic_word(c, s, x0, 260, F(th.font('head'), 72), t, tt, th.ink, a=a)
        n = max(1, len(self.stats)); cw = (x1 - x0) / n
        for i, st in enumerate(self.stats):
            t0, val, pre, suf, label = st[:5]; dec = st[5] if len(st) > 5 else 0
            x = x0 + i * cw
            counter(c, val, x, 560, F(th.font('num'), 190), t, t0, th.accent, dec=dec, prefix=pre, suffix=suf, a=a)
            text(c, label, x + 6, 640, F(th.font('body'), 38), th.ink, a * eo(P(t, t0 + .2, .5)))
            line(c, x + 6, 340, x + 6 + 60 * eo(P(t, t0, .5)), 340, th.accent, a, 4)

    def events(self):
        return [(st[0], 'riser', .5) for st in self.stats]


class CompareTable(Page):
    """title (t, '…') + table(cols, rows, t_cols) — see kit.blocks.table."""
    title = None
    cols = []
    rows = []
    t_cols = None

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t)
        if self.title:
            tt, s = self.title
            kinetic_word(c, s, 110, 210, F(th.font('head'), 72), t, tt, th.ink, a=a)
        table(c, t, self.cols, self.rows, self.t_cols if self.t_cols is not None else self.t0 + .4, x0=110, x1=self.right(), y0=330, a=a)

    def events(self):
        return [(r[2], 'pop', .5) for r in self.rows]


class PromptPage(Page):
    """label (t, '只需一句话') + prompt typed into an input box (prompt=(t0, t1, '…'), send=t) + replies=[(t, '…')]."""
    label = None
    prompt = None
    send = None
    replies = []

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t); x0 = 110; w = self.right() - x0
        if self.label:
            lt, s = self.label
            text(c, s, x0, 230, F(th.font('head'), 64), th.ink, a * eo(P(t, lt, th.dur)))
        if self.prompt:
            p0, p1, s = self.prompt
            send = self.send if self.send is not None else p1 + .2
            k = eo(P(t, p0 - .5, .5))
            h = input_box(c, t, x0, 300 + 30 * (1 - k), w, s, (p0, p1), send, a=a * k)
            y = 300 + h + 60
            for rt, s2 in self.replies:
                q = eo(P(t, rt, th.dur))
                if q <= 0: continue
                f = F(th.font('body'), 40); lines = wrap(s2, f, w - 120); bh = len(lines) * 58 + 54
                rrect(c, x0 + 60, y + 20 * (1 - q), w - 60, bh, 24, th.surface, a * q)
                for i, ln in enumerate(lines): text(c, ln, x0 + 100, y + 68 + i * 58 + 20 * (1 - q), f, th.ink, a * q)
                y += bh + 28

    def events(self):
        ev = []
        if self.send is not None or self.prompt: ev.append(((self.send if self.send is not None else self.prompt[1] + .2), 'pop', .7))
        ev += [(rt, 'pop', .5) for rt, _ in self.replies]
        return ev


class TypeBehind(Scene):
    """full frame: big text types out BEHIND the presenter (typewriter + cursor) on a soft veil from the left.
    text, text_t, x/y/size, step, veil (0..1)."""
    text = '标题'
    text_t = 0
    x, y, size = 80, 640, 210
    step = .13
    veil = .75
    zoom = 1.06

    def xf(self, t):
        return full_xf(lerp(self.zoom, self.zoom + .03, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def behind(self, c, t, ctx):
        th = TH(); a = window(t, self.t0, self.t1, .01, .3)
        if self.veil:
            sh = skia.GradientShader.MakeLinear([(0, 0), (1150, 0)], [CI(th.bg, self.veil * a), CI(th.bg, self.veil * .8 * a), CI(th.bg, 0)], [0, .5, 1])
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
        typewriter(c, self.text, self.x, self.y, F(th.font('display'), self.size), t, self.text_t, th.ink, step=self.step, a=a)

    def events(self):
        return [(self.text_t + i * self.step, 'pop', .35) for i in range(len(self.text))]


class MetalTitle(Page):
    """metallic title with a shine sweep over slowly rotating rings and pulsing markers (dark themes read best).
    title (t, '…'), sub (t, '…'), shine_t (default title t + .5)."""
    title = None
    sub = None
    shine_t = None

    def behind(self, c, t, ctx):
        th = TH(); a = self.a(t)
        rings(c, W / 2, H * .46, t, a=a * eo(P(t, self.t0, 1.2)))

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t)
        if self.title:
            tt, s = self.title
            k = eo(P(t, tt, th.dur * 1.4))
            st = self.shine_t if self.shine_t is not None else tt + .5
            size = min(200, (W - 300) / max(1, len(s)))
            c.save(); c.translate(W / 2, H * .46); sc = lerp(1.08, 1, k); c.scale(sc, sc); c.translate(-W / 2, -H * .46)
            metal_text(c, s, W / 2, H * .46 + size * .35, F(th.font('display'), size), a * k, shine=P(t, st, 1.0), align='c')
            c.restore()
        if self.sub:
            st, s = self.sub
            text(c, s, W / 2, H * .46 + 190, F(th.font('label'), 34), th.muted, a * eo(P(t, st, th.dur)), align='c', spacing=8)

    def events(self):
        return [(self.title[0], 'impact', .8)] if self.title else []


class Callouts(Page):
    """an image card (screenshot / product shot) with pointer labels.
    image='shot.png', rect=(x, y, w, h), callouts=[(t, (px, py) on the image 0..1, (lx, ly) label pos, '标注')],
    strike=(t, x0, x1, y) optional."""
    image = None
    rect = (110, 220, 900, 560)
    callouts = []
    title = None
    _img = None

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t)
        if self.title:
            tt, s = self.title
            kinetic_word(c, s, 110, 170, F(th.font('head'), 60), t, tt, th.ink, a=a)
        x, y, w, h = self.rect
        k = eo(P(t, self.t0 + .1, th.dur))
        if self.image:
            if self._img is None: self._img = skia.Image.open(self.image)
            yy = y + 30 * (1 - k)
            rrect(c, x, yy + 16, w, h, 22, (0, 0, 0), .2 * a * k, blur=20)
            c.save(); c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, yy, w, h), 22, 22), skia.ClipOp.kIntersect, True)
            iw, ih = self._img.width(), self._img.height(); s = max(w / iw, h / ih)
            c.drawImageRect(self._img, skia.Rect.MakeXYWH((iw - w / s) / 2, (ih - h / s) / 2, w / s, h / s), skia.Rect.MakeXYWH(x, yy, w, h), SAMP, skia.Paint(Alphaf=a * k))
            c.restore()
        for ct, (px, py), (lx, ly), s in self.callouts:
            pointer(c, t, ct, lx, ly, x + px * w, y + py * h)
            q = eo(P(t, ct + .25, .35))
            if q > 0:
                f = F(th.font('body'), 32); bw = tw(s, f) + 44
                rrect(c, lx - bw / 2, ly - 30, bw, 56, 28, th.accent, a * q)
                on = max([th.bg, th.ink, th.surface], key=lambda q_: KT.contrast(q_, th.accent))
                text(c, s, lx, ly + 10, f, on, a * q, align='c')

    def events(self):
        return [(ct, 'pop', .6) for ct, *_ in self.callouts]
