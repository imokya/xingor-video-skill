"""travel-route 成片渲染（skia + numpy），绘制逻辑与 player/player.js 一一对应，导出的 MP4 和网页预览一致。

    from travel_core import Trip; from travel_render import Renderer
    R = Renderer(Trip('trip.json')); R.render('out.mp4'); R.still(8.2, 'still.png')
"""
import math, os, subprocess
import numpy as np
import skia
from PIL import Image
from travel_core import (clamp, P, eio, eo, ei, eob, lerp, logl, Cam3, clip_halfplane, arc_point, vec3, ll_of,
                         SEA, LAND, URBAN, NE_ROAD, NE_ROAD_CASE, COAST, BLUE, INK, MUTED, STY, ORDER)

Image.MAX_IMAGE_PIXELS = None
CACHE = os.path.expanduser(os.environ.get('XINGOR_TRAVEL_CACHE', '~/.cache/xingor-travel'))
try:
    import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FF = 'ffmpeg'


def C4(rgb, a=1.0): return skia.Color4f(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, clamp(a))


def paint(rgb, a=1.0, stroke=0.0, blur=0.0):
    p = skia.Paint(AntiAlias=True); p.setColor4f(C4(rgb, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


_tf = {}
def font(size, w=600):
    key = (w, int(size * 4))
    if key not in _tf:
        f = skia.Font(skia.Typeface('PingFang SC', skia.FontStyle(w, 5, skia.FontStyle.kUpright_Slant)), size)
        f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias); _tf[key] = f
    return _tf[key]


def text(c, s, x, y, size, w, rgb, a=1.0, align='l', halo=None):
    if a <= .003 or not s: return 0
    f = font(size, w); tw = f.measureText(s)
    if align == 'c': x -= tw / 2
    elif align == 'r': x -= tw
    if halo: c.drawString(s, x, y, f, paint(halo, a * .9, stroke=size * .22))
    c.drawString(s, x, y, f, paint(rgb, a))
    return tw


def path_from(xs, ys, close):
    p = skia.Path(); p.addPoly([skia.Point(float(a), float(b)) for a, b in zip(xs, ys)], close); return p


def load_tex(name, size=None):
    im = Image.open(os.path.join(CACHE, name)).convert('RGB')
    if size: im = im.resize(size)
    return np.asarray(im).astype(np.float32)


def sample(tex, u, v):
    th, tw = tex.shape[:2]
    u0 = np.floor(u).astype(np.int32); v0 = np.floor(v).astype(np.int32); fu = u - u0; fv = v - v0
    if tex.ndim == 3: fu, fv = fu[..., None], fv[..., None]
    ua, ub = u0 % tw, (u0 + 1) % tw; va, vb = np.clip(v0, 0, th - 1), np.clip(v0 + 1, 0, th - 1)
    return tex[va, ua] * (1 - fu) * (1 - fv) + tex[va, ub] * fu * (1 - fv) + tex[vb, ua] * (1 - fu) * fv + tex[vb, ub] * fu * fv


class Renderer:
    def __init__(self, trip):
        self.t = trip; self.W, self.H = trip.W, trip.H; self.LABEL_A = {}; self.preview = False
        self.EARTH = load_tex('earth.jpg'); self.NIGHT = load_tex('night.jpg'); self.CLOUD = load_tex('clouds.jpg')[..., 0] / 255
        rng = np.random.default_rng(5)
        self.STARS = [(rng.uniform(0, self.W), rng.uniform(0, self.H), rng.uniform(.5, 1.7), rng.uniform(.15, .8)) for _ in range(320)]
        self.PL_XY = np.array([(p[0], p[1]) for p in trip.PLACES], float)
        self.ROADS = []
        for nm, xy, rk, L in sorted(trip.ROADNAMES, key=lambda r: (r[2], -r[3])):
            seg = np.hypot(*np.diff(xy, axis=0).T); cum = np.concatenate([[0], np.cumsum(seg)])
            ai = int(np.clip(np.searchsorted(cum, cum[-1] / 2) - 1, 0, len(seg) - 1))
            af = (cum[-1] / 2 - cum[ai]) / seg[ai] if seg[ai] > 0 else .5
            self.ROADS.append((nm, xy, rk, L, ai, af))                    # 路名锚点：地面中点所在线段 + 段内比例

    # ============================================================ 地球
    def globe(self, c, t, n, overlays=True):
        W, H = self.W, self.H
        lon0, lat0, R, cx, cy, ak = self.t.GLOBE[min(n, len(self.t.GLOBE) - 1)]
        c.drawRect(skia.Rect.MakeWH(W, H), paint((4, 6, 14)))
        for x, y, r, al in self.STARS:
            c.drawCircle(x, y, r, paint((220, 230, 255), al * (.65 + .35 * math.sin(t * 1.7 + x))))
        l, p = math.radians(lon0), math.radians(lat0)
        M = np.array([[-math.sin(l), math.cos(l), 0], [-math.sin(p) * math.cos(l), -math.sin(p) * math.sin(l), math.cos(p)],
                      [math.cos(p) * math.cos(l), math.cos(p) * math.sin(l), math.sin(p)]])
        sun = M @ vec3(78, 18)
        x0, x1 = int(max(0, cx - R * 1.2)), int(min(W, cx + R * 1.2)); y0, y1 = int(max(0, cy - R * 1.2)), int(min(H, cy + R * 1.2))
        xs = (np.arange(x0, x1) + .5 - cx) / R; ys = -(np.arange(y0, y1) + .5 - cy) / R
        X, Y = np.meshgrid(xs, ys); r2 = X * X + Y * Y; inside = r2 <= 1; Z = np.sqrt(np.clip(1 - r2, 0, 1))
        g = np.stack([X, Y, Z], -1) @ M
        lon = np.degrees(np.arctan2(g[..., 1], g[..., 0])); lat = np.degrees(np.arcsin(np.clip(g[..., 2], -1, 1)))
        uv = lambda tex, off=0.0: sample(tex, ((lon + off + 180) % 360) / 360 * tex.shape[1] - .5, (90 - lat) / 180 * tex.shape[0] - .5)
        col = uv(self.EARTH)
        nd = X * sun[0] + Y * sun[1] + Z * sun[2]; day = np.clip(nd * 3 + .5, 0, 1); lam = np.clip(nd, 0, 1)
        col = col * (.1 + lam[..., None]) * day[..., None] + col * .06 * (1 - day[..., None])
        nl = uv(self.NIGHT); col += nl * 1.1 * (1 - day[..., None]) * np.clip((nl[..., :1] - 40) / 120, 0, 1)
        ocean = np.clip((col[..., 2] - col[..., 0] * 1.1) / 40, 0, 1) * day
        hv = sun + np.array([0, 0, 1.0]); hv /= np.linalg.norm(hv)
        col += (np.clip(X * hv[0] + Y * hv[1] + Z * hv[2], 0, 1) ** 90 * ocean)[..., None] * np.array([255, 240, 220]) * .45
        ca = (np.clip((uv(self.CLOUD, t * 2.5) - .25) / .6, 0, 1) * .85)[..., None]
        col = col * (1 - ca) + (np.array([255.0] * 3) * (.12 + .95 * lam[..., None]) * day[..., None] + 8 * (1 - day[..., None])) * ca
        fres = (np.clip((r2 - .55) / .45, 0, 1) ** 2)[..., None]
        col = col * (1 - .5 * fres) + np.array([110, 170, 255]) * .55 * fres * (.25 + .75 * day[..., None])
        rr = np.sqrt(r2); a = np.clip((1 - rr) * R, 0, 1) * inside
        glow = np.clip(1 - (rr - 1) / .12, 0, 1) ** 2.2 * (rr > 1) * np.clip((X * sun[0] + Y * sun[1]) / np.maximum(rr, 1e-6) * .6 + .55, .25, 1) * .8
        out = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
        out[..., :3] = col * a[..., None] + np.array([120, 175, 255]) * (glow * (1 - a))[..., None]
        out[..., 3] = (a + glow * (1 - a)) * 255
        out[..., :3] = np.clip(out[..., :3], 0, 255)
        rgba = np.ascontiguousarray(out.astype(np.uint8))
        img = skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        c.drawImage(img, x0, y0)
        if not overlays: return
        T = self.t.T; fade = 1 - P(t, T['xfade'][0] - .25, .25)
        P3 = lambda v: (cx + (M @ v)[0] * R, cy - (M @ v)[1] * R, (M @ v)[2])
        def arc(k, h, col, al, w, blur=0):
            pts = []
            for i in range(91):
                s = k * i / 90; v = arc_point(self.t.O_ll, self.t.D_ll, s) * (1 + h * math.sin(math.pi * s)); q = P3(v)
                if q[2] > 0 or math.hypot(q[0] - cx, q[1] - cy) > R: pts.append(q)
            if len(pts) > 1: c.drawPath(path_from([q[0] for q in pts], [q[1] for q in pts], False), paint(col, al, w, blur))
            return pts
        if ak > 0:
            arc(ak, .1, (255, 200, 110), .7 * fade, 10, 5)
            pts = arc(ak, .1, (255, 232, 175), fade, 4)
            if ak < 1 and pts:
                q = pts[-1]; c.drawCircle(q[0], q[1], 14, paint((255, 220, 150), .7 * fade, blur=8)); c.drawCircle(q[0], q[1], 6, paint((255, 255, 255), fade))
        for name, ll in ((self.t.cfg['origin']['name'], self.t.O_ll), (self.t.cfg['dest']['name'], self.t.D_ll)):
            q = P3(vec3(*ll))
            if q[2] <= 0: continue
            a2 = eo(P(t, .4, .5)) * fade; ph = (t * 1.1) % 1
            c.drawCircle(q[0], q[1], 7 + ph * 26, paint((255, 220, 150), (1 - ph) * .8 * a2, 2))
            c.drawCircle(q[0], q[1], 5.5, paint((255, 255, 255), a2))
            text(c, name, q[0] + 16, q[1] + 9, 30, 600, (255, 255, 255), a2, halo=(10, 20, 40))

    # ============================================================ 地图图层
    def layer_path(self, cam, layer, area, reach, keep=None):
        pts, offs, bb = layer['pts'], layer['offs'], layer['bb']; path = skia.Path()
        if not len(bb): return path
        tx, ty = cam.T
        sel = (bb[:, 2] > tx - reach) & (bb[:, 0] < tx + reach) & (bb[:, 3] > ty - reach) & (bb[:, 1] < ty + reach)
        if keep is not None: sel &= keep
        idx = np.nonzero(sel)[0]
        if not len(idx): return path
        sx, sy, sz = cam.proj(pts[:, 0], pts[:, 1]); n, k = cam.front_line()
        for i in idx:
            a, b = offs[i], offs[i + 1]; z = sz[a:b]
            if (z < cam.near).all(): continue
            if area:
                if (z >= cam.near).all(): px, py = sx[a:b], sy[a:b]
                else:
                    cl = clip_halfplane(pts[a:b, 0], pts[a:b, 1], n, k)
                    if len(cl) < 3: continue
                    cla = np.array(cl); px, py, _ = cam.proj(cla[:, 0], cla[:, 1])
                if px.max() < 0 or px.min() > self.W or py.max() < -50 or py.min() > self.H: continue
                path.addPoly([skia.Point(float(u), float(v)) for u, v in zip(px, py)], True)
            else:
                seg = []
                for j in range(a, b):
                    if sz[j] >= cam.near: seg.append(skia.Point(float(sx[j]), float(sy[j])))
                    else:
                        if len(seg) > 1: path.addPoly(seg, False)
                        seg = []
                if len(seg) > 1: path.addPoly(seg, False)
        return path

    def draw_base(self, c, cam):
        W, H = self.W, self.H; hz = cam.horizon_y(); B = self.t.base
        c.drawRect(skia.Rect.MakeLTRB(0, max(-10, hz), W, H), paint(SEA))
        reach = cam.dist * 7; kz = clamp((math.log(cam.dist) - math.log(8)) / (math.log(700) - math.log(8)))
        land = self.layer_path(cam, B['land'], True, reach)
        c.drawPath(land, paint(LAND)); c.drawPath(land, paint(COAST, 1, lerp(2.2, 1.2, kz)))
        c.drawPath(self.layer_path(cam, B['urban'], True, reach), paint(URBAN))
        c.drawPath(self.layer_path(cam, B['lakes'], True, reach), paint(SEA))
        c.drawPath(self.layer_path(cam, B['rivers'], False, reach), paint(SEA, 1, lerp(2.4, 1.2, kz)))
        ranks = np.array(B['roads']['meta'], float); rk = 8 if cam.dist < 150 else 6 if cam.dist < 500 else 5
        rd = self.layer_path(cam, B['roads'], False, reach, ranks <= rk); w = lerp(4.0, 1.4, kz)
        c.drawPath(rd, paint(NE_ROAD_CASE, 1, w + 1.4)); c.drawPath(rd, paint(NE_ROAD, 1, w))
        if hz > -10:
            g = skia.GradientShader.MakeLinear([(0, hz), (0, hz + 260)], [C4((222, 232, 244), .95), C4((222, 232, 244), 0)])
            c.drawRect(skia.Rect.MakeLTRB(0, hz, W, hz + 260), skia.Paint(Shader=g))
            g = skia.GradientShader.MakeLinear([(0, hz - 400), (0, hz)], [C4((178, 206, 238)), C4((226, 236, 247))])
            c.drawRect(skia.Rect.MakeLTRB(0, 0, W, max(0, hz + 1)), skia.Paint(Shader=g))

    def draw_city(self, c, cam, key, alpha):
        data = self.t.cities[key]; x0, y0, x1, y1 = self.t.cover[key]; n, k = cam.front_line()
        cl = clip_halfplane([x0, x1, x1, x0], [y0, y0, y1, y1], n, k)
        if len(cl) < 3: return
        cla = np.array(cl); px, py, _ = cam.proj(cla[:, 0], cla[:, 1])
        c.saveLayer(None, skia.Paint(Alphaf=alpha)); c.save(); c.clipPath(path_from(px, py, True), skia.ClipOp.kIntersect, True)
        reach = cam.dist * 7; tx, ty = cam.T
        for cat in ORDER:
            if cat not in data: continue
            L = data[cat]; fill, case, wkm, area = STY[cat]
            if area:
                path = self.layer_path(cam, L, True, reach); c.drawPath(path, paint(fill))
                if case: c.drawPath(path, paint(case, 1, .8))
                continue
            pts, offs, bb = L['pts'], L['offs'], L['bb']
            sel = np.nonzero((bb[:, 2] > tx - reach) & (bb[:, 0] < tx + reach) & (bb[:, 3] > ty - reach) & (bb[:, 1] < ty + reach))[0]
            if not len(sel): continue
            sx, sy, sz = cam.proj(pts[:, 0], pts[:, 1]); groups = {}
            for i in sel:
                a, b = offs[i], offs[i + 1]; z = sz[a:b]
                if (z < cam.near).all(): continue
                zm = float(z[(b - a) // 2]) if z[(b - a) // 2] > cam.near else cam.near
                wpx = clamp(wkm * cam.F / zm, .7, 40); key2 = round(math.log(wpx) * 6) / 6
                pth = groups.setdefault(key2, skia.Path()); seg = []
                for j in range(a, b):
                    if sz[j] >= cam.near: seg.append(skia.Point(float(sx[j]), float(sy[j])))
                    else:
                        if len(seg) > 1: pth.addPoly(seg, False)
                        seg = []
                if len(seg) > 1: pth.addPoly(seg, False)
            for kk in sorted(groups):
                if case: c.drawPath(groups[kk], paint(case, 1, math.exp(kk) + max(1.2, math.exp(kk) * .35)))
            for kk in sorted(groups):
                p = paint(fill, 1, math.exp(kk))
                if cat == 'rail': p.setPathEffect(skia.DashPathEffect.Make([10, 8], 0))
                c.drawPath(groups[kk], p)
        c.restore(); c.restore()

    def draw_map(self, c, cam):
        self.draw_base(c, cam)
        if cam.dist < 70:
            for key in ('origin', 'dest'):
                x0, y0, x1, y1 = self.t.cover[key]; m = cam.dist * 8
                if x1 < cam.T[0] - m or x0 > cam.T[0] + m or y1 < cam.T[1] - m or y0 > cam.T[1] + m: continue
                self.draw_city(c, cam, key, clamp((70 - cam.dist) / 40))

    # ============================================================ 地名 / 路名
    def labels(self, c, cam, allow_roads=True, reserve=()):
        boxes = list(reserve); want = {}; W, H = self.W, self.H
        SZ, WT = [40, 30, 25, 21, 22], [700, 600, 500, 400, 600]
        sx, sy, sz = cam.proj(self.PL_XY[:, 0], self.PL_XY[:, 1])
        for i in sorted(range(len(self.t.PLACES)), key=lambda i: (self.t.PLACES[i][3], self.t.PLACES[i][2])):
            x, y, nm, lvl, vis = self.t.PLACES[i]
            if cam.dist > vis or sz[i] < cam.near or not (40 < sx[i] < W - 40 and 30 < sy[i] < H - 30): continue
            if lvl >= 3 and cam.dist < 1.2: continue
            tw = font(SZ[lvl], WT[lvl]).measureText(nm); X, Y = float(sx[i]), float(sy[i]); dot = lvl <= 1 or lvl == 4
            bx = (X - 8, Y - SZ[lvl], X + 14 + tw, Y + 10) if dot else (X - tw / 2 - 4, Y - SZ[lvl] * .9, X + tw / 2 + 4, Y + 6)
            if any(not (bx[2] < q[0] or bx[0] > q[2] or bx[3] < q[1] or bx[1] > q[3]) for q in boxes): continue
            boxes.append(bx); want[('p', i)] = (X, Y, nm, lvl, dot)
        if allow_roads and cam.dist < 18:
            cnt = 0
            for nm, xy, rk, L, ai, af in self.ROADS:
                cx_, cy_ = xy.mean(0)
                if abs(cx_ - cam.T[0]) > cam.dist * 4 or abs(cy_ - cam.T[1]) > cam.dist * 4: continue
                px, py, pz = cam.proj(xy[:, 0], xy[:, 1])
                # 路名固定在这条路的地面中点，跟着地图走，不随镜头在路上滑动
                if pz[ai] <= cam.near or pz[ai + 1] <= cam.near: continue
                ax, ay = lerp(px[ai], px[ai + 1], af), lerp(py[ai], py[ai + 1], af)
                if not (40 < ax < W - 40 and 70 < ay < H - 50): continue
                i0, i1 = ai, ai + 1
                while i0 > 0 and pz[i0 - 1] > cam.near: i0 -= 1
                while i1 < len(pz) - 1 and pz[i1 + 1] > cam.near: i1 += 1
                pts = np.stack([px[i0:i1 + 1], py[i0:i1 + 1]], 1)
                d = np.hypot(*np.diff(pts, axis=0).T)
                center = float(d[:ai - i0].sum() + d[ai - i0] * af)
                r = self.glyph_run(nm, 19 if rk else 20, pts, center)
                if not r: continue
                box, place = r
                if any(not (box[2] < q[0] or box[0] > q[2] or box[3] < q[1] or box[1] > q[3]) for q in boxes): continue
                boxes.append(box); want[('r', nm)] = place; cnt += 1
                if cnt >= 10: break
        for k in list(self.LABEL_A):
            if k not in want:
                self.LABEL_A[k] -= .1
                if self.LABEL_A[k] <= 0: del self.LABEL_A[k]
        for k in want: self.LABEL_A[k] = 1.0 if self.preview else min(1.0, self.LABEL_A.get(k, 0) + .1)
        for k, v in want.items():
            a = self.LABEL_A[k]
            if k[0] == 'p':
                X, Y, nm, lvl, dot = v
                col = INK if lvl <= 2 else (90, 98, 112)
                if lvl == 4: col = (60, 130, 80)
                if dot:
                    c.drawCircle(X, Y, 6 if lvl == 0 else 4.5, paint((255, 255, 255), a))
                    c.drawCircle(X, Y, 3.6 if lvl == 0 else 2.8, paint(col if lvl != 4 else (60, 160, 90), a))
                    text(c, nm, X + 12, Y + SZ[lvl] * .36, SZ[lvl], WT[lvl], col, a, halo=(255, 255, 255))
                else:
                    text(c, nm, X, Y, SZ[lvl], WT[lvl], col, a, 'c', halo=(255, 255, 255))
            else:
                for ch, x, y, ang, w in v:
                    c.save(); c.translate(float(x), float(y)); c.rotate(math.degrees(ang))
                    text(c, ch, 0, 19 * .36, 19, 500, (70, 74, 84), a, 'c', halo=(255, 255, 255)); c.restore()

    @staticmethod
    def glyph_run(s, size, pts, center=None):
        """沿屏幕折线排字（字保持正向）；center = 路名中心的弧长位置（固定锚点），为空时放在中点"""
        cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
        if pts[-1][0] < pts[0][0]:
            pts = pts[::-1]
            if center is not None: center = cum[-1] - center
            cum = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
        f = font(size, 500); ws = [f.measureText(ch) + 1 for ch in s]; tw = sum(ws)
        if cum[-1] < tw * 1.4: return None
        mid = cum[-1] / 2 if center is None else center
        if mid - tw * .6 < 0 or mid + tw * .6 > cum[-1]: return None
        acc = mid - tw / 2; place = []
        for ch, w in zip(s, ws):
            m = acc + w / 2
            at = lambda q: (np.interp(q, cum, pts[:, 0]), np.interp(q, cum, pts[:, 1]))
            (x, y), (xa, ya), (xb, yb) = at(m), at(max(0, m - w)), at(min(cum[-1], m + w))
            place.append((ch, x, y, math.atan2(yb - ya, xb - xa), w)); acc += w
        angs = [p[3] for p in place]
        if max(angs) - min(angs) > math.radians(50): return None
        xs = [p[1] for p in place]; ys = [p[2] for p in place]
        return (min(xs) - size, min(ys) - size, max(xs) + size, max(ys) + size), place

    # ============================================================ 模型 / 路线
    def draw_model(self, c, cam, mesh, X, Y, Z, heading, size, bank=0.0, pitch=0.0, a=1.0):
        h, b, pt = math.radians(heading), math.radians(bank), math.radians(pitch); ch, sh = math.cos(h), math.sin(h)
        light = np.array([-.4, .5, .8]); light /= np.linalg.norm(light)
        faces = []
        for verts, col in mesh:
            w = []
            for vx, vy, vz in verts:
                x, y, z = vx * size, vy * size, vz * size
                y, z = y * math.cos(pt) - z * math.sin(pt), y * math.sin(pt) + z * math.cos(pt)
                x, z = x * math.cos(b) - z * math.sin(b), x * math.sin(b) + z * math.cos(b)
                w.append((X + x * ch + y * sh, Y - x * sh + y * ch, Z + z))
            faces.append((np.array(w), col))
        sp = skia.Path()
        for w, _ in faces:
            sx, sy, sz = cam.proj(w[:, 0] - w[:, 2] * .55, w[:, 1] - w[:, 2] * .35)
            if (sz < cam.near).any(): continue
            sp.addPoly([skia.Point(float(u), float(v)) for u, v in zip(sx, sy)], True)
        altk = clamp(1 - Z / (size * 6))
        c.drawPath(sp, paint((20, 30, 50), (.12 + .2 * altk) * a, blur=2 + 8 * (1 - altk)))
        draw = []
        for w, col in faces:
            sx, sy, sz = cam.proj(w[:, 0], w[:, 1], w[:, 2])
            if (sz < cam.near).any(): continue
            nrm = np.cross(w[1] - w[0], w[2] - w[0]); ln = np.linalg.norm(nrm)
            if ln < 1e-12: continue
            nrm /= ln
            if np.dot(nrm, cam.C - w.mean(0)) < 0: nrm = -nrm
            lit = .45 + .55 * max(0.0, float(np.dot(nrm, light)))
            draw.append((float(sz.mean()), sx, sy, tuple(min(255, int(v * lit + 10)) for v in col)))
        for _, sx, sy, col in sorted(draw, key=lambda d: -d[0]):
            p = path_from(sx, sy, True); c.drawPath(p, paint(col, a)); c.drawPath(p, paint(col, a, .6))

    def draw_track(self, c, cam, tr, s, solid_w, dash):
        pts, cum = tr.p, tr.cum
        sx, sy, sz = cam.proj(pts[:, 0], pts[:, 1]); W, H = self.W, self.H
        ok = (sz > cam.near) & (sx > -400) & (sx < W + 400) & (sy > -400) & (sy < H + 400)
        for mask, solid in ((ok & (cum > s), False), (ok & (cum <= s), True)):
            idx = np.nonzero(mask)[0]
            for part in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1) if len(idx) > 1 else []:
                if len(part) < 2: continue
                part = part[::max(1, len(part) // 1500)]
                if solid:
                    c.drawPath(path_from(sx[part], sy[part], False), paint((255, 255, 255), 1, solid_w + 5))
                    c.drawPath(path_from(sx[part], sy[part], False), paint(BLUE, 1, solid_w))
                else:
                    p = paint(BLUE, .5 if dash else .35, 4 if dash else 6)
                    if dash: p.setPathEffect(skia.DashPathEffect.Make([16, 12], 0))
                    c.drawPath(path_from(sx[part], sy[part], False), p)

    def plane(self, c, cam, n, a, parked=False):
        S = self.t.ST['plane']; m = int(self.t.T['fly0'] * self.t.fps) if parked else n
        size = cam.dist * .09 + .05; alt = 0 if parked else S['alt'][m]
        self.draw_model(c, cam, self.t.PLANE, S['x'][m], S['y'][m], alt * cam.dist * .085 + size * .07, S['head'][m], size,
                        0 if parked else S['bank'][m], 0 if parked else S['climb'][m], a)

    # ============================================================ 卡片 / 机票
    def ph2g(self, px, py):
        t = self.t; k = t.KM_PER_PX
        return t.PH_CENTER[0] + (px - t.PH_W / 2) * k, t.PH_CENTER[1] + (t.PH_H / 2 - py) * k

    @staticmethod
    def rr_pts(x, y, w, h, r, n=10):
        out = []
        for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
            for i in range(n + 1):
                a = math.radians(a0 + 90 * i / n); out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return out

    def card(self, c, cam, t, n):
        S = self.t.ST['phone']; ui, bez, opn = S['ui'][n], S['bez'][n], S['open'][n]; W, H = self.W, self.H
        if opn < 1:
            g = skia.GradientShader.MakeLinear([(0, 0), (W, H)], [C4((240, 241, 247)), C4((214, 217, 232))])
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=g))
        TH, SX, SY, SW, SH = .12, 14, 14, self.t.PH_W - 28, self.t.PH_H - 28
        if bez > 0:
            out = [self.ph2g(x, y) for x, y in self.rr_pts(SX, SY, SW, SH, 52)]
            top = [cam.proj(gx, gy, 0) for gx, gy in out]; bot = [cam.proj(gx, gy, -TH) for gx, gy in out]
            c.saveLayer(None, skia.Paint(Alphaf=float(bez)))
            c.drawPath(path_from([q[0] for q in bot], [q[1] + 50 for q in bot], True), paint((40, 50, 90), .22, blur=30))
            for i in range(len(out)):
                j = (i + 1) % len(out)
                cz = (top[j][0] - top[i][0]) * (bot[i][1] - top[i][1]) - (top[j][1] - top[i][1]) * (bot[i][0] - top[i][0])
                if cz > 0: continue
                c.drawPath(path_from([top[i][0], top[j][0], bot[j][0], bot[i][0]], [top[i][1], top[j][1], bot[j][1], bot[i][1]], True), paint((236, 239, 246)))
            c.restore()
        grow = math.exp(opn * 5.5) - 1
        win = [self.ph2g(x, y) for x, y in self.rr_pts(SX - grow * 400, SY - grow * 900, SW + grow * 800, SH + grow * 1800, max(.5, 52 * (1 - opn)), 8)]
        n_, k_ = cam.front_line(); cl = clip_halfplane([g[0] for g in win], [g[1] for g in win], n_, k_)
        c.save()
        if opn < .999 and len(cl) >= 3:
            cla = np.array(cl); px, py, _ = cam.proj(cla[:, 0], cla[:, 1]); c.clipPath(path_from(px, py, True), skia.ClipOp.kIntersect, True)
        self.draw_map(c, cam); self.labels(c, cam, opn > .6); self.draw_track(c, cam, self.t.FLIGHT, 0, 7, True)
        if S['ui'][n] > .002 and opn < .999:      # the card face becomes the boarding pass: one layer, map frosted out
            c.drawRect(skia.Rect.MakeWH(W, H), paint((246, 247, 251), .94 * float(S['ui'][n])))
        c.restore()
        if ui > .002 and not cam.fl:
            Hm = cam.homography(); k = self.t.KM_PER_PX
            A = np.array([[k, 0, self.t.PH_CENTER[0] - self.t.PH_W / 2 * k], [0, -k, self.t.PH_CENTER[1] + self.t.PH_H / 2 * k], [0, 0, 1]])
            M = Hm @ A; M /= M[2, 2]
            blur = S['blur_in'][n] + clamp((S['u'][n] - .3) * 30, 0, 8)
            lp = skia.Paint(Alphaf=float(ui))
            if blur > .3: lp.setImageFilter(skia.ImageFilters.Blur(blur, blur))
            c.saveLayer(None, lp); c.concat(skia.Matrix.MakeAll(*[float(v) for v in M.ravel()])); self.ticket(c, t); c.restore()

    def ticket(self, c, t):
        PW, y0 = self.t.PH_W, 500; tk = self.t.cfg.get('ticket', {}); cfg = self.t.cfg   # printed straight on the card
        tag = f"{tk.get('flight', '')}{'' if tk.get('demo') is False else ' · 示意航班'}"
        text(c, tag, 58, y0 + 46, 17, 500, BLUE)
        text(c, tk.get('from', cfg['origin']['name']), 58, y0 + 100, 28, 700, INK); text(c, tk.get('to', cfg['dest']['name']), PW - 58, y0 + 100, 28, 700, INK, 1, 'r')
        text(c, tk.get('dep', ''), 58, y0 + 162, 50, 700, INK); text(c, tk.get('arr', ''), PW - 58, y0 + 162, 50, 700, INK, 1, 'r')
        text(c, tk.get('from_sub', cfg['origin']['airport'].get('code', '')), 58, y0 + 194, 17, 400, MUTED)
        text(c, tk.get('to_sub', cfg['dest']['airport'].get('code', '')), PW - 58, y0 + 194, 17, 400, MUTED, 1, 'r')
        lp = eio(P(t, self.t.T['face'], 1.0)); x0, x1, yl = 58, PW - 58, y0 + 246
        d = paint((205, 211, 222), 1, 3); d.setPathEffect(skia.DashPathEffect.Make([8, 8], 0)); c.drawLine(x0, yl, x1, yl, d)
        c.drawLine(x0, yl, x0 + (x1 - x0) * lp, yl, paint(BLUE, 1, 4)); c.drawCircle(x0 + (x1 - x0) * lp, yl, 7, paint(BLUE))
        text(c, '预计飞行时长', 58, y0 + 300, 18, 400, MUTED); text(c, tk.get('dur', ''), PW - 58, y0 + 300, 22, 600, BLUE, 1, 'r')

    # ============================================================ 卡片 / 署名 / 到达
    def info_card(self, c, a, kicker, title, line, prog):
        if a <= 0: return
        x, y, w, h = 70, 70 + 30 * (1 - a), 560, 196
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y + 10, w, h), 26, 26), paint((0, 0, 0), .16 * a, blur=18))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), 26, 26), paint((255, 255, 255), .96 * a))
        ts = 40.0
        while ts > 22 and font(ts, 700).measureText(title) > w - 68: ts -= 1      # keep the title inside the card
        text(c, kicker, x + 34, y + 46, 20, 400, (120, 128, 140), a); text(c, title, x + 34, y + 100, ts, 700, (28, 32, 40), a)
        text(c, line, x + 34, y + 142, 22, 400, MUTED, a)
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + 34, y + 160, w - 68, 8), 4, 4), paint((225, 230, 238), a))
        if prog > 0: c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x + 34, y + 160, (w - 68) * prog, 8), 4, 4), paint(BLUE, a))

    def credit(self, c, s): text(c, s, self.W - 40, self.H - 30, 18, 400, (90, 96, 110), .8, 'r', halo=(255, 255, 255))

    def arrive(self, c, cam, t):
        T = self.t.T
        if t < T['taxi1'] - .2: return
        x, y, _ = cam.proj(*self.t.PARK); x, y = float(x), float(y); kk = eob(P(t, T['taxi1'] - .2, .5))
        for j in range(2):
            ph = clamp((t - T['taxi1'] - j * .3) / 1.3)
            if 0 < ph < 1: c.drawOval(skia.Rect.MakeXYWH(x - 14 - ph * 110, y - 6 - ph * 50, 28 + ph * 220, 12 + ph * 100), paint(BLUE, (1 - ph) * .7, 3))
        c.save(); c.translate(x, y - lerp(140, 0, clamp(kk)))
        pin = skia.Path(); pin.moveTo(0, 0); pin.cubicTo(-12, -20, -30, -34, -30, -56); pin.arcTo(skia.Rect.MakeXYWH(-30, -86, 60, 60), 180, 180, False)
        pin.cubicTo(30, -34, 12, -20, 0, 0); pin.close()
        c.drawPath(pin, paint((0, 0, 0), .2 * clamp(kk), blur=6)); c.drawPath(pin, paint(BLUE, clamp(kk * 2))); c.drawCircle(0, -56, 11, paint((255, 255, 255), clamp(kk * 2)))
        c.restore()
        q = eo(P(t, T['taxi1'] + .2, .6)); poi = self.t.cfg['poi']
        if self.W < self.H:      # portrait: name centred above the pin so it never leaves the frame
            text(c, poi['name'], x, y - 190, 62, 700, INK, q, 'c', halo=(255, 255, 255))
            text(c, f"{poi.get('sub', self.t.cfg['dest']['name'])}  到达", x, y - 142, 26, 400, (90, 98, 112), q, 'c', halo=(255, 255, 255))
        else:
            text(c, poi['name'], x - 50, y - 40, 66, 700, INK, q, 'r', halo=(255, 255, 255))
            text(c, f"{poi.get('sub', self.t.cfg['dest']['name'])}  到达", x - 54, y + 8, 28, 400, (90, 98, 112), q, 'r', halo=(255, 255, 255))

    # ============================================================ 每帧
    def frame(self, n):
        t = n / self.t.fps; T = self.t.T; W, H = self.W, self.H
        s = skia.Surface(W, H); c = s.getCanvas()
        xf0, xf1 = T['xfade'][0], T['xfade'][0] + T['xfade'][1]
        if t < xf0:
            self.globe(c, t, n); return s
        if t < xf1:
            self.globe(c, t, n, overlays=False)
            c.saveLayer(None, skia.Paint(Alphaf=float(eio((t - xf0) / T['xfade'][1]))))
        cam = self.t.cam(n); cm = self.t.CAMS; n2 = min(n + 1, self.t.N - 1)
        speed = abs(math.log(cm['dist'][n2] / cm['dist'][n])) * 60 + abs(cm['pitch'][n2] - cm['pitch'][n]) * .6
        blur = clamp(speed * 1.6 - 1, 0, 5) if T['flyin'] < t < T['dive1'] + .3 else 0
        if blur > .3: c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(blur, blur)))
        trip = self.t.cfg
        if t < T['dive1']:
            self.card(c, cam, t, n)
            pa = eo(P(t, T['fly0'] - .8, .6))
            if pa > 0: self.plane(c, cam, n, pa, parked=True)
        else:
            if t < T['landed'] + .6:
                self.draw_map(c, cam); ps = self.t.ST['plane']['s'][n]
                self.draw_track(c, cam, self.t.FLIGHT, ps, 7, True); self.labels(c, cam)
                self.plane(c, cam, n, 1 - P(t, T['landed'], .5))
                prog = clamp(ps / self.t.FLIGHT.L); tk = trip.get('ticket', {})
                self.info_card(c, eo(P(t, T['fly0'] + .3, .5)) * (1 - P(t, T['landed'], .4)),
                               f"{tk.get('flight', '')}{'' if tk.get('demo') is False else ' · 示意航班'}",
                               f"{trip['origin']['name']}  →  {trip['dest']['name']}",
                               f'已飞 {self.t.FLIGHT_KM * prog:,.0f} 公里 / 全程约 {self.t.FLIGHT_KM:,.0f} 公里', prog)
                if t < T['landed']: self.credit(c, '地图数据 © OpenStreetMap 贡献者 · Natural Earth')
            if t >= T['landed']:
                if t >= T['landed'] + .6: self.draw_map(c, cam)
                cs = self.t.ST['car']['s'][n]; self.draw_track(c, cam, self.t.TAXI, cs, 9, False)
                res = ()
                if t > T['taxi1'] - .6:
                    x, y, _ = cam.proj(*self.t.PARK); res = ((float(x) - 470, float(y) - 110, float(x) + 40, float(y) + 30),)
                self.labels(c, cam, True, res)
                ta = eo(P(t, T['taxi0'] - .5, .5)); C = self.t.ST['car']
                if ta > 0: self.draw_model(c, cam, self.t.CAR, C['x'][n], C['y'][n], 0, C['head'][n], min(.36, max(.05, cam.dist * .12)), a=ta)
                self.arrive(c, cam, t); kk = cs / self.t.TAXI.L
                self.info_card(c, eo(P(t, T['taxi0'] - .2, .5)), '出租车 · 路线估算', f"{trip['dest']['airport']['name']}  →  {trip['poi']['name']}",
                               f'{self.t.TAXI_KM * kk:.1f} / {self.t.TAXI_KM:.1f} 公里 · 约 {self.t.TAXI_MIN:.0f} 分钟', kk)
                self.credit(c, '地图数据 © OpenStreetMap 贡献者 · 路线 OSRM')
        if blur > .3: c.restore()
        if t < xf1: c.restore()
        return s

    def still(self, t, path):
        self.preview = True; self.LABEL_A.clear()
        self.frame(int(round(t * self.t.fps))).makeImageSnapshot().save(path); self.preview = False

    def render(self, out, t0=0.0, t1=None):
        t1 = t1 or self.t.T['dur']; W, H = self.W, self.H
        p = subprocess.Popen([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(self.t.fps), '-i', '-',
                              '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
        self.LABEL_A.clear()
        for n in range(int(t0 * self.t.fps), min(self.t.N, int(t1 * self.t.fps))):
            p.stdin.write(self.frame(n).makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
            if n % 120 == 0: print(f'{n / self.t.fps:.1f}s', flush=True)
        p.stdin.close(); p.wait(); print('done:', out)
