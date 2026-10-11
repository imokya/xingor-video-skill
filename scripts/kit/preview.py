"""Theme swatch: look at a theme before rendering anything.

    .venv/bin/python SKILL_DIR/scripts/kit/preview.py swatch.png            # the THEME in ./scenes.py
    .venv/bin/python SKILL_DIR/scripts/kit/preview.py swatch.png draft.py   # the THEME in another file

Draws the page background, a headline in the display voice, body text, muted text, an accent keyword, a card on the
surface colour, a subtitle line, the secondary colours, and the contrast report.
"""
import os, sys, importlib.util
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import skia
import kit.theme as KT
from fx import F, text, rrect, paint, circle, line


def swatch(th, path, w=1600, h=900):
    surf = skia.Surface(w, h); c = surf.getCanvas()
    c.drawRect(skia.Rect.MakeWH(w, h), paint(th.bg))
    text(c, th.name, 80, 150, F(th.font('display'), 110), th.ink)
    text(c, '重点关键词', 80, 290, F(th.font('head'), 80), th.accent)
    text(c, '正文 body text · 次要信息', 80, 370, F(th.font('body'), 40), th.ink)
    text(c, '说明文字 muted · label', 80, 430, F(th.font('label'), 30), th.muted, spacing=4)
    rrect(c, 860, 90, 660, 360, 26, th.surface)
    text(c, '卡片标题', 910, 180, F(th.font('head'), 56), th.ink)
    text(c, '卡片正文，', 910, 250, F(th.font('body'), 36), th.ink); text(c, '强调', 1090, 250, F(th.font('body'), 36), th.accent)
    for k, col in enumerate([th.accent, th.accent2, th.wash, th.line, th.muted]):
        circle(c, 940 + k * 100, 360, 34, col)
    rrect(c, 80, 500, 1440, 2, 1, th.line)
    y = 560
    for ln in KT.report(th).split('\n'):
        text(c, ln, 80, y, F('monor', 24), th.ink if '!!' not in ln else th.accent); y += 38
    text(c, '他留下“但愿人长久”', w / 2, h - 50, F(th.font('body'), 46), th.ink, align='c')
    surf.makeImageSnapshot().save(path)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'swatch.png'
    src = sys.argv[2] if len(sys.argv) > 2 else 'scenes.py'
    spec = importlib.util.spec_from_file_location('scenes_for_preview', src); m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.getcwd()); spec.loader.exec_module(m)
    th = KT.resolve(getattr(m, 'THEME', 'neon'))
    swatch(th, out); print(KT.report(th)); print('wrote', out)
