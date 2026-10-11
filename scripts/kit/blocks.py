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
    app_tile       app-icon tile: white card, plate, logo image or placeholder mark; sub-pixel  (from AI 工具合集)
    prompt_pill    pill input rises from a blur, types a prompt, collapses into an accent dot   (from AI 工具合集)
    brand_reveal   a light circle grows from the dot, floods the frame, brand ● name + tagline (from AI 工具合集)
Templates (Scene subclasses for scenes.py)
    Page           base: themed background ('paper' / 'dark' / 'plain'), presenter optional
    TitleCard      kicker + kinetic title with end dot + sub line (+ optional HUD)
    BigStat        up to three counters with labels
    CompareTable   a comparison table page
    PromptPage     a prompt typed into an input box, then reply lines appearing
    TypeBehind     typewriter text BEHIND the presenter over the real video
    MetalTitle     metallic title with a shine sweep over rotating rings
    Callouts       a screenshot / image card with pointer labels
    ListSteps      numbered list / steps
    EndCard        closing line + chips
    LogoCloud      app / logo tiles turning in a 3D-ish cloud (depth = size, blur, fade), popping in one by one
    LogoDrop       app / logo tiles falling, bouncing and piling up in two rows on the floor
    CardWall       a tilted wall of screenshot cards sweeping in with motion blur, then receding into a dim frame
    WallPrompt     CardWall → prompt typed in a pill → pill collapses to a dot → brand page grows from the dot
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


class ListSteps(Page):
    """numbered list / steps without cultural flavour: accent number badges pop in, titles slide in on their words,
    notes in the muted colour, a hairline rule draws under each row. label (t, '流程 · 01'), title (t, '…'),
    items=[(t, '理解内容', '读懂每一句'), …]  (up to 6)."""
    label = None
    title = None
    items = []

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t); x0 = 110; x1 = self.right()
        if self.label:
            lt, s = self.label
            circle(c, x0 + 6, 152, 6, th.accent, a * eo(P(t, lt, .4)))
            text(c, s, x0 + 26, 160, F(th.font('label'), 28), th.muted, a * eo(P(t, lt, .5)), spacing=4)
        if self.title:
            tt, s = self.title
            kinetic_word(c, s, x0, 250, F(th.font('head'), 72), t, tt, th.ink, dist=260, a=a)
        n = max(1, len(self.items)); step = min(118, 520 / n); y0 = 380 if self.title else 260
        on = max([th.bg, th.surface, th.ink], key=lambda q: KT.contrast(q, th.accent))
        for i, (t0, s, note) in enumerate(self.items):
            y = y0 + i * step
            k = eob(P(t, t0, .35), 1.4)
            if k > 0:
                circle(c, x0 + 26, y - 16, 26 * k, th.accent, a)
                text(c, str(i + 1), x0 + 26, y - 4, F(th.font('num'), 34), on, a * clamp(k), align='c')
            w = kinetic_word(c, s, x0 + 76, y, F(th.font('head'), 50), t, t0 + .05, th.ink, dist=140, a=a) - (x0 + 76)
            if note:
                text(c, note, x0 + 76 + w + 30, y - 4, F(th.font('label'), 28), th.muted, a * eo(P(t, t0 + .3, th.dur)))
            lp = eo(P(t, t0 + .1, .6))
            if lp > 0: line(c, x0, y + 36, x0 + (x1 - x0) * lp, y + 36, th.line, .5 * a, 1.5)

    def events(self):
        return [(t0, 'pop', .6) for t0, _, _ in self.items]


class EndCard(Page):
    """closing / call to action without cultural flavour: a big kinetic line with an accent end dot, an accent
    underline drawing in, and pill chips popping in. big=(t, '评论区见'), sub=(t, '…'), items=[(t, '提示词'), …]."""
    big = None
    sub = None
    items = []

    def front(self, c, t, ctx):
        th = TH(); a = self.a(t); x0 = 110
        y = 470
        if self.big:
            bt, s = self.big
            size = min(170, (self.right() - x0) / max(1, len(s)) * .92)
            end = kinetic_word(c, s, x0, y, F(th.font('display'), size), t, bt, th.ink, a=a)
            end_dot(c, end + size * .14, y - size * .07, t, bt + .45, th.accent, max(12, size // 9))
            lp = eo(P(t, bt + .5, .5))
            if lp > 0: line(c, x0 + 4, y + 36, x0 + 4 + (end - x0) * .45 * lp, y + 36, th.accent, a, 8)
        if self.sub:
            st, s = self.sub
            text(c, s, x0, y + 110, F(th.font('body'), 40), th.muted, a * eo(P(t, st, th.dur)))
        xx = x0
        for t0, s in self.items:
            f = F(th.font('body'), 32); w = tw(s, f) + 70
            p = eob(P(t, t0, .4), 1.3)
            if p > 0:
                yy = y + 170 + 20 * (1 - p); al = a * clamp(p * 2)
                rrect(c, xx, yy + 8, w, 62, 31, (0, 0, 0), .1 * al, blur=12)
                rrect(c, xx, yy, w, 62, 31, th.surface, al)
                circle(c, xx + 28, yy + 31, 6, th.accent, al)
                text(c, s, xx + 46, yy + 42, f, th.ink, al)
            xx += w + 26

    def events(self):
        ev = [(t0, 'pop', .5) for t0, _ in self.items]
        if self.big: ev.append((self.big[0], 'impact', .7))
        return ev


# ================================================================ app tiles, card walls, prompt → brand
# (from the 'AI 工具合集' reference: a logo cloud, logos piling on a desk, a tilted wall of screenshots, and a prompt
#  pill that collapses into a dot and opens the brand page). All positions / sizes / angles are floats and are drawn
#  sub-pixel by skia, so slow drifts stay smooth — never round them to ints.
_IMG = {}


def _img(path):
    if path not in _IMG: _IMG[path] = skia.Image.open(path)
    return _IMG[path]


def _k():
    """size unit: 1.0 at 720 px tall."""
    return min(W, H) / 720


TILE_COLORS = [(255, 59, 48), (255, 149, 0), (255, 204, 0), (52, 199, 89), (0, 199, 190), (48, 176, 199),
               (0, 122, 255), (88, 86, 214), (175, 82, 222), (255, 45, 85), (162, 132, 94), (40, 40, 48),
               (90, 200, 250), (255, 120, 80), (120, 220, 120), (230, 60, 140), (70, 90, 230), (236, 236, 240)]


def _glyph(c, kind, r, rgb, a):
    """placeholder logo mark centred at (0, 0) — used when no logo image is given."""
    p = paint(rgb, a)
    if kind == 0: c.drawCircle(0, 0, r, p)
    elif kind == 1: c.drawCircle(0, 0, r, paint(rgb, a, stroke=r * .32))
    elif kind == 2:
        pth = skia.Path(); pth.moveTo(0, -r * 1.1); pth.lineTo(r * 1.05, r * .8); pth.lineTo(-r * 1.05, r * .8); pth.close(); c.drawPath(pth, p)
    elif kind == 3: c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-r, -r, 2 * r, 2 * r), r * .22, r * .22), p)
    elif kind == 4:
        pth = skia.Path(); pth.moveTo(-r * .7, -r); pth.lineTo(r, 0); pth.lineTo(-r * .7, r); pth.close(); c.drawPath(pth, p)
    elif kind == 5:
        pth = skia.Path()
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5; rr = r * 1.15 if i % 2 == 0 else r * .5
            (pth.moveTo if i == 0 else pth.lineTo)(rr * math.cos(ang), rr * math.sin(ang))
        pth.close(); c.drawPath(pth, p)
    elif kind == 6:
        for i in range(3):
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-r + i * r * .8, -r + i * r * .3, r * .5, r * (2 - i * .3)), 3, 3), p)
    elif kind == 7:
        pth = skia.Path(); pth.moveTo(0, -r * 1.2); pth.lineTo(r, 0); pth.lineTo(0, r * 1.2); pth.lineTo(-r, 0); pth.close(); c.drawPath(pth, p)
    else:
        c.drawCircle(-r * .6, 0, r * .45, p); c.drawCircle(r * .6, 0, r * .45, p)


def app_tile(c, x, y, size, logo=None, idx=0, angle=0.0, a=1.0, blur=0.0, shadow=True):
    """an app-icon tile centred at (x, y): white rounded card with a soft shadow, an inner plate with a top highlight,
    and the logo (image path, cover-fitted) — or, with logo=None, a placeholder mark on TILE_COLORS[idx].
    angle in degrees; blur > 0 softens the whole tile (depth of field); a fades it."""
    if a <= .003 or size <= 1: return
    s = size; r = s * .24; ins = s * .045
    layer = blur > .15 or a < .999
    if layer:
        pad = s + blur * 3
        lp = skia.Paint(Alphaf=a)
        if blur > .15: lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.saveLayer(skia.Rect.MakeLTRB(x - pad, y - pad, x + pad, y + pad), lp)
    c.save(); c.translate(x, y); c.rotate(angle)
    if shadow: rrect(c, -s / 2, -s / 2 + s * .07, s, s, r, (0, 0, 0), .3, blur=s * .08)
    rrect(c, -s / 2, -s / 2, s, s, r, (248, 248, 250))
    ir = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-s / 2 + ins, -s / 2 + ins, s - 2 * ins, s - 2 * ins), r * .82, r * .82)
    if logo:
        img = _img(logo); iw, ih = img.width(), img.height(); q = s - 2 * ins; sc = max(q / iw, q / ih)
        c.save(); c.clipRRect(ir, skia.ClipOp.kIntersect, True)
        c.drawRect(ir.rect(), paint((255, 255, 255)))
        c.drawImageRect(img, skia.Rect.MakeXYWH((iw - q / sc) / 2, (ih - q / sc) / 2, q / sc, q / sc), ir.rect(), SAMP)
        c.restore()
    else:
        base = TILE_COLORS[idx % len(TILE_COLORS)]
        c.drawRRect(ir, paint(base))
        hl = skia.GradientShader.MakeLinear([(0, -s / 2), (0, 0)], [CI((255, 255, 255), .28), CI((255, 255, 255), 0)])
        c.drawRRect(ir, skia.Paint(AntiAlias=True, Shader=hl))
        gl = (255, 255, 255) if sum(base) < 600 else (60, 60, 70)
        _glyph(c, idx % 9, s * .2, gl, 1)
    c.restore()
    if layer: c.restore()


class LogoCloud(Page):
    """a cloud of app / logo tiles slowly turning about a vertical axis: far tiles are smaller, softer and fainter,
    every tile bobs and sways on its own, and they pop in one by one from t_in.
    logos=['a.png', …] (None = n placeholder tiles), n, center=(x, y) (default slightly left of centre),
    radius, size=(far, near) px, spin (rad/s), stagger (s between pops), t_in (default t0 + .1)."""
    logos = None
    n = 18
    center = None
    radius = None
    size = None
    spin = .35
    stagger = .08
    t_in = None

    def _tin(self):
        return self.t_in if self.t_in is not None else self.t0 + .1

    def front(self, c, t, ctx):
        a = self.a(t); k = _k()
        logos = list(self.logos or [None] * self.n); N = len(logos)
        cx, cy = self.center or (W * .47, H * .42)
        R = self.radius or 230 * k
        sf, sn = self.size or (70 * k, 130 * k)
        items = []
        for i, lg in enumerate(logos):
            yv = 1 - 2 * (i + .5) / N; rr = math.sqrt(max(0.0, 1 - yv * yv))
            th0 = i * math.pi * (3 - math.sqrt(5)); ph = (i * 2.399) % 6.283
            ang = th0 + (t - self.t0) * self.spin
            depth = (math.cos(ang) * rr + 1) / 2                  # 0 far .. 1 near
            p = clamp((t - self._tin() - i * self.stagger) / .5)
            if p <= 0: continue
            sz = lerp(sf, sn, depth) * eob(p, 1.7)
            x = cx + math.sin(ang) * rr * R * 1.25
            y = cy - yv * R * .95 + math.sin(t * 1.6 + ph) * 8 * k
            items.append((depth, i, lg, sz, x, y, math.sin(t * 1.1 + ph) * 6,
                          max(0.0, 1 - depth * 1.4) * 4 * k, (.45 + .55 * depth) * min(1, p * 2)))
        for depth, i, lg, sz, x, y, tilt, bl, al in sorted(items, key=lambda q: q[0]):
            app_tile(c, x, y, sz, lg, i, tilt, a * al, bl)

    def events(self):
        N = len(self.logos or [None] * self.n)
        return [(self._tin() + i * self.stagger, 'pop', .25) for i in range(0, N, 3)]


class LogoDrop(Page):
    """app / logo tiles drop from above one after another, spin as they fall, bounce twice and settle into two rows
    on the floor (a back row and a front row, two landing on top, a few tilted), each casting a shadow that firms up
    as it lands. logos=[…] (None = n placeholders), n, t_drop (first drop, default t0 + .15), interval (s),
    floor_y (front row bottom edge, default .89 H), size (front tile px), seed (layout / order)."""
    logos = None
    n = 18
    t_drop = None
    interval = .13
    floor_y = None
    size = None
    seed = 7
    _plan = None

    def plan(self):
        if self._plan is not None: return self._plan
        import random
        rnd = random.Random(self.seed); k = _k()
        logos = list(self.logos or [None] * self.n); N = len(logos)
        s = self.size or 104 * k; fy = self.floor_y or H * .89
        extra = min(2, max(0, N - 6)); nf = max(1, math.ceil((N - extra) * .62)); nb = N - extra - nf
        plan = []
        x0 = W / 2 - (nf - 1) * s * 1.04 / 2
        fxs = [x0 + j * s * 1.04 for j in range(nf)]
        for x in fxs: plan.append(dict(layer=1, x=x + rnd.uniform(-6, 6) * k, floor=fy, size=s, rest=rnd.choice([0, 0, 0, -8, 9])))
        sb = s * .87; xb = W / 2 - (nb - 1) * sb * 1.22 / 2
        for j in range(nb): plan.append(dict(layer=0, x=xb + j * sb * 1.22 + rnd.uniform(-6, 6) * k, floor=fy - s * .78, size=sb, rest=rnd.choice([0, 0, 6, -10])))
        for j in range(extra):
            base = fxs[min(len(fxs) - 1, [1, len(fxs) - 3][j % 2] if len(fxs) > 3 else 0)]
            plan.append(dict(layer=2, x=base + s * .45 * (1 if j % 2 == 0 else -.1), floor=fy - s, size=s * .93, rest=[14, -18][j % 2]))
        order = list(range(len(plan))); rnd.shuffle(order)
        t_drop = self.t_drop if self.t_drop is not None else self.t0 + .15
        for kk, j in enumerate(order):
            plan[j].update(t0=t_drop + kk * self.interval, spin=rnd.uniform(-160, 160), logo=logos[j % N], idx=j)
        self._plan = plan
        return plan

    def _state(self, p, t):
        g = 2600 * _k(); tt = t - p['t0']
        if tt < 0: return None
        start = -p['size']; h = p['floor'] - start; tf = math.sqrt(2 * h / g)
        if tt < tf:
            return start + .5 * g * tt * tt, p['rest'] + p['spin'] * (1 - tt / tf)
        tb = tt - tf; v0 = g * tf * .28; y = p['floor']
        for _ in range(2):                                         # two damped bounces
            dur = 2 * v0 / g
            if tb < dur: y = p['floor'] - (v0 * tb - .5 * g * tb * tb); break
            tb -= dur; v0 *= .35
        settle = clamp((tt - tf) / .35)
        return y, p['rest'] + math.sin(settle * math.pi * 2) * (1 - settle) * 10

    def land_times(self):
        g = 2600 * _k()
        return [p['t0'] + math.sqrt(2 * (p['floor'] + p['size']) / g) for p in self.plan()]

    def front(self, c, t, ctx):
        a = self.a(t); k = _k(); drawn = []
        for p in self.plan():
            st = self._state(p, t)
            if st is None: continue
            y, ang = st
            if p['layer'] < 2:
                near = clamp(1 - (p['floor'] - y) / (400 * k)); sw = p['size'] * (.6 + .4 * near)
                c.drawOval(skia.Rect.MakeXYWH(p['x'] - sw / 2, p['floor'] - 10 * k, sw, 20 * k), paint((0, 0, 0), .4 * near * a, blur=6 * k))
            drawn.append((p['layer'], p, y, ang))
        for _, p, y, ang in sorted(drawn, key=lambda d: d[0]):
            app_tile(c, p['x'], y - p['size'] / 2, p['size'], p['logo'], p['idx'], ang, a)

    def events(self):
        return [(lt, 'pop', .22) for lt in self.land_times()]


class CardWall(Page):
    """a tilted wall of screenshot cards sweeps in fast (motion blur), slows and settles while easing back from a slight
    zoom; at `recede` it shrinks into a rounded frame, darkens and blurs, so a prompt or a title can sit on top.
    cards=['shot1.png', …] (cover-fitted; None = placeholder cards), angle (deg), t_settle (s the sweep takes),
    travel (px, default 2.1 H), recede (time or None), recede_dur, seed."""
    cards = None
    angle = -28
    t_settle = 3.2
    travel = None
    recede = None
    recede_dur = .6
    seed = 3
    _pic = None

    def _picture(self):
        if self._pic is not None: return self._pic
        import random
        rnd = random.Random(self.seed); k = _k(); th = TH()
        cw, ch, gap = 400 * k, 260 * k, 34 * k
        D = math.hypot(W, H); trav = self.travel or H * 2.1
        cols = int(D / (cw + gap)) + 3; rows = int((D + trav) / (ch + gap)) + 4
        ww, wh = cols * (cw + gap), rows * (ch + gap)
        rec = skia.PictureRecorder(); c = rec.beginRecording(skia.Rect.MakeXYWH(-ww / 2, -wh / 2, ww, wh))
        cards = list(self.cards or []); ci = 0
        styles = [((250, 250, 252), th.accent), ((22, 26, 24), (90, 220, 120)), ((242, 236, 222), (120, 100, 80)),
                  ((30, 32, 40), (120, 150, 255)), ((255, 255, 255), (230, 70, 60)), ((60, 40, 30), (255, 190, 120))]
        for cx_ in range(cols):
            off = (cx_ % 2) * (ch + gap) / 2
            for ry in range(rows):
                x = -ww / 2 + cx_ * (cw + gap); y = -wh / 2 + ry * (ch + gap) + off
                rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, cw, ch), 16 * k, 16 * k)
                if cards:
                    img = _img(cards[ci % len(cards)]); ci += 1
                    iw, ih = img.width(), img.height(); sc = max(cw / iw, ch / ih)
                    c.save(); c.clipRRect(rr, skia.ClipOp.kIntersect, True)
                    c.drawImageRect(img, skia.Rect.MakeXYWH((iw - cw / sc) / 2, (ih - ch / sc) / 2, cw / sc, ch / sc), rr.rect(), SAMP)
                    c.restore()
                    continue
                bg, acc = rnd.choice(styles); c.drawRRect(rr, paint(bg))
                ln = (255, 255, 255) if sum(bg) < 300 else (0, 0, 0); la = .24 if sum(bg) < 300 else .16
                kind = rnd.randint(0, 3)
                if kind == 0:
                    rrect(c, x + 30 * k, y + 34 * k, rnd.uniform(140, 240) * k, 22 * k, 6 * k, acc)
                    for j in range(5): rrect(c, x + 30 * k, y + (84 + j * 28) * k, cw - (60 + rnd.uniform(0, 120)) * k, 12 * k, 5 * k, ln, la)
                elif kind == 1:
                    rrect(c, x + 30 * k, y + 30 * k, cw - 60 * k, 140 * k, 12 * k, acc)
                    rrect(c, x + 30 * k, y + 194 * k, 190 * k, 16 * k, 5 * k, ln, la); rrect(c, x + 30 * k, y + 222 * k, 130 * k, 14 * k, 5 * k, ln, la)
                elif kind == 2:
                    circle(c, x + cw / 2, y + ch / 2 - 10 * k, 46 * k, acc)
                    rrect(c, x + cw / 2 - 70 * k, y + ch / 2 + 54 * k, 140 * k, 14 * k, 5 * k, ln, la)
                else:
                    rrect(c, x + 30 * k, y + 18 * k, 120 * k, 12 * k, 5 * k, acc)
                    for gx in range(3):
                        for gy in range(2): rrect(c, x + (30 + gx * 118) * k, y + (40 + gy * 100) * k, 100 * k, 80 * k, 10 * k, ln, la)
        self._pic = rec.finishRecordingAsPicture()
        return self._pic

    def _scroll(self, t):
        trav = self.travel or H * 2.1
        p = clamp((t - self.t0) / self.t_settle)
        return trav * (1 - (1 - p) ** 4) - trav / 2 + max(0.0, t - self.t0 - self.t_settle) * 18 * _k()

    def _wall(self, c, t, extra=1.0):
        pic = self._picture()
        sc = lerp(1.18, 1.0, eo(clamp((t - self.t0) / self.t_settle))) * extra
        v = abs(self._scroll(t + 1 / 60) - self._scroll(t)) * 60
        sigma = v * (1.6 / 60) / 2.5                                # motion blur along the scroll axis (~1/37 s shutter)
        c.save(); c.translate(W / 2, H / 2); c.scale(sc, sc); c.rotate(self.angle)
        if sigma > .6:
            c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(.01, sigma, skia.TileMode.kClamp)))
        c.translate(0, -self._scroll(t)); c.drawPicture(pic)
        if sigma > .6: c.restore()
        c.restore()

    def _recede_k(self, t):
        return eio(P(t, self.recede, self.recede_dur)) if self.recede is not None else 0.0

    def behind(self, c, t, ctx):
        k = self._recede_k(t)
        if k <= 0:
            self._wall(c, t); return
        s = lerp(1.0, .87, k); r = 28 * _k() * k
        frame = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W * (1 - s) / 2, H * (1 - s) / 2, W * s, H * s), r, r)
        c.save(); c.clipRRect(frame, skia.ClipOp.kIntersect, True)
        bl = 7 * _k() * k
        c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(bl, bl)) if bl > .2 else None)
        self._wall(c, t, s)
        c.restore()
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), .5 * k))
        c.restore()

    def events(self):
        ev = [(self.t0 + .02, 'whoosh', .7)]
        if self.recede is not None: ev.append((self.recede, 'swish', .4))
        return ev


def _light_dark():
    th = TH(); cols = [th.bg, th.surface, th.ink, (248, 246, 240)]
    return max(cols, key=KT.luminance), min(cols, key=KT.luminance)


def _dot_rgb(light):
    th = TH()
    return max([th.accent, th.accent2], key=lambda q: KT.contrast(q, light))


def prompt_pill(c, t, prompt, t_in, t_type, t_collapse, cx=None, cy=None, w=None, h=None, a=1.0):
    """a pill-shaped input box rises out of a blur (t_in), types `prompt` over t_type=(start, end) behind an accent
    caret, then at t_collapse the text fades, the pill shrinks to a circle, turns accent-coloured with a glow and
    shrinks to a dot that stays (for brand_reveal to grow from). Light pill, dark text, whatever the theme."""
    k = _k(); cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    w = w or 520 * k; h = h or 80 * k
    light, dark = _light_dark(); dot = _dot_rgb(light)
    pin = eo(P(t, t_in, .5))
    if pin <= 0: return
    T = t_collapse
    sh = eio(P(t, T + .2, .4)); red = eio(P(t, T + .5, .25)); shrink = P(t, T + .7, .35) ** 3
    pw = lerp(lerp(w * .92, w, pin), h, sh)
    sz = lerp(1.0, .2, shrink); pw, ph = pw * sz, h * sz
    col = tuple(int(lerp(a_, b_, red)) for a_, b_ in zip(light, dot))
    bl = lerp(10 * k, 0, pin)
    lp = skia.Paint(Alphaf=a * pin)
    if bl > .2: lp.setImageFilter(skia.ImageFilters.Blur(bl, bl))
    c.saveLayer(None, lp)
    if red > 0: circle(c, cx, cy, max(pw, ph) * .9, dot, .55 * red, blur=18 * k * sz + 6 * k)
    else: rrect(c, cx - pw / 2, cy - ph / 2 + 8 * k, pw, ph, ph / 2, (0, 0, 0), .35, blur=14 * k)
    rrect(c, cx - pw / 2, cy - ph / 2, pw, ph, ph / 2, col)
    ta = 1 - P(t, T, .25)
    if ta > 0 and sh < .05:
        f = F(TH().font('body'), h * .4)
        n = int(len(prompt) * clamp((t - t_type[0]) / max(.01, t_type[1] - t_type[0]))) if t >= t_type[0] else 0
        s = prompt[:n]; x0 = cx - pw / 2 + h * .48; base = cy + h * .14
        text(c, s, x0, base, f, dark, ta)
        if t_type[0] <= t <= t_type[1] + .1 or int(t * 2.2) % 2 == 0:
            lx = x0 + tw(s, f) + 4 * k
            rrect(c, lx, cy - h * .24, 3 * k, h * .48, 1, dot, ta)
    c.restore()


def brand_reveal(c, t, t_grow, left, right, tagline='', cx=None, cy=None):
    """a light circle grows out of the accent dot at (cx, cy) with two faint ripple rings, then floods the frame; the
    brand opens on the light page as `left` ● `right` spreading out from the dot, with `tagline` fading in under it."""
    k = _k(); cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    light, dark = _light_dark(); dot = _dot_rgb(light)
    g1 = eo(P(t, t_grow, .5)); g2 = P(t, t_grow + .5, .5) ** 3
    r = lerp(8 * k, 56 * k, g1); r = lerp(r, math.hypot(W, H) / 2 + 20, g2)
    if g1 > 0 and g2 < 1: circle(c, cx, cy + 10 * k, r, (0, 0, 0), .4, blur=16 * k)
    if g1 > 0:
        c.save(); pth = skia.Path(); pth.addCircle(cx, cy, r); c.clipPath(pth, skia.ClipOp.kIntersect, True)
        c.drawRect(skia.Rect.MakeWH(W, H), paint(light))
        vg = skia.GradientShader.MakeRadial((cx, cy), math.hypot(W, H) * .62, [CI(dark, 0), CI(dark, .1)])
        c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=vg))
        kb = eo(P(t, t_grow + .55, .7))
        if kb > 0:
            th = TH(); fb = F(th.font('display'), 92 * k)
            gap = 55 * k * lerp(.6, 1, kb)
            tcol = tuple(int(lerp(a_, b_, kb)) for a_, b_ in zip(light, dark))
            yb = cy + fb.getSize() * .36
            text(c, left, cx - gap, yb, fb, tcol, align='r')
            text(c, right, cx + gap, yb, fb, tcol)
            if tagline:
                ka = clamp(kb * 1.3 - .3)
                text(c, tagline, cx, cy + 108 * k, F(th.font('body'), 30 * k), KT.mix(light, dark, .55), ka, align='c')
        c.restore()
    if 0 < g1 and g2 < .3:
        for q in (.35, .65): circle(c, cx, cy, r * q, dot, .2, stroke=2 * k)
    rd = 8 * k if g2 < 1 else lerp(8 * k, 16 * k, eo(P(t, t_grow + .55, .7)))
    circle(c, cx, cy, rd * 2.2, dot, .4, blur=rd * 1.2)
    circle(c, cx, cy, rd, dot)


class WallPrompt(CardWall):
    """CardWall, then a prompt over the receded wall that turns into the brand page:
    prompt=(t_type0, t_type1, '你想让什么动起来？'), t_in (pill appears, default t_type0 - .6),
    collapse (default t_type1 + .5), brand=(t, '品牌', '副名'), tagline='…'. recede defaults to t_in - .6."""
    prompt = None
    t_in = None
    collapse = None
    brand = None
    tagline = ''

    def _times(self):
        p0, p1, s = self.prompt
        t_in = self.t_in if self.t_in is not None else p0 - .6
        col = self.collapse if self.collapse is not None else p1 + .5
        bt = self.brand[0] if self.brand else col + 1.6
        return t_in, col, bt - .55

    def __init__(self, t0, t1, **kw):
        super().__init__(t0, t1, **kw)
        if self.recede is None and self.prompt: self.recede = self._times()[0] - .6

    def front(self, c, t, ctx):
        if not self.prompt: return
        t_in, col, tg = self._times()
        if t < tg:
            prompt_pill(c, t, self.prompt[2], t_in, self.prompt[:2], col)
            if t >= col + 1.05:
                k = _k(); light, _ = _light_dark(); dot = _dot_rgb(light)
                circle(c, W / 2, H / 2, 8 * k * 2.2, dot, .4, blur=8 * k * 1.2); circle(c, W / 2, H / 2, 8 * k, dot)
        elif self.brand:
            brand_reveal(c, t, tg, self.brand[1], self.brand[2], self.tagline)

    def events(self):
        ev = super().events()
        if self.prompt:
            t_in, col, tg = self._times()
            ev += [(t_in, 'pop', .4), (self.prompt[0], 'pop', .25), (col + .2, 'swish', .5), (col + .7, 'pop', .4), (tg, 'whoosh', .6)]
            if self.brand: ev.append((tg + .55, 'impact', .7))
        return ev
