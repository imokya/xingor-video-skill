"""Reusable scene templates for the xingor style.

All times are SOURCE-video seconds (`t`). A project's scenes.py builds a list of these
(or of its own Scene subclasses) covering the whole video, back to back.

Every template exposes `events()` -> [(t, sfx_kind, gain)] so sound effects line up with the
animations automatically. Kinds: whoosh, swish, pop, impact, riser, glitch.
"""
import math
import skia
from fx import *

# person anchor, overwritten by render.py from meta.json
PERSON = {'head_x': 1060, 'head_top': 70, 'face_y': 430, 'body_left': 600, 'body_right': 1640}


def full_xf(z, fx=None, fy=None):
    fx = PERSON['head_x'] if fx is None else fx
    fy = PERSON['face_y'] if fy is None else fy
    return (z, fx - fx * z, fy - fy * z)


def dark_xf(s, cx):
    hx = PERSON['head_x']
    return (s, cx - hx * s, H - H * s)


def mix_xf(a, b, k):
    return tuple(lerp(a[i], b[i], k) for i in range(3))


def slam_text(c, s, x, y, f, t, t0, rgb=WHITE, a=1.0, stagger=0.05, drop=60, glow=0, glow_rgb=None, align='l', spacing=0):
    """per-character drop-in kinetic text"""
    widths = [tw(ch, f) for ch in s]
    total = sum(widths) + spacing * (len(s) - 1)
    if align == 'c': x -= total / 2
    if align == 'r': x -= total
    xx = x
    for i, ch in enumerate(s):
        p = P(t, t0 + i * stagger, 0.42)
        if p > 0:
            k = eob(p, 1.4)
            c.save()
            cx = xx + widths[i] / 2
            c.translate(cx, y - f.getSize() * .35)
            sc = lerp(1.6, 1.0, eo(p))
            c.scale(sc, sc)
            c.translate(-cx, -(y - f.getSize() * .35))
            text(c, ch, xx, y - drop * (1 - k), f, rgb, a * clamp(p * 2.5), glow=glow, glow_rgb=glow_rgb)
            c.restore()
        xx += widths[i] + spacing
    return total


def check_mark(c, x, y, s, rgb, a, prog=1.0, w=5):
    ck = skia.Path(); ck.moveTo(x - 13 * s, y + 1 * s); ck.lineTo(x - 3 * s, y + 11 * s); ck.lineTo(x + 14 * s, y - 10 * s)
    c.drawPath(partial_path(ck, 0, prog), paint(rgb, a, stroke=w))


def play_icon(c, cx, cy, r, bg=LIME, fg=INK, a=1.0):
    circle(c, cx, cy, r, bg, a)
    tri = skia.Path(); tri.moveTo(cx - r * .27, cy - r * .45); tri.lineTo(cx + r * .47, cy); tri.lineTo(cx - r * .27, cy + r * .45); tri.close()
    c.drawPath(tri, paint(fg, a))


def section_title(c, t, t0, label, title):
    hud_label(c, label, 90, 150, eo(P(t, t0, .3)))
    text(c, title, 90, 220, F('heavy', 58), WHITE, eo(P(t, t0 + .05, .4)))


class Scene:
    """mode: 'full' (video bg), 'dark' (person cutout over dark tech bg), 'card' (video shrunk to a card)."""
    mode = 'full'
    rim = 0.0

    def __init__(self, t0, t1, **kw):
        self.t0, self.t1 = t0, t1
        for k, v in kw.items():
            setattr(self, k, v)

    def xf(self, t):
        return full_xf(1.0)

    def behind(self, c, t, ctx):
        pass

    def front(self, c, t, ctx):
        pass

    def rim_amt(self, t):
        return self.rim

    def events(self):
        return []

    def a(self, t):
        return window(t, self.t0, self.t1, .25, .25)


class DarkScene(Scene):
    """Person slides to the right and floats over the dark background with a lime rim light."""
    mode = 'dark'
    rim = 1.0
    scale = .72
    cx = 1560
    enter_from = None  # xf tuple to animate from; default = full frame

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .6))
        return mix_xf(self.enter_from or full_xf(1.05), dark_xf(self.scale, self.cx), k)


# =============================================================== FULL-FRAME TEMPLATES
class Intro(Scene):
    """Face-tracking brackets + identity chip + REC HUD; optional voice card with live waveform.
    label='这个人 = 我', voice_t=None|time, voice_title='也是我的'"""
    label = '这个人 = 我'
    voice_t = None
    voice_title = ''
    voice_label = 'VOICE · 声音'

    def xf(self, t):
        return full_xf(lerp(1.0, 1.06, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def front(self, c, t, ctx):
        vignette(c, .45)
        hx, ht = PERSON['head_x'], PERSON['head_top']
        p = eo(P(t, self.t0 + .15, .5))
        x, y, w, h = hx - 210, ht + 40, 420, 520
        k = lerp(1.25, 1, p)
        cx, cy = x + w / 2, y + h / 2
        ww, hh = w * k, h * k
        a = p * window(t, self.t0, self.t1, .01, .3)
        corners(c, cx - ww / 2, cy - hh / 2, ww, hh, 40, LIME, a, 4)
        sy = cy - hh / 2 + ((t - self.t0) * 260 % hh)
        line(c, cx - ww / 2 + 10, sy, cx + ww / 2 - 10, sy, LIME, a * .35, 2, blur=4)
        chip(c, self.label, cx - ww / 2, cy - hh / 2 - 46, F('bold', 22), LIME, a * eo(P(t, self.t0 + .9, .3)))
        aw = window(t, self.t0, self.t1, .01, .3)
        blink = 1 if int(t * 2) % 2 == 0 else .25
        circle(c, 70, 64, 8, (255, 70, 70), blink * aw)
        text(c, 'REC  ' + ctx.tc(), 88, 71, F('mono', 18), WHITE, .9 * aw)
        text(c, f'1920×1080 · {ctx.fps}FPS · AI-EDIT', W - 60, 71, F('mono', 16), WHITE, .6 * aw, align='r')
        if self.voice_t is not None:
            a2 = eo(P(t, self.voice_t, .35)) * window(t, self.t0, self.t1, .01, .25)
            if a2 > 0:
                yy = lerp(760, 720, a2)
                glass(c, 70, yy, 560, 170, 18, a2)
                hud_label(c, self.voice_label, 96, yy + 40, a2)
                text(c, self.voice_title, 96, yy + 92, F('heavy', 40), WHITE, a2)
                wave_bars(c, 300, yy + 80, 300, 70, t, 30, LIME, a2, amp=.25 + ctx.amp(t) * 1.6)

    def events(self):
        return [(self.t0 + .2, 'pop', .7)] + ([(self.voice_t, 'pop', .7)] if self.voice_t else [])


class BehindText(Scene):
    """Huge kinetic text BEHIND the person (the signature effect).
    text, text_t, x/y/size, rgb, zoom, echo (outline echo), tag (small HUD label), tag_t"""
    text = '大字'
    text_t = 0
    x, y, size = 60, 640, 210
    rgb = WHITE
    zoom = 1.08
    echo = True
    tag = None
    tag_t = None
    stagger = .08
    font = 'heavy'

    def xf(self, t):
        return full_xf(self.zoom)

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .2)
        f = F(self.font, self.size)
        slam_text(c, self.text, self.x, self.y, f, t, self.text_t, self.rgb, a * .97, stagger=self.stagger)
        if self.echo and t > self.text_t + .5:
            e = eo(P(t, self.text_t + .5, .6))
            text(c, self.text, self.x, self.y + self.size * 1.1 * e, f, LIME, a * .5 * (1 - P(t, self.text_t + 1.3, .8)), stroke=2)

    def front(self, c, t, ctx):
        if self.tag:
            hud_label(c, self.tag, self.x + 10, self.y - self.size - 30, self.a(t) * eo(P(t, self.tag_t or self.text_t, .3)))

    def events(self):
        return [(self.text_t, 'impact', 1.0)]


class SplitWord(Scene):
    """Two words on either side of the head, behind the person: e.g. 'OPUS' | '5.5'.
    left, right, text_t, size, font='disp' (latin) or 'heavy'"""
    left, right = 'OPUS', '5.5'
    text_t = 0
    size = 330
    font = 'disp'
    baseline = 590
    tag = None

    def xf(self, t):
        return full_xf(lerp(1.0, 1.05, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .2)
        p = P(t, self.text_t, .5)
        if p <= 0: return
        f = F(self.font, self.size)
        hx = PERSON['head_x']
        sh = skia.GradientShader.MakeLinear([(0, self.baseline - self.size), (0, self.baseline)], [CI(WHITE), CI((200, 210, 230))])
        for s, x, al in [(self.left, hx - 80, 'r'), (self.right, hx + 90, 'l')]:
            k = eo(p)
            xx = x + (-120 if al == 'r' else 120) * (1 - k)
            w = tw(s, f)
            x0 = xx - w if al == 'r' else xx
            text(c, s, x0, self.baseline, f, LIME, a * k, stroke=3)
            fp = eo(P(t, self.text_t + .3, .5))
            c.save(); c.clipRect(skia.Rect.MakeLTRB(0, self.baseline - self.size * fp, W, self.baseline + 10))
            text(c, s, x0, self.baseline, f, WHITE, a)
            c.restore()

    def front(self, c, t, ctx):
        rp = P(t, self.text_t + .05, .6)
        if 0 < rp < 1:
            circle(c, PERSON['head_x'] - 100, 430, 100 + 700 * eo(rp), LIME, (1 - rp) * .8, stroke=6 * (1 - rp) + 1)
        if self.tag:
            chip(c, self.tag, PERSON['head_x'] - 420, 260, F('mono', 18), LIME, self.a(t) * eo(P(t, self.text_t + .3, .3)))

    def events(self):
        return [(self.text_t, 'impact', 1.0)]


class Checklist(Scene):
    """Left-side list of items that get struck through, then a verdict chip.
    label, items=[(t, text, tag)], strike_t, verdict, verdict_t"""
    label = 'CHECKLIST'
    items = []
    strike_t = None
    verdict = None
    verdict_t = None

    def front(self, c, t, ctx):
        a = self.a(t)
        side_shade(c, .75 * a, 1000)
        hud_label(c, self.label, 90, 300, a * eo(P(t, self.t0 + .1, .3)))
        for i, (t0, s, tag) in enumerate(self.items):
            p = eo(P(t, t0, .4))
            y = 420 + i * 140
            x = lerp(40, 90, p)
            w = text(c, s, x, y, F('heavy', 96), WHITE, a * p)
            if tag:
                chip(c, tag, x + w + 20, y - 66, F('bold', 26), WHITE, a * p * .9, INK)
            if self.strike_t:
                sp = eo(P(t, self.strike_t + i * .12, .3))
                if sp > 0:
                    line(c, x - 10, y - 34, x - 10 + (w + 140) * sp, y - 34, LIME, a, 9)
        if self.verdict:
            p = eob(P(t, self.verdict_t, .4))
            if p > 0:
                c.save(); c.translate(150, 420 + len(self.items) * 140 + 30); c.rotate(-6 * (1 - p)); c.scale(p, p)
                chip(c, self.verdict, -60, -40, F('heavy', 40), LIME, a)
                c.restore()

    def events(self):
        ev = [(t0, 'pop', .7) for t0, _, _ in self.items]
        if self.strike_t: ev.append((self.strike_t, 'swish', .8))
        if self.verdict: ev.append((self.verdict_t, 'pop', .8))
        return ev


class PunchHeadline(Scene):
    """Slow push-in on the face + big headline on the left with a marker highlight.
    lines=[(t, text)], mark=(line_idx, substring, t), label"""
    lines = []
    mark = None
    label = 'NEXT'
    z0, z1 = 1.12, 1.3

    def xf(self, t):
        return full_xf(lerp(self.z0, self.z1, eio((t - self.t0) / max(1, self.t1 - self.t0))), PERSON['head_x'], PERSON['face_y'] - 100)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .1, .15)
        side_shade(c, .7 * a, 900)
        for i in range(14):
            yy = 120 + i * 62
            ph = (t * 2.2 + i * .37) % 1
            line(c, -200 + ph * 900, yy, -200 + ph * 900 + 180, yy, WHITE, .07 * a, 2)
        hud_label(c, self.label, 90, 330, a * eo(P(t, self.t0 + .1, .3)))
        f = F('heavy', 118)
        if self.mark:
            li, sub, mt = self.mark
            s = self.lines[li][1]
            idx = s.find(sub)
            if idx >= 0:
                mp = eo(P(t, mt, .35))
                x0 = 90 + tw(s[:idx], f)
                yb = 470 + li * 140
                rrect(c, x0 - 6, yb - 50, (tw(sub, f) + 12) * mp, 66, 4, LIME, a)
        for i, (t0, s) in enumerate(self.lines):
            slam_text(c, s, 90, 470 + i * 140, f, t, t0, WHITE, a, stagger=.07)

    def events(self):
        return [(self.mark[2], 'pop', .7)] if self.mark else []


class FloatTags(Scene):
    """Around-the-person showcase: big behind word + popping props.
    big=(text, t) behind word; props=[(t, kind, label)] kind in image|motion|sound; verdict=(text, t)"""
    big = None
    props = []
    verdict = None

    def xf(self, t):
        return full_xf(1.04)

    def behind(self, c, t, ctx):
        if not self.big: return
        a = window(t, self.t0, self.t1, .01, .25)
        s, t0 = self.big
        f = F('heavy', 300)
        slam_text(c, s, 40, 690, f, t, t0, WHITE, a, stagger=.09)
        p = eo(P(t, t0 + .3, .5))
        if p > 0:
            text(c, s, 40 + 14 * p, 690 + 14 * p, f, LIME, a * .55 * p, stroke=3)

    def front(self, c, t, ctx):
        a = self.a(t)
        slots = {'image': (1640, 230), 'motion': (1420, 600), 'sound': (1460, 760)}
        for t0, kind, label in self.props:
            if kind == 'image':
                p = eob(P(t, t0, .5), 1.5)
                if p <= 0: continue
                c.save(); c.translate(*slots['image']); c.rotate(lerp(-25, -6, clamp(p))); c.scale(p, p)
                x, y, w, h = -150, -100, 300, 200
                rrect(c, x - 8, y - 8, w + 16, h + 46, 8, WHITE, a)
                sh = skia.GradientShader.MakeLinear([(0, y), (0, y + h)], [CI((80, 130, 255), a), CI((180, 120, 255), a)])
                rrect(c, x, y, w, h, 2, shader=sh)
                circle(c, x + 220, y + 60, 26, (255, 230, 120), a)
                m = skia.Path(); m.moveTo(x, y + h); m.lineTo(x + 90, y + 90); m.lineTo(x + 150, y + 150); m.lineTo(x + 210, y + 70); m.lineTo(x + w, y + h); m.close()
                c.drawPath(m, paint((20, 30, 60), a))
                text(c, label, x, y + h + 30, F('bold', 20), INK, a)
                c.restore()
            elif kind == 'motion':
                p = eo(P(t, t0, .5))
                if p <= 0: continue
                pth = skia.Path(); pth.moveTo(1420, 600); pth.cubicTo(1520, 420, 1700, 680, 1820, 470)
                c.drawPath(partial_path(pth, 0, p), paint(WHITE, a * .7, stroke=3))
                q = eio(((t - t0) * .8) % 1)
                (px, py), _ = path_pos(pth, q * p)
                c.save(); c.translate(px, py); c.rotate(t * 240)
                rrect(c, -18, -18, 36, 36, 6, LIME, a)
                c.restore()
                chip(c, label, 1430, 640, F('bold', 22), WHITE, a * p)
            elif kind == 'sound':
                p = eob(P(t, t0, .4), 1.6)
                if p <= 0: continue
                c.save(); c.translate(*slots['sound']); c.scale(p, p)
                glass(c, 0, 0, 340, 100, 18, a)
                spk = skia.Path(); spk.moveTo(26, 38); spk.lineTo(40, 38); spk.lineTo(58, 22); spk.lineTo(58, 78); spk.lineTo(40, 62); spk.lineTo(26, 62); spk.close()
                c.drawPath(spk, paint(LIME, a))
                text(c, label, 74, 62, F('heavy', 30), WHITE, a)
                wave_bars(c, 150, 50, 170, 50, t, 18, LIME, a)
                c.restore()
        if self.verdict:
            s, t0 = self.verdict
            p = eo(P(t, t0, .4))
            if p > 0:
                w = tw(s, F('heavy', 38)) + 130
                glass(c, 70, 100, w, 90, 16, a * p)
                circle(c, 120, 145, 26, LIME, a * p)
                check_mark(c, 121, 145, 1, INK, a * p, eo(P(t, t0 + .2, .3)))
                text(c, s, 165, 160, F('heavy', 38), WHITE, a * p)

    def events(self):
        ev = [(t0, 'pop', .7) for t0, _, _ in self.props]
        if self.big: ev.append((self.big[1], 'impact', 1.0))
        if self.verdict: ev.append((self.verdict[1], 'pop', .8))
        return ev


class SwapSymbol(Scene):
    """Behind-person '×1' struck out, '∞' spins in on the right. old/new/old_t/strike_t/new_t/tag"""
    old, new = '×1', '∞'
    old_t = strike_t = new_t = 0
    tag = None

    def xf(self, t):
        return full_xf(1.12)

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .25)
        p = eob(P(t, self.old_t, .45), 1.4)
        if p > 0:
            c.save(); c.translate(380, 520); c.scale(lerp(1.4, 1, clamp(p)), lerp(1.4, 1, clamp(p))); c.translate(-380, -520)
            text(c, self.old, 110, 780, F('num', 520), WHITE, a * clamp(p) * lerp(1, .35, P(t, self.strike_t + .15, .3)))
            c.restore()
        sp = eo(P(t, self.strike_t, .25))
        if sp > 0:
            line(c, 90, 700, 90 + 560 * sp, 330, LIME, a, 22)
        q = eob(P(t, self.new_t, .5), 1.5)
        if q > 0:
            c.save(); c.translate(PERSON['head_x'] + 500, 520); c.rotate(lerp(-90, 0, clamp(q))); c.scale(q, q)
            text(c, self.new, 0, 170, F('disp', 460), LIME, a, align='c')
            c.restore()

    def front(self, c, t, ctx):
        if self.tag:
            hud_label(c, self.tag, 90, 120, self.a(t) * eo(P(t, self.old_t + .3, .3)))

    def events(self):
        return [(self.old_t, 'impact', .9), (self.strike_t, 'swish', .8), (self.new_t, 'pop', .8)]


class SplitHalftone(Scene):
    """Left of a moving divider becomes a lime/blue halftone 'digital' version of the frame.
    t_in, left_label, right_label, right_t, verdict, verdict_t. Needs ctx.lum_grid (render does it)."""
    needs_grid = True
    t_in = 0
    left_label, right_label = '数字人 · AVATAR', '真人实拍 · LIVE'
    right_t = None
    verdict = None
    verdict_t = None

    def front(self, c, t, ctx):
        a = self.a(t)
        dp = eo(P(t, self.t_in, .6))
        dx = lerp(-20, PERSON['head_x'], eio(P(t, self.t_in, .7))) + 30 * math.sin(t * 1.3) * dp
        if dp > 0:
            c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 0, dx, H))
            c.drawRect(skia.Rect.MakeWH(W, H), paint((4, 6, 12), .85 * a))
            g = ctx.lum_grid; cs = ctx.cell
            pl = paint(LIME, a); pb = paint(BLUE, a * .9)
            rows, cols = g.shape
            for r in range(rows):
                yy = r * cs + cs / 2
                for q in range(cols):
                    xx = q * cs + cs / 2
                    if xx > dx + cs: break
                    rad = g[r, q] * cs * .55
                    if rad > .8:
                        c.drawCircle(xx, yy, rad, pl if ctx.mask_grid[r, q] > .5 else pb)
            c.restore()
            line(c, dx, 0, dx, H, LIME, a, 3)
            line(c, dx, 0, dx, H, LIME, a * .6, 14, blur=12)
            circle(c, dx, 540, 22, LIME, a)
            text(c, '<>', dx, 547, F('mono', 18), INK, a, align='c')
            chip(c, self.left_label, 70, 90, F('bold', 26), LIME, a * dp)
        if self.right_t is not None:
            rp = eo(P(t, self.right_t, .4))
            if rp > 0:
                chip(c, self.right_label, W - 70, 90, F('bold', 26), WHITE, a * rp, INK, align='r')
        if self.verdict:
            kp = eob(P(t, self.verdict_t, .45), 1.5)
            if kp > 0:
                c.save(); c.translate(1660, 860); c.scale(kp, kp)
                chip(c, self.verdict, 0, -34, F('heavy', 34), LIME, a, align='c')
                c.restore()

    def events(self):
        ev = [(self.t_in, 'glitch', .6)]
        if self.right_t: ev.append((self.right_t, 'pop', .7))
        if self.verdict: ev.append((self.verdict_t, 'pop', .8))
        return ev


class MatteReveal(Scene):
    """Shows off the cutout: background dims + grid, rim light on person, then behind text lands.
    case_label, reveal_t, text, text_t, text_rgb"""
    case_label = 'CASE · 真人口播'
    reveal_t = 0
    text = '放到身后'
    text_t = 0
    text_rgb = LIME

    def xf(self, t):
        return full_xf(lerp(1.0, 1.06, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def rim_amt(self, t):
        return eo(P(t, self.reveal_t, .5)) * window(t, self.t0, self.t1, .01, .3)

    def behind(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .01, .25)
        d = eo(P(t, self.reveal_t - .1, .6))
        if d > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((3, 5, 10), .72 * d * a))
            gp = paint(LIME, .10 * d * a, stroke=1)
            off = (t * 30) % 60
            for x in range(0, W + 60, 60):
                c.drawLine(x - off, 0, x - off, H, gp)
            for y in range(0, H + 60, 60):
                c.drawLine(0, y, W, y, gp)
        if self.text:
            slam_text(c, self.text, 60, 650, F('heavy', 250), t, self.text_t, self.text_rgb, a, stagger=.08, drop=120)

    def front(self, c, t, ctx):
        a = self.a(t)
        corners(c, 40, 40, W - 80, H - 80, 60, WHITE, a * .8 * eo(P(t, self.t0 + .1, .4)), 3)
        chip(c, self.case_label, 70, 70, F('bold', 24), WHITE, a * eo(P(t, self.t0 + .3, .3)), INK)
        p = eo(P(t, self.reveal_t + .9, .4))
        if p > 0:
            hud_label(c, 'MATTE · 人像分离', 1400, 160, a * p)
            pr = clamp((t - self.reveal_t - .9) / .8)
            text(c, f'EDGE {pr * 100:5.1f}%', 1400, 190, F('mono', 15), WHITE, a * p * .8)

    def events(self):
        return [(self.reveal_t, 'riser', .7)] + ([(self.text_t, 'impact', 1.0)] if self.text else [])


class Compare(Scene):
    """Glass panel: slow crawling 'manual' bar vs instant 'AI' bar.
    title, slow=(t, label, tag), fast=(t, label)"""
    title = 'COMPARE'
    panel_t = 0
    slow = None
    fast = None

    def xf(self, t):
        return full_xf(lerp(1.0, 1.04, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def front(self, c, t, ctx):
        a = self.a(t)
        side_shade(c, .7 * a, 1000)
        p = eo(P(t, self.panel_t, .4))
        if p <= 0: return
        x, y, w, h = 70, 240, 600, 470
        glass(c, x, y, w, h, 20, a * p)
        hud_label(c, self.title, x + 28, y + 46, a * p)
        if self.slow:
            t1, lab, tag = self.slow
            p1 = eo(P(t, t1, .4))
            if p1 > 0:
                yy = y + 110
                ww = text(c, lab, x + 28, yy + 30, F('heavy', 40), WHITE, a * p1)
                if tag: chip(c, tag, x + 48 + ww, yy - 4, F('bold', 20), (90, 100, 125), a * p1, WHITE)
                el = max(0, t - t1 - .2)
                prog = min(.18, int(el * 6) * .009)
                rrect(c, x + 28, yy + 64, w - 56, 26, 13, WHITE, .1 * a * p1)
                rrect(c, x + 28, yy + 64, (w - 56) * prog, 26, 13, (150, 160, 185), a * p1)
                text(c, f'{prog * 100:4.1f}%', x + w - 28, yy + 30, F('mono', 20), GREY, a * p1, align='r')
                text(c, f'FRAME {int(el * 10):04d} / {ctx.n_frames}', x + 28, yy + 124, F('monor', 16), GREY, a * p1)
        if self.fast:
            t2, lab = self.fast
            p2 = eo(P(t, t2, .35))
            if p2 > 0:
                yy = y + 300
                text(c, lab, x + 28, yy + 30, F('heavy', 40), LIME, a * p2)
                pr = eexp(P(t, t2 + .4, .6))
                rrect(c, x + 28, yy + 64, w - 56, 26, 13, WHITE, .1 * a * p2)
                rrect(c, x + 28, yy + 64, (w - 56) * pr, 26, 13, LIME, a * p2)
                rrect(c, x + 28, yy + 64, (w - 56) * pr, 26, 13, LIME, a * p2 * .6, blur=12)
                text(c, 'DONE' if pr > .98 else f'{pr * 100:4.1f}%', x + w - 28, yy + 30, F('mono', 20), LIME, a * p2, align='r')

    def events(self):
        ev = [(self.panel_t, 'pop', .6)]
        if self.slow: ev.append((self.slow[0], 'pop', .7))
        if self.fast: ev += [(self.fast[0], 'pop', .7), (self.fast[0] + .4, 'riser', .6)]
        return ev


class CTA(Scene):
    """Ending: numbered chips on the left, big behind word, bouncing arrow.
    items=[(t, text)], big=(text, t), arrow=(text, t)"""
    items = []
    big = None
    arrow = None

    def xf(self, t):
        return full_xf(lerp(1.0, 1.08, eio((t - self.t0) / max(1, self.t1 - self.t0))))

    def behind(self, c, t, ctx):
        if self.big:
            a = window(t, self.t0, self.t1, .01, .4)
            slam_text(c, self.big[0], 60, 680, F('heavy', 210), t, self.big[1], LIME, a, stagger=.07, drop=100)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .45)
        for i, (t0, s) in enumerate(self.items):
            p = eob(P(t, t0, .4), 1.5)
            if p <= 0: continue
            c.save(); c.translate(90, 150 + i * 92); c.scale(clamp(p, 0, 1.2), clamp(p, 0, 1.2))
            glass(c, 0, 0, tw(s, F('heavy', 34)) + 60, 72, 14, a, edge_a=.6)
            text(c, s, 24, 48, F('heavy', 34), WHITE, a)
            c.restore()
        if self.arrow:
            s, t0 = self.arrow
            p = eo(P(t, t0, .3))
            if p > 0:
                bob = math.sin(t * 8) * 10
                ar = skia.Path(); ar.moveTo(1700, 760 + bob); ar.lineTo(1700, 860 + bob); ar.moveTo(1660, 820 + bob); ar.lineTo(1700, 862 + bob); ar.lineTo(1740, 820 + bob)
                glow_path(c, ar, LIME, a * p, 6, 10)
                text(c, s, 1700, 730, F('heavy', 36), WHITE, a * p, align='c')

    def events(self):
        ev = [(t0, 'pop', .7) for t0, _ in self.items]
        if self.big: ev.append((self.big[1], 'impact', 1.0))
        if self.arrow: ev.append((self.arrow[1], 'pop', .7))
        return ev


# =============================================================== DARK TEMPLATES
class Pipeline(DarkScene):
    """Up to 3 nodes left->right with drawn connectors.
    label, title, nodes=[(t, small_label, title, subtitle, visual)] visual in wave|face|play|none"""
    label = 'PIPELINE'
    title = ''
    nodes = []
    scale, cx = .80, 1500

    def front(self, c, t, ctx):
        a = self.a(t)
        section_title(c, t, self.t0 + .1, self.label, self.title)
        y, w, h, gap = 320, 300, 300, 70
        xs = [80 + i * (w + gap) for i in range(len(self.nodes))]
        for i, (t0, lab, title, sub, vis) in enumerate(self.nodes):
            p = eob(P(t, t0, .45), 1.2)
            if p <= 0: continue
            aa = a * clamp(p); x = xs[i]
            nxt = self.nodes[i + 1][0] if i + 1 < len(self.nodes) else 1e9
            active = window(t, t0, nxt, .1, .3)
            c.save(); c.translate(x + w / 2, y + h / 2); c.scale(lerp(.85, 1, p), lerp(.85, 1, p)); c.translate(-(x + w / 2), -(y + h / 2))
            glass(c, x, y, w, h, 20, aa, edge=LIME, edge_a=.25 + .6 * active)
            if active > 0:
                rrect(c, x, y, w, h, 20, LIME, aa * .5 * active, stroke=3, blur=12)
            hud_label(c, lab, x + 24, y + 42, aa)
            latin = all(ord(ch) < 0x2000 for ch in title)
            text(c, title, x + 22, y + 120, F('disp', 64) if latin else F('heavy', 50), WHITE, aa)
            text(c, sub, x + 24, y + 162, F('med', 24), GREY, aa)
            vy = y + 230
            if vis == 'wave':
                wave_bars(c, x + 24, vy, w - 48, 70, t, 32, LIME, aa, amp=.25 + 1.6 * ctx.amp(t) * active)
            elif vis == 'face':
                fx_, fy = x + 70, vy
                circle(c, fx_, fy, 42, WHITE, aa * .9, stroke=3)
                circle(c, fx_ - 14, fy - 10, 4, WHITE, aa); circle(c, fx_ + 14, fy - 10, 4, WHITE, aa)
                m = 3 + 42 * ctx.amp(t) * active
                rrect(c, fx_ - 12, fy + 14 - m / 2, 24, max(4, m), 6, LIME, aa)
                for j in range(5):
                    for k in range(3):
                        circle(c, x + 140 + j * 26, vy - 26 + k * 26, 4 + 3 * abs(math.sin(t * 4 + j + k)), BLUE, aa * .8)
            elif vis == 'play':
                play_icon(c, x + 60, vy, 38, LIME, INK, aa)
                pr = eio(P(t, t0 + .2, 1.2))
                rrect(c, x + 120, vy - 5, 150, 10, 5, WHITE, aa * .2)
                rrect(c, x + 120, vy - 5, 150 * pr, 10, 5, LIME, aa)
                text(c, f'{int(pr * 100)}%', x + 120, vy - 18, F('mono', 16), LIME, aa)
            c.restore()
        for i in range(len(self.nodes) - 1):
            t0 = self.nodes[i + 1][0] - .5
            p = eo(P(t, t0, .45))
            if p <= 0: continue
            x0 = xs[i] + w + 6; x1 = xs[i + 1] - 6; yy = y + h / 2
            pth = skia.Path(); pth.moveTo(x0, yy); pth.lineTo(x1, yy)
            glow_path(c, partial_path(pth, 0, p), LIME, a, 3, 8)
            circle(c, lerp(x0, x1, (t * 1.6) % 1), yy, 5, WHITE, a * p)

    def events(self):
        return [(n[0], 'pop', .7) for n in self.nodes]


class Steps(DarkScene):
    """Vertical numbered workflow with a glowing spine; each step lights up on its word.
    label, title, steps=[(t, zh, en, desc, visual)] visual in file|lines|frames|letters|wave|none (+ visual_arg)"""
    label = 'WORKFLOW'
    title = ''
    steps = []
    enter_from = None

    def front(self, c, t, ctx):
        a = self.a(t)
        hud_label(c, self.label, 90, 120, a * eo(P(t, self.t0 + .1, .3)))
        text(c, self.title, 90, 185, F('heavy', 52), WHITE, a * eo(P(t, self.t0 + .15, .4)))
        n = len(self.steps)
        gap = min(124, 640 / max(1, n - 1)) if n > 1 else 124
        x0, y0 = 90, 230
        lastp = 0
        for i, st in enumerate(self.steps):
            if t > st[0]: lastp = i + eo(P(t, st[0], .4))
        spine = gap * (n - 1)
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine, WHITE, .12 * a, 3)
        prog = clamp((lastp - 1) / max(1, n - 1)) if lastp > 1 else 0
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine * prog, LIME, a, 4)
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine * prog, LIME, a * .6, 10, blur=8)
        for i, stp in enumerate(self.steps):
            t0, zh, en, desc, vis = stp[:5]
            varg = stp[5] if len(stp) > 5 else None
            p = eo(P(t, t0, .45))
            if p <= 0: continue
            nxt = self.steps[i + 1][0] if i + 1 < n else 1e9
            act = window(t, t0, nxt, .1, .25)
            y = y0 + i * gap
            circle(c, x0 + 30, y + 52, 16, LIME if act > .1 else (40, 48, 64), a * p)
            if act <= .1:
                check_mark(c, x0 + 30, y + 52, .6, LIME, a * p, 1, 3)
            else:
                ph = (t * 1.5) % 1
                circle(c, x0 + 30, y + 52, 16 + 14 * ph, LIME, a * p * (1 - ph), stroke=2)
            cx = x0 + 70 + (1 - p) * 40
            glass(c, cx, y, 900, 104, 14, a * p, edge_a=.25 + .6 * act)
            text(c, f'{i + 1:02d}', cx + 24, y + 70, F('num', 54), LIME if act > .1 else GREY, a * p)
            text(c, zh, cx + 100, y + 56, F('heavy', 34), WHITE, a * p)
            text(c, en, cx + 102, y + 86, F('mono', 13), LIME, a * p * .9, spacing=1.5)
            text(c, desc, cx + 330, y + 64, F('med', 22), GREY if act < .5 else WHITE, a * p)
            vx, vy, aa = cx + 700, y + 52, a * p
            if vis == 'file':
                chip(c, varg or 'input.mp4', vx, vy - 20, F('bold', 20), WHITE, aa, INK)
            elif vis == 'lines':
                for k in range(3):
                    lw = [150, 110, 160][k]
                    rrect(c, vx, vy - 26 + k * 20, lw, 10, 5, WHITE, aa * .3)
                    rrect(c, vx, vy - 26 + k * 20, lw * eo(P(t, t0 + .2 + k * .15, .4)) * [.4, .8, .55][k], 10, 5, LIME, aa)
            elif vis == 'frames':
                for k in range(3):
                    s = eob(P(t, t0 + .1 + k * .12, .4), 1.4)
                    rrect(c, vx + k * 56, vy - 22, 48 * clamp(s), 44, 6, [BLUE, LIME, VIOLET][k], aa * .9)
            elif vis == 'letters':
                for k, ch in enumerate(varg or 'ABC'):
                    bob = abs(math.sin(t * 6 + k)) * 12 * act
                    text(c, ch, vx + k * 44, vy + 16 - bob, F('disp', 44), LIME if k == 1 else WHITE, aa)
            elif vis == 'wave':
                wave_bars(c, vx, vy, 170, 50, t, 16, LIME, aa, amp=.4 + 1.4 * ctx.amp(t) * act)

    def events(self):
        return [(s[0], 'pop', .7) for s in self.steps]


class DataCards(DarkScene):
    """2x2 grid of animated data cards. cards=[(t, kind, opts)]:
      ('counter', {'value': int|None(=frame count), 'label':..., 'unit':...})
      ('bars',    {'values':[...], 'label':..., 'note':'+95%'})
      ('highlight', {'text':'重点放大', 'label':...})
      ('ring',    {'pct':1.0, 'title':'直观', 'sub':'一眼看懂', 'label':...})"""
    label = 'DATA'
    title = ''
    cards = []

    def front(self, c, t, ctx):
        a = self.a(t)
        section_title(c, t, self.t0 + .2, self.label, self.title)
        pos = [(90, 270), (610, 270), (90, 600), (610, 600)]
        for i, (t0, kind, o) in enumerate(self.cards[:4]):
            x, y = pos[i]
            p = eob(P(t, t0, .45), 1.3)
            if p <= 0: continue
            aa = a * clamp(p)
            c.save(); c.translate(x + 240, y + 150); c.scale(lerp(.8, 1, clamp(p)), lerp(.8, 1, clamp(p))); c.translate(-(x + 240), -(y + 150))
            glass(c, x, y, 480, 300, 18, aa)
            hud_label(c, o.get('label', kind.upper()), x + 24, y + 40, aa)
            if kind == 'counter':
                val = o.get('value') or ctx.n_frames
                v = int(val * eexp(P(t, t0 + .1, 1.6)))
                fnum = F('num', 150)
                text(c, f'{v:,}', x + 24, y + 200, fnum, WHITE, aa)
                text(c, o.get('unit', ''), x + 30 + tw(f'{val:,}', fnum), y + 196, F('heavy', 40), LIME, aa)
                rrect(c, x + 24, y + 240, 432 * eexp(P(t, t0 + .1, 1.6)), 8, 4, LIME, aa)
            elif kind == 'bars':
                vals = o.get('values', [.35, .55, .42, .7, .62, .95])
                mx = max(vals)
                bw = 380 / len(vals)
                for k, v in enumerate(vals):
                    g = eob(P(t, t0 + .1 + k * .08, .5), 1.3)
                    bh = 190 * v / mx * g
                    rrect(c, x + 40 + k * bw, y + 270 - bh, bw * .63, bh, 6, LIME if k == len(vals) - 1 else (70, 82, 110), aa)
                if o.get('note') and t > t0 + .8:
                    text(c, o['note'], x + 40 + (len(vals) - 1) * bw + bw * .31, y + 66, F('mono', 18), LIME, aa * eo(P(t, t0 + .8, .3)), align='c')
            elif kind == 'highlight':
                for k in range(4):
                    rrect(c, x + 24, y + 80 + k * 46, [400, 330, 420, 260][k], 18, 9, WHITE, aa * .18)
                hp = eo(P(t, t0 + .35, .5))
                rrect(c, x + 20, y + 112, 300 * hp, 64, 8, LIME, aa)
                if hp > .5:
                    text(c, o.get('text', '重点'), x + 36, y + 160, F('heavy', 44), INK, aa * clamp((hp - .5) * 2))
            elif kind == 'ring':
                cx, cy, r = x + 150, y + 170, 86
                circle(c, cx, cy, r, WHITE, aa * .12, stroke=20)
                rp = eexp(P(t, t0 + .1, 1.2)) * o.get('pct', 1.0)
                arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), -90, 359.9 * rp)
                c.drawPath(arc, paint(LIME, aa, stroke=20))
                text(c, f'{int(rp * 100)}%', cx, cy + 16, F('num', 52), WHITE, aa, align='c')
                text(c, o.get('title', ''), x + 290, y + 160, F('heavy', 52), WHITE, aa)
                text(c, o.get('sub', ''), x + 290, y + 210, F('med', 24), GREY, aa)
            c.restore()

    def events(self):
        return [(cd[0], 'pop', .7) for cd in self.cards]


class SkillCore(DarkScene):
    """Modules orbit, converge into a glowing hexagon core, then the core emits copies.
    label, title, modules=[...], mods_t, converge_t, core_t, core_text, core_sub, core_chip,
    emit_t (None to skip), emit_title, emit_label, emit_n, stamp=(text, t)"""
    label = 'PACKAGE'
    title = ''
    modules = []
    mods_t = converge_t = core_t = 0
    core_text = 'SKILL'
    core_sub = ''
    core_chip = ''
    emit_t = None
    emit_title = ''
    emit_label = ''
    emit_n = 4
    stamp = None

    def hexagon(self, c, cx, cy, r, a, t):
        pth = skia.Path()
        for i in range(6):
            ang = math.pi / 6 + i * math.pi / 3 + t * .25
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            pth.moveTo(x, y) if i == 0 else pth.lineTo(x, y)
        pth.close()
        sh = skia.GradientShader.MakeRadial((cx, cy), max(r, 1), [CI(LIME, .35 * a), CI((10, 14, 24), .95 * a)])
        c.drawPath(pth, skia.Paint(AntiAlias=True, Shader=sh))
        glow_path(c, pth, LIME, a, 4, 16)

    def front(self, c, t, ctx):
        a = self.a(t)
        emitting = self.emit_t is not None and t >= self.emit_t
        hud_label(c, self.label, 90, 150, a * eo(P(t, self.t0 + .15, .3)))
        tp = eo(P(t, self.emit_t, .4)) if emitting else eo(P(t, self.t0 + .25, .4))
        text(c, self.emit_title if emitting else self.title, 90, 220, F('heavy', 58), WHITE, a * tp)
        cx0, cy0 = 590, 560
        move = eio(P(t, self.emit_t, .6)) if self.emit_t else 0
        cx = lerp(cx0, 300, move); cy = cy0; hr = lerp(130, 95, move)
        conv = eio(P(t, self.converge_t, .9))
        nm = len(self.modules)
        for i, s in enumerate(self.modules):
            p = eob(P(t, self.mods_t + i * .2, .45), 1.4)
            if p <= 0 or conv >= 1: continue
            ang = -math.pi / 2 + i * 2 * math.pi / nm + t * .15
            R = lerp(330, 0, conv)
            x = cx0 + R * math.cos(ang) * 1.25; y = cy0 + R * math.sin(ang) * .78
            f = F('bold', 26); cw = tw(s, f) + 36
            line(c, cx0, cy0, x, y, LIME, a * .25 * clamp(p) * (1 - conv), 1.5)
            c.save(); c.translate(x, y); c.scale(clamp(p) * (1 - conv * .6), clamp(p) * (1 - conv * .6))
            glass(c, -cw / 2, -28, cw, 56, 12, a * clamp(p) * (1 - conv), edge_a=.6)
            text(c, s, 0, 9, f, WHITE, a * clamp(p) * (1 - conv), align='c')
            c.restore()
        hp = eob(P(t, self.core_t, .55), 1.6)
        if hp > 0:
            for k in range(3):
                rp = P(t, self.core_t + .05 + k * .15, .9)
                if 0 < rp < 1:
                    circle(c, cx, cy, hr + 260 * eo(rp), LIME, a * (1 - rp) * .7, stroke=3)
            self.hexagon(c, cx, cy, hr * clamp(hp, 0, 1.2), a, t)
            fs = 64 * hr / 130 * min(1, 5 / max(1, len(self.core_text)))
            text(c, self.core_text, cx, cy + fs * .34, F('disp', fs), WHITE, a * clamp(hp), align='c')
            lp = eo(P(t, self.core_t + 1.0, .4)) * (1 - move)
            if self.core_sub: text(c, self.core_sub, cx, cy + hr + 52, F('mono', 20), LIME, a * lp, align='c')
            if self.core_chip: chip(c, self.core_chip, cx, cy + hr + 76, F('bold', 24), LIME, a * lp, align='c')
        if self.emit_t is not None:
            for i in range(self.emit_n):
                t0 = self.emit_t + .4 + i * .5
                p = eo(P(t, t0, .55))
                if p <= 0: continue
                x = lerp(cx, 520 + i * 150, p); y = lerp(cy, 410 + i * 26, p)
                c.save(); c.translate(x, y); c.scale(lerp(.2, 1, p), lerp(.2, 1, p)); c.rotate(lerp(0, -4 + i * 3, p))
                col = [BLUE, LIME, VIOLET, LIME][i % 4]
                glass(c, 0, 0, 260, 160, 12, a, edge=col, edge_a=.8)
                sh = skia.GradientShader.MakeLinear([(0, 0), (260, 120)], [CI(col, .55 * a), CI(INK, .2 * a)])
                rrect(c, 10, 10, 240, 110, 8, shader=sh)
                play_icon(c, 130, 65, 22, WHITE, INK, a * .9)
                text(c, f'VIDEO_{i + 1:02d}.mp4', 12, 146, F('mono', 15), WHITE, a)
                c.restore()
            n = sum(1 for i in range(self.emit_n) if t > self.emit_t + .7 + i * .5)
            if n:
                ap = a * eo(P(t, self.emit_t + .7, .3))
                text(c, f'×{n}', 520, 800, F('num', 120), LIME, ap)
                text(c, self.emit_label, 640, 790, F('bold', 28), WHITE, ap)
        if self.stamp:
            s, t0 = self.stamp
            sp = eo(P(t, t0, .3))
            if sp > 0:
                f = F('heavy', 34)
                chip(c, s, 520, 840, f, WHITE, a * sp, INK)
                line(c, 520, 866, 520 + (tw(s, f) + 28) * eo(P(t, t0 + .2, .3)), 866, LIME, a, 6)

    def events(self):
        ev = [(self.mods_t + i * .2, 'pop', .6) for i in range(len(self.modules))]
        ev.append((self.core_t, 'impact', 1.0))
        if self.emit_t is not None:
            ev += [(self.emit_t + .4 + i * .5, 'pop', .6) for i in range(self.emit_n)]
        if self.stamp: ev.append((self.stamp[1] + .2, 'swish', .8))
        return ev


class Analyze(DarkScene):
    """Reference cards get scanned, then analysis rows (rhythm/type/motion) appear, then an
    auto-edit timeline replaces the cards. cards_t, scan_t, rows=[(t, zh, en, kind)], timeline_t"""
    label = 'ANALYZE'
    title = ''
    cards_t = 0
    scan_t = None
    rows = []
    timeline_t = None
    timeline_label = 'AUTO EDIT · 自动安排画面'
    enter_from = None

    def ref_card(self, c, x, y, w, h, t, idx, a):
        hues = [(BLUE, VIOLET), (LIME, BLUE), (VIOLET, (255, 90, 140))]
        h1, h2 = hues[idx % 3]
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 14, 14), skia.ClipOp.kIntersect, True)
        sh = skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [CI(h1, .8 * a), CI(h2, .55 * a)])
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(Shader=sh))
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint((0, 0, 0), .35 * a))
        if idx % 3 == 0:
            for k in range(5):
                bh = 30 + 60 * abs(math.sin(t * 3 + k))
                rrect(c, x + 30 + k * 50, y + h - 30 - bh, 30, bh, 4, WHITE, .8 * a)
        elif idx % 3 == 1:
            text(c, 'BIG', x + 24 + 10 * math.sin(t * 2), y + 120, F('disp', 92), WHITE, .9 * a)
        else:
            for k in range(3):
                ang = t * 2 + k * 2.1
                circle(c, x + w / 2 + 60 * math.cos(ang), y + h / 2 + 40 * math.sin(ang), 18, WHITE, .85 * a)
        c.restore()
        rrect(c, x, y, w, h, 14, WHITE, .25 * a, stroke=1.5)
        text(c, f'REF_0{idx + 1}.mp4', x + 12, y + h + 26, F('monor', 15), GREY, a)

    def front(self, c, t, ctx):
        a = self.a(t)
        section_title(c, t, self.t0 + .15, self.label, self.title)
        out = eio(P(t, self.timeline_t - .2, .5)) if self.timeline_t else 0
        for i in range(3):
            p = eob(P(t, self.cards_t + i * .18, .5), 1.3)
            if p <= 0: continue
            self.ref_card(c, 90 + i * 335, 280 + (1 - p) * 80 - out * 40, 300, 170, t, i, a * clamp(p) * (1 - out))
        if self.scan_t:
            sp = P(t, self.scan_t, 1.4)
            if 0 < sp < 1 and out < 1:
                sx = lerp(80, 1100, eio(sp))
                c.drawRect(skia.Rect.MakeLTRB(80, 270, sx, 460), paint(LIME, .08 * a))
                line(c, sx, 260, sx, 480, LIME, a, 3)
                line(c, sx, 260, sx, 480, LIME, a * .8, 10, blur=10)
                text(c, f'ANALYZING  {int(eio(sp) * 100):3d}%', sx + 12, 262, F('mono', 16), LIME, a)
        if self.timeline_t:
            tp = eo(P(t, self.timeline_t, .5))
            if tp > 0:
                x, y, w = 90, 270, 1030
                glass(c, x, y, w, 220, 16, a * tp)
                hud_label(c, self.timeline_label, x + 22, y + 38, a * tp)
                tracks = [('V1', [(0, .3), (.32, .55), (.57, 1)], BLUE), ('T1', [(.05, .25), (.4, .52), (.62, .9)], LIME),
                          ('A1', [(.1, .14), (.33, .37), (.58, .62), (.8, .84)], VIOLET)]
                ts = self.timeline_t + 1.5
                for k, (nm, clips, col) in enumerate(tracks):
                    ty = y + 66 + k * 46
                    text(c, nm, x + 22, ty + 24, F('mono', 15), GREY, a * tp)
                    rrect(c, x + 70, ty, w - 100, 34, 6, WHITE, .05 * a * tp)
                    for j, (c0, c1) in enumerate(clips):
                        cp = eob(P(t, ts + (k * 3 + j) * .09, .35), 1.2)
                        if cp <= 0: continue
                        cx0 = x + 70 + c0 * (w - 100); cx1 = x + 70 + c1 * (w - 100)
                        rrect(c, cx0 + 2, ty + 2 - 30 * (1 - cp), cx1 - cx0 - 4, 30, 5, col, a * clamp(cp) * .9)
                if t > ts:
                    ph = x + 70 + (w - 100) * clamp((t - ts) / 1.5)
                    line(c, ph, y + 56, ph, y + 210, WHITE, a * tp, 2)
                    circle(c, ph, y + 56, 6, WHITE, a * tp)
        for i, (t0, zh, en, kind) in enumerate(self.rows[:3]):
            p = eo(P(t, t0, .4))
            if p <= 0: continue
            x, y, w, h = 90 + (1 - p) * -60, 540 + i * 108, 1030, 92
            glass(c, x, y, w, h, 14, a * p)
            text(c, zh, x + 26, y + 58, F('heavy', 36), WHITE, a * p)
            text(c, en, x + 210, y + 54, F('mono', 15), LIME, a * p, spacing=2)
            vx = x + 420
            if kind == 'rhythm':
                for k in range(22):
                    beat = (k % 4 == 0)
                    ph = (t * 2.2 - k * .08) % 1
                    hh = (46 if beat else 22) * (0.6 + 0.4 * (1 - ph))
                    rrect(c, vx + k * 26, y + h / 2 - hh / 2, 8, hh, 3, LIME if beat else WHITE, a * p * (.95 if beat else .45))
            elif kind == 'type':
                xx = vx
                for k, wv in enumerate([180, 90, 140, 60, 120]):
                    s = eo(P(t, t0 + .1 + k * .07, .3))
                    rrect(c, xx, y + 22 + (k % 2) * 26, wv * s, 20 if k % 2 == 0 else 14, 4, WHITE if k != 2 else LIME, a * p * (.85 if k != 2 else 1))
                    xx += wv + 14
            else:
                pth = skia.Path(); pth.moveTo(vx, y + h - 18); pth.cubicTo(vx + 200, y + h - 18, vx + 260, y + 18, vx + 560, y + 18)
                c.drawPath(pth, paint(WHITE, a * p * .3, stroke=2))
                glow_path(c, partial_path(pth, 0, eo(P(t, t0 + .1, .7))), LIME, a * p, 3, 8)
                (px, py), _ = path_pos(pth, eio((t * .7) % 1))
                circle(c, px, py, 9, WHITE, a * p)

    def events(self):
        ev = [(self.cards_t + i * .18, 'pop', .6) for i in range(3)] + [(r[0], 'pop', .7) for r in self.rows]
        if self.scan_t: ev.append((self.scan_t, 'riser', .7))
        if self.timeline_t: ev.append((self.timeline_t + 1.5, 'glitch', .5))
        return ev


class ThisVideo(Scene):
    """Meta moment: the video shrinks into a card above a timeline of THIS edit (real scene/caption/sfx data)."""
    mode = 'card'
    timeline_t = None
    stats_t = None

    def xf(self, t):
        k = eio(P(t, self.t0 + .1, .8))
        s = lerp(1.0, .62, k)
        cy = lerp(540, 400, k)
        return (s, 960 - 960 * s, cy - 540 * s)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .2)
        k = eio(P(t, self.t0 + .1, .8))
        if k <= 0: return
        s, ox, oy = self.xf(t)
        corners(c, ox - 16, oy - 16, W * s + 32, H * s + 32, 36, LIME, a * k, 3)
        hud_label(c, 'THIS VIDEO · 本片', ox, oy - 34, a * k)
        text(c, 'RENDER · OK', ox + W * s, oy - 24, F('mono', 16), LIME, a * k, align='r')
        tp = eo(P(t, self.timeline_t or self.t0 + .6, .5))
        if tp > 0:
            x, y, w = 200, 805, 1520
            text(c, 'TIMELINE', x, y - 16, F('mono', 14), GREY, a * tp)
            total = ctx.scenes[-1].t1
            for i, sc in enumerate(ctx.scenes):
                gp = eo(P(t, (self.timeline_t or self.t0 + .6) + i * .04, .3))
                x0 = x + w * sc.t0 / total; x1 = x + w * sc.t1 / total
                col = {'full': (70, 82, 110), 'dark': BLUE, 'card': LIME, 'talk': VIOLET}[sc.mode]
                rrect(c, x0 + 1.5, y, (x1 - x0 - 3) * gp, 36, 4, col, a * tp * .9)
            for s0, s1, _ in ctx.captions:
                rrect(c, x + w * s0 / total, y + 44, max(2, w * (s1 - s0) / total - 2), 10, 3, WHITE, a * tp * .35)
            for st_, kind, g in ctx.sfx:
                xx = x + w * st_ / total
                line(c, xx, y + 60, xx, y + 72, LIME, a * tp * .7, 2)
            ph = x + w * t / total
            line(c, ph, y - 10, ph, y + 80, WHITE, a * tp, 2)
            circle(c, ph, y - 10, 6, WHITE, a * tp)
        if self.stats_t:
            sp = eo(P(t, self.stats_t, .4))
            if sp > 0:
                stats = [(f'{len(ctx.scenes)}', '个镜头'), (f'{len(ctx.captions)}', '条字幕'), (f'{len(ctx.sfx)}', '个音效')]
                xx = 200
                for v, l in stats:
                    ww = text(c, v, xx, 930, F('num', 54), LIME, a * sp)
                    ww2 = text(c, l, xx + ww + 10, 924, F('med', 22), WHITE, a * sp)
                    xx += ww + ww2 + 70

    def events(self):
        return [(self.t0 + .1, 'whoosh', .6)] + ([(self.stats_t, 'pop', .7)] if self.stats_t else [])


# =============================================================== TALK CARD (口播小窗)
PAPER = (244, 244, 240)
PAPER_INK = (16, 18, 22)
PAPER_GREY = (128, 132, 140)


def spring(x):
    """damped spring 0->1 with a small overshoot; feels 'physical' for card moves."""
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - math.exp(-6.5 * x) * math.cos(8.0 * x) * (1 - .25 * x)


CARD_SLOTS = {
    # name: (center x, center y, w, h, radius)
    'full':   (W / 2, H / 2, W, H, 0),
    'right':  (1530, 505, 470, 820, 30),
    'left':   (390, 520, 440, 780, 30),
    'center': (W / 2, 500, 520, 860, 30),
    'bubble': (1730, 210, 240, 240, 120),
    'bubble_l': (190, 210, 240, 240, 120),
    'wide':   (1370, 470, 860, 520, 26),
}


def paper_bg(c, t, a=1.0, grid=True):
    c.drawRect(skia.Rect.MakeWH(W, H), paint(PAPER, a))
    sh = skia.GradientShader.MakeRadial((W * .35, H * .3), W * .8, [CI(WHITE, .7 * a), CI(WHITE, 0)])
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=sh))
    if grid:
        gp = paint(PAPER_INK, .035 * a, stroke=1)
        for x in range(0, W, 80): c.drawLine(x, 0, x, H, gp)
        for y in range(0, H, 80): c.drawLine(0, y, W, y, gp)
    # floor shelf the card stands on (subtle perspective plane)
    sh = skia.GradientShader.MakeLinear([(0, 730), (0, H)], [CI((225, 226, 222), 0), CI((214, 216, 212), .9 * a)])
    c.drawRect(skia.Rect.MakeLTRB(0, 730, W, H), skia.Paint(Shader=sh))


def marked_line(c, s, x, y, f, t, t0, theme, a=1.0, mark_t=None):
    """Headline where [brackets] mark highlighted words. paper: ink text on a lime marker;
    dark: lime text. Words slide up + fade in with a light stagger."""
    parts = []
    buf = ''; hl = False
    for ch in s:
        if ch == '[': parts.append((buf, hl)); buf = ''; hl = True
        elif ch == ']': parts.append((buf, hl)); buf = ''; hl = False
        else: buf += ch
    parts.append((buf, hl))
    xx = x
    ink = PAPER_INK if theme == 'paper' else WHITE
    for i, (seg, h) in enumerate(parts):
        if not seg: continue
        p = eo(P(t, t0 + i * .08, .45))
        w = tw(seg, f)
        if h and theme == 'paper':
            mp = eo(P(t, (mark_t or t0 + .35) + i * .05, .35))
            rrect(c, xx - 6, y - f.getSize() * .42, (w + 12) * mp, f.getSize() * .5, 4, LIME, a * p)
        col = (LIME if h else ink) if theme == 'dark' else ink
        text(c, seg, xx, y + 26 * (1 - p), f, col, a * p)
        xx += w
    return xx - x


class TalkCard(Scene):
    """口播小窗: the talking-head lives in ONE persistent card that pops in, morphs and moves.
    Inspired by vertical 'on air' presenter cards. Face-tracked crop, soft shadow, ON AIR pill.

    theme: 'paper' (light editorial) | 'dark'
    path:  [(t, slot), ...]  slot = name in CARD_SLOTS or a (cx, cy, w, h, r) tuple.
           First entry is the start state ('full' makes the full video shrink into the card).
    label: pill text, e.g. 'ON AIR · 阿星'   hud: top-left code label, e.g. '// 01 — 方法'
    kicker / lines=[(t, '先做[完整]产品'), ...] / items=[(t, text)]: built-in left-side content
    Override content(c, t, ctx, card_rect) for custom demos (it gets the card rect to avoid)."""
    mode = 'talk'
    theme = 'paper'
    path = [(0, 'right')]
    label = 'ON AIR'
    hud = None
    kicker = None
    kicker_t = None
    lines = []
    items = []
    morph = .85
    smooth_in = True

    def draw_bg(self, c, t, ctx):
        if self.theme == 'paper':
            paper_bg(c, t)
        else:
            dark_bg(c, t)

    def state(self, t):
        def get(s):
            return CARD_SLOTS[s] if isinstance(s, str) else s
        cur = get(self.path[0][1])
        for i in range(1, len(self.path)):
            t0, s = self.path[i]
            if t < t0: break
            k = spring(P(t, t0, self.morph))
            nxt = get(s)
            cur = tuple(lerp(cur[j], nxt[j], k) for j in range(5))
        # entrance pop (only when not starting from full frame)
        if self.path[0][1] != 'full':
            k = spring(P(t, self.t0, .55))
            cx, cy, w, h, r = cur
            s = lerp(.86, 1, k)
            cur = (cx, cy + 40 * (1 - k), w * s, h * s, r * s)
        return cur

    def crop(self, w, h, ctx):
        """source rect to show in a card of size w x h: centered on the face, zooming in as the card
        gets smaller; blends to the whole frame as the card approaches full size."""
        fullness = clamp((w * h) / (W * H) * 1.6)
        hx = ctx.head_x
        fy = CP_face_y()
        zoom = lerp(1.0, 2.1, clamp(1 - h / 860)) if h < 860 else 1.0
        ch = H / zoom
        cw = min(W, ch * w / h)
        ch = cw * h / w
        x0 = clamp(hx - cw / 2, 0, W - cw)
        y0 = clamp(fy - ch * .42, 0, H - ch)
        full = (0, 0, W, H)
        rect = (x0, y0, cw, ch)
        return tuple(lerp(rect[i], full[i], fullness ** 2) for i in range(4))

    def card_rect(self, t):
        cx, cy, w, h, r = self.state(t)
        return (cx - w / 2, cy - h / 2, w, h, r)

    def draw_card(self, c, t, ctx):
        x, y, w, h, r = self.card_rect(t)
        a = window(t, self.t0 - 1, self.t1, .01, .2) if self.path[0][1] == 'full' else window(t, self.t0, self.t1, .15, .2)
        big = clamp((w * h) / (W * H) * 1.6)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
        sh_a = (.30 if self.theme == 'paper' else .55) * (1 - big)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + 6, y + 30, w - 12, h - 10), r, r), paint((0, 0, 0), sh_a * a, blur=34))
        c.save(); c.clipRRect(rr, skia.ClipOp.kIntersect, True)
        sx, sy, sw, shh = self.crop(w, h, ctx)
        c.drawImageRect(ctx.img, skia.Rect.MakeXYWH(sx, sy, sw, shh), skia.Rect.MakeXYWH(x, y, w, h),
                        skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone), skia.Paint(Alphaf=a))
        c.restore()
        ring = WHITE if self.theme == 'paper' else LIME
        if r >= min(w, h) / 2 - 2:  # bubble: white/lime ring like a sticker
            c.drawRRect(rr, paint(ring, a, stroke=5))
        else:
            c.drawRRect(rr, paint(WHITE, .5 * a * (1 - big), stroke=1.5))
        # ON AIR pill, fades out as the card shrinks to a bubble or grows to full
        la = a * clamp((h - 400) / 200) * (1 - big)
        if la > 0 and self.label:
            f = F('mono', 17)
            lw = tw(self.label, f) + 58
            rrect(c, x + 18, y + 18, lw, 38, 19, (10, 10, 12), .55 * la)
            pulse = .55 + .45 * (0.5 + 0.5 * math.sin(t * 5))
            circle(c, x + 39, y + 37, 6, LIME, la * pulse)
            text(c, self.label, x + 54, y + 43, f, WHITE, la)

    def content(self, c, t, ctx, card):
        a = self.a(t)
        ink = PAPER_INK if self.theme == 'paper' else WHITE
        grey = PAPER_GREY if self.theme == 'paper' else GREY
        x0 = 120 if card[0] > W / 2 - 100 else 760
        if self.kicker:
            kp = eo(P(t, self.kicker_t or self.t0 + .2, .4))
            text(c, self.kicker, x0, 250, F('bold', 24), grey, a * kp, spacing=3)
        for i, (t0, s) in enumerate(self.lines):
            marked_line(c, s, x0, 370 + i * 118, F('heavy', 100), t, t0, self.theme, a)
        for i, (t0, s) in enumerate(self.items):
            p = spring(P(t, t0, .55))
            if p <= 0: continue
            f = F('bold', 30)
            w = tw(s, f) + 56
            xx = x0 + sum(tw(it[1], f) + 76 for it in self.items[:i])
            yy = 640 + 40 * (1 - p)
            if self.theme == 'paper':
                rrect(c, xx, yy + 10, w, 66, 14, (0, 0, 0), .10 * a, blur=14)
                rrect(c, xx, yy, w, 66, 14, WHITE, a * clamp(p * 3))
                text(c, s, xx + 28, yy + 44, f, ink, a * clamp(p * 3))
            else:
                glass(c, xx, yy, w, 66, 14, a * clamp(p * 3), edge_a=.6)
                text(c, s, xx + 28, yy + 44, f, WHITE, a * clamp(p * 3))

    def front(self, c, t, ctx):
        a = self.a(t)
        if self.hud:
            col = PAPER_GREY if self.theme == 'paper' else GREY
            text(c, self.hud, 40, 46, F('mono', 18), col, a)
            text(c, ctx.tc(), W - 40, 46, F('mono', 18), col, a, align='r')
        card = self.card_rect(t)
        self.content(c, t, ctx, card)
        self.draw_card(c, t, ctx)

    def events(self):
        ev = [(t0, 'swish', .6) for t0, _ in self.path[1:]]
        ev += [(t0, 'pop', .6) for t0, _ in self.items]
        return ev


def CP_face_y():
    return PERSON['face_y']
