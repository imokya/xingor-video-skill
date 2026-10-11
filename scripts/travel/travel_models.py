"""travel-route 的 3D 模型（低多边形）：客机和出租车。每个面是 (顶点列表, 颜色)，单位长度约 1，y 朝前、x 朝右、z 朝上。
渲染时按法线和光照着色、按深度排序（travel_render.draw_model / player.js drawModel）。"""
import math
import numpy as np


def box(cx, cy, cz, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    q = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return [[v[i] for i in f] for f in q]


def ring(y, rx, rz, zc, n):
    return [(rx * math.cos(2 * math.pi * i / n), y, zc + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]


def loft(rings, col, F, cap0=True, cap1=True):
    n = len(rings[0])
    for s in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            F.append(([rings[s][i], rings[s][j], rings[s + 1][j], rings[s + 1][i]], col))
    if cap0: F.append((rings[0][::-1], col))
    if cap1: F.append((rings[-1], col))


def slab(outline, z0, z1, col, F, col_side=None):
    """把平面轮廓（x, y）挤出成有厚度的板"""
    top = [(x, y, z1) for x, y in outline]; bot = [(x, y, z0) for x, y in outline][::-1]
    F.append((top, col)); F.append((bot, col_side or col))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        (xa, ya), (xb, yb) = outline[i], outline[j]
        F.append(([(xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)], col_side or col))


def airliner(BLUE=(38, 108, 255)):
    """客机：机长约 1（y 朝前，x 朝右，z 朝上）"""
    F = []
    WHITE, BELLY, BLUE_, GLASS, ENG = (248, 249, 252), (226, 230, 238), BLUE, (40, 50, 70), (210, 214, 222)
    n = 16
    secs = [(.50, .004, .0), (.485, .022, .004), (.46, .038, .008), (.42, .050, .01), (.36, .056, .01), (.20, .058, .0),
            (-.22, .058, .0), (-.32, .052, .012), (-.40, .040, .03), (-.46, .026, .045), (-.50, .010, .055)]
    rings = [ring(y, r, r * 1.04, zc, n) for y, r, zc in secs]
    # 机身上半白、下半浅灰
    for s in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            zmid = (rings[s][i][2] + rings[s][j][2]) / 2 - secs[s][2]
            col = WHITE if zmid > -.01 else BELLY
            F.append(([rings[s][i], rings[s][j], rings[s + 1][j], rings[s + 1][i]], col))
    # 驾驶舱风挡
    for sx in (1, -1):
        F.append(([(sx * .012, .462, .036), (sx * .034, .452, .03), (sx * .036, .432, .040), (sx * .012, .44, .048)], GLASS))
    # 舷窗线
    for sx in (1, -1):
        for k in range(18):
            y = .30 - k * .03
            F.append(([(sx * .0585, y, .018), (sx * .0585, y - .012, .018), (sx * .0585, y - .012, .026), (sx * .0585, y, .026)], GLASS))
    # 机身蓝色腰线
    for sx in (1, -1):
        F.append(([(sx * .0586, .34, .002), (sx * .0586, -.30, .002), (sx * .0586, -.30, -.006), (sx * .0586, .34, -.006)], BLUE_))
    # 主翼（后掠 + 翼梢小翼）
    wing = [(.05, .10), (.56, -.12), (.58, -.17), (.05, -.08)]
    for sx in (1, -1):
        o = [(sx * x, y) for x, y in wing]
        if sx < 0: o = o[::-1]
        slab(o, -.012, -.002, WHITE, F, BELLY)
        tip = sx * .565
        F.append(([(tip, -.12, -.002), (tip + sx * .01, -.16, .05), (tip + sx * .01, -.18, .05), (tip, -.17, -.002)], BLUE_))
        F.append(([(tip, -.17, -.002), (tip + sx * .01, -.18, .05), (tip + sx * .01, -.16, .05), (tip, -.12, -.002)], BLUE_))
        # 发动机（圆筒 + 进气口）+ 吊架
        ex = sx * .21
        er = [ring(y, .032, .032, -.05, 12) for y in (.06, .05, -.06, -.08)]
        er = [[(x + ex, y, z) for x, y, z in r] for r in er]
        loft(er, ENG, F, cap0=False)
        F.append(([(x * .7 + ex * .3, y, z * .7 - .05 * .3) for x, y, z in er[0]][::-1], (60, 64, 74)))
        F.append(([(ex, .02, -.018), (ex, -.06, -.018), (ex, -.06, -.008), (ex, .03, -.006)], BELLY))
    # 水平尾翼
    stab = [(.02, -.37), (.20, -.46), (.21, -.50), (.02, -.46)]
    for sx in (1, -1):
        o = [(sx * x, y) for x, y in stab]
        if sx < 0: o = o[::-1]
        slab([(x, y) for x, y in o], .040, .048, WHITE, F, BELLY)
    # 垂直尾翼（带蓝色涂装）
    fin = [(-.30, .05), (-.43, .25), (-.49, .26), (-.49, .055)]
    side = [(0.006, y, z) for y, z in fin]
    F.append((side, BLUE_)); F.append(([(-x, y, z) for x, y, z in side][::-1], BLUE_))
    for i in range(len(fin)):
        j = (i + 1) % len(fin)
        F.append(([(0.006, fin[i][0], fin[i][1]), (-.006, fin[i][0], fin[i][1]), (-.006, fin[j][0], fin[j][1]), (0.006, fin[j][0], fin[j][1])], BLUE_))
    return F


def taxi():
    """出租车：车长约 1（y 朝前）"""
    F = []
    Y, Y2, GL, TIRE, LIGHT, RED, DARK = (255, 200, 40), (236, 170, 20), (46, 56, 74), (30, 32, 36), (255, 250, 220), (230, 60, 50), (60, 64, 72)
    w = .21
    prof = [(-.50, .07), (-.50, .20), (-.46, .24), (-.30, .25), (-.22, .40), (.12, .41), (.24, .26), (.46, .24), (.50, .18), (.50, .07)]
    # 车身侧面 + 顶面（按侧面轮廓逐段挤出）
    for sx in (1, -1):
        side = [(sx * w, y, z) for y, z in prof]
        F.append((side if sx > 0 else side[::-1], Y))
    for i in range(len(prof) - 1):
        (ya, za), (yb, zb) = prof[i], prof[i + 1]
        glass = (i in (3, 5))                                       # 前后挡风玻璃
        col = GL if glass else (Y2 if i in (0, 8) else Y)
        F.append(([(w * .93 if za > .3 else w, ya, za), (-w * .93 if za > .3 else -w, ya, za),
                   (-w * .93 if zb > .3 else -w, yb, zb), (w * .93 if zb > .3 else w, yb, zb)], col))
    F.append(([(w, -.5, .07), (-w, -.5, .07), (-w, .5, .07), (w, .5, .07)], DARK))
    # 侧窗
    for sx in (1, -1):
        win = [(sx * w * 1.002, -.27, .27), (sx * w * 1.002, -.20, .385), (sx * w * 1.002, .10, .395), (sx * w * 1.002, .20, .27)]
        F.append((win if sx > 0 else win[::-1], GL))
        F.append(([(sx * w * 1.003, -.44, .15), (sx * w * 1.003, .46, .15), (sx * w * 1.003, .46, .13), (sx * w * 1.003, -.44, .13)], (30, 30, 30)))
    # 车轮
    for yw in (-.31, .31):
        for sx in (1, -1):
            rr = [(sx * (w + .005), yw + .085 * math.cos(a), .085 + .085 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
            F.append((rr if sx > 0 else rr[::-1], TIRE))
    # 车灯
    for sx in (1, -1):
        F.append(([(sx * .17, .502, .19), (sx * .08, .502, .19), (sx * .08, .502, .16), (sx * .17, .502, .16)], LIGHT))
        F.append(([(sx * .08, -.502, .19), (sx * .17, -.502, .19), (sx * .17, -.502, .16), (sx * .08, -.502, .16)], RED))
    # 顶灯
    for f in box(0, -.04, .44, .16, .08, .06): F.append((f, (255, 255, 255)))
    return F
