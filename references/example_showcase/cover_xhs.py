"""EXAMPLE — 小红书 3:4 cover: tilted wall of real output frames + bold hook + thin wordmark. Paths are project-local."""
"""小红书 3:4 cover with impact: tilted wall of real outputs + huge headline.
    python cover_xhs.py ../封面_小红书_v2.png"""
import sys
import skia
from PIL import Image

import promo8 as P8
from promo8 import text, tw, paint, rrect, circle, line, CI, INK, WHITE, GREY, ACC
from cover import load, cover_crop

CW, CH = 1080, 1440
P8.W, P8.H = CW, CH


def HF(size, w=800, fam='Lantinghei SC'):
    f = skia.Font(skia.Typeface(fam, skia.FontStyle(w, 5, skia.FontStyle.kUpright_Slant)), size)
    f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); return f


def main(out):
    surf = skia.Surface(CW, CH); c = surf.getCanvas()
    P8.bg_dark(c, 3.0)
    # ---------------- tilted masonry wall of real outputs
    V = lambda n: cover_crop(load(n + '.png', 700), 9 / 16)
    L = lambda n: cover_crop(load(n + '.png', 900), 16 / 9)
    cols = [[('globe', L), ('church', V), ('sdgt2', L), ('silk', L)],
            [('sxd', V), ('taxi', L), ('duck', L), ('sushi', L)],
            [('silk', L), ('river', V), ('car', L), ('globe', L)],
            [('crane', V), ('sushi', L), ('sdgt', L), ('sxd', V)],
            [('car', L), ('church', V), ('duck', L), ('taxi', L)]]
    cw, gap = 300, 26
    c.save(); c.translate(CW / 2, 430); c.rotate(-14); c.translate(-CW / 2, -430)
    x0 = CW / 2 - (len(cols) * cw + (len(cols) - 1) * gap) / 2
    offs = [-260, -60, -340, -150, -420]
    for i, col in enumerate(cols):
        x = x0 + i * (cw + gap) + cw / 2; y = offs[i]
        for name, mk in col:
            img = mk(name); h = cw * img.height() / img.width()
            P8.card(c, img, x, y + h / 2, cw, h, 1, 20)
            y += h + gap
    c.restore()
    # light from the top-right + fade the wall into the headline area
    sh = skia.GradientShader.MakeRadial((CW * .8, 120), 700, [CI(ACC, .22), CI(ACC, 0)])
    c.drawRect(skia.Rect.MakeWH(CW, CH), skia.Paint(Shader=sh))
    sh = skia.GradientShader.MakeLinear([(0, 470), (0, 740)], [CI(INK, 0), CI(INK, 1)])
    c.drawRect(skia.Rect.MakeXYWH(0, 560, CW, CH - 560), skia.Paint(Shader=sh))
    # ---------------- top badges
    f = HF(30, 400, 'Avenir Next'); s = 'xingor video skill'; w = tw(s, f) + 48
    rrect(c, 60, 56, w, 60, 30, INK, .72); rrect(c, 60.5, 56.5, w - 1, 59, 30, ACC, .8, stroke=1.5)
    circle(c, 84, 86, 5, ACC); text(c, s, 98, 97, f, WHITE)
    # ---------------- headline
    fn = HF(92, 200, 'Avenir Next')                                  # thin, tracked wordmark with a cold-metal gradient
    g = skia.GradientShader.MakeLinear([(0, 720), (0, 800)], [CI((255, 255, 255)), CI((222, 232, 248)), CI((160, 184, 222))], [0, .55, 1])
    wx = text(c, 'xingor', 56, 795, fn, WHITE, 1, sp=10, shader=g)
    text(c, 'VIDEO SKILL', 56 + wx + 34, 790, HF(30, 400, 'Avenir Next'), ACC, 1, sp=12)
    text(c, '一句话', 60, 1040, HF(250), WHITE)
    f2 = HF(196); s2 = '剪出大片'; w2 = tw(s2, f2)
    rrect(c, 52, 1084, w2 + 40, 224, 18, ACC)
    text(c, s2, 72, 1262, f2, INK)
    # stats stacked to the right of 一句话
    sx = 60 + tw('一句话', HF(250)) + 36
    for j, (n, u) in enumerate((('5', '种风格'), ('44', '个组件'))):
        yy = 915 + j * 100
        wn = text(c, n, sx, yy, P8.F('disp', 84), WHITE)
        text(c, u, sx + wn + 8, yy - 6, HF(28, 500, 'PingFang SC'), GREY)
    # ---------------- footer
    line(c, 60, 1346, CW - 60, 1346, WHITE, .25, 1)
    text(c, '开源 · Claude Code / Codex / Cursor', 60, 1392, HF(26, 400, 'PingFang SC'), GREY, 1, sp=1)
    text(c, '旅行 · 纪录片 · 国风 · 3D', CW - 60, 1390, HF(28, 500, 'PingFang SC'), GREY, 1, 'r', sp=2)
    P8.vignette(c, .35); P8.grain(c, 0, .7)
    arr = surf.toarray(colorType=skia.kRGBA_8888_ColorType)
    Image.fromarray(arr[:, :, :3]).save(out); print(out, arr.shape)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '../封面_小红书_v2.png')
