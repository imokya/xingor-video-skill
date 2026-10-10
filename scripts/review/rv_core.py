"""flat-review · 撞色测评 — 画面与声音组件（PIL + numpy，无需 skia / 抠像）

所有时间单位都是秒；画面坐标按 1080×1440（3:4）设计。视频号 6:7 由渲染器上下各裁 90 px，
HUD 会自动往里收（set_crop）。场景文件里 `from rv_core import *` 后直接用这些函数。
"""
import glob, json, math, os, re, shutil, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

# ================= 画布 / 配色 =================
W, H, FPS = 1080, 1440, 30
DIAG = math.hypot(W, H)
BLACK = (16, 16, 18); CORAL = (238, 75, 58); CREAM = (241, 237, 228); BLUE = (44, 46, 232)
GREY = (70, 70, 76)
FRINGE = [(150, 90, 255), (60, 200, 255)]          # 圆形转场边缘的色差
CROP = 0                                             # 6:7 时为 90（上下各裁掉的像素）

def set_crop(c):
    global CROP
    CROP = c

# ================= ffmpeg =================
def ffmpeg():
    if os.environ.get('FFMPEG'): return os.environ['FFMPEG']
    if os.path.exists('./ffmpeg'): return os.path.abspath('./ffmpeg')
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    p = shutil.which('ffmpeg')
    if p: return p
    raise SystemExit('找不到 ffmpeg：先跑 setup.sh，或设置环境变量 FFMPEG')
FF = ffmpeg()

# ================= 字体（macOS） =================
def _find(pattern_list):
    for pat in pattern_list:
        hits = sorted(glob.glob(pat))
        if hits: return hits[0]
    return None

_AF = '/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*.asset/AssetData/'
_FONT_FILES = {
    'lanting': _find([_AF + 'Lantinghei.ttc', '/Library/Fonts/Lantinghei.ttc']),
    'pingfang': _find([_AF + 'PingFang.ttc', '/System/Library/Fonts/PingFang.ttc']),
}
FONTS = {   # kind -> (文件, ttc 序号)
    'heavy': (_FONT_FILES['lanting'], 2),                          # 兰亭黑 Heavy：中文大字
    'bold': (_FONT_FILES['pingfang'], 11),                         # 苹方 Semibold：字幕、标签
    'med': (_FONT_FILES['pingfang'], 7),                           # 苹方 Medium：正文
    'black': ('/System/Library/Fonts/Supplemental/Arial Black.ttf', 0),   # 英文大字（只用 ASCII！）
    'serif': ('/System/Library/Fonts/Supplemental/Baskerville.ttc', 2),   # 英文细斜体（不能写中文）
    'mono': ('/System/Library/Fonts/Menlo.ttc', 1),                # HUD 小字（不能写中文）
    'monor': ('/System/Library/Fonts/Menlo.ttc', 0),
}
for k in ('heavy', 'bold', 'med'):
    if not FONTS[k][0]:
        FONTS[k] = ('/System/Library/Fonts/STHeiti Medium.ttc', 0)      # 兜底
_fc = {}
def F(kind, size):
    size = int(size)
    if (kind, size) not in _fc: _fc[kind, size] = ImageFont.truetype(FONTS[kind][0], size, index=FONTS[kind][1])
    return _fc[kind, size]

# ================= 缓动 =================
def clamp(x, a=0, b=1): return max(a, min(b, x))
def P(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def eo(x): return 1 - (1 - x) ** 3
def eexp(x): return 1 if x >= 1 else 1 - 2 ** (-10 * x)
def eob(x, s=1.7): x -= 1; return 1 + (s + 1) * x ** 3 + s * x ** 2
def eio(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2

# ================= 时间线（配音字级时间） =================
class Timeline:
    """rv_align.py 产出的 timeline.json：lines[i] = {text, s, e, words:[{w,s,e}]}"""
    def __init__(self, path):
        self.d = json.load(open(path)); self.lines = self.d['lines']; self.dur = self.d['dur']; self._c = {}
    def ls(self, i): return self.lines[i]['s']
    def le(self, i): return self.lines[i]['e']
    def at(self, i, s, n=0):
        """第 i 句里第 n 次出现 s 的时刻（按字插值；s 可以是多个字）。注意：同一个字前面出现过要用 n 指定。"""
        if i not in self._c:
            txt, ts = '', []
            for w in self.lines[i]['words']:
                core = [c for c in w['w'] if c.strip() and c not in '，。、：；？！,.!?"“”（）()…—']
                for k, c in enumerate(core):
                    txt += c; ts.append(w['s'] + (w['e'] - w['s']) * k / max(1, len(core)))
            self._c[i] = (txt, ts)
        txt, ts = self._c[i]; pos = -1
        for _ in range(n + 1):
            pos = txt.find(s, pos + 1)
            if pos < 0: raise KeyError(f'第 {i} 句里没有第 {n + 1} 个「{s}」：{self.lines[i]["text"]}')
        return ts[pos]
    def find_line(self, prefix):
        for i, l in enumerate(self.lines):
            if l['text'].startswith(prefix): return i
        raise KeyError(prefix)

TL = None          # 渲染器加载后赋值；场景文件用 ls / le / at
def ls(i): return TL.ls(i)
def le(i): return TL.le(i)
def at(i, s, n=0): return TL.at(i, s, n)
def line(prefix): return TL.find_line(prefix)

# ================= 资源 =================
ASSETS = '.'
_img = {}
def img(name):
    """素材图（相对 ASSETS 或绝对路径）"""
    p = name if os.path.isabs(name) else os.path.join(ASSETS, name)
    if p not in _img: _img[p] = Image.open(p).convert('RGB')
    return _img[p]

def rounded(im, r=22):
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], r, fill=255)
    out = im.convert('RGBA'); out.putalpha(m); return out

def shadow(frame, x, y, w, h, a=90):
    sh = Image.new('RGBA', (w + 120, h + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([60, 80, w + 60, h + 80], 22, fill=(40, 30, 20, a))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(24)), (int(x) - 60, int(y) - 60))

def fade(lay, a):
    if a < 1: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * a)))
    return lay

_vid = {}
def video_frames(path, w, h, fps=FPS):
    """把视频解成指定尺寸（cover 裁切）的帧列表"""
    key = (path, w, h)
    if key not in _vid:
        raw = subprocess.run([FF, '-v', 'error', '-i', path, '-vf', f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}',
                              '-r', str(fps), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        n = len(raw) // (w * h * 3)
        _vid[key] = [Image.frombuffer('RGB', (w, h), raw[i * w * h * 3:(i + 1) * w * h * 3]) for i in range(n)]
    return _vid[key]

def video_at(path, w, h, t, loop=True):
    fr = video_frames(path, w, h)
    k = int(max(0, t) * FPS)
    return fr[k % len(fr)] if loop else fr[min(k, len(fr) - 1)]

# ================= 文字 =================
_sc = {}
def sprite(s, kind, size, color, sx=1.0):
    key = (s, kind, size, color, sx)
    if key not in _sc:
        f = F(kind, size); l, t, r, b = f.getbbox(s)
        im = Image.new('RGBA', (r - l + 20, b - t + 20), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10 - l, 10 - t), s, font=f, fill=color)
        if sx != 1.0: im = im.resize((max(1, int(im.width * sx)), im.height), Image.LANCZOS)
        _sc[key] = im
    return _sc[key]

def blur_x(im, length):
    """横向运动模糊"""
    length = int(abs(length))
    if length < 2: return im
    a = np.asarray(im).astype(np.float32)
    n = min(length, 24); acc = np.zeros((a.shape[0], a.shape[1] + length, 4), np.float32)
    for i in range(n):
        o = int(i * length / n); acc[:, o:o + a.shape[1]] += a
    return Image.fromarray((acc / n).clip(0, 255).astype(np.uint8))

def word(frame, s, kind, size, color, x, y, t, t0, sx=1.15, t_out=None, dist=480, from_left=False, stagger=.05):
    """宽体大字逐字滑入（运动模糊 + 压扁回弹），t_out 之后向左甩出。返回末尾 x（放句尾圆点用）"""
    f = F(kind, size); cx = x
    for i, ch in enumerate(s):
        spr = sprite(ch, kind, size, color, sx); adv = f.getlength(ch) * sx
        p = P(t, t0 + i * stagger, .42)
        if p <= 0: cx += adv; continue
        e = eexp(p); e2 = eexp(clamp(p + 1 / (FPS * .42)))
        off = (1 - e) * dist * (-1 if from_left else 1); v = abs(e2 - e) * dist
        if t_out is not None and t >= t_out:
            q = P(t, t_out + i * .025, .32)
            if q >= 1: cx += adv; continue
            off = -(q ** 3) * 1400; v = 3 * q * q * 1400 / (FPS * .32)
        g = blur_x(spr, v * 1.6) if v > 2 else spr
        sq = 1 + .35 * (1 - e)
        if sq > 1.01: g = g.resize((int(g.width * sq), g.height))
        frame.alpha_composite(g, (int(cx + off - (g.width - spr.width) / 2), int(y)))
        cx += adv
    return cx

def text(frame, xy, s, kind, size, color, anchor='la', alpha=1.0):
    if alpha <= 0: return
    if alpha >= 1:
        ImageDraw.Draw(frame).text(xy, s, font=F(kind, size), fill=color, anchor=anchor); return
    lay = Image.new('RGBA', frame.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text(xy, s, font=F(kind, size), fill=tuple(color) + (int(255 * alpha),), anchor=anchor)
    frame.alpha_composite(lay)

def dot(frame, x, y, t, t0, color, r=26):
    """句尾彩色圆点（弹出）"""
    p = eob(P(t, t0, .3))
    if p > 0:
        rr = r * p; ImageDraw.Draw(frame).ellipse([x - rr, y - rr, x + rr, y + rr], fill=color)

def title(frame, t, s, t0, fg, dotc=CORAL, size=170, y=300, t_out=None, from_left=False, x=86):
    """段落大标题：自动缩字号防溢出 + 句尾圆点"""
    f = F('heavy', size)
    while x + f.getlength(s) * 1.12 + 70 > W and size > 80:
        size -= 6; f = F('heavy', size)
    end = word(frame, s, 'heavy', size, fg, x, y, t, t0 - .06, sx=1.12, t_out=t_out, from_left=from_left)
    if dotc and (t_out is None or t < t_out):
        r = max(14, size // 8); dot(frame, end + r + 10, y + size * .93, t, t0 + .4, dotc, r)
    return end

def chip(frame, x, y, s, size, bgc, fgc, t=None, t0=None, anchor='l', kind='bold'):
    """胶囊标签（淡入上浮）。返回宽度"""
    a = 1 if t0 is None else eo(P(t, t0, .25))
    if a <= 0: return 0
    f = F(kind, size); w = f.getlength(s) + size * 1.1; h = size * 1.8
    if anchor == 'r': x -= w
    if anchor == 'c': x -= w / 2
    lay = Image.new('RGBA', frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + w, y + h], h / 2, fill=tuple(bgc) + (255,))
    d.text((x + w / 2, y + h / 2), s, font=f, fill=fgc, anchor='mm')
    frame.alpha_composite(fade(lay, a), (0, int(14 * (1 - a))))
    return w

def sec(frame, t, t0, fg, tag, name, serif=None):
    """左上段落小标签：mono 英文 tag + 中文名 + 右侧英文细斜体"""
    p = eo(P(t, t0, .4))
    text(frame, (90, 186), tag, 'mono', 24, fg, alpha=p)
    text(frame, (90, 222), name, 'bold', 40, fg, alpha=p)
    if serif: text(frame, (W - 90, 232), serif, 'serif', 40, fg, 'ra', alpha=p)

def wrap(s, f, width):
    """按词换行：英文单词不拆，标点不放行首"""
    toks = re.findall(r'[A-Za-z0-9.:\-]+|.', s); lines, cur = [], ''
    for tk in toks:
        if f.getlength(cur + tk) > width and cur and tk not in '，。、）：；！？,.)':
            lines.append(cur); cur = tk.lstrip()
        else: cur += tk
    if cur or not lines: lines.append(cur)
    return lines

# ================= 图形 =================
def iris(frame, cx, cy, r, color):
    """圆形扩张（带紫/青色差边）"""
    if r <= 0: return
    d = ImageDraw.Draw(frame)
    for k, c in enumerate(FRINGE):
        rr = r + (2 - k) * 9; d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=c)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

def check(d, x, y, s, color, width=5):
    d.line([(x, y + s * .5), (x + s * .38, y + s * .85), (x + s, y + s * .1)], fill=color, width=width, joint='curve')

def pointer(frame, t, t0, x0, y0, x1, y1, color):
    p = eo(P(t, t0, .35))
    if p <= 0: return
    d = ImageDraw.Draw(frame)
    d.line([(x0, y0), (x0 + (x1 - x0) * p, y0 + (y1 - y0) * p)], fill=color, width=3)
    if p >= 1: d.ellipse([x1 - 9, y1 - 9, x1 + 9, y1 + 9], fill=color)

def strike(frame, t, t0, x0, x1, y, color, w=8):
    p = eo(P(t, t0, .3))
    if p > 0: ImageDraw.Draw(frame).line([(x0, y), (x0 + (x1 - x0) * p, y)], fill=color, width=w)

def spinner(d, cx, cy, r, t, color):
    a = (t * 400) % 360; d.arc([cx - r, cy - r, cx + r, cy + r], a, a + 270, fill=color, width=5)

def ring(frame, cx, cy, r, t, t0, color, width=6):
    """圈注（弹出）"""
    q = eob(P(t, t0, .3))
    if q > 0:
        rr = r * q; ImageDraw.Draw(frame).ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=color, width=width)

def img_card(frame, name, x, y, w, t, t0, crop=None, r=20, rise=True, max_h=None):
    """截图卡片从下方升起。返回 (x, y, w, h)；crop=(x0,y0,x1,y1) 比例"""
    p = eob(P(t, t0, .55), 1.2)
    if p <= 0: return None
    im = img(name) if isinstance(name, str) else name
    if crop: im = im.crop((int(crop[0] * im.width), int(crop[1] * im.height), int(crop[2] * im.width), int(crop[3] * im.height)))
    h = int(im.height * w / im.width)
    if max_h and h > max_h: im = ImageOps.fit(im, (w, max_h), centering=(.5, 0)); h = max_h
    yy = int(y + (1 - p) * 700) if rise else int(y)
    shadow(frame, x, yy, w, h)
    frame.alpha_composite(rounded(im.resize((w, h), Image.LANCZOS), r), (int(x), yy))
    return (x, yy, w, h)

def tilt_card(frame, im, cx, cy, w, ang, t, t0):
    """斜放的卡片弹出（钩子快剪用）"""
    p = eob(P(t, t0, .38), 1.4)
    if p <= 0: return
    im = img(im) if isinstance(im, str) else im
    h = int(im.height * w / im.width)
    c = rounded(im.convert('RGB').resize((max(2, int(w * p)), max(2, int(h * p))), Image.LANCZOS), 18)
    sh = Image.new('RGBA', (c.width + 120, c.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([60, 84, c.width + 60, c.height + 84], 18, fill=(0, 0, 0, 120))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    a = ang * (1 - .4 * (1 - p))
    sh = sh.rotate(a, expand=True, resample=Image.BICUBIC); c = c.rotate(a, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(sh, (int(cx - sh.width / 2), int(cy - sh.height / 2)))
    frame.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))

def zoom_card(frame, name, x, y, w, h, z, region, r=22):
    """卡片内从全图推到 region=(x0,y0,x1,y1)（比例），z=0..1"""
    im = img(name) if isinstance(name, str) else name
    reg = tuple((0, 0, 1, 1)[i] + (region[i] - (0, 0, 1, 1)[i]) * z for i in range(4))
    c = im.crop((int(reg[0] * im.width), int(reg[1] * im.height), int(reg[2] * im.width), int(reg[3] * im.height)))
    c = ImageOps.fit(c, (w, h))
    shadow(frame, x, y, w, h); frame.alpha_composite(rounded(c, r), (int(x), int(y)))

def big_number(frame, t, t0, value, suffix, x, y, size, color, dec=0, dur=.8):
    """大数字从 0 跳到 value"""
    p = eexp(P(t, t0, dur))
    if p <= 0: return
    text(frame, (x, y), f'{value * p:.{dec}f}{suffix}', 'black', size, color)

def browser(frame, t, box, pages, stops, label='', t_in=None):
    """浏览器窗口里竖向滚动多张页面截图。pages=[图名]；stops=[(时刻, 第几页)]"""
    bx, by, bw, bh = box
    p = eob(P(t, t_in if t_in is not None else stops[0][0] - .5, .55), 1.2)
    if p <= 0: return
    by = by + int((1 - min(p, 1)) * 800)
    d = ImageDraw.Draw(frame)
    shadow(frame, bx, by, bw, bh)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 20, fill=(34, 34, 37))
    for i, c in enumerate([(236, 95, 82), (240, 190, 60), (90, 200, 90)]):
        d.ellipse([bx + 24 + i * 26, by + 18, bx + 40 + i * 26, by + 34], fill=c)
    d.rounded_rectangle([bx + 120, by + 12, bx + bw - 24, by + 40], 14, fill=(52, 52, 56))
    if label: text(frame, (bx + 140, by + 15), label, 'monor', 18, (180, 180, 186))
    cw = bw - 16; vh = bh - 60
    ims = [img(n) for n in pages]; hs = [int(i.height * cw / i.width) for i in ims]
    key = ('browser', tuple(pages), cw)
    if key not in _img:
        col = Image.new('RGB', (cw, sum(hs))); yy = 0
        for i, h in zip(ims, hs): col.paste(i.resize((cw, h), Image.LANCZOS), (0, yy)); yy += h
        _img[key] = col
    tops = [sum(hs[:k]) for k in range(len(hs))]
    off = 0
    for i in range(1, len(stops)):
        off += (tops[stops[i][1]] - tops[stops[i - 1][1]]) * eio(P(t, stops[i][0], .6))
    off = min(off, _img[key].height - vh)
    frame.paste(_img[key].crop((0, int(off), cw, int(off) + vh)), (bx + 8, by + 52))

# ================= 头像（可选） =================
AVATAR = None       # 头像视频/图片路径；None 时不画
_av = {}
def avatar(frame, cx, cy, r, t, ring=None):
    if r < 2 or not AVATAR: return
    if 'frames' not in _av:
        if AVATAR.lower().endswith(('.mp4', '.mov', '.webm')): _av['frames'] = video_frames(AVATAR, 480, 480, 24)
        else: _av['frames'] = [ImageOps.fit(Image.open(AVATAR).convert('RGB'), (480, 480))]
    fr = _av['frames'][int(t * 24) % len(_av['frames'])]
    d = int(r * 2); im = fr.resize((d, d), Image.LANCZOS).convert('RGBA')
    m = Image.new('L', (d * 4, d * 4), 0); ImageDraw.Draw(m).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=255)
    im.putalpha(m.resize((d, d), Image.LANCZOS))
    if ring: ImageDraw.Draw(frame).ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=ring)
    frame.alpha_composite(im, (int(cx - r), int(cy - r)))

# ================= 仿 App 输入框打字 =================
BOX_BG = (42, 42, 45); BOX_TXT = (236, 236, 236); SEND_BLUE = (38, 112, 245)
def inputbox(frame, t, x, y, w, prompt, t_type, t_send, attach=None, t_attach=None, alpha=1.0, yoff=0):
    """深色胶囊输入框：逐字打出 prompt（t_type=(开始,结束)），t_send 时发送键按下。attach=图名 时弹出附件缩略图"""
    if alpha <= 0: return 0
    f = F('med', 30)
    n = int(len(prompt) * clamp((t - t_type[0]) / max(.01, t_type[1] - t_type[0])))
    shown = prompt[:n] if t < t_send else prompt
    TW = w - 90
    full_lines = wrap(prompt, f, TW); lines = wrap(shown, f, TW) if shown else ['']
    att_h = 150 if (attach is not None and t_attach is not None and t >= t_attach) else 0
    h = 34 + len(full_lines) * 46 + 92 + att_h
    lay = Image.new('RGBA', frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y = y + yoff
    d.rounded_rectangle([x, y, x + w, y + h], 44, fill=BOX_BG + (255,), outline=(78, 78, 84, 255), width=2)
    cx0, cy = x + 52, y + h - 52
    d.line([(cx0 - 14, cy), (cx0 + 14, cy)], fill=BOX_TXT, width=3); d.line([(cx0, cy - 14), (cx0, cy + 14)], fill=BOX_TXT, width=3)
    mx = x + w - 150
    d.rounded_rectangle([mx - 8, cy - 18, mx + 8, cy + 4], 8, outline=BOX_TXT, width=3)
    d.arc([mx - 15, cy - 12, mx + 15, cy + 12], 0, 180, fill=BOX_TXT, width=3); d.line([(mx, cy + 12), (mx, cy + 20)], fill=BOX_TXT, width=3)
    press = P(t, t_send, .12) * (1 - P(t, t_send + .12, .15))
    r = 32 * (1 - .15 * press); sx = x + w - 66
    d.ellipse([sx - r, cy - r, sx + r, cy + r], fill=SEND_BLUE)
    d.line([(sx, cy + 13), (sx, cy - 13)], fill=(255, 255, 255), width=4)
    d.line([(sx - 11, cy - 2), (sx, cy - 13), (sx + 11, cy - 2)], fill=(255, 255, 255), width=4)
    if att_h:
        a = eob(P(t, t_attach, .35)); tw, th = int(208 * a), int(117 * a)
        if tw > 4: lay.alpha_composite(rounded(ImageOps.fit(img(attach), (208, 117)), 12).resize((tw, th)), (int(x + 44), int(y + 24)))
    ty = y + 30 + att_h
    for i, ln in enumerate(lines): d.text((x + 44, ty + i * 46), ln, font=f, fill=BOX_TXT)
    if (t < t_send and int(t * 2.5) % 2 == 0) or t_type[0] <= t < t_type[1]:
        lx = x + 44 + f.getlength(lines[-1]); ly = ty + (len(lines) - 1) * 46
        d.rectangle([lx + 3, ly + 2, lx + 6, ly + 38], fill=BOX_TXT)
    frame.alpha_composite(fade(lay, alpha))
    return h

# ================= 动态对比表 =================
def table(frame, t, fg, hl, cols, rows, t_cols, y0=610, colx=(300, 560, 820)):
    """cols=[(主名, 副名)]，t_cols=列名出现时刻；rows=[(行名, [值...], 出现时刻, 高亮列或 None)]，数字会从 0 跳到目标值"""
    d = ImageDraw.Draw(frame)
    for i, (a, b) in enumerate(cols):
        p = eo(P(t, t_cols + i * .1, .35))
        if p <= 0: continue
        text(frame, (colx[i], y0 + 20 * (1 - p)), a, 'heavy', 40, fg, alpha=p)
        text(frame, (colx[i], y0 + 54 + 20 * (1 - p)), b, 'med', 24, fg, alpha=p)
    lp = eo(P(t, t_cols, .6))
    if lp > 0: d.line([(90, y0 + 104), (90 + (W - 180) * lp, y0 + 104)], fill=fg, width=3)
    for r, (name, vals, t0, best) in enumerate(rows):
        t0 -= .05; y = y0 + 130 + r * 98
        p = eo(P(t, t0, .3))
        if p <= 0: continue
        text(frame, (90, y + 14), name, 'bold', 34, fg, alpha=p)
        for i, v in enumerate(vals):
            q = P(t, t0 + .08 + i * .08, .5)
            if q <= 0: continue
            m = re.match(r'(\$?)([\d.]+)(\D*)', v)
            if m and q < 1:
                dec = len(m.group(2).split('.')[1]) if '.' in m.group(2) else 0
                s = f'{m.group(1)}{float(m.group(2)) * eexp(q):.{dec}f}{m.group(3)}'
            else: s = v
            big = bool(m)
            if best == i and q >= 1:
                f = F('mono' if big else 'bold', 36 if big else 32)
                d.rounded_rectangle([colx[i] - 12, y + 4, colx[i] + f.getlength(s) + 12, y + 64], 8, fill=hl)
            text(frame, (colx[i], y + 12), s, 'mono' if big else 'bold', 36 if big else 32, fg, alpha=eo(q) if q < 1 else 1)
        lp = eo(P(t, t0, .5)); d.line([(90, y + 84), (90 + (W - 180) * lp, y + 84)], fill=GREY, width=1)

# ================= HUD / 字幕 =================
HUD = dict(brand='', label='HANDS-ON', tasks=0)
def hud(frame, t, fg, chapter='', task=0, dur=1.0):
    """四角角标 + 左上品牌/右上章节 + 底部时间码/任务进度格/进度线（6:7 时只留进度线）"""
    d = ImageDraw.Draw(frame); L = 28; c = CROP * 2 // 3; cb = CROP + 30 if CROP else 44
    for (x, y, sx, sy) in [(44, 44 + c, 1, 1), (W - 44, 44 + c, -1, 1), (44, H - cb, 1, -1), (W - 44, H - cb, -1, -1)]:
        d.line([(x, y), (x + sx * L, y)], fill=fg, width=3); d.line([(x, y), (x, y + sy * L)], fill=fg, width=3)
    x0 = 80
    if AVATAR: avatar(frame, 96, 82 + c, 17, t); x0 = 124
    if HUD['brand']:
        d.text((x0, 70 + c), HUD['brand'], font=F('mono', 22), fill=fg)
        x0 += F('mono', 22).getlength(HUD['brand']) + 26
    d.text((x0, 70 + c), HUD['label'], font=F('monor', 22), fill=fg)
    if chapter: d.text((W - 80, 70 + c), chapter, font=F('mono', 22), fill=fg, anchor='ra')
    n = HUD['tasks']
    if not c:
        fr = int(t * FPS)
        d.text((80, H - 96), f'00:00:{fr // FPS:02d}:{fr % FPS:02d}', font=F('mono', 22), fill=fg)
        d.text((300, H - 96), f'{FPS} FPS', font=F('monor', 22), fill=fg)
        if n:
            xb = W - 80 - 38 * n
            for i in range(n):
                bx = xb + i * 24
                d.rectangle([bx, H - 92, bx + 15, H - 77], outline=fg, width=2, fill=fg if i < task else None)
            d.text((W - 80, H - 96), f'{task}/{n}', font=F('mono', 22), fill=fg, anchor='ra')
    py = H - CROP - 34 if CROP else H - 58
    d.line([(44, py), (44 + (W - 88) * clamp(t / dur), py)], fill=fg, width=3)

KEYWORDS = []
_PUNCT = '，。：？、,.；！'
def build_cues(tl):
    """按标点把每句切成字幕块；时间取自字级时间"""
    cues = []
    for li, l in enumerate(tl.lines):
        times = []
        for w in l['words']:
            core = [c for c in w['w'] if c not in _PUNCT and c.strip()]
            for k, _ in enumerate(core): times.append(w['s'] + (w['e'] - w['s']) * k / max(1, len(core)))
        if not times: continue
        chunks, cur, idx, start = [], '', 0, times[0]
        for c in l['text']:
            if c in '，。：？；！':
                if cur.strip(): chunks.append((cur.strip(), start))
                cur = ''; continue
            if c.strip() and c not in _PUNCT and c not in '"“”':
                if not cur.strip(): start = times[min(idx, len(times) - 1)]
                idx += 1
            elif not cur.strip(): continue
            cur += c
        if cur.strip(): chunks.append((cur.strip(), start))
        nxt = tl.lines[li + 1]['s'] if li + 1 < len(tl.lines) else tl.dur
        for k, (s, st) in enumerate(chunks):
            en = chunks[k + 1][1] - .04 if k + 1 < len(chunks) else min(l['e'] + .35, nxt - .05)
            cues.append((st - .06, en, s.replace('"', '').replace('“', '').replace('”', '')))
    return cues
CUES = []

def _split_kw(s):
    parts = []; i = 0
    kws = sorted(KEYWORDS, key=len, reverse=True)
    while i < len(s):
        hit = next((k for k in kws if s.startswith(k, i)), None)
        if hit: parts.append((hit, True)); i += len(hit)
        else:
            if parts and not parts[-1][1]: parts[-1] = (parts[-1][0] + s[i], False)
            else: parts.append((s[i], False))
            i += 1
    return parts

def subtitle(frame, t, fg, pill_bg, pill_fg, y=1232):
    """当前字幕块；KEYWORDS 里的词垫色块"""
    for (t0, t1, s) in CUES:
        if not (t0 <= t < t1): continue
        a = min(P(t, t0, .1), 1 - P(t, t1 - .08, .08))
        parts = _split_kw(s); size = 48; f = F('bold', size)
        total = sum(f.getlength(p) + (22 if hi else 0) for p, hi in parts)
        if total > 940:
            size = int(size * 940 / total); f = F('bold', size)
            total = sum(f.getlength(p) + (22 if hi else 0) for p, hi in parts)
        x = (W - total) / 2
        lay = Image.new('RGBA', frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for p, hi in parts:
            w = f.getlength(p)
            if hi:
                d.rounded_rectangle([x, y - 6, x + w + 22, y + size + 18], 10, fill=tuple(pill_bg) + (255,))
                d.text((x + 11, y), p, font=f, fill=pill_fg); x += w + 22
            else:
                d.text((x, y), p, font=f, fill=fg); x += w
        frame.alpha_composite(fade(lay, a))

# ================= 段落引擎 =================
DOTPOS = {}
TR = .5
def render_segments(segs, t, dur):
    """segs=[(开始, 底色, 前景色, 章节, 任务进度, 场景函数, 转场起点)]，转场起点：'c' 中心 / 'b' 底部 / 'dot' 上一段句尾圆点 / 'cut' 硬切"""
    k = max(i for i, s in enumerate(segs) if t >= s[0])
    st, bg, fg, chap, task, fn, org = segs[k]
    if k > 0 and t < st + TR and segs[k - 1][1] != bg and org != 'cut':
        pst, pbg = segs[k - 1][0], segs[k - 1][1]
        frame = Image.new('RGBA', (W, H), pbg + (255,)); segs[k - 1][5](frame, t)
        ox, oy = {'b': (W / 2, H + 100), 'dot': DOTPOS.get('q', (W / 2, H / 2))}.get(org, (W / 2, H / 2))
        iris(frame, ox, oy, (DIAG + 400) * eexp(P(t, st, TR)), bg)
        if t < st + .25: fg, chap, task = segs[k - 1][2], segs[k - 1][3], segs[k - 1][4]
    else:
        frame = Image.new('RGBA', (W, H), bg + (255,)); fn(frame, t)
    hud(frame, t, fg, chap, task, dur)
    if bg == CORAL: subtitle(frame, t, BLACK, BLACK, CREAM)
    else: subtitle(frame, t, fg, CORAL, CREAM)
    if t > dur - .5: frame = Image.blend(frame.convert('RGB'), Image.new('RGB', (W, H), BLACK), P(t, dur - .5, .5))
    return frame.convert('RGB')

def s_dot(frame, t):
    """开场黑场：中心圆点 + 两圈扩散环"""
    d = ImageDraw.Draw(frame)
    r = 22 * eob(P(t, .05, .3)); d.ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], fill=CORAL)
    for k in range(2):
        p = P(t, .15 + k * .15, .55)
        if 0 < p < 1:
            rr = 30 + 300 * eo(p); lay = Image.new('RGBA', frame.size, (0, 0, 0, 0))
            ImageDraw.Draw(lay).ellipse([W / 2 - rr, H / 2 - rr, W / 2 + rr, H / 2 + rr], outline=CREAM + (int(255 * (1 - p)),), width=2)
            frame.alpha_composite(lay)

# ================= 声音 =================
SR = 44100
def read_wav(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return a, w.getframerate()

def pcm(path, sr=SR):
    raw = subprocess.run([FF, '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def loud(vo, target=-13.5, ceil=.89):
    """人声：整体提到目标 RMS，分块限幅压峰值"""
    sp = vo[np.abs(vo) > .01]
    if not len(sp): return vo
    x = vo * 10 ** ((target - 20 * np.log10(np.sqrt(np.mean(sp ** 2)))) / 20)
    B = 128; n = len(x) // B * B
    pk = np.abs(x[:n]).reshape(-1, B).max(1); pk = np.maximum(pk, np.concatenate([pk[1:], pk[-1:]]))
    gain = np.minimum(1, ceil / np.maximum(pk, 1e-6))
    for i in range(1, len(gain)): gain[i] = min(gain[i], gain[i - 1] + .02)
    x[:n] *= np.repeat(gain, B); x[n:] *= gain[-1]
    return np.clip(x, -.98, .98)

class Sfx:
    """合成音效轨：sfx.whoosh(t) / pop(t) / key(t) / typing(a, b) / hit(t) / clip(t, 文件, 音量)"""
    def __init__(self, dur, sr=SR, seed=3):
        self.sr = sr; self.n = int(dur * sr); self.out = np.zeros(self.n, np.float32); self.rng = np.random.default_rng(seed)
    def add(self, t0, sig, g):
        i = int(t0 * self.sr); j = min(self.n, i + len(sig))
        if 0 <= i < self.n: self.out[i:j] += sig[:j - i] * g
    def whoosh(self, t0, d=.45, g=.06):
        k = int(d * self.sr); x = self.rng.standard_normal(k).astype(np.float32); y = np.zeros(k, np.float32)
        for i in range(1, k): y[i] = y[i - 1] + (.02 + .33 * (i / k) ** 1.5) * (x[i] - y[i - 1])
        self.add(t0, y * np.sin(np.linspace(0, np.pi, k)) ** 2 * 3, g)
    def pop(self, t0, f=880, d=.09, g=.05):
        k = int(d * self.sr); tt = np.arange(k) / self.sr
        self.add(t0, np.sin(2 * np.pi * f * tt * (1 + 2 * np.exp(-tt * 60))) * np.exp(-tt * 40), g)
    def key(self, t0, g=.035):
        k = int(.018 * self.sr); self.add(t0, self.rng.standard_normal(k).astype(np.float32) * np.exp(-np.arange(k) / self.sr * 350), g)
    def typing(self, a, b):
        tt = a
        while tt < b: self.key(tt, .035 * (.7 + .6 * self.rng.random())); tt += .07 + .05 * self.rng.random()
    def hit(self, t0, f=55, d=.6, g=.2):
        k = int(d * self.sr); tt = np.arange(k) / self.sr
        self.add(t0, np.sin(2 * np.pi * f * tt * (1 + 1.5 * np.exp(-tt * 30))) * np.exp(-tt * 7), g)
    def clip(self, t0, path, g=1.0, normalize=True):
        a = pcm(path, self.sr)
        if len(a):
            if normalize: a = a / (np.abs(a).max() + 1e-6) * .9
            self.add(t0, a, g)

# ================= 钩子（正片前的快剪预告） =================
class Hook:
    """beats=[dict(key=钩子配音里的字, label=大字, bg, fg, cards=[(图名或可调用(t)->Image, cx, cy, w, 角度, 延迟)])]
       finale=函数(frame, t, hk) 画最后一段；sting=dict(line1='Muse', line2='实测', serif='...')
       cues=[(开始字, 结束字或时刻, 字幕)]"""
    def __init__(self, words_json, wav, beats, finale_key, finale, send_key, sting, cues, v0=.12):
        self.words = json.load(open(words_json)); self.wav = wav; self.v0 = v0
        self.beats = beats; self.finale = finale; self.sting = sting; self.cues_spec = cues
        self.seg = [self.hk(b['key']) - (.12 if i == 0 else .06) for i, b in enumerate(beats)] + [self.hk(finale_key) - .06]
        self.send = self.hk(send_key) + .25
        self.sting_t = self.send + .5
        self.dur = round(self.sting_t + .6, 2)
    def hk(self, ch, n=0):
        k = 0
        for w in self.words:
            if ch in w['w']:
                if k == n: return self.v0 + w['s']
                k += 1
        raise KeyError(f'钩子配音里没有「{ch}」')
    def _bar(self, frame, t, fg):
        n = len(self.beats); x0, x1, y = 90, W - 90, 128 + CROP * 2 // 3; gap = 10
        w = (x1 - x0 - gap * (n - 1)) / n; d = ImageDraw.Draw(frame)
        for i in range(n):
            a, b = self.seg[i], self.seg[i + 1]; p = clamp((t - a) / (b - a)); bx = x0 + i * (w + gap)
            d.rectangle([bx, y, bx + w, y + 5], outline=fg, width=1)
            if p > 0: d.rectangle([bx, y, bx + w * p, y + 5], fill=fg)
    def render(self, t):
        n = len(self.beats)
        i = sum(1 for x in self.seg[1:] if t >= x)
        if t >= self.sting_t: i = n + 1
        if i < n: bg, fg = self.beats[i]['bg'], self.beats[i]['fg']
        elif i == n: bg, fg = CREAM, BLACK
        else: bg, fg = CORAL, BLACK
        frame = Image.new('RGBA', (W, H), bg + (255,))
        if i < n:
            b = self.beats[i]; t0 = self.seg[i]; ty = 190 + CROP // 2
            end = word(frame, b['label'], 'heavy', 230 if len(b['label']) <= 3 else 190, fg, 86, ty, t, t0 - .02, stagger=.035, dist=380)
            dot(frame, min(end + 40, W - 60), ty + 214, t, t0 + .18, CREAM if bg == CORAL else CORAL, 24)
            text(frame, (90, 470 + CROP // 2), f'0{i + 1} / 0{n}', 'mono', 26, fg, alpha=eo(P(t, t0, .2)))
            for (src, cx, cy, w, ang, dl) in b.get('cards', []):
                im = src(t - t0) if callable(src) else src
                tilt_card(frame, im, cx, cy, w, ang, t, t0 + dl)
            self._bar(frame, t, fg)
        elif i == n:
            self.finale(frame, t, self); self._bar(frame, t, BLACK)
            if t >= self.send + .15: iris(frame, W / 2, H / 2, (DIAG + 300) * eexp(P(t, self.send + .15, .45)), CORAL)
        else:
            t0 = self.sting_t; s = self.sting
            mend = word(frame, s['line1'], 'black', 250, BLACK, 86, 420, t, t0 - .12, sx=1.0, dist=460)
            avatar(frame, min(mend + 90, W - 125), 570, 70 * eob(P(t, t0 + .1, .35)), t, ring=BLACK)
            end = word(frame, s['line2'], 'heavy', 250, BLACK, 90, 700, t, t0, from_left=True, dist=460)
            dot(frame, end + 44, 932, t, t0 + .35, CREAM, 28)
            if s.get('serif'): text(frame, (92, 1010), s['serif'], 'serif', 56, BLACK, alpha=eo(P(t, t0 + .3, .35)))
        d = ImageDraw.Draw(frame); L = 28; c = CROP * 2 // 3; cb = CROP + 30 if CROP else 44
        for (x, y, sx, sy) in [(44, 44 + c, 1, 1), (W - 44, 44 + c, -1, 1), (44, H - cb, 1, -1), (W - 44, H - cb, -1, -1)]:
            d.line([(x, y), (x + sx * L, y)], fill=fg, width=3); d.line([(x, y), (x, y + sy * L)], fill=fg, width=3)
        x0 = 80
        if AVATAR: avatar(frame, 96, 82 + c, 17, t); x0 = 124
        if HUD['brand']: d.text((x0, 70 + c), HUD['brand'], font=F('mono', 22), fill=fg); x0 += F('mono', 22).getlength(HUD['brand']) + 26
        d.text((x0, 70 + c), 'PREVIEW', font=F('monor', 22), fill=fg)
        if int(t * 3) % 2 == 0: d.ellipse([W - 92, 74 + c, W - 78, 88 + c], fill=CORAL if bg != CORAL else BLACK)
        d.text((W - 104, 70 + c), 'REC', font=F('mono', 22), fill=fg, anchor='ra')
        for (a, b, txt) in self.cues_spec:
            a = self.hk(a) - .05 if isinstance(a, str) else a
            b = self.hk(b) - .05 if isinstance(b, str) else (self.send + .25 if b is None else b)
            if a <= t < b:
                f = F('bold', 48); w = f.getlength(txt); pill = BLACK if bg == CORAL else CORAL
                d.rounded_rectangle([(W - w) / 2 - 16, 1226, (W + w) / 2 + 16, 1296], 10, fill=pill)
                d.text((W / 2, 1261), txt, font=f, fill=CREAM, anchor='mm')
        return frame.convert('RGB')
    def audio(self, sr=SR):
        a, r = read_wav(self.wav)
        if r != sr: a = pcm(self.wav, sr)
        out = np.zeros(int(self.dur * sr), np.float32); i = int(self.v0 * sr)
        out[i:i + len(a)] += a[:len(out) - i]
        out = loud(out)
        fx = Sfx(self.dur, sr, 7)
        for x in self.seg[1:]: fx.whoosh(x - .12, .35, .06)
        for x in self.seg[:-1]: fx.hit(x + .05, 70, .35, .12)
        fx.whoosh(self.send + .1, .45, .07); fx.hit(self.sting_t, 55, .6, .2)
        return np.clip(out + fx.out, -.98, .98)

# ================= 背景音乐 =================
def mix_bgm(vo, music_path, outro=0.0, bed=-14.0, hook=0.0, sr=SR):
    """音乐循环铺满（去掉原曲结尾淡出、2 秒交叉衔接）；比人声低 |bed| dB，说话时再压 6 dB；钩子段 +3 dB；片尾前 1.5 秒淡出"""
    n = len(vo); m = pcm(music_path, sr)
    rms = np.array([np.sqrt(np.mean(m[i:i + sr] ** 2)) for i in range(0, len(m) - sr, sr)])
    m = m[:int(np.where(rms > rms.max() * .35)[0][-1] * sr)]
    xf = 2 * sr; out = m.copy()
    while len(out) < n:
        ramp = np.linspace(0, 1, xf); out = np.concatenate([out[:-xf], out[-xf:] * (1 - ramp) + m[:xf] * ramp, m[xf:]])
    bgm = out[:n]
    act = np.abs(vo) > .02
    base = np.sqrt(np.mean(vo[act] ** 2)) / np.sqrt(np.mean(bgm ** 2)) * 10 ** (bed / 20)
    win = int(.05 * sr)
    env = np.array([np.max(np.abs(vo[i:i + win])) for i in range(0, n, win)])
    talk = (env > .03).astype(np.float32); duck = np.zeros_like(talk); g = 0.0
    for i, v in enumerate(talk): g = g + (v - g) * (.6 if v > g else .12); duck[i] = g
    t = np.arange(n) / sr
    gain_db = np.repeat(-6 * duck, win)[:n] + np.where(t < hook, 3.0, 0.0)
    gain = base * 10 ** (gain_db / 20)
    main_end = n / sr - outro
    gain *= np.clip(t / .3, 0, 1) * np.clip((main_end - t) / 1.5, 0, 1)
    return np.clip(vo + bgm * gain, -.98, .98)

# ================= 场景文件开头调用 =================
def setup(timeline, assets='.', avatar=None, brand='', label='HANDS-ON', tasks=0, keywords=()):
    """场景文件第一行调用：加载配音时间线、素材目录、头像、HUD 文案、字幕高亮词"""
    global TL, ASSETS, AVATAR, CUES, TL_PATH
    TL = Timeline(timeline); TL_PATH = timeline; ASSETS = assets; AVATAR = avatar
    HUD.update(brand=brand, label=label, tasks=tasks)
    KEYWORDS[:] = list(keywords)
    CUES = build_cues(TL)
    return TL
