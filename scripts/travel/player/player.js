// travel-route 预览播放器：读取 data.json（travel_core.Trip.export_web 生成），在浏览器里实时绘制。
// 相机、飞机、出租车的逐帧状态在 Python 里已经平滑好；这里只负责画。
'use strict';
const W = 1920, H = 1080;
const $ = (id) => document.getElementById(id);
const BLUE = [38, 108, 255], INK = [36, 40, 50], MUTED = [110, 118, 130];
const SEA = [170, 208, 240], LAND = [244, 242, 236], URBAN = [236, 232, 226];
const NE_ROAD = [255, 214, 140], NE_ROAD_CASE = [232, 184, 110], COAST = [150, 188, 222];
const rgba = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const P = (t, t0, d) => clamp((t - t0) / d);
const eio = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const eo = (x) => { x = clamp(x); return 1 - (1 - x) ** 3; };
const ei = (x) => { x = clamp(x); return x ** 3; };
const eob = (x, s = 1.7) => { x = clamp(x) - 1; return x * x * ((s + 1) * x + s) + 1; };
const lerp = (a, b, k) => a + (b - a) * k;
const logl = (a, b, k) => Math.exp(lerp(Math.log(a), Math.log(b), k));
const rad = (d) => d * Math.PI / 180;

let D, T, FR;
const bg = $('bg').getContext('2d');
const ctx = $('map').getContext('2d');
const uictx = $('ui').getContext('2d');

// ------------------------------------------------------------------ 相机（与 Python Cam3 相同）
function Cam(tx, ty, head, pitch, dist, cx, cy, F = 1500, flip = 0) {
  const h = rad(head), p = rad(pitch), hx = Math.sin(h), hy = Math.cos(h);
  const f = [hx * Math.sin(p), hy * Math.sin(p), -Math.cos(p)];
  const r = [hy, -hx, 0];
  const u = [r[1] * f[2] - r[2] * f[1], r[2] * f[0] - r[0] * f[2], r[0] * f[1] - r[1] * f[0]];
  const C = [tx - f[0] * dist, ty - f[1] * dist, -f[2] * dist];
  const fl = Math.abs(flip) > 1e-4;
  return { f, r, u, C, F, cx, cy, dist, T: [tx, ty], near: dist * .05, fl, fc: Math.cos(rad(flip)), fs: Math.sin(rad(flip)) };
}
function proj(c, x, y, z = 0) {
  if (c.fl) { const ox = x - c.T[0]; x = c.T[0] + ox * c.fc - z * c.fs; z = ox * c.fs + z * c.fc; }
  const dx = x - c.C[0], dy = y - c.C[1], dz = z - c.C[2];
  const xc = dx * c.r[0] + dy * c.r[1] + dz * c.r[2];
  const yc = dx * c.u[0] + dy * c.u[1] + dz * c.u[2];
  const zc = dx * c.f[0] + dy * c.f[1] + dz * c.f[2];
  const zz = Math.max(zc, 1e-6);
  return [c.cx + c.F * xc / zz, c.cy - c.F * yc / zz, zc];
}
let PX = new Float64Array(1 << 16), PY = new Float64Array(1 << 16), PZ = new Float64Array(1 << 16);
function projArr(c, p) {                       // p = Float32Array [x0,y0,x1,y1,...]
  const n = p.length / 2;
  if (PX.length < n) { PX = new Float64Array(n * 2); PY = new Float64Array(n * 2); PZ = new Float64Array(n * 2); }
  const C0 = c.C[0], C1 = c.C[1], C2 = c.C[2], r = c.r, u = c.u, f = c.f, F = c.F;
  if (c.fl) { for (let i = 0; i < n; i++) { const q = proj(c, p[2 * i], p[2 * i + 1]); PX[i] = q[0]; PY[i] = q[1]; PZ[i] = q[2]; } return n; }
  for (let i = 0; i < n; i++) {
    const dx = p[2 * i] - C0, dy = p[2 * i + 1] - C1, dz = -C2;
    const xc = dx * r[0] + dy * r[1];
    const yc = dx * u[0] + dy * u[1] + dz * u[2];
    const zc = dx * f[0] + dy * f[1] + dz * f[2];
    const zz = zc > 1e-6 ? zc : 1e-6;
    PX[i] = c.cx + F * xc / zz; PY[i] = c.cy - F * yc / zz; PZ[i] = zc;
  }
  return n;
}
function frontLine(c) { if (c.fl) return [0, 0, -1e18]; return [c.f[0], c.f[1], c.near + c.f[0] * c.C[0] + c.f[1] * c.C[1] + c.f[2] * c.C[2]]; }
function clipHalf(p, n0, n1, k) {               // 保留 n·p >= k（地面坐标）
  const out = [], m = p.length / 2;
  for (let i = 0; i < m; i++) {
    const j = (i - 1 + m) % m;
    const ax = p[2 * j], ay = p[2 * j + 1], bx = p[2 * i], by = p[2 * i + 1];
    const da = n0 * ax + n1 * ay - k, db = n0 * bx + n1 * by - k;
    if (db >= 0) {
      if (da < 0) { const s = da / (da - db); out.push(ax + (bx - ax) * s, ay + (by - ay) * s); }
      out.push(bx, by);
    } else if (da >= 0) { const s = da / (da - db); out.push(ax + (bx - ax) * s, ay + (by - ay) * s); }
  }
  return out;
}
function horizonY(c) {
  const nrm = Math.hypot(c.f[0], c.f[1]);
  if (nrm < 1e-6) return -1e9;
  const X = c.C[0] + c.f[0] / nrm * c.dist * 400, Y = c.C[1] + c.f[1] / nrm * c.dist * 400;
  const [, y, z] = proj(c, X, Y);
  return z > 0 ? y : -1e9;
}
function camAt(n) {
  const k = FR.cam;
  return Cam(k.tx[n], k.ty[n], k.head[n], k.pitch[n], k.dist[n], k.cx[n], k.cy[n], k.F[n], k.flip[n]);
}

// ------------------------------------------------------------------ 图层
function prep(list) {
  for (const f of list) { f.p = Float32Array.from(f.p); }
  return list;
}
function addFeature(path, c, f, area, nf) {
  const n = projArr(c, f.p);
  let any = false, all = true;
  for (let i = 0; i < n; i++) { if (PZ[i] >= c.near) any = true; else all = false; }
  if (!any) return false;
  if (area) {
    let xs, ys, m;
    if (all) { xs = PX; ys = PY; m = n; }
    else {
      const cl = clipHalf(f.p, nf[0], nf[1], nf[2]);
      if (cl.length < 6) return false;
      m = cl.length / 2; xs = new Float64Array(m); ys = new Float64Array(m);
      for (let i = 0; i < m; i++) { const q = proj(c, cl[2 * i], cl[2 * i + 1]); xs[i] = q[0]; ys[i] = q[1]; }
    }
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    for (let i = 0; i < m; i++) { x0 = Math.min(x0, xs[i]); x1 = Math.max(x1, xs[i]); y0 = Math.min(y0, ys[i]); y1 = Math.max(y1, ys[i]); }
    if (x1 < 0 || x0 > W || y1 < -50 || y0 > H) return false;
    path.moveTo(xs[0], ys[0]);
    for (let i = 1; i < m; i++) path.lineTo(xs[i], ys[i]);
    path.closePath();
  } else {
    let pen = false;
    for (let i = 0; i < n; i++) {
      if (PZ[i] >= c.near) { pen ? path.lineTo(PX[i], PY[i]) : path.moveTo(PX[i], PY[i]); pen = true; }
      else pen = false;
    }
  }
  return true;
}
function inReach(f, c, reach) {
  const b = f.bb;
  return b[2] > c.T[0] - reach && b[0] < c.T[0] + reach && b[3] > c.T[1] - reach && b[1] < c.T[1] + reach;
}
function layerPath(c, list, area, reach, keep) {
  const path = new Path2D(), nf = frontLine(c);
  for (const f of list) {
    if (!inReach(f, c, reach)) continue;
    if (keep && !keep(f)) continue;
    addFeature(path, c, f, area, nf);
  }
  return path;
}
function stroke(path, col, w, a = 1) {
  ctx.strokeStyle = rgba(col, a); ctx.lineWidth = w; ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.stroke(path);
}
function fill(path, col, a = 1) { ctx.fillStyle = rgba(col, a); ctx.fill(path); }

function drawBase(c) {
  const hz = horizonY(c);
  ctx.fillStyle = rgba(SEA); ctx.fillRect(0, Math.max(-10, hz), W, H);
  const reach = c.dist * 7;
  const kz = clamp((Math.log(c.dist) - Math.log(8)) / (Math.log(700) - Math.log(8)));
  const land = layerPath(c, D.base.land, true, reach);
  fill(land, LAND); stroke(land, COAST, lerp(2.2, 1.2, kz));
  fill(layerPath(c, D.base.urban, true, reach), URBAN);
  fill(layerPath(c, D.base.lakes, true, reach), SEA);
  stroke(layerPath(c, D.base.rivers, false, reach), SEA, lerp(2.4, 1.2, kz));
  const rk = c.dist < 150 ? 8 : c.dist < 500 ? 6 : 5;
  const rd = layerPath(c, D.base.roads, false, reach, (f) => f.m <= rk);
  const w = lerp(4, 1.4, kz);
  stroke(rd, NE_ROAD_CASE, w + 1.4); stroke(rd, NE_ROAD, w);
  if (hz > -10) {
    let g = ctx.createLinearGradient(0, hz, 0, hz + 260);
    g.addColorStop(0, 'rgba(222,232,244,.95)'); g.addColorStop(1, 'rgba(222,232,244,0)');
    ctx.fillStyle = g; ctx.fillRect(0, hz, W, 260);
    g = ctx.createLinearGradient(0, hz - 400, 0, hz);
    g.addColorStop(0, 'rgb(178,206,238)'); g.addColorStop(1, 'rgb(226,236,247)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, Math.max(0, hz + 1));
  }
}

function drawCity(c, city, alpha) {
  const C = D.cities[city];
  const [x0, y0, x1, y1] = C.cover;
  const nf = frontLine(c);
  const cl = clipHalf([x0, y0, x1, y0, x1, y1, x0, y1], nf[0], nf[1], nf[2]);
  if (cl.length < 6) return;
  ctx.save(); ctx.globalAlpha = alpha;
  const cov = new Path2D();
  for (let i = 0; i < cl.length / 2; i++) { const q = proj(c, cl[2 * i], cl[2 * i + 1]); i ? cov.lineTo(q[0], q[1]) : cov.moveTo(q[0], q[1]); }
  cov.closePath(); ctx.clip(cov);
  const reach = c.dist * 7;
  for (const L of C.layers) {
    if (L.area) {
      const path = layerPath(c, L.f, true, reach);
      fill(path, L.fill);
      if (L.case) stroke(path, L.case, .8);
    } else {
      // 按每条线到相机的距离算宽度，分组描边
      const groups = new Map(), nf2 = frontLine(c);
      for (const f of L.f) {
        if (!inReach(f, c, reach)) continue;
        const n = f.p.length / 2, mid = (n >> 1);
        const z = proj(c, f.p[2 * mid], f.p[2 * mid + 1])[2];
        const wpx = clamp(L.w * c.F / Math.max(z, c.near), .7, 40);
        const key = Math.round(Math.log(wpx) * 6) / 6;
        let pth = groups.get(key); if (!pth) { pth = new Path2D(); groups.set(key, pth); }
        addFeature(pth, c, f, false, nf2);
      }
      const keys = [...groups.keys()].sort((a, b) => a - b);
      if (L.case) for (const k of keys) { const w = Math.exp(k); stroke(groups.get(k), L.case, w + Math.max(1.2, w * .35)); }
      for (const k of keys) {
        if (L.cat === 'rail') ctx.setLineDash([10, 8]);
        stroke(groups.get(k), L.fill, Math.exp(k)); ctx.setLineDash([]);
      }
    }
  }
  ctx.restore();
}

function drawMap(c) {
  drawBase(c);
  if (c.dist < 70) {
    for (const city of ['origin', 'dest']) {
      const [x0, y0, x1, y1] = D.cities[city].cover, m = c.dist * 8;
      if (x1 < c.T[0] - m || x0 > c.T[0] + m || y1 < c.T[1] - m || y0 > c.T[1] + m) continue;
      drawCity(c, city, clamp((70 - c.dist) / 40));
    }
  }
}

// ------------------------------------------------------------------ 文字 / 地名 / 路名
function font(size, w = 600) { return `${w} ${size}px "PingFang SC", -apple-system, sans-serif`; }
function text(s, x, y, size, w, col, a = 1, align = 'left', halo = null) {
  if (a <= .003 || !s) return 0;
  ctx.font = font(size, w); ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  if (halo) { ctx.strokeStyle = rgba(halo, a * .9); ctx.lineWidth = size * .22; ctx.lineJoin = 'round'; ctx.strokeText(s, x, y); }
  ctx.fillStyle = rgba(col, a); ctx.fillText(s, x, y);
  return ctx.measureText(s).width;
}
const LABEL_A = new Map();
function overlap(b, boxes) { return boxes.some((q) => !(b[2] < q[0] || b[0] > q[2] || b[3] < q[1] || b[1] > q[3])); }
function glyphRun(s, size, xs, ys, center = null) {
  // center：路名中心在这段折线上的弧长位置（固定锚点）；为空时放在中点
  const cum = [0];
  for (let i = 1; i < xs.length; i++) cum.push(cum[i - 1] + Math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]));
  if (xs[xs.length - 1] < xs[0]) {
    xs = xs.slice().reverse(); ys = ys.slice().reverse();
    const L0 = cum[cum.length - 1]; if (center != null) center = L0 - center;
    cum.length = 0; cum.push(0);
    for (let i = 1; i < xs.length; i++) cum.push(cum[i - 1] + Math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1]));
  }
  ctx.font = font(size, 500);
  const ws = [...s].map((ch) => ctx.measureText(ch).width + 1), tw = ws.reduce((a, b) => a + b, 0), L = cum[cum.length - 1];
  if (L < tw * 1.4) return null;
  const mid = center == null ? L / 2 : center;
  if (mid - tw * .6 < 0 || mid + tw * .6 > L) return null;
  const at = (m) => {
    let i = 1; while (i < cum.length - 1 && cum[i] < m) i++;
    const k = (m - cum[i - 1]) / Math.max(1e-9, cum[i] - cum[i - 1]);
    return [lerp(xs[i - 1], xs[i], k), lerp(ys[i - 1], ys[i], k)];
  };
  let acc = mid - tw / 2; const place = [];
  [...s].forEach((ch, i) => {
    const w = ws[i], m = acc + w / 2, [x, y] = at(m), [xa, ya] = at(Math.max(0, m - w)), [xb, yb] = at(Math.min(L, m + w));
    place.push([ch, x, y, Math.atan2(yb - ya, xb - xa), w]); acc += w;
  });
  const angs = place.map((p) => p[3]);
  if (Math.max(...angs) - Math.min(...angs) > rad(50)) return null;
  const px = place.map((p) => p[1]), py = place.map((p) => p[2]);
  return [[Math.min(...px) - size, Math.min(...py) - size, Math.max(...px) + size, Math.max(...py) + size], place];
}
function drawLabels(c, allowRoads = true, reserve = []) {
  const boxes = reserve.slice(), want = new Map();
  const SZ = [40, 30, 25, 21, 22], WT = [700, 600, 500, 400, 600];
  for (const [i, pl] of D.placesSorted) {
    const [x, y, nm, lvl, vis] = pl;
    if (c.dist > vis) continue;
    if (lvl >= 3 && c.dist < 1.2) continue;
    const [sx, sy, sz] = proj(c, x, y);
    if (sz < c.near || !(sx > 40 && sx < W - 40 && sy > 30 && sy < H - 30)) continue;
    ctx.font = font(SZ[lvl], WT[lvl]); const tw = ctx.measureText(nm).width;
    const dot = lvl <= 1 || lvl === 4;
    const bx = dot ? [sx - 8, sy - SZ[lvl], sx + 14 + tw, sy + 10] : [sx - tw / 2 - 4, sy - SZ[lvl] * .9, sx + tw / 2 + 4, sy + 6];
    if (overlap(bx, boxes)) continue;
    boxes.push(bx); want.set('p' + i, ['p', sx, sy, nm, lvl, dot]);
  }
  if (allowRoads && c.dist < 18) {
    let cnt = 0;
    for (const r of D.roadsSorted) {
      const [nm, xy, rk] = r;
      if (Math.abs(r.cx - c.T[0]) > c.dist * 4 || Math.abs(r.cy - c.T[1]) > c.dist * 4) continue;
      // 路名固定在这条路的地面中点（锚点），跟着地图走，不随镜头在路上滑动
      const n = projArr(c, xy), ai = r.ai, af = r.af;
      if (PZ[ai] <= c.near || PZ[ai + 1] <= c.near) continue;
      const ax = lerp(PX[ai], PX[ai + 1], af), ay = lerp(PY[ai], PY[ai + 1], af);
      if (ax < 40 || ax > W - 40 || ay < 70 || ay > H - 50) continue;
      let i0 = ai, i1 = ai + 1;
      while (i0 > 0 && PZ[i0 - 1] > c.near) i0--;
      while (i1 < n - 1 && PZ[i1 + 1] > c.near) i1++;
      const xs = [], ys = []; let center = 0;
      for (let i = i0; i <= i1; i++) {
        if (i > i0) { const d = Math.hypot(PX[i] - PX[i - 1], PY[i] - PY[i - 1]); if (i <= ai) center += d; else if (i === ai + 1) center += d * af; }
        xs.push(PX[i]); ys.push(PY[i]);
      }
      const res = glyphRun(nm, rk ? 19 : 20, xs, ys, center);
      if (!res || overlap(res[0], boxes)) continue;
      boxes.push(res[0]); want.set('r' + nm, ['r', res[1]]);
      if (++cnt >= 10) break;
    }
  }
  for (const k of [...LABEL_A.keys()]) if (!want.has(k)) { const v = LABEL_A.get(k) - .1; v <= 0 ? LABEL_A.delete(k) : LABEL_A.set(k, v); }
  for (const k of want.keys()) LABEL_A.set(k, Math.min(1, (LABEL_A.get(k) || 0) + .1));
  for (const [k, v] of want) {
    const a = LABEL_A.get(k);
    if (v[0] === 'p') {
      const [, X, Y, nm, lvl, dot] = v;
      let col = lvl <= 2 ? INK : [90, 98, 112]; if (lvl === 4) col = [60, 130, 80];
      if (dot) {
        ctx.fillStyle = rgba([255, 255, 255], a); ctx.beginPath(); ctx.arc(X, Y, lvl === 0 ? 6 : 4.5, 0, 7); ctx.fill();
        ctx.fillStyle = rgba(lvl === 4 ? [60, 160, 90] : col, a); ctx.beginPath(); ctx.arc(X, Y, lvl === 0 ? 3.6 : 2.8, 0, 7); ctx.fill();
        text(nm, X + 12, Y + SZ[lvl] * .36, SZ[lvl], WT[lvl], col, a, 'left', [255, 255, 255]);
      } else text(nm, X, Y, SZ[lvl], WT[lvl], col, a, 'center', [255, 255, 255]);
    } else {
      for (const [ch, x, y, ang, w] of v[1]) {
        ctx.save(); ctx.translate(x, y); ctx.rotate(ang);
        text(ch, 0, 19 * .36, 19, 500, [70, 74, 84], a, 'center', [255, 255, 255]);
        ctx.restore();
      }
    }
  }
}

// ------------------------------------------------------------------ 3D 模型
const LIGHT = (() => { const v = [-.4, .5, .8], n = Math.hypot(...v); return v.map((x) => x / n); })();
function drawModel(c, mesh, X, Y, Z, heading, size, bank = 0, pitch = 0, a = 1) {
  const h = rad(heading), b = rad(bank), pt = rad(pitch), ch = Math.cos(h), sh = Math.sin(h);
  const cb = Math.cos(b), sb = Math.sin(b), cp = Math.cos(pt), sp = Math.sin(pt);
  const faces = [];
  for (const [v, col] of mesh) {
    const w = [];
    for (let i = 0; i < v.length; i += 3) {
      let x = v[i] * size, y = v[i + 1] * size, z = v[i + 2] * size;
      [y, z] = [y * cp - z * sp, y * sp + z * cp];
      [x, z] = [x * cb - z * sb, x * sb + z * cb];
      w.push([X + x * ch + y * sh, Y - x * sh + y * ch, Z + z]);
    }
    faces.push([w, col]);
  }
  // 影子
  const sp2 = new Path2D();
  for (const [w] of faces) {
    let ok = true; const pts = w.map((q) => { const r = proj(c, q[0] - q[2] * .55, q[1] - q[2] * .35, 0); if (r[2] < c.near) ok = false; return r; });
    if (!ok) continue;
    pts.forEach((q, i) => i ? sp2.lineTo(q[0], q[1]) : sp2.moveTo(q[0], q[1])); sp2.closePath();
  }
  const altk = clamp(1 - Z / (size * 6));
  ctx.save(); ctx.filter = `blur(${(2 + 8 * (1 - altk)).toFixed(1)}px)`;
  ctx.fillStyle = rgba([20, 30, 50], (.12 + .2 * altk) * a); ctx.fill(sp2); ctx.restore();
  const draw = [];
  for (const [w, col] of faces) {
    const pr = w.map((q) => proj(c, q[0], q[1], q[2]));
    if (pr.some((q) => q[2] < c.near)) continue;
    const e1 = [w[1][0] - w[0][0], w[1][1] - w[0][1], w[1][2] - w[0][2]], e2 = [w[2][0] - w[0][0], w[2][1] - w[0][1], w[2][2] - w[0][2]];
    let n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    const ln = Math.hypot(...n); if (ln < 1e-12) continue; n = n.map((x) => x / ln);
    const cen = [0, 1, 2].map((k) => w.reduce((s, q) => s + q[k], 0) / w.length);
    const view = [c.C[0] - cen[0], c.C[1] - cen[1], c.C[2] - cen[2]];
    if (n[0] * view[0] + n[1] * view[1] + n[2] * view[2] < 0) n = n.map((x) => -x);
    const lit = .45 + .55 * Math.max(0, n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]);
    draw.push([pr.reduce((s, q) => s + q[2], 0) / pr.length, pr, col.map((v) => Math.min(255, v * lit + 10))]);
  }
  draw.sort((p, q) => q[0] - p[0]);
  ctx.save(); ctx.globalAlpha = a; ctx.lineWidth = .6; ctx.lineJoin = 'round';
  for (const [, pr, col] of draw) {
    ctx.beginPath(); pr.forEach((q, i) => i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])); ctx.closePath();
    ctx.fillStyle = ctx.strokeStyle = rgba(col); ctx.fill(); ctx.stroke();
  }
  ctx.restore();
}

// ------------------------------------------------------------------ 航线 / 出租车路线
function drawTrack(c, tr, s, solidW, dash) {
  const n = projArr(c, tr.p);
  const runs = [[], []];                       // 0 未走, 1 已走
  let cur = null, curKind = -1;
  const flush = () => { if (cur && cur.length > 1) runs[curKind].push(cur); cur = null; };
  for (let i = 0; i < n; i++) {
    const ok = PZ[i] > c.near && PX[i] > -400 && PX[i] < W + 400 && PY[i] > -400 && PY[i] < H + 400;
    const kind = tr.cum[i] <= s ? 1 : 0;
    if (!ok) { flush(); continue; }
    if (kind !== curKind) { if (cur && cur.length) { const last = cur[cur.length - 1]; flush(); cur = [last]; } curKind = kind; }
    if (!cur) cur = [];
    cur.push([PX[i], PY[i]]);
  }
  flush();
  const path = (list) => { const p = new Path2D(); for (const r of list) r.forEach((q, i) => i ? p.lineTo(q[0], q[1]) : p.moveTo(q[0], q[1])); return p; };
  const todo = path(runs[0]), done = path(runs[1]);
  if (dash) ctx.setLineDash([16, 12]);
  stroke(todo, BLUE, dash ? 4 : 6, dash ? .5 : .35); ctx.setLineDash([]);
  stroke(done, [255, 255, 255], solidW + 5); stroke(done, BLUE, solidW);
}

// ------------------------------------------------------------------ 卡片 / 标注
function rrect(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function infoCard(a, kicker, title, line, prog) {
  if (a <= 0) return;
  const x = 70, y = 70 + 30 * (1 - a), w = 560, h = 196;
  ctx.save(); ctx.globalAlpha = a;
  ctx.shadowColor = 'rgba(0,0,0,.16)'; ctx.shadowBlur = 18; ctx.shadowOffsetY = 10;
  rrect(x, y, w, h, 26); ctx.fillStyle = 'rgba(255,255,255,.96)'; ctx.fill(); ctx.restore();
  text(kicker, x + 34, y + 46, 20, 400, [120, 128, 140], a);
  text(title, x + 34, y + 100, 40, 700, [28, 32, 40], a);
  text(line, x + 34, y + 142, 22, 400, MUTED, a);
  ctx.globalAlpha = a; rrect(x + 34, y + 160, w - 68, 8, 4); ctx.fillStyle = 'rgb(225,230,238)'; ctx.fill();
  if (prog > 0) { rrect(x + 34, y + 160, (w - 68) * prog, 8, 4); ctx.fillStyle = rgba(BLUE); ctx.fill(); }
  ctx.globalAlpha = 1;
}
function credit(s) { text(s, W - 40, H - 30, 18, 400, [90, 96, 110], .8, 'right', [255, 255, 255]); }
function arrive(c, t) {
  if (t < T.taxi1 - .2) return;
  const [x, y] = proj(c, D.park[0], D.park[1]);
  const kk = eob(P(t, T.taxi1 - .2, .5));
  for (let j = 0; j < 2; j++) {
    const ph = clamp((t - T.taxi1 - j * .3) / 1.3);
    if (ph > 0 && ph < 1) { ctx.strokeStyle = rgba(BLUE, (1 - ph) * .7); ctx.lineWidth = 3; ctx.beginPath(); ctx.ellipse(x, y, 14 + ph * 110, 6 + ph * 50, 0, 0, 7); ctx.stroke(); }
  }
  ctx.save(); ctx.translate(x, y - lerp(140, 0, clamp(kk)));
  const pin = new Path2D(); pin.moveTo(0, 0); pin.bezierCurveTo(-12, -20, -30, -34, -30, -56); pin.arc(0, -56, 30, Math.PI, 0); pin.bezierCurveTo(30, -34, 12, -20, 0, 0); pin.closePath();
  ctx.fillStyle = rgba(BLUE, clamp(kk * 2)); ctx.fill(pin);
  ctx.fillStyle = rgba([255, 255, 255], clamp(kk * 2)); ctx.beginPath(); ctx.arc(0, -56, 11, 0, 7); ctx.fill();
  ctx.restore();
  const q = eo(P(t, T.taxi1 + .2, .6));
  text(D.trip.poi, x - 50, y - 40, 66, 700, INK, q, 'right', [255, 255, 255]);
  text(`${D.trip.poi_sub || D.trip.dest}  到达`, x - 54, y + 8, 28, 400, [90, 98, 112], q, 'right', [255, 255, 255]);
}

// ------------------------------------------------------------------ 手机（屏幕就是地面上的一块区域）
function homography(c) {
  const { f, r, u, C, F, cx, cy } = c, dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const Hm = [[F * r[0] + cx * f[0], F * r[1] + cx * f[1], -F * dot(r, C) - cx * dot(f, C)],
              [-F * u[0] + cy * f[0], -F * u[1] + cy * f[1], F * dot(u, C) - cy * dot(f, C)],
              [f[0], f[1], -dot(f, C)]];
  const k = D.phone.km_per_px, pc = D.phone.center, pw = D.phone.w, ph = D.phone.h;
  const A = [[k, 0, pc[0] - pw / 2 * k], [0, -k, pc[1] + ph / 2 * k], [0, 0, 1]];
  const M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) for (let q = 0; q < 3; q++) M[i][j] += Hm[i][q] * A[q][j];
  return M;
}
function phonePx2ground(px, py) {
  const k = D.phone.km_per_px, pc = D.phone.center;
  return [pc[0] + (px - D.phone.w / 2) * k, pc[1] + (D.phone.h / 2 - py) * k];
}
function rrPts(x, y, w, h, r, n = 10) {          // 圆角矩形轮廓点（手机设计稿坐标）
  const out = [], cs = [[x + w - r, y + r, -90], [x + w - r, y + h - r, 0], [x + r, y + h - r, 90], [x + r, y + r, 180]];
  for (const [cx, cy, a0] of cs) for (let i = 0; i <= n; i++) { const a = rad(a0 + 90 * i / n); out.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]); }
  return out;
}
function drawPhone(c, t, n) {
  // 地图卡片：没有手机外壳，只是一块带厚边的圆角玻璃卡片
  const ps = FR.phone, ui = ps.ui[n], bez = ps.bez[n], open = ps.open[n];
  if (open < 1) {
    const g = ctx.createLinearGradient(0, 0, W, H); g.addColorStop(0, 'rgb(240,241,247)'); g.addColorStop(1, 'rgb(214,217,232)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  const TH = 0.12, SX = 14, SY = 14, SW = D.phone.w - 28, SH = D.phone.h - 28;
  if (bez > 0) {
    const out = rrPts(SX, SY, SW, SH, 52).map(([x, y]) => phonePx2ground(x, y));
    const top = out.map((g) => proj(c, g[0], g[1], 0)), bot = out.map((g) => proj(c, g[0], g[1], -TH));
    ctx.save(); ctx.globalAlpha = bez;
    ctx.filter = 'blur(30px)'; ctx.fillStyle = 'rgba(40,50,90,.22)'; ctx.beginPath();
    bot.forEach((q, i) => i ? ctx.lineTo(q[0], q[1] + 50) : ctx.moveTo(q[0], q[1] + 50)); ctx.fill(); ctx.filter = 'none';
    for (let i = 0; i < out.length; i++) {
      const j = (i + 1) % out.length;
      const cz = (top[j][0] - top[i][0]) * (bot[i][1] - top[i][1]) - (top[j][1] - top[i][1]) * (bot[i][0] - top[i][0]);
      if (cz > 0) continue;
      ctx.fillStyle = 'rgb(236,239,246)'; ctx.beginPath();
      ctx.moveTo(top[i][0], top[i][1]); ctx.lineTo(top[j][0], top[j][1]); ctx.lineTo(bot[j][0], bot[j][1]); ctx.lineTo(bot[i][0], bot[i][1]); ctx.closePath(); ctx.fill();
    }
    ctx.restore();
  }
  const grow = Math.exp(open * 5.5) - 1;
  const win = rrPts(SX - grow * 400, SY - grow * 900, SW + grow * 800, SH + grow * 1800, Math.max(.5, 52 * (1 - open)), 8).map(([x, y]) => phonePx2ground(x, y));
  const nf = frontLine(c);
  let flat = []; for (const g of win) flat.push(g[0], g[1]);
  flat = clipHalf(flat, nf[0], nf[1], nf[2]);
  ctx.save();
  if (open < .999 && flat.length >= 6) {
    const clip = new Path2D();
    for (let i = 0; i < flat.length / 2; i++) { const q = proj(c, flat[2 * i], flat[2 * i + 1]); i ? clip.lineTo(q[0], q[1]) : clip.moveTo(q[0], q[1]); }
    clip.closePath(); ctx.clip(clip);
  }
  drawMap(c);
  drawLabels(c, open > .6);
  drawTrack(c, D.flight, 0, 7, true);
  // 卡片边缘高光
  ctx.restore();
  const uiEl = $('ui');
  if (ui > .002 && !c.fl) {
    const M = homography(c);
    const m = [M[0][0], M[1][0], 0, M[2][0], M[0][1], M[1][1], 0, M[2][1], 0, 0, 1, 0, M[0][2], M[1][2], 0, M[2][2]];
    uiEl.style.transform = `matrix3d(${m.map((v) => v / M[2][2]).join(',')})`;
    uiEl.style.opacity = ui; uiEl.style.display = 'block';
    uiEl.style.filter = `blur(${(ps.blur_in[n] + clamp((ps.u[n] - .3) * 30, 0, 8)).toFixed(1)}px)`;
    drawPhoneUI(t, ui);
  } else uiEl.style.display = 'none';
}
function drawPhoneUI(t, a) {
  const c = uictx, PW = 430, y0 = 500;
  c.clearRect(0, 0, 430, 900);
  c.save(); c.shadowColor = 'rgba(30,40,70,.14)'; c.shadowBlur = 18; c.shadowOffsetY = 6;
  c.fillStyle = 'rgba(255,255,255,.86)'; c.beginPath(); c.roundRect(30, y0, PW - 60, 360, 30); c.fill(); c.restore();
  const tx = (s, x, y, size, w, col, align = 'left') => { c.font = font(size, w); c.textAlign = align; c.fillStyle = rgba(col); c.fillText(s, x, y); };
  const tk = D.trip.ticket || {};
  tx(ticketTag(), 58, y0 + 46, 17, 500, BLUE);
  tx(tk.from || D.trip.origin, 58, y0 + 100, 28, 700, INK); tx(tk.to || D.trip.dest, PW - 58, y0 + 100, 28, 700, INK, 'right');
  tx(tk.dep || '', 58, y0 + 162, 50, 700, INK); tx(tk.arr || '', PW - 58, y0 + 162, 50, 700, INK, 'right');
  tx(tk.from_sub || D.trip.o_code, 58, y0 + 194, 17, 400, MUTED); tx(tk.to_sub || D.trip.d_code, PW - 58, y0 + 194, 17, 400, MUTED, 'right');
  const lp = eio(P(t, T.face, 1.0)), x0 = 58, x1 = PW - 58, yl = y0 + 246;
  c.strokeStyle = 'rgb(205,211,222)'; c.lineWidth = 3; c.setLineDash([8, 8]); c.beginPath(); c.moveTo(x0, yl); c.lineTo(x1, yl); c.stroke(); c.setLineDash([]);
  c.strokeStyle = rgba(BLUE); c.lineWidth = 4; c.beginPath(); c.moveTo(x0, yl); c.lineTo(x0 + (x1 - x0) * lp, yl); c.stroke();
  c.fillStyle = rgba(BLUE); c.beginPath(); c.arc(x0 + (x1 - x0) * lp, yl, 7, 0, 7); c.fill();
  tx('预计飞行时长', 58, y0 + 300, 18, 400, MUTED); tx((D.trip.ticket || {}).dur || '', PW - 58, y0 + 300, 22, 600, BLUE, 'right'); c.textAlign = 'left';
}

// ------------------------------------------------------------------ 地球（WebGL）
const gl = $('globe').getContext('webgl', { premultipliedAlpha: false, alpha: true });
let GL = null;
function initGlobe(imgs) {
  const vs = 'attribute vec2 p; void main(){ gl_Position = vec4(p,0.,1.); }';
  const fs = `precision highp float;
  uniform vec2 res, ctr; uniform float R, tm; uniform mat3 M; uniform vec3 sun;
  uniform sampler2D earth, night, clouds;
  const float PI = 3.14159265;
  vec2 uvOf(vec3 g, float lonOff){ float lon = atan(g.y, g.x) + lonOff; float lat = asin(clamp(g.z,-1.,1.));
    return vec2(fract((lon + PI) / (2.*PI)), (PI/2. - lat) / PI); }
  void main(){
    vec2 px = vec2(gl_FragCoord.x, res.y - gl_FragCoord.y);
    vec2 q = (px - ctr) / R; q.y = -q.y;
    float r2 = dot(q,q);
    if (r2 > 1.) { float rr = sqrt(r2); float g = pow(clamp(1. - (rr - 1.)/.12, 0., 1.), 2.2);
      float side = clamp(dot(q/rr, sun.xy)*.6 + .55, .25, 1.); float a = g*side*.8;
      gl_FragColor = vec4(vec3(120.,175.,255.)/255., a); return; }
    float z = sqrt(1. - r2); vec3 cam = vec3(q, z); vec3 g = M * cam;
    vec3 col = texture2D(earth, uvOf(g, 0.)).rgb;
    float nd = dot(cam, sun); float day = clamp(nd*3. + .5, 0., 1.); float lam = max(nd, 0.);
    col = col*(.1 + lam)*day + col*.06*(1.-day);
    vec3 nl = texture2D(night, uvOf(g, 0.)).rgb; col += nl*1.1*(1.-day)*clamp((nl.r*255. - 40.)/120., 0., 1.);
    float ocean = clamp((col.b - col.r*1.1)*255./40., 0., 1.)*day;
    vec3 hv = normalize(sun + vec3(0.,0.,1.)); col += pow(max(dot(cam,hv),0.), 90.)*ocean*vec3(1.,.94,.86)*.45;
    float cl = texture2D(clouds, uvOf(g, tm*2.5*PI/180.)).r; float ca = clamp((cl - .25)/.6, 0., 1.)*.85;
    vec3 cc = vec3(1.)*(.12 + .95*lam)*day + vec3(.03)*(1.-day); col = col*(1.-ca) + cc*ca;
    float fres = pow(clamp((r2 - .55)/.45, 0., 1.), 2.);
    col = col*(1. - .5*fres) + vec3(110.,170.,255.)/255.*.55*fres*(.25 + .75*day);
    float a = clamp((1. - sqrt(r2))*R, 0., 1.);
    gl_FragColor = vec4(col, a);
  }`;
  const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(s)); return s; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, fs)); gl.linkProgram(pr); gl.useProgram(pr);
  const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  ['earth', 'night', 'clouds'].forEach((name, i) => {
    const tex = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, imgs[name]);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.uniform1i(gl.getUniformLocation(pr, name), i);
  });
  GL = { pr, u: (n) => gl.getUniformLocation(pr, n) };
}
function vec3(lon, lat) { const lo = rad(lon), la = rad(lat); return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)]; }
function globeM(lon0, lat0) {
  const l = rad(lon0), p = rad(lat0);
  return [[-Math.sin(l), Math.cos(l), 0], [-Math.sin(p) * Math.cos(l), -Math.sin(p) * Math.sin(l), Math.cos(p)], [Math.cos(p) * Math.cos(l), Math.cos(p) * Math.sin(l), Math.sin(p)]];
}
const mul = (M, v) => M.map((r) => r[0] * v[0] + r[1] * v[1] + r[2] * v[2]);
function arcPoint(va, vb, k, bow = 0.11) {      // 飞线：球面二次曲线，控制点向东侧移（与 Python arc_point 一致）
  const nrm = (v) => { const l = Math.hypot(...v); return v.map((x) => x / l); };
  const m = nrm([va[0] + vb[0], va[1] + vb[1], va[2] + vb[2]]);
  let n = nrm([va[1] * vb[2] - va[2] * vb[1], va[2] * vb[0] - va[0] * vb[2], va[0] * vb[1] - va[1] * vb[0]]);
  const lm = Math.atan2(m[1], m[0]), east = [-Math.sin(lm), Math.cos(lm), 0];
  if (n[0] * east[0] + n[1] * east[1] < 0) n = n.map((x) => -x);
  const c = nrm([m[0] + n[0] * bow, m[1] + n[1] * bow, m[2] + n[2] * bow]);
  return nrm([0, 1, 2].map((i) => (1 - k) ** 2 * va[i] + 2 * k * (1 - k) * c[i] + k * k * vb[i]));
}
function slerp(a, b, s) {
  const om = Math.acos(clamp(a[0] * b[0] + a[1] * b[1] + a[2] * b[2], -1, 1));
  if (om < 1e-9) return a;
  const k0 = Math.sin((1 - s) * om) / Math.sin(om), k1 = Math.sin(s * om) / Math.sin(om);
  return [a[0] * k0 + b[0] * k1, a[1] * k0 + b[1] * k1, a[2] * k0 + b[2] * k1];
}
const STARS = Array.from({ length: 320 }, (_, i) => { const r = (k) => (Math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1; const a = Math.abs; return [a(r(1)) * W, a(r(2)) * H, .5 + a(r(3)) * 1.2, .15 + a(r(4)) * .65]; });
function drawGlobe(t, n, overlays = true) {
  const [lon0, lat0, R, cx, cy, ak] = D.frames.globe[Math.min(n, D.frames.globe.length - 1)];
  bg.fillStyle = 'rgb(4,6,14)'; bg.fillRect(0, 0, W, H);
  for (const [x, y, r, a] of STARS) { bg.fillStyle = `rgba(220,230,255,${a * (.65 + .35 * Math.sin(t * 1.7 + x))})`; bg.beginPath(); bg.arc(x, y, r, 0, 7); bg.fill(); }
  const M = globeM(lon0, lat0), sun = mul(M, vec3(78, 18));
  gl.viewport(0, 0, W, H); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
  gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.uniform2f(GL.u('res'), W, H); gl.uniform2f(GL.u('ctr'), cx, cy); gl.uniform1f(GL.u('R'), R); gl.uniform1f(GL.u('tm'), t);
  gl.uniformMatrix3fv(GL.u('M'), false, new Float32Array([M[0][0], M[0][1], M[0][2], M[1][0], M[1][1], M[1][2], M[2][0], M[2][1], M[2][2]]));
  gl.uniform3f(GL.u('sun'), ...sun);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  if (!overlays) return;
  // 飞线、城市点（2D 层）
  ctx.clearRect(0, 0, W, H);
  const P3 = (v) => { const q = mul(M, v); return [cx + q[0] * R, cy - q[1] * R, q[2]]; };
  const arc = (a, b, s1, h, col, al, w) => {
    const va = vec3(...D.city_pts[a]), vb = vec3(...D.city_pts[b]); const pts = [];
    for (let i = 0; i <= 90; i++) { const s = s1 * i / 90, v = arcPoint(va, vb, s), k = 1 + h * Math.sin(Math.PI * s); const q = P3([v[0] * k, v[1] * k, v[2] * k]);
      if (q[2] > 0 || Math.hypot(q[0] - cx, q[1] - cy) > R) pts.push(q); }
    if (pts.length < 2) return pts;
    ctx.strokeStyle = rgba(col, al); ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.beginPath(); pts.forEach((q, i) => i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])); ctx.stroke();
    return pts;
  };
  const fade = 1 - P(t, T.xfade[0] - .25, .25);
  const k = ak;
  let pts = [];
  if (k > 0) {
    ctx.save(); ctx.filter = 'blur(5px)'; arc(D.trip.origin, D.trip.dest, k, .1, [255, 200, 110], .7 * fade, 10); ctx.restore();
    pts = arc(D.trip.origin, D.trip.dest, k, .1, [255, 232, 175], fade, 4);
    if (k < 1 && pts.length) { const q = pts[pts.length - 1]; ctx.fillStyle = `rgba(255,255,255,${fade})`; ctx.shadowColor = 'rgba(255,220,150,.9)'; ctx.shadowBlur = 18; ctx.beginPath(); ctx.arc(q[0], q[1], 6, 0, 7); ctx.fill(); ctx.shadowBlur = 0; }
  }
  for (const name of [D.trip.origin, D.trip.dest]) {
    const q = P3(vec3(...D.city_pts[name])); if (q[2] <= 0) continue;
    const a = eo(P(t, .4, .5)) * fade, ph = (t * 1.1) % 1;
    ctx.strokeStyle = `rgba(255,220,150,${(1 - ph) * .8 * a})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(q[0], q[1], 7 + ph * 26, 0, 7); ctx.stroke();
    ctx.fillStyle = `rgba(255,255,255,${a})`; ctx.beginPath(); ctx.arc(q[0], q[1], 5.5, 0, 7); ctx.fill();
    text(name, q[0] + 16, q[1] + 9, 30, 600, [255, 255, 255], a, 'left', [10, 20, 40]);
  }
}

// ------------------------------------------------------------------ 每帧
function frame(t) {
  const n = clamp(Math.round(t * D.fps), 0, D.n - 1);
  const xf0 = T.xfade[0], xf1 = T.xfade[0] + T.xfade[1];
  const globeOn = t < xf1;
  $('globe').style.display = $('bg').style.display = globeOn ? 'block' : 'none';
  if (t < xf0) {
    $('ui').style.display = 'none'; $('map').style.filter = 'none'; $('map').style.opacity = 1;
    drawGlobe(t, n);
    return;
  }
  if (globeOn) drawGlobe(t, n, false);
  $('map').style.opacity = globeOn ? eio((t - xf0) / T.xfade[1]) : 1;
  const c = camAt(n);
  ctx.clearRect(0, 0, W, H);
  // 冲进屏幕时按相机速度加一点动态模糊
  const n2 = Math.min(n + 1, D.n - 1), k = FR.cam;
  const speed = Math.abs(Math.log(k.dist[n2] / k.dist[n])) * 60 + Math.abs(k.pitch[n2] - k.pitch[n]) * .6;
  $('map').style.filter = (t > T.flyin && t < T.dive1 + .3) ? `blur(${clamp(speed * 1.6 - 1, 0, 5).toFixed(1)}px)` : 'none';
  if (t < T.dive1) {
    drawPhone(c, t, n);
    const pa = eo(P(t, T.fly0 - .8, .6));
    if (pa > 0) drawPlane(c, D.n0, pa, true);
  } else {
    $('ui').style.display = 'none';
    if (t < T.landed + .6) {
      drawMap(c);
      const s = FR.plane.s[n];
      drawTrack(c, D.flight, s, 7, true);
      drawLabels(c);
      drawPlane(c, n, 1 - P(t, T.landed, .5), false);
      const prog = clamp(s / D.flight.L);
      infoCard(eo(P(t, T.fly0 + .3, .5)) * (1 - P(t, T.landed, .4)), ticketTag(), `${D.trip.o_code || D.trip.origin}  →  ${D.trip.d_code || D.trip.dest}`,
        `已飞 ${Math.round(D.flight.km * prog).toLocaleString()} km / 约 ${Math.round(D.flight.km).toLocaleString()} km`, prog);
      if (t < T.landed) credit('地图数据 © OpenStreetMap 贡献者 · Natural Earth');
    }
    if (t >= T.landed) {
      if (t >= T.landed + .6) drawMap(c);
      const s = FR.car.s[n];
      drawTrack(c, D.taxi, s, 9, false);
      let res = [];
      if (t > T.taxi1 - .6) { const [x, y] = proj(c, D.park[0], D.park[1]); res = [[x - 470, y - 110, x + 40, y + 30]]; }
      drawLabels(c, true, res);
      const ta = eo(P(t, T.taxi0 - .5, .5));
      if (ta > 0) drawModel(c, D.models.car, FR.car.x[n], FR.car.y[n], 0, FR.car.head[n], Math.min(.36, Math.max(.05, c.dist * .12)), 0, 0, ta);
      arrive(c, t);
      const kk = s / D.taxi.L;
      infoCard(eo(P(t, T.taxi0 - .2, .5)), '出租车 · 路线估算', `${D.trip.d_air}  →  ${D.trip.poi}`, `${(D.taxi.km * kk).toFixed(1)} / ${D.taxi.km.toFixed(1)} km · 约 ${Math.round(D.taxi.min)} 分钟`, kk);
      credit('地图数据 © OpenStreetMap 贡献者 · 路线 OSRM');
    }
  }
}
function ticketTag() { const tk = D.trip.ticket || {}; return `${tk.flight || ''}${tk.demo === false ? '' : ' · 示意航班'}`; }
function drawPlane(c, n, a, parked) {
  const p = FR.plane, m = parked ? D.n0 : n;
  const size = c.dist * .09 + .05;
  const alt = parked ? 0 : p.alt[m];
  drawModel(c, D.models.plane, p.x[m], p.y[m], alt * c.dist * .085 + size * .07, p.head[m], size, parked ? 0 : p.bank[m], parked ? 0 : p.climb[m], a);
}

// ------------------------------------------------------------------ 播放控制
let t0 = performance.now(), cur = 0, playing = false, speed = 1, loop = true;
function fit() {
  const wrap = $('wrap'), s = Math.min(wrap.clientWidth / W, wrap.clientHeight / H);
  const st = $('stage'); st.style.transform = `scale(${s})`;
  st.style.marginLeft = `${(wrap.clientWidth - W * s) / 2}px`; st.style.marginTop = `${(wrap.clientHeight - H * s) / 2}px`;
  wrap.style.display = 'block';
}
window.addEventListener('resize', fit);
function tick(now) {
  if (playing) {
    cur += (now - t0) / 1000 * speed;
    if (cur >= D.dur) { if (loop) { cur = 0; LABEL_A.clear(); } else { cur = D.dur - 1e-3; playing = false; $('play').textContent = '播放'; } }
  }
  t0 = now;
  frame(cur);
  $('seek').value = cur; $('time').textContent = `${cur.toFixed(2)} / ${D.dur.toFixed(2)} s`;
  requestAnimationFrame(tick);
}
$('play').onclick = () => { playing = !playing; $('play').textContent = playing ? '暂停' : '播放'; };
$('seek').oninput = (e) => { cur = +e.target.value; LABEL_A.clear(); };
$('speed').onchange = (e) => { speed = +e.target.value; };
$('loop').onclick = () => { loop = !loop; $('loop').textContent = `循环：${loop ? '开' : '关'}`; };
window.addEventListener('keydown', (e) => { if (e.code === 'Space') { e.preventDefault(); $('play').click(); } });

(async () => {
  D = await (await fetch('data.json')).json();
  T = D.T; FR = D.frames;
  prep(D.base.land); prep(D.base.lakes); prep(D.base.rivers); prep(D.base.coast); prep(D.base.urban); prep(D.base.roads);
  for (const c of Object.values(D.cities)) for (const L of c.layers) prep(L.f);
  D.flight.p = Float32Array.from(D.flight.p); D.taxi.p = Float32Array.from(D.taxi.p);
  D.placesSorted = D.places.map((p, i) => [i, p]).sort((a, b) => a[1][3] - b[1][3] || (a[1][2] < b[1][2] ? -1 : 1));
  D.roadsSorted = D.roads.map((r) => { const xy = Float32Array.from(r[1]); let sx = 0, sy = 0; for (let i = 0; i < xy.length; i += 2) { sx += xy[i]; sy += xy[i + 1]; }
    const o = [r[0], xy, r[2], r[3]]; o.cx = sx / (xy.length / 2); o.cy = sy / (xy.length / 2);
    // 地面中点锚点：所在线段 ai 和段内比例 af
    const segs = []; let L = 0; for (let i = 2; i < xy.length; i += 2) { const d = Math.hypot(xy[i] - xy[i - 2], xy[i + 1] - xy[i - 1]); segs.push(d); L += d; }
    let acc = 0; o.ai = 0; o.af = .5;
    for (let i = 0; i < segs.length; i++) { if (acc + segs[i] >= L / 2) { o.ai = i; o.af = segs[i] > 0 ? (L / 2 - acc) / segs[i] : .5; break; } acc += segs[i]; }
    return o; }).sort((a, b) => a[2] - b[2] || b[3] - a[3]);
  D.n0 = Math.round(T.fly0 * D.fps);
  $('seek').max = D.dur;
  const load = (src) => new Promise((ok) => { const im = new Image(); im.onload = () => ok(im); im.src = src; });
  const [earth, night, clouds] = await Promise.all([load('earth.jpg'), load('night.jpg'), load('clouds.jpg')]);
  initGlobe({ earth, night, clouds });
  $('loading').remove();
  fit();
  const q = new URLSearchParams(location.search);
  if (q.has('t')) cur = +q.get('t');
  if (q.has('play')) { playing = true; $('play').textContent = '暂停'; }
  requestAnimationFrame(tick);
})();
