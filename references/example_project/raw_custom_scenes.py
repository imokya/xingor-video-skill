"""Scene definitions. All times are SOURCE-video seconds (st)."""
import math
import numpy as np
import skia
from fx import *

SFX = []  # (src_time, kind, gain)


def sfx(t, kind, g=1.0):
    SFX.append((t, kind, g))


def full_xf(z, fx=1060, fy=430):
    return (z, fx - fx * z, fy - fy * z)


def dark_xf(s, cx):
    return (s, cx - 1060 * s, 1080 - 1080 * s)


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


class Scene:
    mode = 'full'  # full | dark | card
    rim = 0.0

    def __init__(self, t0, t1):
        self.t0, self.t1 = t0, t1

    def xf(self, t):
        return full_xf(1.0)

    def behind(self, c, t, ctx):
        pass

    def front(self, c, t, ctx):
        pass

    def rim_amt(self, t):
        return self.rim


# ---------------------------------------------------------------- A: intro
class SIntro(Scene):
    def xf(self, t):
        return full_xf(lerp(1.0, 1.06, eio(t / 3)))

    def front(self, c, t, ctx):
        vignette(c, .45)
        # face tracking frame
        p = eo(P(t, 0.15, .5))
        x, y, w, h = 850, 110, 420, 520
        k = lerp(1.25, 1, p)
        cx, cy = x + w / 2, y + h / 2
        ww, hh = w * k, h * k
        a = p * window(t, 0, 2.9, .01, .3)
        corners(c, cx - ww / 2, cy - hh / 2, ww, hh, 40, LIME, a, 4)
        # scan line inside box
        sy = cy - hh / 2 + (t * 260 % hh)
        line(c, cx - ww / 2 + 10, sy, cx + ww / 2 - 10, sy, LIME, a * .35, 2, blur=4)
        chip(c, '这个人 = 我', cx - ww / 2, cy - hh / 2 - 46, F('bold', 22), LIME, a * eo(P(t, .9, .3)))
        text(c, f'MATCH {min(99.7, (t - .9) * 160):.1f}%' if t > .9 else '', cx + ww / 2, cy - hh / 2 - 16, F('mono', 16), LIME, a, align='r')
        # HUD
        blink = 1 if int(t * 2) % 2 == 0 else .25
        circle(c, 70, 64, 8, (255, 70, 70), blink * window(t, 0, 3, .01, .3))
        text(c, 'REC  ' + ctx.tc(), 88, 71, F('mono', 18), WHITE, .9 * window(t, 0, 3, .01, .3))
        text(c, '1920×1080 · 25FPS · AI-EDIT', W - 60, 71, F('mono', 16), WHITE, .6 * window(t, 0, 3, .01, .3), align='r')
        # voice card
        a2 = eo(P(t, 2.0, .35)) * window(t, 0, 3.05, .01, .25)
        if a2 > 0:
            yy = lerp(760, 720, a2)
            glass(c, 70, yy, 560, 170, 18, a2)
            hud_label(c, 'VOICE · 声音', 96, yy + 40, a2)
            text(c, '也是我的', 96, yy + 92, F('heavy', 40), WHITE, a2)
            wave_bars(c, 300, yy + 80, 300, 70, t, 30, LIME, a2, amp=.25 + ctx.amp(t) * 1.6)


# ---------------------------------------------------------------- B: not filmed
class SNotFilmed(Scene):
    def xf(self, t):
        return full_xf(1.1)

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .2)
        f = F('heavy', 210)
        slam_text(c, '不是我拍的', 60, 640, f, t, 4.3, WHITE, a * .96, stagger=.08, glow=0)
        # outline echo
        if t > 4.8:
            e = eo(P(t, 4.8, .6))
            text(c, '不是我拍的', 60, 640 + 230 * e, f, LIME, a * .5 * (1 - P(t, 5.6, .8)), stroke=2)

    def front(self, c, t, ctx):
        a = window(t, 3.1, self.t1, .2, .2)
        hud_label(c, 'NOT FILMED · 非实拍', 70, 330, a * eo(P(t, 3.4, .3)))
        # camera crossed
        p = eo(P(t, 5.1, .35))
        if p > 0:
            x, y = 1500, 160
            rrect(c, x, y, 140, 92, 14, WHITE, a * p, stroke=4)
            circle(c, x + 70, y + 46, 26, WHITE, a * p, stroke=4)
            rrect(c, x + 140, y + 26, 30, 40, 4, WHITE, a * p, stroke=4)
            pp = eo(P(t, 5.4, .25))
            line(c, x - 20, y + 120, x - 20 + 210 * pp, y + 120 - 150 * pp, LIME, a, 8)


# ---------------------------------------------------------------- C: no manual editing
class SNoHands(Scene):
    def xf(self, t):
        return full_xf(1.0)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .25, .2)
        side_shade(c, .75 * a, 1000)
        hud_label(c, 'POST-PRODUCTION', 90, 300, a * eo(P(t, 6.6, .3)))
        rows = [('剪辑', 7.05), ('动效', 7.45)]
        for i, (s, t0) in enumerate(rows):
            p = eo(P(t, t0, .4))
            y = 420 + i * 140
            x = lerp(40, 90, p)
            text(c, s, x, y, F('heavy', 96), WHITE, a * p)
            chip(c, '手动', x + 215, y - 66, F('bold', 26), WHITE, a * p * .9, INK)
            sp = eo(P(t, 8.6 + i * .12, .3))
            if sp > 0:
                line(c, x - 10, y - 34, x - 10 + 340 * sp, y - 34, LIME, a, 9)
        p = eob(P(t, 9.0, .4))
        if p > 0:
            c.save(); c.translate(150, 760); c.rotate(-6 * (1 - p)); c.scale(p, p)
            chip(c, '0% 手工 · 全交给 AI', -60, -40, F('heavy', 40), LIME, a)
            c.restore()


# ---------------------------------------------------------------- D: hand to Opus 5.5
class SOpus(Scene):
    def xf(self, t):
        return full_xf(lerp(1.0, 1.05, eio((t - self.t0) / 3.1)))

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .2)
        p = P(t, 11.6, .5)
        if p <= 0: return
        f = F('disp', 330)
        sh = skia.GradientShader.MakeLinear([(0, 260), (0, 600)], [CI(WHITE), CI((200, 210, 230))])
        for s, x, al in [('OPUS', 980, 'r'), ('5.5', 1150, 'l')]:
            k = eo(p)
            xx = x + (-120 if al == 'r' else 120) * (1 - k)
            w = tw(s, f)
            x0 = xx - w if al == 'r' else xx
            # outline first, then fill wipes up
            c.drawString(s, x0, 590, f, paint(LIME, a * k, stroke=3))
            fp = eo(P(t, 11.9, .5))
            c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 590 - 330 * fp, W, 600))
            c.drawString(s, x0, 590, f, skia.Paint(AntiAlias=True, Shader=sh, Alphaf=a))
            c.restore()

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .2)
        side_shade(c, .45 * a, 700)
        # script card
        p = eo(P(t, 10.4, .4))
        fly = eio(P(t, 11.25, .5))
        if p > 0 and fly < 1:
            x = lerp(80, 760, fly); y = lerp(660, 420, fly); s = lerp(1, .3, fly)
            c.save(); c.translate(x, y); c.scale(s, s); c.rotate(lerp(-3, 20, fly))
            glass(c, 0, 0, 360, 200, 16, a * p * (1 - fly))
            hud_label(c, '口播稿.txt', 24, 40, a * p * (1 - fly))
            for i in range(4):
                lw = [290, 250, 300, 180][i] * eo(P(t, 10.55 + i * .12, .3))
                rrect(c, 24, 70 + i * 30, lw, 12, 6, WHITE, .5 * a * p * (1 - fly))
            c.restore()
        # impact ring
        rp = P(t, 11.75, .6)
        if 0 < rp < 1:
            circle(c, 960, 430, 100 + 700 * eo(rp), LIME, (1 - rp) * .8, stroke=6 * (1 - rp) + 1)
        chip(c, 'MODEL', 640, 260, F('mono', 18), LIME, a * eo(P(t, 12.0, .3)))


# ---------------------------------------------------------------- E: pipeline (dark)
class SPipeline(Scene):
    mode = 'dark'
    rim = 1.0

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .7))
        return mix_xf(full_xf(1.05), dark_xf(.80, 1500), k)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .25)
        hud_label(c, 'PIPELINE · 01', 90, 150, a * eo(P(t, 12.95, .3)))
        text(c, 'AI 制作流水线', 90, 220, F('heavy', 58), WHITE, a * eo(P(t, 13.0, .4)))
        nodes = [(80, 13.15, '01 · VOICE', 'MiniMax', '生成我的声音'),
                 (450, 15.35, '02 · AVATAR', 'HeyGen', '驱动数字人'),
                 (820, 17.3, '03 · OUTPUT', '口播成片', '把内容讲出来')]
        y, w, h = 320, 300, 300
        for i, (x, t0, lab, title, sub) in enumerate(nodes):
            p = eob(P(t, t0, .45), 1.2)
            if p <= 0: continue
            aa = a * clamp(p)
            active = window(t, t0, nodes[i + 1][1] if i < 2 else 99, .1, .3)
            c.save(); c.translate(x + w / 2, y + h / 2); c.scale(lerp(.85, 1, p), lerp(.85, 1, p)); c.translate(-(x + w / 2), -(y + h / 2))
            glass(c, x, y, w, h, 20, aa, edge=LIME, edge_a=.25 + .6 * active)
            if active > 0:
                rrect(c, x, y, w, h, 20, LIME, aa * .5 * active, stroke=3, blur=12)
            hud_label(c, lab, x + 24, y + 42, aa)
            fnt = F('disp', 64) if i < 2 else F('heavy', 50)
            text(c, title, x + 22, y + 120, fnt, WHITE, aa)
            text(c, sub, x + 24, y + 162, F('med', 24), GREY, aa)
            vy = y + 230
            if i == 0:
                wave_bars(c, x + 24, vy, w - 48, 70, t, 32, LIME, aa, amp=.15 + 1.6 * ctx.amp(t) * active + .1)
            elif i == 1:
                # dot face + talking mouth
                fx, fy = x + 70, vy
                circle(c, fx, fy, 42, WHITE, aa * .9, stroke=3)
                circle(c, fx - 14, fy - 10, 4, WHITE, aa)
                circle(c, fx + 14, fy - 10, 4, WHITE, aa)
                m = 3 + 14 * ctx.amp(t) * 3 * active
                rrect(c, fx - 12, fy + 14 - m / 2, 24, max(4, m), 6, LIME, aa)
                for j in range(5):
                    for k in range(3):
                        circle(c, x + 140 + j * 26, vy - 26 + k * 26, 4 + 3 * abs(math.sin(t * 4 + j + k)), BLUE, aa * .8)
            else:
                cx, cy = x + 60, vy
                circle(c, cx, cy, 38, LIME, aa)
                tri = skia.Path(); tri.moveTo(cx - 10, cy - 17); tri.lineTo(cx + 18, cy); tri.lineTo(cx - 10, cy + 17); tri.close()
                c.drawPath(tri, paint(INK, aa))
                pr = eio(P(t, t0 + .2, 1.2))
                rrect(c, x + 120, vy - 5, 150, 10, 5, WHITE, aa * .2)
                rrect(c, x + 120, vy - 5, 150 * pr, 10, 5, LIME, aa)
                text(c, f'{int(pr * 100)}%', x + 120, vy - 18, F('mono', 16), LIME, aa)
            c.restore()
        # connectors
        for i, t0 in enumerate([14.8, 16.9]):
            p = eo(P(t, t0, .45))
            if p <= 0: continue
            x0 = nodes[i][0] + w + 6; x1 = nodes[i + 1][0] - 6; yy = y + h / 2
            pth = skia.Path(); pth.moveTo(x0, yy); pth.lineTo(x1, yy)
            glow_path(c, partial_path(pth, 0, p), LIME, a, 3, 8)
            d = (t * 1.6) % 1
            circle(c, lerp(x0, x1, d), yy, 5, WHITE, a * p)


# ---------------------------------------------------------------- F: most interesting
class SInteresting(Scene):
    def xf(self, t):
        return full_xf(lerp(1.12, 1.3, eio((t - self.t0) / 2.2)), 1060, 330)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .1, .15)
        side_shade(c, .7 * a, 900)
        # speed streaks
        for i in range(14):
            yy = 120 + i * 62
            ph = (t * 2.2 + i * .37) % 1
            line(c, -200 + ph * 900, yy, -200 + ph * 900 + 180, yy, WHITE, .07 * a, 2)
        hud_label(c, 'NEXT · 重点来了', 90, 330, a * eo(P(t, 18.9, .3)))
        f = F('heavy', 118)
        mp = eo(P(t, 19.95, .35))
        x0 = 90 + tw('最', f)
        rrect(c, x0 - 6, 470 - 50, (tw('有意思', f) + 12) * mp, 66, 4, LIME, a)
        slam_text(c, '最有意思', 90, 470, f, t, 19.0, WHITE, a, stagger=.07)
        slam_text(c, '的部分', 90, 610, f, t, 19.55, WHITE, a, stagger=.07)


# ---------------------------------------------------------------- G: analyse refs (dark)
class SAnalyze(Scene):
    mode = 'dark'
    rim = 1.0

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .6))
        return mix_xf(dark_xf(1.0, 1060), dark_xf(.72, 1560), k)

    def ref_card(self, c, x, y, w, h, t, idx, a):
        hues = [(BLUE, VIOLET), (LIME, BLUE), (VIOLET, (255, 90, 140))]
        h1, h2 = hues[idx]
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 14, 14), skia.ClipOp.kIntersect, True)
        sh = skia.GradientShader.MakeLinear([(x, y), (x + w, y + h)], [CI(h1, .8 * a), CI(h2, .55 * a)])
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), skia.Paint(Shader=sh))
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), paint((0, 0, 0), .35 * a))
        if idx == 0:
            for k in range(5):
                bh = 30 + 60 * abs(math.sin(t * 3 + k))
                rrect(c, x + 30 + k * 50, y + h - 30 - bh, 30, bh, 4, WHITE, .8 * a)
        elif idx == 1:
            text(c, 'BIG', x + 24 + 10 * math.sin(t * 2), y + 120, F('disp', 92), WHITE, .9 * a)
        else:
            for k in range(3):
                ang = t * 2 + k * 2.1
                circle(c, x + w / 2 + 60 * math.cos(ang), y + h / 2 + 40 * math.sin(ang), 18, WHITE, .85 * a)
        c.restore()
        rrect(c, x, y, w, h, 14, WHITE, .25 * a, stroke=1.5)
        text(c, f'REF_0{idx + 1}.mp4', x + 12, y + h + 26, F('monor', 15), GREY, a)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .25)
        hud_label(c, 'ANALYZE · 02', 90, 150, a * eo(P(t, 21.0, .3)))
        text(c, '拆解喜欢的视频', 90, 220, F('heavy', 58), WHITE, a * eo(P(t, 21.1, .4)))
        # phase 1/2 — reference cards
        out = eio(P(t, 27.1, .5))
        cw, ch = 300, 170
        for i in range(3):
            p = eob(P(t, 21.6 + i * .18, .5), 1.3)
            if p <= 0: continue
            x = 90 + i * 335; y = 280 + (1 - p) * 80 - out * 40
            self.ref_card(c, x, y, cw, ch, t, i, a * clamp(p) * (1 - out))
        sp = P(t, 23.6, 1.4)
        if 0 < sp < 1 and out < 1:
            sx = lerp(80, 1100, eio(sp))
            line(c, sx, 260, sx, 480, LIME, a, 3, blur=0)
            c.drawRect(skia.Rect.MakeLTRB(80, 270, sx, 460), paint(LIME, .08 * a))
            line(c, sx, 260, sx, 480, LIME, a * .8, 10, blur=10)
            text(c, f'ANALYZING  {int(eio(sp) * 100):3d}%', sx + 12, 262, F('mono', 16), LIME, a)
        # phase 4 — auto timeline replaces cards
        tp = eo(P(t, 27.3, .5))
        if tp > 0:
            x, y, w = 90, 270, 1030
            glass(c, x, y, w, 220, 16, a * tp)
            hud_label(c, 'AUTO EDIT · 自动安排画面', x + 22, y + 38, a * tp)
            tracks = [('V1', [(0, .3), (.32, .55), (.57, 1)], BLUE), ('T1', [(.05, .25), (.4, .52), (.62, .9)], LIME), ('A1', [(.1, .14), (.33, .37), (.58, .62), (.8, .84)], VIOLET)]
            for k, (nm, clips, col) in enumerate(tracks):
                ty = y + 66 + k * 46
                text(c, nm, x + 22, ty + 24, F('mono', 15), GREY, a * tp)
                rrect(c, x + 70, ty, w - 100, 34, 6, WHITE, .05 * a * tp)
                for j, (c0, c1) in enumerate(clips):
                    cp = eob(P(t, 28.9 + (k * 3 + j) * .09, .35), 1.2)
                    if cp <= 0: continue
                    cx0 = x + 70 + c0 * (w - 100); cx1 = x + 70 + c1 * (w - 100)
                    rrect(c, cx0 + 2, ty + 2 - 30 * (1 - cp), cx1 - cx0 - 4, 30, 5, col, a * clamp(cp) * .9)
            ph = x + 70 + (w - 100) * clamp((t - 28.9) / 1.5)
            if t > 28.9:
                line(c, ph, y + 56, ph, y + 210, WHITE, a * tp, 2)
                circle(c, ph, y + 56, 6, WHITE, a * tp)
        # analysis rows
        rows = [(25.0, '节奏', 'RHYTHM'), (25.75, '文字排版', 'TYPOGRAPHY'), (26.35, '动画方式', 'MOTION')]
        for i, (t0, zh, en) in enumerate(rows):
            p = eo(P(t, t0, .4))
            if p <= 0: continue
            x, y, w, h = 90 + (1 - p) * -60, 540 + i * 108, 1030, 92
            glass(c, x, y, w, h, 14, a * p, edge_a=.5 if i == 2 else .3)
            text(c, zh, x + 26, y + 58, F('heavy', 36), WHITE, a * p)
            text(c, en, x + 210, y + 54, F('mono', 15), LIME, a * p, spacing=2)
            vx = x + 420
            if i == 0:
                for k in range(22):
                    beat = (k % 4 == 0)
                    ph = (t * 2.2 - k * .08) % 1
                    hh = (46 if beat else 22) * (0.6 + 0.4 * (1 - ph))
                    rrect(c, vx + k * 26, y + h / 2 - hh / 2, 8, hh, 3, LIME if beat else WHITE, a * p * (.95 if beat else .45))
            elif i == 1:
                ww = [180, 90, 140, 60, 120]
                xx = vx
                for k, wv in enumerate(ww):
                    s = eo(P(t, t0 + .1 + k * .07, .3))
                    rrect(c, xx, y + 22 + (k % 2) * 26, wv * s, 20 if k % 2 == 0 else 14, 4, WHITE if k != 2 else LIME, a * p * (.85 if k != 2 else 1))
                    xx += wv + 14
            else:
                pth = skia.Path(); pth.moveTo(vx, y + h - 18); pth.cubicTo(vx + 200, y + h - 18, vx + 260, y + 18, vx + 560, y + 18)
                c.drawPath(pth, paint(WHITE, a * p * .3, stroke=2))
                glow_path(c, partial_path(pth, 0, eo(P(t, t0 + .1, .7))), LIME, a * p, 3, 8)
                q = (t * .7) % 1
                (px, py), _ = path_pos(pth, eio(q))
                circle(c, px, py, 9, WHITE, a * p)


# ---------------------------------------------------------------- H: where big text/img/anim/sfx
class SDecide(Scene):
    def xf(self, t):
        return full_xf(1.04)

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .25)
        f = F('heavy', 300)
        slam_text(c, '大字', 40, 690, f, t, 30.8, WHITE, a, stagger=.09)
        p = eo(P(t, 31.1, .5))
        if p > 0:
            text(c, '大字', 40 + 14 * p, 690 + 14 * p, f, LIME, a * .55 * p, stroke=3)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .25)
        # image card
        p = eob(P(t, 31.95, .5), 1.5)
        if p > 0:
            c.save(); c.translate(1640, 230); c.rotate(lerp(-25, -6, clamp(p))); c.scale(p, p)
            x, y, w, h = -150, -100, 300, 200
            rrect(c, x - 8, y - 8, w + 16, h + 46, 8, WHITE, a)
            sh = skia.GradientShader.MakeLinear([(0, y), (0, y + h)], [CI((80, 130, 255), a), CI((180, 120, 255), a)])
            rrect(c, x, y, w, h, 2, shader=sh)
            circle(c, x + 220, y + 60, 26, (255, 230, 120), a)
            m = skia.Path(); m.moveTo(x, y + h); m.lineTo(x + 90, y + 90); m.lineTo(x + 150, y + 150); m.lineTo(x + 210, y + 70); m.lineTo(x + w, y + h); m.close()
            c.drawPath(m, paint((20, 30, 60), a))
            text(c, '图片 IMAGE', x, y + h + 30, F('bold', 20), INK, a)
            c.restore()
        # motion path
        p = eo(P(t, 33.5, .5))
        if p > 0:
            pth = skia.Path(); pth.moveTo(1420, 600); pth.cubicTo(1520, 420, 1700, 680, 1820, 470)
            c.drawPath(partial_path(pth, 0, p), paint(WHITE, a * .7, stroke=3))
            q = eio(((t - 33.5) * .8) % 1)
            (px, py), _ = path_pos(pth, q * p)
            c.save(); c.translate(px, py); c.rotate(t * 240)
            rrect(c, -18, -18, 36, 36, 6, LIME, a)
            c.restore()
            chip(c, '动画 MOTION', 1430, 640, F('bold', 22), WHITE, a * p)
        # sfx chip
        p = eob(P(t, 33.95, .4), 1.6)
        if p > 0:
            c.save(); c.translate(1460, 760); c.scale(p, p)
            glass(c, 0, 0, 340, 100, 18, a)
            spk = skia.Path(); spk.moveTo(26, 38); spk.lineTo(40, 38); spk.lineTo(58, 22); spk.lineTo(58, 78); spk.lineTo(40, 62); spk.lineTo(26, 62); spk.close()
            c.drawPath(spk, paint(LIME, a))
            text(c, '音效', 74, 62, F('heavy', 30), WHITE, a)
            wave_bars(c, 150, 50, 170, 50, t, 18, LIME, a)
            c.restore()
        # verdict
        p = eo(P(t, 34.6, .4))
        if p > 0:
            glass(c, 70, 100, 400, 90, 16, a * p)
            circle(c, 120, 145, 26, LIME, a * p)
            ck = skia.Path(); ck.moveTo(107, 146); ck.lineTo(117, 156); ck.lineTo(134, 135)
            c.drawPath(partial_path(ck, 0, eo(P(t, 34.8, .3))), paint(INK, a * p, stroke=5))
            text(c, 'AI 自己判断', 165, 160, F('heavy', 38), WHITE, a * p)


# ---------------------------------------------------------------- I: not just once
class SNotOnce(Scene):
    def xf(self, t):
        return full_xf(1.12)

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .25)
        f = F('num', 520)
        p = eob(P(t, 36.3, .45), 1.4)
        if p > 0:
            c.save(); c.translate(380, 520); c.scale(lerp(1.4, 1, clamp(p)), lerp(1.4, 1, clamp(p))); c.translate(-380, -520)
            text(c, '×1', 110, 780, f, WHITE, a * clamp(p) * lerp(1, .35, P(t, 38.1, .3)))
            c.restore()
        sp = eo(P(t, 37.95, .25))
        if sp > 0:
            line(c, 90, 700, 90 + 560 * sp, 330, LIME, a, 22)
        q = eob(P(t, 38.2, .5), 1.5)
        if q > 0:
            c.save(); c.translate(1560, 520); c.rotate(lerp(-90, 0, clamp(q))); c.scale(q, q)
            text(c, '∞', 0, 170, F('disp', 460), LIME, a, align='c')
            c.restore()

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .2)
        hud_label(c, 'REUSE · 不止用一次', 90, 120, a * eo(P(t, 36.8, .3)))


# ---------------------------------------------------------------- J/K: skill (dark)
class SSkill(Scene):
    mode = 'dark'
    rim = 1.0
    MODS = ['节奏分析', '文字排版', '动画模板', '字幕系统', '音效匹配', '人像分割']

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .6))
        return mix_xf(full_xf(1.12), dark_xf(.72, 1560), k)

    def hexagon(self, c, cx, cy, r, a, t):
        pth = skia.Path()
        for i in range(6):
            ang = math.pi / 6 + i * math.pi / 3 + t * .25
            x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
            pth.moveTo(x, y) if i == 0 else pth.lineTo(x, y)
        pth.close()
        sh = skia.GradientShader.MakeRadial((cx, cy), r, [CI(LIME, .35 * a), CI((10, 14, 24), .95 * a)])
        c.drawPath(pth, skia.Paint(AntiAlias=True, Shader=sh))
        glow_path(c, pth, LIME, a, 4, 16)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .25)
        hud_label(c, 'PACKAGE · 03', 90, 150, a * eo(P(t, 39.0, .3)))
        title = '沉淀成一个 Skill' if t < 45.1 else '以后直接复用'
        tp = eo(P(t, 39.1, .4)) if t < 45.1 else eo(P(t, 45.15, .4))
        text(c, title, 90, 220, F('heavy', 58), WHITE, a * tp)
        cx0, cy0 = 590, 560
        move = eio(P(t, 45.2, .6))
        cx = lerp(cx0, 300, move); cy = cy0; hr = lerp(130, 95, move)
        conv = eio(P(t, 42.6, .9))
        for i, s in enumerate(self.MODS):
            p = eob(P(t, 41.2 + i * .2, .45), 1.4)
            if p <= 0 or conv >= 1: continue
            ang = -math.pi / 2 + i * math.pi / 3 + t * .15
            R = lerp(330, 0, conv)
            x = cx0 + R * math.cos(ang) * 1.25; y = cy0 + R * math.sin(ang) * .78
            f = F('bold', 26)
            cw = tw(s, f) + 36
            c.save(); c.translate(x, y); c.scale(clamp(p) * (1 - conv * .6), clamp(p) * (1 - conv * .6))
            glass(c, -cw / 2, -28, cw, 56, 12, a * clamp(p) * (1 - conv), edge_a=.6)
            text(c, s, 0, 9, f, WHITE, a * clamp(p) * (1 - conv), align='c')
            c.restore()
            if conv < 1 and p > 0:
                line(c, cx0, cy0, x, y, LIME, a * .25 * clamp(p) * (1 - conv), 1.5)
        hp = eob(P(t, 43.3, .55), 1.6)
        if hp > 0:
            for k in range(3):
                rp = P(t, 43.35 + k * .15, .9)
                if 0 < rp < 1:
                    circle(c, cx, cy, hr + 260 * eo(rp), LIME, a * (1 - rp) * .7, stroke=3)
            self.hexagon(c, cx, cy, hr * clamp(hp, 0, 1.2), a, t)
            text(c, 'SKILL', cx, cy + 22 * (hr / 130), F('disp', 64 * hr / 130), WHITE, a * clamp(hp), align='c')
            lp = eo(P(t, 44.3, .4)) * (1 - move)
            text(c, 'video-fx.skill', cx, cy + hr + 52, F('mono', 20), LIME, a * lp, align='c')
            chip(c, '可重复调用', cx, cy + hr + 76, F('bold', 24), LIME, a * lp, align='c')
        # K: emit videos
        for i in range(4):
            t0 = 45.6 + i * .5
            p = eo(P(t, t0, .55))
            if p <= 0: continue
            x = lerp(cx, 520 + i * 150, p); y = lerp(cy, 470 + i * 26 - 60, p)
            s = lerp(.2, 1, p)
            c.save(); c.translate(x, y); c.scale(s, s); c.rotate(lerp(0, -4 + i * 3, p))
            glass(c, 0, 0, 260, 160, 12, a, edge=[BLUE, LIME, VIOLET, LIME][i], edge_a=.8)
            sh = skia.GradientShader.MakeLinear([(0, 0), (260, 120)], [CI([BLUE, LIME, VIOLET, BLUE][i], .55 * a), CI(INK, .2 * a)])
            rrect(c, 10, 10, 240, 110, 8, shader=sh)
            circle(c, 130, 65, 22, WHITE, a * .9)
            tri = skia.Path(); tri.moveTo(123, 54); tri.lineTo(140, 65); tri.lineTo(123, 76); tri.close()
            c.drawPath(tri, paint(INK, a))
            text(c, f'VIDEO_{i + 1:02d}.mp4', 12, 146, F('mono', 15), WHITE, a)
            c.restore()
        n = sum(1 for i in range(4) if t > 45.6 + i * .5 + .3)
        if n:
            text(c, f'×{n}', 520, 800, F('num', 120), LIME, a * eo(P(t, 45.9, .3)))
            text(c, '同一个 Skill 反复出片', 640, 790, F('bold', 28), WHITE, a * eo(P(t, 45.9, .3)))
        sp = eo(P(t, 47.5, .3))
        if sp > 0:
            f = F('heavy', 34)
            chip(c, '不用每次重新设计', 520, 830, f, WHITE, a * sp, INK)
            line(c, 520, 856, 520 + (tw('不用每次重新设计', f) + 28) * eo(P(t, 47.7, .3)), 856, LIME, a, 6)


# ---------------------------------------------------------------- L: 5 steps (dark)
class SSteps(Scene):
    mode = 'dark'
    rim = 1.0
    STEPS = [(48.85, '新的口播', 'INPUT', '丢进一段口播.mp4'),
             (50.95, '理解内容', 'UNDERSTAND', '读懂每一句在讲什么'),
             (51.9, '拆出画面', 'STORYBOARD', '决定每句话配什么画面'),
             (53.8, '文字 + 动画', 'MOTION', '生成对应的字和动效'),
             (55.5, '节奏 + 音效', 'RHYTHM · SFX', '卡点、音效一起补上')]

    def xf(self, t):
        return dark_xf(.72, 1560)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .25)
        hud_label(c, 'WORKFLOW · 04', 90, 120, a * eo(P(t, 48.7, .3)))
        text(c, '一段口播 → 一条成片', 90, 185, F('heavy', 52), WHITE, a * eo(P(t, 48.75, .4)))
        x0, y0, gap = 90, 230, 124
        # spine
        lastp = 0
        for i, (t0, *_r) in enumerate(self.STEPS):
            if t > t0: lastp = i + eo(P(t, t0, .4))
        spine_len = gap * (len(self.STEPS) - 1)
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine_len, WHITE, .12 * a, 3)
        prog = clamp((lastp - 1) / (len(self.STEPS) - 1)) if lastp > 1 else 0
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine_len * prog, LIME, a, 4)
        line(c, x0 + 30, y0 + 52, x0 + 30, y0 + 52 + spine_len * prog, LIME, a * .6, 10, blur=8)
        for i, (t0, zh, en, desc) in enumerate(self.STEPS):
            p = eo(P(t, t0, .45))
            if p <= 0: continue
            nxt = self.STEPS[i + 1][0] if i + 1 < len(self.STEPS) else 99
            act = window(t, t0, nxt, .1, .25)
            y = y0 + i * gap
            circle(c, x0 + 30, y + 52, 16, LIME if act > .1 else (40, 48, 64), a * p)
            if act <= .1:
                ck = skia.Path(); ck.moveTo(x0 + 23, y + 52); ck.lineTo(x0 + 29, y + 58); ck.lineTo(x0 + 38, y + 46)
                c.drawPath(ck, paint(LIME, a * p, stroke=3))
            else:
                circle(c, x0 + 30, y + 52, 16 + 14 * ((t * 1.5) % 1), LIME, a * p * (1 - (t * 1.5) % 1), stroke=2)
            cx = x0 + 70 + (1 - p) * 40
            glass(c, cx, y, 900, 104, 14, a * p, edge_a=.25 + .6 * act)
            text(c, f'{i + 1:02d}', cx + 24, y + 70, F('num', 54), LIME if act > .1 else GREY, a * p)
            text(c, zh, cx + 100, y + 56, F('heavy', 34), WHITE, a * p)
            text(c, en, cx + 102, y + 86, F('mono', 13), LIME, a * p * .9, spacing=1.5)
            text(c, desc, cx + 330, y + 64, F('med', 22), GREY if act < .5 else WHITE, a * p)
            # mini visuals
            vx = cx + 700; vy = y + 52
            aa = a * p
            if i == 0:
                chip(c, '口播.mp4', vx, vy - 20, F('bold', 20), WHITE, aa, INK)
            elif i == 1:
                for k in range(3):
                    lw = [150, 110, 160][k]
                    rrect(c, vx, vy - 26 + k * 20, lw, 10, 5, WHITE, aa * .3)
                    hl = eo(P(t, t0 + .2 + k * .15, .4))
                    rrect(c, vx, vy - 26 + k * 20, lw * hl * [.4, .8, .55][k], 10, 5, LIME, aa)
            elif i == 2:
                for k in range(3):
                    s = eob(P(t, t0 + .1 + k * .12, .4), 1.4)
                    rrect(c, vx + k * 56, vy - 22, 48 * clamp(s), 44, 6, [BLUE, LIME, VIOLET][k], aa * .9)
            elif i == 3:
                for k, ch in enumerate('ABC'):
                    bob = abs(math.sin(t * 6 + k)) * 12 * act
                    text(c, ch, vx + k * 44, vy + 16 - bob, F('disp', 44), LIME if k == 1 else WHITE, aa)
            else:
                wave_bars(c, vx, vy, 170, 50, t, 16, LIME, aa, amp=.3 + 1.4 * ctx.amp(t) * act + .1)


# ---------------------------------------------------------------- M: avatar vs real split
class SSplit(Scene):
    def xf(self, t):
        return full_xf(1.0)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .25)
        dp = eo(P(t, 59.4, .6))
        # divider position sweeps in
        dx = lerp(-20, 1060, eio(P(t, 59.4, .7))) + 30 * math.sin(t * 1.3) * dp
        if dp > 0:
            c.save(); c.clipRect(skia.Rect.MakeLTRB(0, 0, dx, H))
            c.drawRect(skia.Rect.MakeWH(W, H), paint((4, 6, 12), .85 * a))
            g = ctx.lum_grid  # (rows, cols) luminance 0..1
            cs = ctx.cell
            pl = paint(LIME, a); pb = paint(BLUE, a * .9)
            rows, cols = g.shape
            for r in range(rows):
                yy = r * cs + cs / 2
                for q in range(cols):
                    xx = q * cs + cs / 2
                    if xx > dx + cs: break
                    v = g[r, q]
                    rad = v * cs * .55
                    if rad > .8:
                        c.drawCircle(xx, yy, rad, pl if ctx.mask_grid[r, q] > .5 else pb)
            c.restore()
            line(c, dx, 0, dx, H, LIME, a, 3)
            line(c, dx, 0, dx, H, LIME, a * .6, 14, blur=12)
            circle(c, dx, 540, 22, LIME, a)
            text(c, '<>', dx, 549, F('mono', 18), INK, a, align='c')
            chip(c, '数字人 · AVATAR', 70, 90, F('bold', 26), LIME, a * dp)
        rp = eo(P(t, 60.7, .4))
        if rp > 0:
            chip(c, '真人实拍 · LIVE', W - 70, 90, F('bold', 26), WHITE, a * rp, INK, align='r')
        kp = eob(P(t, 61.85, .45), 1.5)
        if kp > 0:
            c.save(); c.translate(1660, 860); c.scale(kp, kp)
            chip(c, '同一套 Skill 都能用', 0, -34, F('heavy', 34), LIME, a, align='c')
            c.restore()


# ---------------------------------------------------------------- N: matte demo
class SMatte(Scene):
    def xf(self, t):
        return full_xf(lerp(1.0, 1.06, eio((t - self.t0) / 6)))

    def rim_amt(self, t):
        return eo(P(t, 65.7, .5)) * window(t, self.t0, self.t1, .01, .3)

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .25)
        d = eo(P(t, 65.6, .6))
        if d > 0:
            c.drawRect(skia.Rect.MakeWH(W, H), paint((3, 5, 10), .72 * d * a))
            gp = paint(LIME, .10 * d * a, stroke=1)
            off = (t * 30) % 60
            for x in range(0, W + 60, 60):
                c.drawLine(x - off, 0, x - off, H, gp)
            for y in range(0, H + 60, 60):
                c.drawLine(0, y, W, y, gp)
        f = F('heavy', 250)
        slam_text(c, '放到身后', 60, 650, f, t, 67.7, LIME, a, stagger=.08, drop=120)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .25)
        corners(c, 40, 40, W - 80, H - 80, 60, WHITE, a * .8 * eo(P(t, 63.2, .4)), 3)
        chip(c, 'CASE · 真人口播', 70, 70, F('bold', 24), WHITE, a * eo(P(t, 63.4, .3)), INK)
        p = eo(P(t, 66.6, .4))
        if p > 0:
            hud_label(c, 'MATTE · 人像分离', 1400, 160, a * p)
            pr = clamp((t - 66.6) / .8)
            text(c, f'EDGE {pr * 100:5.1f}%', 1400, 190, F('mono', 15), WHITE, a * p * .8)


# ---------------------------------------------------------------- O: data viz (dark)
class SData(Scene):
    mode = 'dark'
    rim = 1.0

    def xf(self, t):
        k = eio(P(t, self.t0 + .05, .6))
        return mix_xf(full_xf(1.06), dark_xf(.72, 1560), k)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .25)
        hud_label(c, 'DATA · 05', 90, 150, a * eo(P(t, 69.4, .3)))
        text(c, '数字 → 动态画面', 90, 220, F('heavy', 58), WHITE, a * eo(P(t, 69.5, .4)))
        cards = [(90, 270, 70.4), (610, 270, 71.15), (90, 600, 72.15), (610, 600, 73.8)]
        for i, (x, y, t0) in enumerate(cards):
            p = eob(P(t, t0, .45), 1.3)
            if p <= 0: continue
            aa = a * clamp(p)
            c.save(); c.translate(x + 240, y + 150); c.scale(lerp(.8, 1, clamp(p)), lerp(.8, 1, clamp(p))); c.translate(-(x + 240), -(y + 150))
            glass(c, x, y, 480, 300, 18, aa)
            if i == 0:
                hud_label(c, 'FRAMES · 本片总帧数', x + 24, y + 40, aa)
                v = int(ctx.n_frames * eexp(P(t, t0 + .1, 1.6)))
                text(c, f'{v:,}', x + 24, y + 200, F('num', 150), WHITE, aa)
                text(c, '帧', x + 30 + tw(f'{ctx.n_frames:,}', F('num', 150)), y + 196, F('heavy', 40), LIME, aa)
                rrect(c, x + 24, y + 240, 432 * eexp(P(t, t0 + .1, 1.6)), 8, 4, LIME, aa)
            elif i == 1:
                hud_label(c, 'CHART · 数据', x + 24, y + 40, aa)
                vals = [.35, .55, .42, .7, .62, .95]
                for k, v in enumerate(vals):
                    g = eob(P(t, t0 + .1 + k * .08, .5), 1.3)
                    bh = 190 * v * g
                    rrect(c, x + 40 + k * 70, y + 270 - bh, 44, bh, 6, LIME if k == 5 else (70, 82, 110), aa)
                if t > t0 + .8:
                    text(c, '+95%', x + 400, y + 270 - 190 - 14, F('mono', 18), LIME, aa * eo(P(t, t0 + .8, .3)), align='c')
            elif i == 2:
                hud_label(c, 'KEY POINT · 重点', x + 24, y + 40, aa)
                for k in range(4):
                    rrect(c, x + 24, y + 80 + k * 46, [400, 330, 420, 260][k], 18, 9, WHITE, aa * .18)
                hp = eo(P(t, t0 + .35, .5))
                rrect(c, x + 20, y + 112, 300 * hp, 64, 8, LIME, aa)
                if hp > .5:
                    text(c, '重点放大', x + 36, y + 160, F('heavy', 44), INK, aa * clamp((hp - .5) * 2))
            else:
                hud_label(c, 'MOTION · 动态', x + 24, y + 40, aa)
                cx, cy, r = x + 150, y + 170, 86
                circle(c, cx, cy, r, WHITE, aa * .12, stroke=20)
                rp = eexp(P(t, t0 + .1, 1.2))
                arc = skia.Path(); arc.addArc(skia.Rect.MakeLTRB(cx - r, cy - r, cx + r, cy + r), -90, 359.9 * rp)
                c.drawPath(arc, paint(LIME, aa, stroke=20))
                text(c, f'{int(rp * 100)}%', cx, cy + 16, F('num', 52), WHITE, aa, align='c')
                text(c, '直观', x + 290, y + 160, F('heavy', 52), WHITE, aa)
                text(c, '一眼看懂', x + 290, y + 210, F('med', 24), GREY, aa)
            c.restore()


# ---------------------------------------------------------------- P: manual vs AI
class SManualVsAI(Scene):
    def xf(self, t):
        return full_xf(lerp(1.0, 1.04, eio((t - self.t0) / 6.7)))

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .25, .25)
        side_shade(c, .7 * a, 1000)
        p = eo(P(t, 76.6, .4))
        if p <= 0: return
        x, y, w, h = 70, 240, 600, 470
        glass(c, x, y, w, h, 20, a * p)
        hud_label(c, 'COMPARE · 剪辑方式', x + 28, y + 46, a * p)
        # manual
        p1 = eo(P(t, 78.2, .4))
        if p1 > 0:
            yy = y + 110
            text(c, '手动剪辑', x + 28, yy + 30, F('heavy', 40), WHITE, a * p1)
            chip(c, '一帧一帧', x + 230, yy - 4, F('bold', 20), (90, 100, 125), a * p1, WHITE)
            el = max(0, t - 78.4)
            prog = min(.18, int(el * 6) * .009)
            rrect(c, x + 28, yy + 64, w - 56, 26, 13, WHITE, .1 * a * p1)
            rrect(c, x + 28, yy + 64, (w - 56) * prog, 26, 13, (150, 160, 185), a * p1)
            text(c, f'{prog * 100:4.1f}%', x + w - 28, yy + 30, F('mono', 20), GREY, a * p1, align='r')
            text(c, f'FRAME {int(el * 25 * 0.4):04d} / 2335', x + 28, yy + 124, F('monor', 16), GREY, a * p1)
        p2 = eo(P(t, 80.9, .35))
        if p2 > 0:
            yy = y + 300
            text(c, '交给 AI', x + 28, yy + 30, F('heavy', 40), LIME, a * p2)
            pr = eexp(P(t, 81.3, .6))
            rrect(c, x + 28, yy + 64, w - 56, 26, 13, WHITE, .1 * a * p2)
            rrect(c, x + 28, yy + 64, (w - 56) * pr, 26, 13, LIME, a * p2)
            rrect(c, x + 28, yy + 64, (w - 56) * pr, 26, 13, LIME, a * p2 * .6, blur=12)
            text(c, 'DONE' if pr > .98 else f'{pr * 100:4.1f}%', x + w - 28, yy + 30, F('mono', 20), LIME, a * p2, align='r')


# ---------------------------------------------------------------- Q: this very video (card)
class SThisVideo(Scene):
    mode = 'card'

    def xf(self, t):
        k = eio(P(t, self.t0 + .1, .8))
        s = lerp(1.0, .62, k)
        cx = lerp(960, 960, k); cy = lerp(540, 400, k)
        return (s, cx - 960 * s, cy - 540 * s)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .3, .2)
        k = eio(P(t, self.t0 + .1, .8))
        if k <= 0: return
        s, ox, oy = self.xf(t)
        corners(c, ox - 16, oy - 16, W * s + 32, H * s + 32, 36, LIME, a * k, 3)
        hud_label(c, 'THIS VIDEO · 本片', ox, oy - 34, a * k)
        text(c, 'RENDER · OK', ox + W * s, oy - 24, F('mono', 16), LIME, a * k, align='r')
        # timeline of all scenes
        tp = eo(P(t, 83.0, .5))
        if tp > 0:
            x, y, w = 200, 805, 1520
            text(c, 'TIMELINE', x, y - 16, F('mono', 14), GREY, a * tp)
            total = ctx.scenes[-1].t1
            for i, sc in enumerate(ctx.scenes):
                gp = eo(P(t, 83.0 + i * .04, .3))
                x0 = x + w * sc.t0 / total; x1 = x + w * sc.t1 / total
                col = {'full': (70, 82, 110), 'dark': BLUE, 'card': LIME}[sc.mode]
                rrect(c, x0 + 1.5, y, (x1 - x0 - 3) * gp, 36, 4, col, a * tp * .9)
            for j, (s0, s1, _) in enumerate(ctx.captions):
                xx = x + w * s0 / total
                rrect(c, xx, y + 44, max(2, w * (s1 - s0) / total - 2), 10, 3, WHITE, a * tp * .35)
            for (st_, kind, g) in SFX:
                xx = x + w * st_ / total
                line(c, xx, y + 60, xx, y + 72, LIME, a * tp * .7, 2)
            ph = x + w * t / total
            line(c, ph, y - 10, ph, y + 80, WHITE, a * tp, 2)
            circle(c, ph, y - 10, 6, WHITE, a * tp)
        sp = eo(P(t, 84.7, .4))
        if sp > 0:
            stats = [(f'{len(ctx.scenes)}', '个镜头'), (f'{len(ctx.captions)}', '条字幕'), (f'{len(SFX)}', '个音效'), ('Opus 5.5', '全程制作')]
            xx = 200
            for v, l in stats:
                ww = text(c, v, xx, 930, F('num', 54), LIME, a * sp)
                ww2 = text(c, l, xx + ww + 10, 924, F('med', 22), WHITE, a * sp)
                xx += ww + ww2 + 70


# ---------------------------------------------------------------- R: CTA
class SCTA(Scene):
    def xf(self, t):
        return full_xf(lerp(1.0, 1.08, eio((t - self.t0) / 6.5)))

    def behind(self, c, t, ctx):
        a = window(t, 0, self.t1, .01, .4)
        slam_text(c, '评论区见', 60, 680, F('heavy', 210), t, 91.7, LIME, a, stagger=.07, drop=100)

    def front(self, c, t, ctx):
        a = window(t, self.t0, self.t1, .2, .45)
        items = [(87.5, '① 流程怎么搭'), (89.9, '② 相关提示词'), (90.55, '③ Skill 做法')]
        for i, (t0, s) in enumerate(items):
            p = eob(P(t, t0, .4), 1.5)
            if p <= 0: continue
            y = 150 + i * 92
            c.save(); c.translate(90, y); c.scale(clamp(p, 0, 1.2), clamp(p, 0, 1.2))
            glass(c, 0, 0, 380, 72, 14, a, edge_a=.6)
            text(c, s, 24, 48, F('heavy', 34), WHITE, a)
            c.restore()
        p = eo(P(t, 92.1, .3))
        if p > 0:
            bob = math.sin(t * 8) * 10
            ar = skia.Path(); ar.moveTo(1700, 760 + bob); ar.lineTo(1700, 860 + bob); ar.moveTo(1660, 820 + bob); ar.lineTo(1700, 862 + bob); ar.lineTo(1740, 820 + bob)
            glow_path(c, ar, LIME, a * p, 6, 10)
            text(c, '留言告诉我', 1700, 730, F('heavy', 36), WHITE, a * p, align='c')


def build_scenes():
    S = [SIntro(0, 3.05), SNotFilmed(3.05, 6.5), SNoHands(6.5, 9.7), SOpus(9.7, 12.8),
         SPipeline(12.8, 18.7), SInteresting(18.7, 20.86), SAnalyze(20.86, 30.4),
         SDecide(30.4, 36.05), SNotOnce(36.05, 38.83), SSkill(38.83, 48.6),
         SSteps(48.6, 57.8), SSplit(57.8, 63.1), SMatte(63.1, 69.2), SData(69.2, 75.7),
         SManualVsAI(75.7, 82.4), SThisVideo(82.4, 86.6), SCTA(86.6, 93.4)]
    return S


def register_sfx(scenes):
    SFX.clear()
    for sc in scenes[1:]:
        sfx(sc.t0 - .12, 'whoosh', .8)
    for t in [4.3, 11.72, 30.8, 36.3, 43.35, 67.7, 91.7]:
        sfx(t, 'impact', 1.0)
    for t in [0.2, 2.0, 7.05, 7.45, 9.0, 10.4, 13.15, 15.35, 17.3, 19.95, 21.6, 21.78, 21.96, 25.0, 25.75, 26.35,
              31.95, 33.5, 33.95, 34.6, 38.2, 41.2, 41.4, 41.6, 41.8, 42.0, 42.2, 45.6, 46.1, 46.6, 47.1, 47.5,
              48.85, 50.95, 51.9, 53.8, 55.5, 60.7, 61.85, 63.4, 70.4, 71.15, 72.15, 73.8, 78.2, 80.9, 84.7,
              87.5, 89.9, 90.55, 92.1]:
        sfx(t, 'pop', .7)
    for t in [8.6, 37.95, 47.7]:
        sfx(t, 'swish', .8)
    for t in [23.6, 65.6, 81.3]:
        sfx(t, 'riser', .7)
    for t in [28.9, 59.4]:
        sfx(t, 'glitch', .6)
    sfx(82.5, 'whoosh', .6)
