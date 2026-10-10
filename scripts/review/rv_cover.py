"""撞色测评封面（橙红底 + 宽体大标题 + 句尾圆点 + 斜放主图卡片 + 标签）
  python rv_cover.py --image 主图.png --t1 Muse --t2 实测 --serif "what can it actually do?" \
      --chips 查资料,写代码,画图,做视频 --left "MUSE  HANDS-ON" --right "5 TASKS · 2026" --ratio 3x4 --out 封面.png
  --ratio 3x4（1080×1440 小红书） | 6x7（1080×1260 视频号） | 4x3（1440×1080 横版）
  --focus 0.6,0.45  主图裁切中心；--tag "文字" 卡片右上角黑标签（可选，别写成广告口吻）
主图可以是视频：--image clip.mp4 --at 3.8（取第 3.8 秒那一帧）
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rv_core import F, FF, BLACK, CORAL, CREAM, rounded

def opt(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d

def wide(s, kind, size, color, sx=1.12):
    f = F(kind, size); l, t, r, b = f.getbbox(s)
    im = Image.new('RGBA', (r - l + 20, b - t + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - l, 10 - t), s, font=f, fill=color)
    return im.resize((int(im.width * sx), im.height), Image.LANCZOS)

def fit(s, kind, size, color, maxw, sx=1.12):
    im = wide(s, kind, size, color, sx)
    while im.width > maxw and size > 60: size -= 6; im = wide(s, kind, size, color, sx)
    return im

def chip(cv, x, y, s, size, bg, fg, anchor='l'):
    f = F('bold', size); w = f.getlength(s) + size * 1.2; h = size * 1.85
    if anchor == 'r': x -= w
    d = ImageDraw.Draw(cv); d.rounded_rectangle([x, y, x + w, y + h], h / 2, fill=bg)
    d.text((x + w / 2, y + h / 2), s, font=f, fill=fg, anchor='mm'); return w

def shadow(cv, x, y, w, h):
    sh = Image.new('RGBA', (w + 160, h + 160), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([80, 104, w + 80, h + 104], 28, fill=(0, 0, 0, 140))
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(30)), (x - 80, y - 80))

src = opt('--image'); at = float(opt('--at', '0'))
if src.lower().endswith(('.mp4', '.mov', '.webm')):
    tmp = '/tmp/_rv_cover_frame.png'
    subprocess.run([FF, '-v', 'error', '-y', '-ss', str(at), '-i', src, '-frames:v', '1', tmp], check=True); src = tmp
main = Image.open(src).convert('RGB')
ratio = opt('--ratio', '3x4'); W, H = {'3x4': (1080, 1440), '6x7': (1080, 1260), '4x3': (1440, 1080)}[ratio]
focus = tuple(float(x) for x in opt('--focus', '0.6,0.45').split(','))
chips = [c for c in opt('--chips', '').split(',') if c]
cv = Image.new('RGBA', (W, H), CORAL + (255,)); d = ImageDraw.Draw(cv)
d.text((86, 72), opt('--left', ''), font=F('mono', 26), fill=BLACK)
d.text((W - 86, 72), opt('--right', ''), font=F('mono', 26), fill=BLACK, anchor='ra')
land = ratio == '4x3'
t1 = fit(opt('--t1', 'Muse'), 'black', 220 if land else 300, BLACK, 560 if land else 900, sx=1.0)
cv.alpha_composite(t1, (70, 170 if land else 130))
t2 = fit(opt('--t2', '实测'), 'heavy', 230 if land else (260 if H < 1300 else 300), BLACK, 470 if land else 640)
y2 = (170 if land else 130) + t1.height - 8; cv.alpha_composite(t2, (76, y2))
r = 28; cx, cy = 76 + t2.width + 40, y2 + t2.height - 44
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CREAM)
if opt('--serif'): d.text((86, y2 + t2.height + 18), opt('--serif'), font=F('serif', 50 if H < 1300 else 56), fill=BLACK)
if land:
    cw, ch = 600, 740; card = rounded(ImageOps.fit(main, (cw, ch), centering=focus), 30).rotate(-3, expand=True, resample=Image.BICUBIC)
    px, py = W - 80 - card.width, (H - card.height) // 2 + 20
else:
    cw = 860 if H < 1300 else 980; ch = int(cw * 9 / 16)
    card = rounded(ImageOps.fit(main, (cw, ch), centering=focus), 30).rotate(-3, expand=True, resample=Image.BICUBIC)
    px, py = W // 2 - card.width // 2, y2 + t2.height + (90 if H < 1300 else 110)
shadow(cv, px + 20, py + 10, cw, ch); cv.alpha_composite(card, (px, py))
if opt('--tag'): chip(cv, px + card.width - 30, py + 10, opt('--tag'), 28, BLACK, CREAM, anchor='r')
x = 86; yc = H - 170 if land else min(H - 140, py + card.height - 70)
for s in chips: x += chip(cv, x, yc, s, 34, CREAM, BLACK) + 14
dd = ImageDraw.Draw(cv); L = 30
for (qx, qy, sx, sy) in [(44, 44, 1, 1), (W - 44, 44, -1, 1), (44, H - 44, 1, -1), (W - 44, H - 44, -1, -1)]:
    dd.line([(qx, qy), (qx + sx * L, qy)], fill=BLACK, width=4); dd.line([(qx, qy), (qx, qy + sy * L)], fill=BLACK, width=4)
cv.convert('RGB').save(opt('--out', f'封面_{ratio}.png')); print('ok', opt('--out', f'封面_{ratio}.png'), W, H)
