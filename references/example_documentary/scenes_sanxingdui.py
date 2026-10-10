"""示例项目：《三星堆》documentary（9:16，27 句旁白，约 2 分 53 秒）

在项目目录（含 img/ cut/ audio/ vo.json sfx/）里运行：
  python <skill>/references/example_documentary/scenes_sanxingdui.py --stills 3 15 90
  python <skill>/references/example_documentary/scenes_sanxingdui.py --music music/188.mp3 --out ../三星堆_成片.mp4
  python <skill>/references/example_documentary/scenes_sanxingdui.py --ratio 3x4 --music music/188.mp3   # 小红书 3:4
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "doc"))
import doc_core as dc
dc.init(os.getcwd(), lead=0.15, gap=0.42, tail=7.0,
        extra={0: 0.5, 2: 0.6, 4: 0.3, 6: 0.3, 9: 0.4, 12: 0.5, 13: 0.3, 17: 0.3, 18: 0.4, 21: 0.5, 23: 0.3, 24: 0.6})
dc.HUD_TAG = "SANXINGDUI · 广汉"
from doc_core import *  # noqa: F401,F403


@lru_cache(None)
@lru_cache(None)
def ghost(kind, w=520, h=200):
    """半透明示意轮廓：象牙 / 礼器（非实物）"""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "ivory":
        top = [(x, h * 0.55 - math.sin(x / w * math.pi) * h * 0.35) for x in np.linspace(0, w, 40)]
        bot = [(x, h * 0.55 - math.sin(x / w * math.pi) * h * 0.35 + lerp(h * 0.28, h * 0.04, x / w)) for x in np.linspace(w, 0, 40)]
        d.polygon(top + bot, fill=(250, 238, 210, 150), outline=(255, 245, 225, 255))
    else:  # 牙璋式礼器的抽象轮廓
        d.polygon([(0, h * 0.42), (w * 0.72, h * 0.32), (w, h * 0.12), (w * 0.94, h * 0.5), (w, h * 0.88), (w * 0.72, h * 0.68), (0, h * 0.58)],
                  fill=(190, 230, 210, 140), outline=(220, 250, 235, 255))
    return im.filter(ImageFilter.GaussianBlur(0.6))


# ================================================================ v2 镜头（开场 5 句）
def v_shot_01(u, D):
    """光缝开场 → 金面人头自黑暗中被顶光照亮"""
    im = bg_grad().copy()
    slit = prog(u, 0.05, 0.9)
    if u < 1.3:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        w_ = W * slit
        d.rectangle((W / 2 - w_ / 2, 758, W / 2 + w_ / 2, 762), fill=(255, 230, 170, int(255 * (1 - prog(u, 0.9, 1.3)))))
        over(im, lay.filter(ImageFilter.GaussianBlur(3)))
        over(im, lay.filter(ImageFilter.GaussianBlur(18)))
    rings(im, u, a=prog(u, 0.8, 2.0) * 0.9)
    im = god_rays2(im, u, W / 2, -260, prog(u, 0.6, 2.2))
    t_face, t_from = at_char(0, "这张脸") - 0.3, at_char(0, "来自") - 0.2
    type_behind(im, "这张脸", 300, W / 2, 400, u, t_face, step=0.14)
    type_behind(im, "来自哪里？", 168, W / 2, 1300, u, t_from, step=0.11)
    rev = prog(u, 0.5, 3.0, ease_io)
    head = cut_sized("gold_mask_2", int(960 * lerp(1.12, 1.0, rev)))
    head = spot(head, lerp(-0.1, 1.3, rev))
    ry = math.sin(u * 0.7) * 6
    head_p = persp(head, ry) if abs(ry) > 0.2 else head
    g = rim_glow("gold_mask_2", head.height)
    put(im, g, W / 2, 900, prog(u, 1.2, 2.6) * (0.8 + 0.2 * math.sin(u * 2)))
    put(im, head_p, W / 2, 900 + math.sin(u * 1.1) * 6, prog(u, 0.4, 1.0))
    particles(im, u, 60, (255, 220, 160), 7, speed=0.8)
    # 观众的猜测：三张悬浮标签
    for k, (txt, x, y) in enumerate([("外星？", 180, 660), ("异域？", 900, 820), ("神话？", 190, 1010)]):
        a = prog(u, 4.3 + k * 0.18, 4.6 + k * 0.18)
        if a > 0:
            fw = int(font(46, BLACK).getlength(txt)) + 70
            glass(im, (x - fw / 2, y - 40 + (1 - a) * 30, x + fw / 2, y + 40 + (1 - a) * 30), a, radius=40)
            put(im, text_img(txt, 46, GOLD_HI, BLACK, shadow=False), x, y + (1 - a) * 30, a)
    hud(im, u, prog(u, 1.5, 2.5))
    over(im, vignette(0.8))
    return im


EYE_L, EYE_R, EAR_R = (0.255, 0.27), (0.745, 0.27), (0.985, 0.22)  # mask_zongmu_pd 抠图内的归一化坐标


def v_shot_02(u, D):
    """纵目面具从景深中飞出 + HUD 标注卡"""
    im = bg_grad().copy()
    rings(im, u + 3, a=0.8)
    k = prog(u, 0.0, 0.9, ease_io)
    hh = int(lerp(300, 640, k))
    cx, cy = W / 2, 820
    obj = cut_sized("mask_zongmu_pd", hh)
    ry = lerp(-28, 0, k) + math.sin(u * 0.8) * 3
    g = rim_glow("mask_zongmu_pd", hh, (140, 230, 200), 22)
    put(im, g, cx, cy, k * 0.9)
    po = persp(obj, ry) if abs(ry) > 0.2 else obj
    put(im, po, cx, cy, k)
    ow, oh = obj.size
    to = lambda nx, ny: (cx - ow / 2 + ow * nx, cy - oh / 2 + oh * ny)
    t_eye, t_ear = at_char(1, "双目") - S(1), at_char(1, "巨耳") - S(1)
    # 双目
    pe = prog(u, t_eye - 0.5, t_eye + 0.3)
    for nx, ny in (EYE_L, EYE_R):
        x, y = to(nx, ny)
        if pe > 0:
            pulse_dot(im, x, y, u, pe, (150, 240, 210))
    xl, yl = to(*EYE_L)
    leader(im, pe, [(xl, yl), (xl - 40, yl - 200), (160, yl - 200)])
    if pe > 0.6:
        glass(im, (70, yl - 330, 470, yl - 210), prog(u, t_eye - 0.1, t_eye + 0.3))
        put(im, text_img("纵目", 50, GOLD_HI, BLACK, shadow=False), 270, yl - 290, prog(u, t_eye, t_eye + 0.3))
        put(im, text_img("眼球外凸 约 16 厘米", 28, PAPER, REG, shadow=False), 270, yl - 240, prog(u, t_eye + 0.1, t_eye + 0.4))
    # 巨耳
    pr = prog(u, t_ear - 0.4, t_ear + 0.4)
    xe, ye = to(*EAR_R)
    if pr > 0:
        pulse_dot(im, xe - 20, ye, u, pr, (150, 240, 210))
    leader(im, pr, [(xe - 20, ye), (xe - 60, ye + 420), (760, ye + 420)])
    if pr > 0.6:
        glass(im, (600, ye + 440, 1010, ye + 560), prog(u, t_ear, t_ear + 0.3))
        put(im, text_img("巨耳", 50, GOLD_HI, BLACK, shadow=False), 805, ye + 480, prog(u, t_ear + 0.1, t_ear + 0.4))
        put(im, text_img("向两侧张开", 28, PAPER, REG, shadow=False), 805, ye + 530, prog(u, t_ear + 0.2, t_ear + 0.5))
    # 宽度标尺
    rp = prog(u, t_ear + 0.6, t_ear + 1.4, ease_io)
    if rp > 0:
        x0, x1 = cx - ow / 2, cx + ow / 2
        yy = cy + oh / 2 + 60
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        a_, b_ = lerp(cx, x0, rp), lerp(cx, x1, rp)
        d.line((a_, yy, b_, yy), fill=GOLD_HI + (255,), width=3)
        d.line((a_, yy - 14, a_, yy + 14), fill=GOLD_HI + (255,), width=3)
        d.line((b_, yy - 14, b_, yy + 14), fill=GOLD_HI + (255,), width=3)
        over(im, lay)
        put(im, text_img("宽 138 厘米 · 高 66 厘米", 34, GOLD_HI, BOLD), cx, yy + 44, prog(u, t_ear + 1.0, t_ear + 1.4))
    particles(im, u, 40, (170, 240, 220), 21, speed=0.6)
    hud(im, u + 5)
    over(im, vignette(0.75))
    return im


def v_shot_03(u, D):
    """四川定位 + 年份 → 金属片名"""
    cut_t = at_char(2, "三星堆") - S(2) - 0.15
    im = bg_grad().copy()
    rings(im, u + 6, a=0.7)
    # 面具缩成上方卡片
    k = prog(u, 0.0, 0.8, ease_io)
    if u < cut_t:
        float_obj(im, "mask_zongmu_pd", int(lerp(640, 380, k)), W / 2, lerp(820, 560, k), u, light=1.0, rim=True, rim_a=0.6)
    if u < cut_t + 0.6:
        a = prog(u, 0.4, 0.9) * (1 - prog(u, cut_t + 0.1, cut_t + 0.6))
        glass(im, (90, 900, 520, 1300), a)
        glass(im, (560, 900, 990, 1300), a)
        # 左卡：定位雷达
        if a > 0.02:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            cx, cy = 305, 1070
            for kk in range(3):
                ph = (u * 0.9 + kk / 3) % 1
                r = 20 + ph * 130
                d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GOLD_HI + (int(200 * (1 - ph) * a),), width=3)
            d.line((cx - 150, cy, cx + 150, cy), fill=GOLD + (int(80 * a),), width=1)
            d.line((cx, cy - 130, cx, cy + 130), fill=GOLD + (int(80 * a),), width=1)
            d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=CINNABAR + (int(255 * a),))
            over(im, lay)
            put(im, text_img("四川 · 广汉", 44, PAPER, BLACK, shadow=False), 305, 1240, a)
            n = int(3000 * prog(u, 0.6, cut_t - 0.2, lambda x: 1 - (1 - min(1, max(0, x))) ** 3))
            metal_put(im, f"{n:,}", 110, 775, 1060, a)
            put(im, text_img("年 · 距今约", 34, PAPER, REG, shadow=False), 775, 1170, a)
            put(im, text_img("商代晚期", 34, GOLD_HI, BOLD, shadow=False), 775, 1235, a)
    else:
        v = u - cut_t
        a = prog(v, 0.0, 0.4)
        # 「三星堆」打在面具背后，面具从上方落回中央挡住大字的下半部
        type_behind(im, "三星堆", 330, W / 2, 610, v, 0.0, step=0.16, alpha=0.95)
        m = prog(v, 0.2, 1.0, ease_io)
        float_obj(im, "mask_zongmu_pd", int(lerp(380, 560, m)), W / 2, lerp(560, 950, m), u, light=1.0, rim=True, rim_a=0.8)
        chars_in(im, "青铜纵目面具", 56, W / 2, 1300, v, 0.6, step=0.06, color=GOLD_HI, idx=BOLD, spacing=12)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lw = 360 * prog(v, 0.5, 1.1, ease_io)
        d.line((W / 2 - lw, 1370, W / 2 + lw, 1370), fill=GOLD + (220,), width=2)
        over(im, lay)
    hud(im, u + 10)
    over(im, vignette(0.75))
    return im


CAROUSEL = ["head_17a", "sxd_585", "head_19a", "head_2b", "head_5a", "head_22c"]


def v_shot_04(u, D):
    """为什么铸成这样：青铜人头 3D 旋转木马"""
    im = bg_grad().copy()
    rings(im, u + 9, cx=W / 2, cy=880, a=0.6)
    n = len(CAROUSEL)
    rot = u * 0.55 + 0.4
    items = []
    for i, name in enumerate(CAROUSEL):
        ang = rot + i * 2 * math.pi / n
        z = math.cos(ang)  # 1=最前
        x = W / 2 + math.sin(ang) * 400
        y = 880 - z * 40
        s = 0.55 + 0.45 * (z + 1) / 2
        items.append((z, name, x, y, s, ang))
    for z, name, x, y, s, ang in sorted(items):
        light = 0.35 + 0.65 * (z + 1) / 2
        obj = cut_sized(name, int(700 * s))
        obj = lit(obj, light)
        ry = -math.degrees(math.sin(ang)) * 0.5
        obj = persp(obj, ry)
        if z > 0.7:
            put(im, rim_glow(name, int(700 * s)), x, y, (z - 0.7) / 0.3 * 0.8)
        put(im, obj, x, y, prog(u, 0.0, 0.6))
    chars_in(im, "为什么", 96, W / 2, 300, u, 0.4, step=0.1, color=GOLD_HI)
    put(im, text_img("把一张脸，铸成这个样子？", 46, PAPER, BOLD, spacing=4), W / 2, 420, prog(u, 0.9, 1.4))
    particles(im, u, 40, (230, 210, 170), 41, speed=0.6)
    hud(im, u + 14)
    over(im, vignette(0.75))
    return im


FAN = [("tree_full_sa", "神树", 0.5, 0.4), ("tree_bird_1", "神鸟", 0.55, 0.45), ("figure_a", "巨人", 0.5, 0.2)]


@lru_cache(None)
def photo_card(name, title, fx, fy, w=400, h=560):
    pic = cover(load(name), 1.0, fx, fy, (w, h - 90)).convert("RGBA")
    card = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 34, 20 + w, 34 + h), 26, fill=(0, 0, 0, 200))
    card = Image.alpha_composite(card, sh.filter(ImageFilter.GaussianBlur(14)))
    body = Image.new("RGBA", (w, h), (18, 30, 30, 255))
    body.paste(pic, (0, 0))
    d = ImageDraw.Draw(body)
    d.text((w / 2, h - 46), title, font=font(52, BLACK), fill=GOLD_HI, anchor="mm")
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 26, fill=255)
    body.putalpha(m)
    card.paste(body, (20, 20), body)
    ImageDraw.Draw(card).rounded_rectangle((20, 20, 20 + w - 1, 20 + h - 1), 26, outline=GOLD + (255,), width=3)
    return card


def v_shot_05(u, D):
    """三张卡片扇形展开 → 第一张冲向镜头"""
    im = bg_grad().copy()
    rings(im, u + 12, cy=900, a=0.6)
    fan = prog(u, 0.3, 1.4, ease_io)
    zoom = prog(u, D - 1.2, D, ease_io)
    order = [2, 1, 0]  # 先画后面的
    for i in order:
        name, title, fx, fy = FAN[i]
        ang = lerp(0, (i - 1) * 16, fan)
        x = W / 2 + lerp(0, (i - 1) * 290, fan)
        y = 920 + lerp(0, abs(i - 1) * 50, fan)
        card = photo_card(name, title, fx, fy)
        if i == 0 and zoom > 0:
            continue
        a = prog(u, 0.0 + i * 0.12, 0.4 + i * 0.12) * (1 - zoom)
        ry = math.sin(u * 0.9 + i) * 8
        c2 = persp(card, ry).rotate(-ang, Image.BICUBIC, expand=True)
        put(im, c2, x, y, a)
    if zoom > 0:
        name, title, fx, fy = FAN[0]
        card = photo_card(name, title, fx, fy)
        s = lerp(1.0, 3.2, zoom)
        put(im, card.rotate(lerp(16, 0, zoom), Image.BICUBIC, expand=True), lerp(W / 2 - 290, W / 2, zoom), lerp(970, 900, zoom), 1.0, s)
    put(im, text_img("一同出土的东西", 62, GOLD_HI, BLACK, spacing=8), W / 2, 330, prog(u, 0.2, 0.7) * (1 - zoom))
    hud(im, u + 18)
    over(im, vignette(0.7))
    return im


# ---------------------------------------------------------------- 6 神树升起 + 标尺 + 神鸟
def v_shot_06(u, D):
    im = stage(u, 20)
    im = god_rays2(im, u, 470, -300, prog(u, 0.3, 1.5) * 0.8)
    th = 1280
    cy = rise_obj(im, "tree_full_sa", th, 450, 880, u, 0.0, 1.5, (190, 220, 170))
    top, bot = 880 - th / 2, 880 + th / 2
    p = prog(u, 0.6, lt(5, "九只") - 0.2, ease_io)
    if p > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        x = 860
        yt = lerp(bot, top, p)
        d.line((x, bot, x, yt), fill=GOLD_HI + (255,), width=4)
        for k in range(21):
            yy = lerp(bot, top, k / 20)
            if yy >= yt:
                d.line((x - (16 if k % 5 == 0 else 8), yy, x, yy), fill=GOLD_HI + (200,), width=2)
        d.line((x - 30, yt, x + 30, yt), fill=GOLD_HI + (255,), width=4)
        over(im, lay)
        metal_put(im, f"{3.96 * p:.2f}", 64, x - 110, yt + 4, 1.0)      # 读数放在标尺顶端左侧
        put(im, text_img("米", 30, PAPER, BOLD), x - 20, yt + 8, 1.0)
    tb = lt(5, "九只") - 0.3
    k = prog(u, tb, tb + 0.8, ease_io)
    if k > 0:
        bx, by = lerp(1250, 800, k), lerp(300, 1150, 1) + 0
        by = 1120
        put(im, rim_glow("tree_bird_1", 360, (150, 230, 200)), bx, by, k * 0.8)
        put(im, cut_sized("tree_bird_1", 360), bx, by + math.sin(u * 2) * 8, k)
        metal_put(im, "× 9", 110, 800, 1360, prog(u, tb + 0.5, tb + 0.9), scale=1.2 - 0.2 * prog(u, tb + 0.5, tb + 0.9))
    particles(im, u, 50, (210, 230, 200), 61, speed=0.7)
    return finish(im, u, 20)


FIG_HANDS = [(0.26, 0.055), (0.86, 0.115)]


def v_shot_07(u, D):
    im = stage(u, 24, cy=700)
    im = god_rays2(im, u, 540, -300, prog(u, 0.2, 1.4) * 0.8)
    fh = 1300
    cy = rise_obj(im, "figure_a", fh, 540, 900, u, 0.0, 1.6, (230, 200, 140))
    fw = cut_sized("figure_a", fh).width
    th = lt(6, "双手") - 0.2
    pa = prog(u, th, th + 0.4)
    if pa > 0:
        for nx, ny in FIG_HANDS:
            pulse_dot(im, 540 - fw / 2 + fw * nx, cy - fh / 2 + fh * ny, u, pa)
    ta = lt(6, "空无") - 0.2
    chip(im, "手中空无一物", 800, 420, prog(u, ta, ta + 0.35), 36)
    stat_card(im, 820, 1260, 360, 150, "青铜大立人", "通高约 2.6 米", prog(u, 1.2, 1.6))
    particles(im, u, 40, (230, 210, 170), 71, speed=0.6)
    return finish(im, u, 24)


def v_shot_08(u, D):
    """神树结构线"""
    im = stage(u, 28, rings_a=0.5)
    th, cx, cyc = 1300, 470, 880
    obj = lit(cut_sized("tree_full_sa", th), 0.45)
    put(im, obj, cx, cyc)
    t_tier, t_br, t_bird, t_drag = lt(7, "三层"), lt(7, "每层"), lt(7, "鸟立"), lt(7, "一条龙")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    top, bot = cyc - th / 2 + 60, cyc + th / 2 - 80
    trunk = prog(u, t_tier - 0.8, t_tier)
    d.line((cx, bot, cx, lerp(bot, top, trunk)), fill=GOLD_HI + (230,), width=6)
    tiers = [lerp(top, bot, f) for f in (0.12, 0.38, 0.62)]
    birds = []
    for k, ty in enumerate(tiers):
        a = prog(u, t_tier + k * 0.3, t_tier + 0.4 + k * 0.3)
        if a > 0:
            d.ellipse((cx - 20, ty - 20, cx + 20, ty + 20), outline=GOLD_HI + (int(255 * a),), width=5)
        for j, side in enumerate([-1, 1, 0]):
            b = prog(u, t_br + (k * 3 + j) * 0.12, t_br + 0.4 + (k * 3 + j) * 0.12)
            if b <= 0:
                continue
            span = 250 - k * 30
            ex = cx + side * span if side else cx + 70
            ey = ty + 150 if side else ty + 90
            pts = [(lerp(cx, ex, s_), ty - 70 * math.sin(math.pi * s_) + (ey - ty) * s_ ** 2) for s_ in np.linspace(0, b, 24)]
            d.line(pts, fill=GOLD_HI + (230,), width=4)
            birds.append(pts[-1])
    ba = prog(u, t_bird, t_bird + 0.6)
    if ba > 0:
        for k, (bx, by) in enumerate(birds):
            r = 13 + 5 * math.sin(u * 6 + k)
            d.ellipse((bx - r, by - r - 18, bx + r, by + r - 18), fill=(255, 230, 160, int(240 * ba)))
    da = prog(u, t_drag, t_drag + 1.8, ease_io)
    if da > 0:
        pts = [(cx + 60 * math.sin(s_ * 10), lerp(top + 30, bot, s_)) for s_ in np.linspace(0, da, 90)]
        d.line(pts, fill=(255, 180, 100, 240), width=8)
    over(im, lay)
    over(im, lay.filter(ImageFilter.GaussianBlur(10)))
    rows = [("3", "层树枝", t_tier), ("9", "根树枝", t_br + 0.6), ("9", "只神鸟", t_bird), ("1", "条龙", t_drag)]
    for k, (num, txt, t0) in enumerate(rows):
        a = prog(u, t0, t0 + 0.4)
        if a > 0:
            y = 520 + k * 190
            glass(im, (760 + (1 - a) * 80, y - 75, 1020 + (1 - a) * 80, y + 75), a)
            metal_put(im, num, 84, 820 + (1 - a) * 80, y, a)
            put(im, text_img(txt, 32, PAPER, BOLD, shadow=False), 925 + (1 - a) * 80, y, a)
    return finish(im, u, 28)


def v_shot_09(u, D):
    """沟通天地"""
    im = stage(u, 32, rings_a=0.0)
    rings(im, u, cy=330, a=0.55, spin=10)
    rings(im, u + 3, cy=1420, a=0.55, spin=10)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    a = prog(u, 0.3, 1.5)
    ImageDraw.Draw(lay).rectangle((W / 2 - 50, 0, W / 2 + 50, H), fill=(255, 225, 160, int(80 * a)))
    over(im, lay.filter(ImageFilter.GaussianBlur(46)))
    float_obj(im, "tree_full_sa", 1150, W / 2, 880, u, light=0.85, rim_a=0.7)
    particles(im, u, 70, GOLD_HI, 91, speed=3.0, area=(W / 2 - 150, 0, W / 2 + 150, H))
    metal_put(im, "天", 150, W / 2, 230, prog(u, 0.5, 1.0), scale=1.3 - 0.3 * prog(u, 0.5, 1.0))
    metal_put(im, "地", 150, W / 2, 1420, prog(u, 0.9, 1.4), scale=1.3 - 0.3 * prog(u, 0.9, 1.4))
    return finish(im, u, 32)


def v_shot_10(u, D):
    """无法确定 · 声音听不见了"""
    im = stage(u, 36)
    card = card_img("tree_1c", 760, 960, lerp(1.1, 1.3, ease(u / D)), 0.5, 0.55)
    put_card(im, card, W / 2, 800, prog(u, 0.0, 0.5), ry=math.sin(u * 0.7) * 10, rot=-2)
    t0 = lt(9, "讲述")
    amp = 1 - prog(u, t0, D - 0.6)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    pts = [(x, 1380 + amp * 70 * math.sin(x / 24 + u * 9) * math.sin((x - 120) / 840 * math.pi) * (0.6 + 0.4 * math.sin(x / 70 + u * 3)))
           for x in range(120, 961, 5)]
    d.line(pts, fill=GOLD_HI + (int(110 + 140 * amp),), width=4)
    over(im, lay)
    over(im, lay.filter(ImageFilter.GaussianBlur(8)))
    chip(im, "神话？无法确定", W / 2, 210, prog(u, 0.4, 0.8), 40)
    return finish(im, u, 36)


FIG_CARDS = [("figure_1", "长衣", 0.5, 0.45, "纹饰繁复的长衣"), ("figure_2", "赤脚", 0.5, 0.45, "赤脚 · 立于高台"), ("figure_5", "双手", 0.5, 0.45, "双手一上一下")]


def v_shot_11(u, D):
    im = stage(u, 40)
    float_obj(im, "figure_a", 760, 150, 1080, u, light=0.5, rim_a=0.4)
    times = [0.2, lt(10, "赤脚") - 0.2, lt(10, "双手") - 0.2]
    for k, ((name, key, fx, fy, txt), t0) in enumerate(zip(FIG_CARDS, times)):
        a = prog(u, t0, t0 + 0.6, ease_io)
        if a <= 0:
            continue
        card = card_cached(name, 600, 800, 1.15, fx, fy, title=txt)
        settle = [(-6, 590, 760), (3, 620, 820), (-2, 600, 880)][k]
        rot = lerp(25, settle[0], a)
        x = lerp(1300, settle[1], a)
        y = settle[2]
        dim = 1 - 0.35 * prog(u, times[k + 1], times[k + 1] + 0.4) if k < 2 else 1
        put_card(im, card, x, y, min(1, a * 1.4) * dim, ry=lerp(-30, 0, a), rot=rot)
    return finish(im, u, 40)


RINGS_B = [(0.24, 0.42), (0.61, 0.67)]


def fig_b_card(u, D, w=900, h=1180, s0=1.1, s1=1.45, fx=(0.45, 0.55), fy=(0.5, 0.6), dark=1.0):
    p = ease_io(u / D)
    s, cx, cy = lerp(s0, s1, p), lerp(*fx, p), lerp(*fy, p)
    src = load("figure_b")
    card = card_img("figure_b", w, h, s, cx, cy, dark=dark)
    x0, y0, k = cover_box(src.width, src.height, w, h, s, cx, cy)
    to = lambda nx, ny: ((nx * src.width - x0) * k + 20, (ny * src.height - y0) * k + 20)
    return card, to, k * src.width


def v_shot_12(u, D):
    """双手成环，里面是空的"""
    im = stage(u, 44)
    card, to, sw = fig_b_card(u, D)
    lay = card.copy()
    d = ImageDraw.Draw(lay)
    for k, (nx, ny) in enumerate(RINGS_B):
        x, y = to(nx, ny)
        a = prog(u, 0.7 + k * 0.4, 1.3 + k * 0.4)
        r = 0.065 * sw
        if a > 0:
            d.arc((x - r, y - r * 0.6, x + r, y + r * 0.6), -90, -90 + 360 * a, fill=GOLD_HI + (255,), width=7)
            d.ellipse((x - r * 0.5, y - r * 0.3, x + r * 0.5, y + r * 0.3), fill=(255, 230, 170, int(110 * a)))
    put_card(im, lay, W / 2, 840, prog(u, 0, 0.4), ry=math.sin(u * 0.6) * 4)
    t0 = lt(11, "空的") - 0.1
    metal_put(im, "空", 170, W / 2, 230, prog(u, t0, t0 + 0.3), scale=1.4 - 0.4 * prog(u, t0, t0 + 0.3))
    return finish(im, u, 44)


def v_shot_13(u, D):
    """象牙？礼器？存疑"""
    im = stage(u, 48)
    card, to, sw = fig_b_card(u, D, w=740, h=960, s0=1.45, s1=1.5, fx=(0.55, 0.56), fy=(0.6, 0.61), dark=0.7)
    t1, t2, t3 = lt(12, "象牙"), lt(12, "礼器"), lt(12, "争论")
    lay = card.copy()
    x, y = to(*RINGS_B[1])
    a1 = prog(u, t1 - 0.2, t1 + 0.3) * (1 - prog(u, t2 - 0.4, t2 - 0.1))
    a2 = prog(u, t2 - 0.1, t2 + 0.4) * (1 - prog(u, t3 - 0.3, t3))
    for kind, a in (("ivory", a1), ("ritual", a2)):
        if a > 0:
            g = ghost(kind).rotate(-18, Image.BICUBIC, expand=True)
            put(lay, g, x, y, a * 0.9)
    put_card(im, lay, W / 2, 900, 1.0)
    chip(im, "象牙？", 300, 310, a1, 46)
    put_card(im, card_cached("ivory_tusk", 380, 250, 1.3, 0.55, 0.3, title="象牙"), 790, 320, a1, rot=4)
    chip(im, "礼器？", W / 2, 310, a2, 46, (190, 240, 220))
    put(im, text_img("（示意轮廓）", 26, (200, 185, 160), REG), W / 2, 1450, max(a1, a2))
    sa = prog(u, t3, t3 + 0.2)
    if sa > 0:
        put(im, seal_img("存疑"), W / 2, 380, sa, 1.7 - 0.7 * sa)
    return finish(im, u, 48)


def pit_mouth(base, a, cy=1300, w=760, glow=True):
    if a <= 0.01:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.polygon([(W / 2 - w / 2, cy - 60), (W / 2 + w / 2, cy - 60), (W / 2 + w / 2 - 70, cy + 120), (W / 2 - w / 2 + 70, cy + 120)],
              fill=(6, 8, 8, int(230 * a)), outline=GOLD_HI + (int(255 * a),))
    over(base, lay)
    if glow:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse((W / 2 - w / 2, cy - 90, W / 2 + w / 2, cy - 30), fill=(255, 200, 120, int(120 * a)))
        over(base, g.filter(ImageFilter.GaussianBlur(30)))


def v_shot_14(u, D):
    """器物坠入坑口：连成故事"""
    im = stage(u, 52)
    pit_mouth(im, prog(u, 0.2, 0.7))
    objs = [("mask_zongmu_pd", 300, 250, 560), ("tree_full_sa", 760, 560, 760), ("figure_a", 820, 860, 760)]
    for k, (name, h, x, y) in enumerate(objs):
        t0 = 1.5 + k * 0.5
        f = prog(u, t0, t0 + 1.1, lambda x_: min(1, max(0, x_)) ** 2)
        if f >= 1:
            continue
        s = lerp(1.0, 0.25, f)
        cx, cy = lerp(x, W / 2 + (k - 1) * 120, f), lerp(y, 1290, f)
        put(im, rim_glow(name, h), cx, cy, 0.6 * prog(u, k * 0.15, 0.5 + k * 0.15) * (1 - f), s)
        put(im, cut_sized(name, h), cx, cy + math.sin(u * 1.3 + k) * 6 * (1 - f), prog(u, 0.0 + k * 0.15, 0.4 + k * 0.15) * (1 - prog(u, t0 + 0.9, t0 + 1.1)), s)
    pit_mouth(im, 0)
    metal_put(im, "处境", 120, W / 2, 1050, prog(u, D - 1.6, D - 1.0))
    return finish(im, u, 52)


def v_shot_15(u, D):
    """1986 · 两座器物坑"""
    im = stage(u, 56)
    a = prog(u, 0.05, 0.3)
    metal_put(im, "1986", 220, W / 2, 300, a, shine_p=prog(u, 0.4, 1.4, lambda x: min(1, max(0, x))), scale=1.6 - 0.6 * a)
    card = card_img("excavation_2", 660, 860, lerp(1.05, 1.15, ease(u / D)), 0.5, 0.45, src=sepia("excavation_2"))
    put_card(im, card, 420, 920, prog(u, 0.4, 0.9), rot=lerp(-12, -4, prog(u, 0.4, 1.2, ease_io)), ry=6)
    m = prog(u, lt(14, "两座") - 0.3, lt(14, "两座") + 0.2)
    if m > 0:
        glass(im, (690, 760, 1020, 1180), m)
        put(im, text_img("广汉 · 三星堆", 30, PAPER, BOLD, shadow=False), 855, 810, m)
        for k, (lab, yy) in enumerate((("一号坑", 930), ("二号坑", 1060))):
            ak = prog(u, lt(14, "两座") + k * 0.3, lt(14, "两座") + 0.4 + k * 0.3)
            d = ImageDraw.Draw(im)
            if ak > 0:
                d.rectangle((730, yy - 40, 800, yy + 40), outline=GOLD_HI, width=3)
                pulse_dot(im, 765, yy, u, ak)
                put(im, text_img(lab, 38, GOLD_HI, BLACK, shadow=False), 900, yy, ak)
        put(im, text_img("（位置示意）", 22, (190, 175, 150), REG, shadow=False), 855, 1150, m)
    put(im, text_img("1986 年发掘现场（展板翻拍）", 24, (210, 195, 165), REG), 420, 1390, prog(u, 1.0, 1.5))
    return finish(im, u, 56)


def v_shot_16(u, D):
    """面具、神树残件、青铜人像、象牙"""
    im = stage(u, 60)
    card = card_img("pit_2", 980, 760, lerp(1.25, 1.4, ease(u / D)), lerp(0.4, 0.6, ease_io(u / D)), 0.5)
    put_card(im, card, W / 2, 860, prog(u, 0, 0.5), ry=math.sin(u * 0.5) * 5)
    put(im, text_img("二号器物坑（展板照片）", 28, PAPER, REG), W / 2, 450, prog(u, 0.3, 0.8))
    tags = [("面具", 230, 300), ("神树残件", 560, 230), ("青铜人像", 820, 330), ("象牙", 330, 1300)]
    for txt, x, y in tags:
        t0 = lt(15, txt) - 0.2
        chip(im, txt, x, y if txt != "象牙" else 1300, prog(u, t0, t0 + 0.35), 40)
    return finish(im, u, 60)


@lru_cache(None)
def crack_paths(seed=3):
    rnd = random.Random(seed)
    paths = []
    for k in range(7):
        x, y = rnd.uniform(140, 940), rnd.uniform(520, 1200)
        ang = rnd.uniform(0, 2 * math.pi)
        pts = [(x, y)]
        for i in range(14):
            ang += rnd.uniform(-0.7, 0.7)
            x += math.cos(ang) * 36; y += math.sin(ang) * 36
            pts.append((x, y))
        paths.append(pts)
    return paths


def v_shot_17(u, D):
    """破碎 · 灰烬 · 烧损"""
    im = stage(u, 64)
    card = card_img("pit_1", 960, 820, lerp(1.3, 1.45, ease(u / D)), 0.62, 0.45, dark=0.9)
    put_card(im, card, W / 2, 860, prog(u, 0, 0.5), ry=math.sin(u * 0.5) * 4)
    cp = prog(u, 0.3, lt(16, "灰烬"), ease_io)
    if cp > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for pts in crack_paths():
            n = max(2, int(len(pts) * cp))
            d.line(pts[:n], fill=(10, 8, 6, 230), width=4)
            d.line([(x + 2, y + 2) for x, y in pts[:n]], fill=(255, 210, 160, 70), width=1)
        over(im, lay)
    ea = prog(u, lt(16, "灰烬") - 0.3, lt(16, "灰烬") + 0.6)
    red_glow(im, u, ea * 0.8)
    particles(im, u, int(70 * ea) + 5, (190, 180, 165), 171, speed=0.9)
    for txt, x, y in (("破碎", 260, 300), ("灰烬", 540, 230), ("烧损", 820, 300)):
        t0 = lt(16, txt) - 0.2
        chip(im, txt, x, y, prog(u, t0, t0 + 0.35), 42)
    return finish(im, u, 64)


def v_shot_18(u, D):
    """技术 · 材料 · 人力"""
    im = stage(u, 68, cy=820)
    ry = math.sin(u * 0.6) * 10
    hh = 1150
    obj = persp(cut_sized("head_gold", hh), ry)
    put(im, rim_glow("head_gold", hh), 350, 860, 0.8 * prog(u, 0, 0.6))
    put(im, obj, 350, 860 + math.sin(u * 1.1) * 6, prog(u, 0, 0.5))
    rows = [("技术", "复杂的铸造技术"), ("材料", "铜、锡、铅与黄金"), ("劳作", "许多人的长期劳作")]
    for k, (key, sub) in enumerate(rows):
        t0 = lt(17, key) - 0.3
        stat_card(im, 800, 560 + k * 250, 400, 190, {"技术": "技术", "材料": "材料", "劳作": "人力"}[key], sub, prog(u, t0, t0 + 0.45))
    return finish(im, u, 68)


def v_shot_19(u, D):
    """为什么被埋进土坑"""
    im = stage(u, 72, rings_a=0.4)
    pit_mouth(im, prog(u, 0.0, 0.5), cy=1230, w=820)
    a = prog(u, 0.1, 0.35)
    metal_put(im, "？", 380, W / 2, 760, a, shine_p=prog(u, 0.5, 1.6, lambda x: min(1, max(0, x))), scale=1.6 - 0.6 * a)
    particles(im, u, 90, (150, 118, 86), 191, speed=1.6)
    return finish(im, u, 72)


@lru_cache(None)
def soil_tex(w, h, kind):
    rng = np.random.default_rng({"bronze": 1, "ivory": 2, "soil": 3}[kind])
    base = {"bronze": (34, 44, 40), "ivory": (52, 42, 32), "soil": (112, 80, 52)}[kind]
    arr = np.ones((h, w, 3)) * np.array(base) + rng.normal(0, 9, (h, w, 3))
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if kind == "ivory":
        d = ImageDraw.Draw(im)
        for _ in range(22):
            x, y = rng.uniform(-40, w), rng.uniform(14, h - 14)
            L = rng.uniform(120, 240)
            d.line([(x + s_ * L, y - math.sin(s_ * math.pi) * 16) for s_ in np.linspace(0, 1, 12)], fill=(234, 222, 194), width=int(rng.uniform(8, 13)))
    return im


SECTION_HEADS = ["head_19a", "head_2b", "head_15a", "head_22c", "head_5a", "sxd_585", "head_17a"]


def v_shot_20(u, D):
    """土坑剖面：器物 → 象牙 → 填土（示意）"""
    im = stage(u, 76, rings_a=0.3)
    x0, x1, top, bot = 110, 880, 560, 1300
    glass(im, (x0 - 40, top - 80, x1 + 40, bot + 60), 1.0)
    d = ImageDraw.Draw(im)
    d.line([(x0, top), (x0 + 80, bot), (x1 - 80, bot), (x1, top)], fill=GOLD, width=3)
    xat = lambda yy: (lerp(x0, x0 + 80, (yy - top) / (bot - top)), lerp(x1, x1 - 80, (yy - top) / (bot - top)))
    layers = [("bronze", "器物", 250), ("ivory", "象牙", 170), ("soil", "填土", 320)]
    y = bot
    for kind, key, hh in layers:
        t0 = lt(19, key) - 0.4
        a = prog(u, t0, t0 + 0.7, ease_io)
        yt = y - hh
        if a > 0:
            l1, r1 = xat(yt); l2, r2 = xat(y)
            tex = soil_tex(int(r1 - l1) + 2, hh, kind)
            m = Image.new("L", tex.size, 0)
            ImageDraw.Draw(m).polygon([(0, 0), (r1 - l1, 0), (r2 - l1, hh), (l2 - l1, hh)], fill=int(255 * min(1, a * 1.4)))
            drop = int((1 - a) * -300)
            im.paste(tex, (int(l1), int(yt + drop)), m)
            if kind == "bronze":
                for j, name in enumerate(SECTION_HEADS):
                    fj = prog(u, t0 + j * 0.08, t0 + 0.6 + j * 0.08, lambda x_: min(1, max(0, x_)) ** 2)
                    if fj > 0:
                        hx = lerp(l2 + 60, r2 - 60, j / (len(SECTION_HEADS) - 1))
                        hy = lerp(top - 300, y - 90 - (j % 2) * 40, fj)
                        put(im, cut_sized(name, 150).rotate(90 if j % 2 else -80, Image.BICUBIC, expand=True), hx, hy, 1.0)
            put(im, text_img(key, 44, GOLD_HI, BLACK), x1 + 10, yt + hh / 2 + drop, prog(u, t0 + 0.5, t0 + 0.9), anchor="lm")
        y = yt
    put(im, text_img("器物坑堆积 · 示意", 40, PAPER, BOLD, spacing=6), W / 2, 420, prog(u, 0.1, 0.5))
    return finish(im, u, 76)


def v_shot_21(u, D):
    """仪式"""
    im = stage(u, 80)
    card = card_img("altar", 940, 1060, lerp(1.15, 1.3, ease(u / D)), 0.55, 0.4, dark=0.85)
    im2 = im.copy()
    put_card(im2, card, W / 2, 860, prog(u, 0, 0.5), ry=math.sin(u * 0.5) * 6, rot=-1.5)
    im2 = god_rays2(im2, u, 560, -200, prog(u, 0.2, 1.4))
    chip(im2, "推测 · 有组织的仪式", W / 2, 220, prog(u, lt(20, "仪式") - 0.4, lt(20, "仪式")), 40)
    put(im2, text_img("三星堆博物馆 · 祭坛复原雕塑", 26, PAPER, REG), W / 2, 1420, prog(u, 0.6, 1.0))
    return finish(im2, u, 80)


def v_shot_22(u, D):
    """仪式为了什么"""
    im = stage(u, 84)
    float_obj(im, "head_14b", 1050, W / 2, 900, u, light=0.7, rim_a=0.6)
    qs = [("仪式为了什么？", lt(21, "仪式") - 0.2, 0), ("为何不再使用？", lt(21, "为什么") - 0.2, math.pi)]
    for txt, t0, ph in qs:
        a = prog(u, t0, t0 + 0.4)
        ang = u * 0.6 + ph
        x, y = W / 2 + math.cos(ang) * 330, 900 + math.sin(ang) * 120
        chip(im, txt, x, y, a, 40)
    t3 = lt(21, "仍然")
    metal_put(im, "？", 200, W / 2, 260, prog(u, t3, t3 + 0.3), scale=1.4 - 0.4 * prog(u, t3, t3 + 0.3))
    return finish(im, u, 84)


@lru_cache(None)
def tree_cut_pieces(th=1300, cols=4, rows=7):
    obj = cut_sized("tree_full_sa", th)
    w, h = obj.size
    rnd = random.Random(11)
    pcs = []
    for r in range(rows):
        for c in range(cols):
            box = (int(c * w / cols), int(r * h / rows), int((c + 1) * w / cols), int((r + 1) * h / rows))
            pc = obj.crop(box)
            if pc.getchannel("A").getbbox() is None:
                continue
            ang = rnd.uniform(0, 2 * math.pi)
            pcs.append((pc, box, math.cos(ang) * rnd.uniform(500, 900), math.sin(ang) * rnd.uniform(600, 1000), rnd.uniform(-90, 90), rnd.uniform(0, 0.6)))
    return obj, pcs


def v_shot_23(u, D):
    """修复：碎片拼回神树"""
    cut_t = lt(22, "一点点") - 0.9
    im = stage(u, 88)
    if u < cut_t + 0.4:
        a = prog(u, 0, 0.5) * (1 - prog(u, cut_t, cut_t + 0.4))
        card = card_img("restoration", 900, 700, lerp(1.05, 1.15, ease(u / max(0.1, cut_t))), 0.5, 0.5)
        put_card(im, card, W / 2, 850, a, ry=math.sin(u * 0.6) * 6)
        put(im, text_img("三星堆文物保护与修复馆", 30, PAPER, REG), W / 2, 1260, a)
    if u >= cut_t:
        v = u - cut_t
        obj, pcs = tree_cut_pieces()
        ox, oy = W / 2 - obj.width / 2, 880 - obj.height / 2
        done = True
        for pc, (x0, y0, x1, y1), dx, dy, rot, delay in pcs:
            k = 1 - prog(v, 0.3 + delay, 1.9 + delay, ease_io)
            done = done and k <= 0
            piece = pc.rotate(rot * k, Image.BILINEAR, expand=True) if abs(rot * k) > 0.3 else pc
            put(im, piece, ox + (x0 + x1) / 2 + dx * k, oy + (y0 + y1) / 2 + dy * k, min(1, (1 - k) * 3 + 0.2))
        if done:
            f = prog(v, 2.6, 3.0) * (1 - prog(v, 3.0, 3.8))
            put(im, rim_glow("tree_full_sa", 1300, (255, 220, 150)), W / 2, 880, f)
    particles(im, u, 40, GOLD_HI, 231)
    return finish(im, u, 88)


def v_shot_24(u, D):
    """仰头看见神树"""
    im = stage(u, 92, rings_a=0.4, cy=400)
    th = 1750
    p = prog(u, 0, D, ease_io)
    cy = lerp(450, 1100, p)
    im = god_rays2(im, u, 540, -300, 0.9)
    put(im, rim_glow("tree_full_sa", th, (230, 220, 170)), W / 2, cy, 0.7)
    put(im, cut_sized("tree_full_sa", th), W / 2, cy)
    particles(im, u, 60, GOLD_HI, 241, speed=0.8)
    return finish(im, u, 92)


def v_shot_25(u, D):
    """三千多年前仰望它的人"""
    im = bg_grad().copy()
    im = Image.eval(im, lambda v: int(v * 0.7))
    rnd = random.Random(5)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(140):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 1100)
        tw = 0.4 + 0.6 * abs(math.sin(u * rnd.uniform(0.5, 2) + i))
        r = rnd.uniform(1, 3)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 240, 210, int(200 * tw)))
    over(im, lay)
    put(im, lit(cut_sized("tree_full_sa", 1300), 0.16), 620, 900)
    fig = lit(cut_sized("figure_a", 560), 0.08)
    put(im, fig, 230, 1300, prog(u, 0.6, 1.4))
    particles(im, u, 40, (230, 210, 170), 251, speed=0.5)
    over(im, vignette(0.9))
    return im


def v_shot_26(u, D):
    """回到那张脸"""
    im = stage(u, 100, rings_a=0.8, cy=820)
    s = lerp(1.0, 1.35, prog(u, 0, D, ease_io))
    float_obj(im, "mask_zongmu_pd", 620, W / 2, 820, u, scale=s, rim_a=0.8)
    return finish(im, u, 100)


def v_shot_27(u, D):
    """片尾"""
    im = stage(u, 104, rings_a=0.6, cy=820)
    light = lerp(1.0, 0.1, prog(u, 0.0, 4.6))
    float_obj(im, "gold_mask_2", 1000, W / 2, 900, u, light=light, rim_a=light)
    a = prog(u, 4.6, 5.6)
    metal_put(im, "三星堆", 190, W / 2, 860, a, shine_p=prog(u, 5.2, 6.4, lambda x: min(1, max(0, x))), spacing=26, scale=1.15 - 0.15 * a)
    chars_in(im, "古蜀 · 距今约三千年", 42, W / 2, 1040, u, 5.4, step=0.05, color=PAPER, idx=REG, spacing=8)
    put(im, text_img("图片：Wikimedia Commons（CC0 / CC 授权）· 音效：Mixkit", 22, (170, 155, 130), REG), W / 2, 1820, prog(u, 6.0, 6.8))
    fade = prog(u, D - 1.2, D)
    if fade > 0:
        im = Image.blend(im, Image.new("RGB", (W, H), (0, 0, 0)), fade)
    over(im, vignette(0.8))
    return im




# ================================================================ 音效时间表（Mixkit 编号, 峰值对齐时刻, 音量）
def sfx_events():
    """(素材编号, 峰值对齐的时刻, 音量)"""
    A = lambda k: SPANS[k][0]
    ev = []
    # 1 金面人头
    ev += [(790, 1.25, 0.55), (788, 1.25, 0.6), (498, 0.15 + 2.6, 0.4), (2350, 4.35, 0.35)]
    for i in range(3):   # 打字：这张脸
        ev.append((3005, at_char(0, "这张脸") - 0.3 + i * 0.14 + 0.03, 0.22))
    for i in range(5):   # 打字：来自哪里？
        ev.append((3005, at_char(0, "来自") - 0.2 + i * 0.11 + 0.03, 0.2))
    # 2 纵目面具飞出 + 标注
    a = A(1)
    t_eye, t_ear = at_char(1, "双目"), at_char(1, "巨耳")
    ev += [(1143, a + 0.85, 0.55), (3120, t_eye - 0.45, 0.35), (3005, t_eye - 0.05, 0.4),
           (3120, t_ear - 0.35, 0.35), (3005, t_ear + 0.05, 0.4), (3120, t_ear + 0.65, 0.3)]
    # 3 定位卡 → 金属片名
    a = A(2)
    cut_t = at_char(2, "三星堆") - 0.15
    ev += [(3005, a + 0.45, 0.35), (3005, a + 0.6, 0.3), (3120, a + 0.5, 0.3), (788, cut_t + 0.05, 0.45)]
    for i in range(3):   # 打字：三星堆
        ev.append((1485 if i == 2 else 3005, cut_t + i * 0.16 + 0.04, 0.5 if i == 2 else 0.28))
    # 4 旋转木马
    a = A(3)
    ev += [(1486, a + 0.4, 0.4), (498, a + 0.45, 0.35)]
    # 5 扇形卡片 → 冲进神树
    a, b = SPANS[4]
    ev += [(3005, a + 0.1, 0.35), (3005, a + 0.22, 0.32), (3005, a + 0.34, 0.3), (1143, b - XF - 0.1, 0.5)]
    return ev + sfx_events_rest()



def sfx_events_rest():
    A = lambda k: SPANS[k][0]
    ev = []
    ev += [(1143, A(5) + 1.2, 0.45), (3120, A(5) + 0.7, 0.3), (2350, at_char(5, "九只") + 0.4, 0.4)]
    ev += [(1143, A(6) + 1.4, 0.45), (3005, at_char(6, "双手"), 0.35), (3005, at_char(6, "空无"), 0.35), (3005, A(6) + 1.3, 0.3)]
    for key in ("三层", "每层", "鸟立", "一条龙"):
        ev.append((3120, at_char(7, key) - 0.1, 0.32))
    ev += [(788, A(8) + 0.9, 0.35), (2350, A(8) + 0.6, 0.3)]
    ev += [(1486, A(9) + 0.3, 0.3), (498, at_char(9, "讲述"), 0.35)]
    for key in ("长衣", "赤脚", "双手"):
        ev.append((1143, A(10) + (0.4 if key == "长衣" else at_char(10, key) - A(10) - 0.2 + 0.4), 0.3))
    ev += [(3120, A(11) + 0.8, 0.3), (1485, at_char(11, "空的") + 0.05, 0.45)]
    ev += [(3005, at_char(12, "象牙"), 0.35), (3005, at_char(12, "礼器"), 0.35), (788, at_char(12, "争论") + 0.15, 0.4)]
    ev += [(1486, A(13) + 1.4, 0.35), (498, A(13) + 2.3, 0.35)]
    ev += [(2908, A(14) + 0.25, 0.55), (3120, at_char(14, "两座"), 0.3)]
    for key in ("面具", "神树残件", "青铜人像", "象牙"):
        ev.append((3005, at_char(15, key) - 0.05, 0.32))
    for key in ("破碎", "灰烬", "烧损"):
        ev.append((3005, at_char(16, key) - 0.05, 0.32))
    for key in ("技术", "材料", "劳作"):
        ev.append((3120, at_char(17, key) - 0.15, 0.3))
    ev += [(788, A(18) + 0.3, 0.45), (498, A(18) + 0.35, 0.4)]
    for key in ("器物", "象牙", "填土"):
        ev.append((1143, at_char(19, key) + 0.2, 0.3))
    ev += [(2350, A(20) + 0.6, 0.3)]
    ev += [(498, at_char(21, "仍然"), 0.35)]
    ev += [(1486, at_char(22, "一点点") - 0.4, 0.4), (788, at_char(22, "一点点") + 2.1, 0.4)]
    ev += [(790, A(23) + 2.0, 0.3)]
    ev += [(1486, A(25) + 0.5, 0.25)]
    ev += [(790, A(26) + 4.7, 0.4), (1485, A(26) + 4.75, 0.5), (788, A(26) + 4.75, 0.45)]
    return ev


SHOTS = [v_shot_01, v_shot_02, v_shot_03, v_shot_04, v_shot_05] + [globals()[f"v_shot_{k:02d}"] for k in range(6, 28)]

if __name__ == "__main__":
    dc.main(SHOTS, sfx_events)
