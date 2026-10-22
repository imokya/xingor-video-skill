// v4：借鉴参考 1 的「每章一种材质」—— 暖黑金尘 / 方格纸墨水 / 黑板粉笔 / 暗红暗房
// 原则：字一律清晰；一屏一件事；标题区 180–330 / 主视觉 380–1150 / 字幕 1260，互不重叠
import { keys, clamp01, smooth, mulberry32 } from '../../scripts/web/util.js';

export const W = 1080, H = 1440, FPS = 60, DUR = 165.0;
const out = document.getElementById('c'); out.width = W; out.height = H;
const g = out.getContext('2d');
const VO = await (await fetch('/vo/full/vo.json')).json();
const AT = await (await fetch('/vo/times.json')).json();
const LINES = VO.map(x => x.text);
const SRC = (await (await fetch(import.meta.url)).text()).split('\n').filter(l => l.trim() && l.length < 140);   // 本片自己的源码，结尾用
const ramp = (t, a, b) => smooth(clamp01((t - a) / (b - a)));
const win = (t, a, b, f = 0.5) => ramp(t, a, a + f) * (1 - ramp(t, b - f, b));
const back = x => { x = clamp01(x); const c = 1.6; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2; };
const SERIF = (w, s) => `${w} ${s}px "Songti SC", "STSong", serif`;
const SANS = (w, s) => `${w} ${s}px "PingFang SC"`;
const THIN = s => `200 ${s}px "Helvetica Neue"`;
const TYPE = s => `${s}px "American Typewriter", "Courier New", monospace`;
const CX = W / 2, SUB_Y = 1262;
const hash = i => { const s = Math.sin(i * 12.9898 + 78.233) * 43758.5453; return s - Math.floor(s); };
// 调色板
const GOLD = '#e9c77f', GOLD2 = '#f6dfa6', CREAM = '#efe7d6', INK = '#2b2723', RED = '#c4472f', BLUE = '#2f5577';
const CHALK = '#eeeee4', CHALKY = '#f0d77a', CHALKR = '#e6875e';

// ---------- 通用 ----------
function rr(x, y, w, h, r) { g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath(); }
function txt(s, x, y, font, col, a = 1, align = 'center', sp = 0, glow = 0) {
  if (a <= 0) return; g.save(); g.globalAlpha *= a; g.font = font; g.fillStyle = col; g.textAlign = align; g.letterSpacing = sp + 'px';
  if (glow) { g.shadowColor = col; g.shadowBlur = glow * 0.35; } g.fillText(s, x, y); g.restore();
}
// 标题：宋体，逐字淡入（只在开头一瞬带轻微模糊，成形后锐利）
function title(s, x, y, size, col, t, t0, o = {}) {
  const stag = o.stag ?? 0.06, sp = o.sp ?? size * 0.1, outK = o.out ? ramp(t, o.out - 0.5, o.out) : 0;
  if (t < t0 || outK >= 1) return;
  g.save(); g.font = SERIF(o.w || 600, size);
  const ch = [...s], ws = ch.map(c => g.measureText(c).width + sp), tot = ws.reduce((m, v) => m + v, 0) - sp; let cx = x - tot / 2;
  ch.forEach((c, i) => {
    const k = smooth(clamp01((t - t0 - i * stag) / 0.7)), a = k * (1 - outK);
    if (a > 0) { g.save(); g.globalAlpha *= a; if (k < 1) g.filter = `blur(${(1 - k) * 8}px)`; g.fillStyle = col; if (o.glow) { g.shadowColor = col; g.shadowBlur = o.glow * 0.35; } g.fillText(c, cx, y + (1 - k) * 10); g.restore(); }
    cx += ws[i];
  });
  g.restore();
}
// 书写揭示：从左到右露出（墨水 / 粉笔）
function reveal(fn, x0, w, k) { if (k <= 0) return; g.save(); g.beginPath(); g.rect(x0 - 20, -H, (w + 40) * k, 3 * H); g.clip(); fn(); g.restore(); }

// ---------- 材质 ----------
const R = mulberry32(9);
const DUST = Array.from({ length: 220 }, () => [R() * W, R() * H, 0.3 + R() * 0.7, R() * 6.28]);
function matDark(t) {
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#0e0c0a'); bg.addColorStop(0.6, '#17130f'); bg.addColorStop(1, '#1e1913');
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  const gr = g.createRadialGradient(CX, 700, 0, CX, 700, 800); gr.addColorStop(0, 'rgba(233,199,127,0.07)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, y, z, ph] of DUST) { const Y = ((y - t * 7 * z) % H + H) % H; g.globalAlpha = 0.06 + 0.22 * z * (0.6 + 0.4 * Math.sin(t * 1.3 + ph)); g.fillStyle = GOLD; g.beginPath(); g.arc(x + Math.sin(t * 0.4 + ph) * 12, Y, 0.6 + 1.2 * z, 0, 7); g.fill(); }
  g.restore();
}
let PAPER = null;
function matPaper() {
  if (!PAPER) {
    PAPER = document.createElement('canvas'); PAPER.width = W; PAPER.height = H; const m = PAPER.getContext('2d'), r = mulberry32(4);
    m.fillStyle = CREAM; m.fillRect(0, 0, W, H);
    for (let i = 0; i < 26000; i++) { m.fillStyle = `rgba(110,90,60,${r() * 0.05})`; m.fillRect(r() * W, r() * H, 1.3, 1.3); }
    for (let x = 0; x <= W; x += 24) { m.strokeStyle = x % 120 === 0 ? 'rgba(120,140,150,0.22)' : 'rgba(120,140,150,0.09)'; m.lineWidth = 1; m.beginPath(); m.moveTo(x + 0.5, 0); m.lineTo(x + 0.5, H); m.stroke(); }
    for (let y = 0; y <= H; y += 24) { m.strokeStyle = y % 120 === 0 ? 'rgba(120,140,150,0.22)' : 'rgba(120,140,150,0.09)'; m.beginPath(); m.moveTo(0, y + 0.5); m.lineTo(W, y + 0.5); m.stroke(); }
    const v = m.createRadialGradient(CX, H / 2, 300, CX, H / 2, 1000); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(70,50,20,0.22)'); m.fillStyle = v; m.fillRect(0, 0, W, H);
  }
  g.drawImage(PAPER, 0, 0);
}
let BOARD = null;
function matBoard() {
  if (!BOARD) {
    BOARD = document.createElement('canvas'); BOARD.width = W; BOARD.height = H; const m = BOARD.getContext('2d'), r = mulberry32(6);
    const bg = m.createLinearGradient(0, 0, W, H); bg.addColorStop(0, '#22382e'); bg.addColorStop(1, '#1a2c24'); m.fillStyle = bg; m.fillRect(0, 0, W, H);
    for (let i = 0; i < 70; i++) { const x = r() * W, y = r() * H, rad = 80 + r() * 260, gr = m.createRadialGradient(x, y, 0, x, y, rad); gr.addColorStop(0, `rgba(220,230,220,${0.02 + r() * 0.03})`); gr.addColorStop(1, 'rgba(220,230,220,0)'); m.fillStyle = gr; m.fillRect(x - rad, y - rad, rad * 2, rad * 2); }   // 擦痕
    for (let i = 0; i < 30000; i++) { m.fillStyle = `rgba(255,255,255,${r() * 0.035})`; m.fillRect(r() * W, r() * H, 1.2, 1.2); }
    const v = m.createRadialGradient(CX, H / 2, 300, CX, H / 2, 1000); v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(0,0,0,0.35)'); m.fillStyle = v; m.fillRect(0, 0, W, H);
  }
  g.drawImage(BOARD, 0, 0);
}
function matDarkroom(t) {
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#1a0807'); bg.addColorStop(0.5, '#2a0d0b'); bg.addColorStop(1, '#160606'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  const gr = g.createRadialGradient(CX, 260, 0, CX, 260, 900); gr.addColorStop(0, `rgba(210,60,40,${0.22 + 0.03 * Math.sin(t * 2)})`); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
}
// 粉笔字：先画字，再用噪点抠掉一部分像素，得到粉笔颗粒感（结果缓存）
const CHALK_CACHE = new Map();
function chalkText(s, size, col, w = 500) {
  const key = s + size + col + w; if (CHALK_CACHE.has(key)) return CHALK_CACHE.get(key);
  const c = document.createElement('canvas'), m = c.getContext('2d'); m.font = SERIF(w, size);
  const tw = Math.ceil(m.measureText(s).width + 20), th = Math.ceil(size * 1.4); c.width = tw; c.height = th;
  m.font = SERIF(w, size); m.textBaseline = 'middle'; m.fillStyle = col; m.fillText(s, 10, th / 2); m.globalAlpha = 0.5; m.fillText(s, 11, th / 2 + 0.6);
  m.globalCompositeOperation = 'destination-out'; const r = mulberry32(s.length * 31 + size);
  for (let i = 0; i < tw * th * 0.09; i++) { m.globalAlpha = 0.25 + r() * 0.55; m.fillRect(r() * tw, r() * th, 1 + r() * 1.6, 1 + r() * 1.2); }
  const o = { c, w: tw, h: th }; CHALK_CACHE.set(key, o); return o;
}
function chalk(s, x, y, size, col, k, align = 'center', w = 500) {
  if (k <= 0) return; const o = chalkText(s, size, col, w), x0 = align === 'center' ? x - o.w / 2 : align === 'right' ? x - o.w : x;
  reveal(() => g.drawImage(o.c, x0, y - o.h / 2), x0, o.w, k);
  return o.w;
}
function chalkLine(pts, col, wdt, k, seed = 1) {   // 粉笔线：略抖动的折线，按进度画出
  if (k <= 0) return; const r = mulberry32(seed); g.save(); g.strokeStyle = col; g.lineWidth = wdt; g.lineCap = 'round'; g.globalAlpha *= 0.85;
  const n = Math.max(2, Math.floor(pts.length * k)); g.beginPath();
  for (let i = 0; i < n; i++) { const [x, y] = pts[i]; i ? g.lineTo(x + (r() - 0.5) * 1.5, y + (r() - 0.5) * 1.5) : g.moveTo(x, y); }
  g.stroke(); g.restore();
}
const bez = (x1, y1, cx, cy, x2, y2, n = 40) => Array.from({ length: n + 1 }, (_, i) => { const s = i / n; return [(1 - s) ** 2 * x1 + 2 * (1 - s) * s * cx + s * s * x2, (1 - s) ** 2 * y1 + 2 * (1 - s) * s * cy + s * s * y2]; });
// 墨水斜线填充的柱子
function hatchBar(x, y, w, h, col, sel) {
  if (h < 1) return; g.save(); g.strokeStyle = col; g.lineWidth = 2.2; g.strokeRect(x, y, w, h);
  g.beginPath(); g.rect(x, y, w, h); g.clip(); g.lineWidth = sel ? 2.4 : 1.4; g.globalAlpha *= sel ? 0.9 : 0.55;
  for (let k = -h; k < w + h; k += sel ? 9 : 13) { g.beginPath(); g.moveTo(x + k, y + h); g.lineTo(x + k + h, y); g.stroke(); }
  g.restore();
}

// ================= 1 钩子：荧光蒲公英——每颗种子带着一个字，AI 一颗颗挑来拼成句子，风一吹全散了 =================
const REPLY = '今天天气真', C1 = [['好', .62], ['不错', .15], ['热', .09], ['冷', .06], ['晴', .04]];
function matTeal(t) {   // 深青夜色
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#0b161d'); bg.addColorStop(0.55, '#12303a'); bg.addColorStop(1, '#1c4848'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, y, z, ph] of DUST) { const Y = ((y - t * 9 * z) % H + H) % H; g.globalAlpha = 0.05 + 0.18 * z * (0.6 + 0.4 * Math.sin(t * 1.3 + ph)); g.fillStyle = '#bfe8e0'; g.beginPath(); g.arc(x + Math.sin(t * 0.4 + ph) * 12, Y, 0.5 + z, 0, 7); g.fill(); }
  g.restore();
}
const HX = CX, HY = 950, HR = 225, SY = 330, HSENT = '今天天气真好，适合出门散步。';
const HGLY = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经天气好今真阳光雨风云花';
const DSEED = Array.from({ length: 210 }, (_, i) => { const u = 1 - 2 * (i + 0.5) / 210, th = i * 2.39996, s = Math.sqrt(1 - u * u), x = s * Math.cos(th), z = s * Math.sin(th); return { x, y: u * -1, z, c: HGLY[(hash(i + 70) * HGLY.length) | 0], h: hash(i + 71), h2: hash(i + 72), ph: hash(i + 73) * 6.28 }; });
// 拼句子用的种子（偏上、偏前的那些），每个字再配两颗「落选」的种子
const HPOOL = DSEED.map((s, i) => i).filter(i => DSEED[i].z > -0.2).sort((a, b) => DSEED[a].y - DSEED[b].y);
const HTYPE = [...HSENT].map((c, i) => ({ c, seed: HPOOL[i * 3], dec: [HPOOL[i * 3 + 1], HPOOL[i * 3 + 2]], l0: 0.5 + i * 0.17 }));
HTYPE.forEach((o, i) => { DSEED[o.seed].c = o.c; DSEED[o.seed].used = 1; o.dec.forEach((d, j) => { DSEED[d].used = 1; if (i === 5) DSEED[d].c = ['不错', '热'][j]; }); });
DSEED.forEach((s, i) => { s.rel = 3.0 + (1 - (s.x + 1) / 2) * 0.6 + s.h * 0.9; });
const tipOf = s => [HX + s.x * HR, HY + s.y * HR];
function seedGlyph(x, y, ang, c, size, a) {   // 一颗飞着的种子：冠毛（一圈细丝）+ 字 + 细柄
  if (a <= 0.01) return;
  g.save(); g.translate(x, y); g.globalAlpha *= a; g.strokeStyle = 'rgba(200,238,230,0.38)'; g.lineWidth = 0.8;
  const r = size * 0.85; g.beginPath(); for (let k = 0; k < 11; k++) { const an = ang - 1.3 + k / 10 * 2.6; g.moveTo(Math.cos(an) * r * 0.45, Math.sin(an) * r * 0.45); g.lineTo(Math.cos(an) * r, Math.sin(an) * r); } g.stroke();
  g.beginPath(); g.moveTo(-Math.cos(ang) * r * 0.5, -Math.sin(ang) * r * 0.5); g.lineTo(-Math.cos(ang) * r * 1.4, -Math.sin(ang) * r * 1.4); g.stroke();
  g.fillStyle = '#e4f5f0'; g.shadowColor = 'rgba(160,240,220,0.9)'; g.shadowBlur = 6; g.font = SERIF(500, size); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(c, 0, 0);
  g.restore();
}
const qb = (a, b, c, e) => (1 - e) ** 2 * a + 2 * (1 - e) * e * b + e * e * c;
const gust = (x0, y0, s, dt) => [x0 + (90 + 200 * s.h) * dt + Math.sin(dt * 1.3 + s.ph) * 40 * dt - 60 * (s.h2 - 0.5) * dt, y0 - (40 + 150 * s.h2) * dt - 8 * dt * dt + Math.sin(dt * 2 + s.ph) * 30];
function sHook(t) {
  matTeal(t);
  title('它连下一个字', CX, 700, 104, 'rgba(200,232,226,0.30)', t, 4.4, { w: 600 });
  title('都不知道', CX, 860, 150, 'rgba(200,232,226,0.30)', t, 5.0, { w: 800, stag: 0.12 });
  const fin = ramp(t, 0, 0.6), out = 1 - ramp(t, 7.3, 8.0);
  // 花茎 + 花托
  g.save(); g.globalAlpha = fin; g.strokeStyle = 'rgba(170,222,212,0.5)'; g.lineWidth = 2.2; g.beginPath(); g.moveTo(CX + 30, H); g.quadraticCurveTo(CX + 40, HY + 200, HX, HY + 6); g.stroke();
  g.fillStyle = '#d8f0e8'; g.shadowColor = 'rgba(160,240,220,0.8)'; g.shadowBlur = 10; g.beginPath(); g.arc(HX, HY, 7, 0, 7); g.fill(); g.restore();
  // 还长在花上的种子（按深度排序，后面的暗）
  const onHead = DSEED.filter(s => !(s.used && t > 0.4) && t < s.rel).sort((a, b) => a.z - b.z);
  g.save(); g.globalAlpha = fin;
  for (const s of onHead) {
    if (s.used) { const o = HTYPE.find(o => o.seed === DSEED.indexOf(s) || o.dec.includes(DSEED.indexOf(s))); if (o && t >= o.l0) continue; }
    const [x, y] = tipOf(s), d = 0.5 + 0.5 * s.z, sway = Math.sin(t * 1.2 + s.ph) * 2;
    g.strokeStyle = `rgba(190,232,224,${0.10 + 0.25 * d})`; g.lineWidth = 0.8; g.beginPath(); g.moveTo(HX, HY); g.lineTo(x + sway, y); g.stroke();
    g.save(); g.globalAlpha *= 0.25 + 0.75 * d; g.fillStyle = '#dff3ee'; g.font = SERIF(500, Math.round(14 + 9 * d)); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s.c, x + sway, y); g.restore();
  }
  g.restore();
  // 拼句子：选中的种子飞到句子里；两颗落选的飞到旁边，又飘走
  g.font = SERIF(500, 52); const tw = g.measureText(HSENT).width; let sx = CX - tw / 2, lastX = sx;
  HTYPE.forEach((o, i) => {
    const cw = g.measureText(o.c).width, slot = [sx + cw / 2, SY - 18]; sx += cw;
    const s = DSEED[o.seed], [x0, y0] = tipOf(s), e = smooth(clamp01((t - o.l0) / 0.85)), bt = 4.0 + i * 0.06;
    if (t >= o.l0) o.dec.forEach((di, j) => {
      const ds = DSEED[di], [a0, b0] = tipOf(ds), side = j ? 1 : -1, tx = slot[0] + side * (70 + 40 * ds.h), ty = slot[1] - 60 - 50 * ds.h2, k = (t - o.l0) / 0.85;
      const kk = smooth(clamp01(k)), x = qb(a0, a0 + side * 160, tx, kk), y = qb(b0, (b0 + ty) / 2, ty, kk), dr = Math.max(0, k - 1) * 0.85;
      seedGlyph(x + side * 60 * dr, y - 70 * dr, -Math.PI / 2, ds.c, 16 + 10 * kk, (i === 5 ? 0.75 : 0.5) * (1 - clamp01(dr / 0.9)));
    });
    if (t < o.l0) return;
    if (e < 1) { const x = qb(x0, x0 + (s.h - 0.5) * 420, slot[0], e), y = qb(y0, (y0 + slot[1]) / 2 + 80, slot[1], e); seedGlyph(x, y, -Math.PI / 2, o.c, 16 + 36 * e ** 3, 1); return; }
    lastX = sx;
    if (t < bt) { txt(o.c, slot[0], SY, SERIF(500, 52), '#e4f5f0', 1, 'center', 0, 6); return; }
    const [x, y] = gust(slot[0], slot[1], s, t - bt); seedGlyph(x, y, -Math.PI / 2 + 0.4, o.c, 52 - 26 * ramp(t, bt, bt + 1.2), out);
  });
  if (t > 0.5 && t < 4.0 && Math.floor(t * 2.4) % 2 === 0) { g.fillStyle = '#cfe9e3'; g.fillRect(lastX + 6, SY - 42, 3, 50); }
  // 风来了：整朵蒲公英散开，满天都是字
  for (const s of DSEED) {
    if (s.used || t < s.rel) continue; const dt = t - s.rel, [x0, y0] = tipOf(s), [x, y] = gust(x0, y0, s, dt);
    seedGlyph(x, y, -Math.PI / 2 + 0.5 + Math.sin(dt + s.ph) * 0.3, s.c, 14 + 14 * s.h2 * ramp(dt, 0, 1.5) + 5 * (0.5 + 0.5 * s.z), out * (0.4 + 0.6 * (0.5 + 0.5 * s.z)) * ramp(dt, 0, 0.3));
  }
  txt('每一步，都要从几万个字里挑一个', CX, 430, SERIF(400, 32), '#a9cec8', win(t, 1.2, 3.8), 'center', 4);
}
// ================= 2 文字接龙（方格纸 + 墨水图表）=================
const ROUNDS = [
  { s: '今天天气真', c: C1, t0: 11.8, tp: 14.2, tf: 15.0 },
  { s: '今天天气真好', c: [['，', .48], ['啊', .21], ['！', .14], ['呀', .09], ['。', .08]], t0: 15.4, tp: 16.2, tf: 16.8 },
  { s: '今天天气真好，', c: [['适合', .35], ['我们', .22], ['出去', .18], ['心情', .12], ['阳光', .08]], t0: 17.0, tp: 17.6, tf: 18.1 },
];
const FINAL = '今天天气真好，适合出门散步。';
// 「接龙」：一串字像龙一样游动，最后头五个字落下，成为「今天天气真 ＿」
const DRAG = [...'今天天气真好适合出门散步阳光不燥微风正好'];
const dragonPos = u => [CX + 380 * Math.sin(1.25 * u), 770 + 220 * Math.sin(2.1 * u + 0.6)];
function dragon(t) {
  const a = ramp(t, 7.9, 8.5), u0 = 1.0 + (t - 7.6) * 1.0, gone = ramp(t, 9.3, 9.9);
  g.font = SERIF(600, 80); const full = '今天天气真＿', fw = g.measureText(full).width; let lx = CX - fw / 2;
  const slots = [...'今天天气真'].map(c => { const w = g.measureText(c).width, x = lx + w / 2; lx += w; return x; });
  g.save(); g.strokeStyle = 'rgba(43,39,35,0.22)'; g.lineWidth = 1.2; g.globalAlpha = a * (1 - gone); g.beginPath();
  for (let k = 0; k <= 120; k++) { const [x, y] = dragonPos(u0 + 0.05 - k * 0.025); k ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); g.restore();
  // 按弧长等距排字：从龙头往回走，每 50px 放一个字
  const P = []; { let u = u0, [lx0, ly0] = dragonPos(u), acc = 0; P.push([lx0, ly0, 0]); while (P.length < DRAG.length && u > u0 - 12) { u -= 0.004; const [x, y] = dragonPos(u); acc += Math.hypot(x - lx0, y - ly0); if (acc >= 50) { P.push([x, y, Math.atan2(ly0 - y, lx0 - x)]); acc = 0; } lx0 = x; ly0 = y; } }
  DRAG.forEach((c, i) => {
    if (!P[i]) return; const [px, py, tan] = P[i], ang0 = 0.3 * Math.sin(tan);
    const land = i < 5 ? smooth(clamp01((t - 9.3 - i * 0.07) / 0.8)) : 0, size = 46 - i * 1.1;
    const x = px + ((slots[i] ?? px) - px) * land, y = py + (592 - py) * land, sz = size + (80 - size) * land, ang = ang0 * (1 - land);
    g.save(); g.translate(x, y); g.rotate(ang); txt(c, 0, sz * 0.35, SERIF(600, sz), i === 0 && land < 0.5 ? RED : INK, a * (i < 5 ? 1 : 1 - gone)); g.restore();
  });
  const uw = g.measureText('＿').width; txt('＿', CX + fw / 2 - uw / 2, 620, SERIF(600, 80), INK, ramp(t, 10.1, 10.5));
}
function inkBar(x, y, w, h, col, sel, t, seed) {   // 墨水注满的柱子：液面轻轻晃
  if (h < 1) return; const wave = xx => y + Math.sin(t * 5 + seed * 2 + xx * 0.08) * Math.min(4, h * 0.1);
  g.save(); g.beginPath(); g.moveTo(x, y + h); for (let k = 0; k <= 10; k++) g.lineTo(x + w * k / 10, wave(w * k / 10)); g.lineTo(x + w, y + h); g.closePath();
  g.fillStyle = sel ? 'rgba(196,71,47,0.10)' : 'rgba(43,39,35,0.06)'; g.fill(); g.strokeStyle = col; g.lineWidth = 2.2; g.stroke(); g.clip();
  g.lineWidth = sel ? 2.4 : 1.4; g.globalAlpha *= sel ? 0.9 : 0.55; for (let k = -h; k < w + h; k += sel ? 9 : 13) { g.beginPath(); g.moveTo(x + k, y + h); g.lineTo(x + k + h, y - 10); g.stroke(); }
  g.restore();
}
const FASTC = ['出', '门', '散', '步', '。'];
function sChain(t) {
  matPaper();
  title('文字接龙', CX, 270, 104, INK, t, 8.2);
  txt('每一步，只猜下一个字', CX, 340, SERIF(500, 34), '#6b6256', ramp(t, 8.8, 9.4), 'center', 6);
  if (t < 11.0) { dragon(t); return; }
  let r = ROUNDS[0]; for (const x of ROUNDS) if (t >= x.t0) r = x;
  const fast = clamp01((t - 18.3) / 1.8), fk = Math.min(4, Math.floor(fast * 5));
  let sent = t >= r.tf ? r.s + r.c[0][0] : r.s; if (t >= 18.3) sent = FINAL.slice(0, 9 + Math.ceil(fast * 5));
  // 句子：从「龙」落下的位置，平滑移到上方并缩小；末尾始终留一个「＿」= 下一个字
  const m = smooth(clamp01((t - 11.0) / 0.8)), size = 80 + (60 - 80) * m, sy = 620 + (520 - 620) * m, done = t > 20.1;
  const show = done ? sent : sent + '＿'; g.font = SERIF(600, size); const sw = g.measureText(show).width, sx0 = CX - sw / 2;
  txt(show, sx0, sy, SERIF(600, size), INK, 1, 'left');
  const blankX = sx0 + g.measureText(sent).width + g.measureText('＿').width / 2;
  const ax = ramp(t, 11.2, 11.9);   // 坐标轴画出来，而不是一下出现
  g.strokeStyle = 'rgba(43,39,35,0.6)'; g.lineWidth = 2; g.beginPath(); g.moveTo(CX - 420, 548); g.lineTo(CX - 420 + 840 * ax, 548); g.stroke();
  txt(`第 ${t < 18.3 ? ROUNDS.indexOf(r) + 1 : 4 + fk} 步`, CX - 420, 440, SERIF(500, 30), RED, ax, 'left');
  const bx = CX - 380, by = 1060, bw = 760, bh = 380;
  g.save(); g.strokeStyle = INK; g.lineWidth = 2.4; g.beginPath(); g.moveTo(bx, by - (bh + 20) * ax); g.lineTo(bx, by); g.lineTo(bx + bw * ax, by); g.stroke(); g.restore();
  txt('概率', bx - 14, by - bh - 34, SERIF(500, 26), '#6b6256', ax, 'left');
  // 每一轮（快进阶段也一样）：柱子长出来 → 红笔在候选之间来回跳，越来越慢，停在一个上 → 这个字飞进句子
  let cands, t0, tp, tf;
  if (t < 18.3) ({ c: cands, t0, tp, tf } = r);
  else { const st = 18.3 + fk * 0.36; t0 = st; tp = st + 0.2; tf = st + 0.34; cands = [[FASTC[fk], 0.4 + hash(fk) * 0.3], ...[0, 1, 2, 3].map(j => [GL[(hash(fk * 9 + j) * GL.length) | 0], 0.25 * hash(fk * 5 + j)])]; }
  const grow = clamp01((t - t0) / (t < 18.3 ? 0.9 : 0.2)), ch = ramp(t, tp, tp + 0.25), fly = clamp01((t - tp - 0.1) / Math.max(0.15, tf - tp - 0.1));
  const xs = i => bx + 40 + i * 145 + 50;
  cands.forEach(([c, p], i) => {
    const x = xs(i) - 50, w = 100, hgt = bh * p * back((grow - i * 0.08) * 1.4), sel = i === 0 && ch > 0;
    inkBar(x, by - hgt, w, hgt, sel ? RED : INK, sel, t, i);
    txt(c, x + w / 2, by + 56, SERIF(600, 44), sel ? RED : INK, clamp01(grow * 3));
    txt(`${Math.round(p * 100)}%`, x + w / 2, by - hgt - 16, THIN(26), sel ? RED : '#5d554b', clamp01(grow * 2));
    if (sel) { g.save(); g.strokeStyle = RED; g.lineWidth = 3; g.globalAlpha = ch * (1 - fly * 0.6); g.beginPath(); g.ellipse(x + w / 2, by + 40, 48, 38, -0.1, 0, 6.283 * ch); g.stroke(); g.restore(); }
  });
  // 红笔尖：来回跳（抽样），按概率最后落在最高的那根上
  const scan = clamp01((t - (tp - (t < 18.3 ? 0.7 : 0.18))) / (t < 18.3 ? 0.7 : 0.18));
  if (scan > 0 && scan < 1) { const e = 1 - (1 - scan) ** 2, px = xs(0) + 290 * Math.abs(Math.cos(e * 9)) * (1 - e) ** 1.5; g.save(); g.fillStyle = RED; g.beginPath(); g.moveTo(px, by + 92); g.lineTo(px - 10, by + 112); g.lineTo(px + 10, by + 112); g.closePath(); g.fill(); g.restore(); }
  // 选中的字沿弧线飞进「＿」，身后留一串墨点
  if (fly > 0 && fly < 1) {
    const [c] = cands[0], x0 = xs(0), y0 = by + 56, cx = (x0 + blankX) / 2 + 160, cy = (y0 + sy) / 2, P = e => [qb(x0, cx, blankX, e), qb(y0, cy, sy, e)];
    g.save(); g.fillStyle = RED; for (let q = 0; q < 14; q++) { const e = smooth(fly) - q * 0.025; if (e <= 0) break; const [x, y] = P(e); g.globalAlpha = 0.5 * (1 - q / 14); g.beginPath(); g.arc(x, y - 14, 3 - q * 0.15, 0, 7); g.fill(); } g.restore();
    const [x, y] = P(smooth(fly)); txt(c, x, y, SERIF(700, 44 + (size - 44) * fly), RED, 1);
  }
  txt('准确说，猜的是「词元」　·　概率为示意', CX, 1180, SERIF(400, 24), '#8a8072', win(t, 12.0, 18.2));
}

// ================= 3 历史：香农 1951（暖黑 + 档案卡）=================
// 「1951」由几百个漂浮的字母聚成；随后一条电报纸带：每个字母下面的点 = 猜了几次才猜中（香农实验，示意）
const TAPE = 'THERE IS NO REVERSE ON A MOTORCYCLE A FRIEND OF MINE FOUND THIS OUT RATHER DRAMATICALLY THE OTHER DAY';
const GUESS = [1,1,1,5,1,1,2,1,1,2,1,1,15,1,17,1,1,1,2,1,3,2,1,2,2,7,1,1,1,1,4,1,1,1,1,1,3,1,8,6,1,3,1,1,1,1,1,1,1,1,1,1,1,1,1,6,2,1,1,1,1,1,1,2,1,1,1,1,1,1,4,1,1,5,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1];
const TAPE3 = (TAPE + ' ').repeat(3), GUESS3 = [...GUESS, 1, ...GUESS, 1, ...GUESS, 1];
const NTYPED = t => t < 26.3 ? 0 : (Math.min(t, 35.1) - 26.3) / 0.12 + Math.max(0, t - 35.1) / 0.025;   // 35.1 之后（AI）打字飞快
const TAU = i => i <= 73.33 ? 26.3 + i * 0.12 : 35.1 + (i - 73.33) * 0.025;
let NUM51 = null;
function num51() {   // 在离屏画布上写「1951」，取样成目标点
  if (NUM51) return NUM51; const c = document.createElement('canvas'); c.width = 900; c.height = 360; const m = c.getContext('2d');
  m.fillStyle = '#fff'; m.font = '200 330px "Helvetica Neue"'; m.textAlign = 'center'; m.textBaseline = 'middle'; m.fillText('1951', 450, 190);
  const d = m.getImageData(0, 0, 900, 360).data, pts = [], r = mulberry32(51);
  for (let y = 0; y < 360; y += 7) for (let x = 0; x < 900; x += 7) if (d[(y * 900 + x) * 4] > 128 && r() < 0.8) pts.push([x - 450, y - 190]);
  return NUM51 = pts.map(([x, y], i) => ({ x, y, sx: (hash(i + 900) - 0.5) * 1400, sy: (hash(i + 901) - 0.5) * 1700, c: String.fromCharCode(65 + ((hash(i + 902) * 26) | 0)), d: hash(i + 903) }));
}
function sHistory(t) {
  matDark(t);
  // 1) 「1951」：金色细线先描出 Didot 字形的轮廓，再缓缓填色；随后缩到顶部当标题
  const up = smooth(clamp01((t - 25.4) / 0.8)), sc = 1 - 0.62 * up, oy = 700 + (250 - 700) * up, ox = CX - 150 * up;
  const draw = smooth(clamp01((t - 21.2) / 2.2)), fill = ramp(t, 22.9, 24.2);
  g.save(); g.translate(ox, oy); g.scale(sc, sc); g.font = '400 300px Didot, "Bodoni 72", serif'; g.textAlign = 'center'; g.textBaseline = 'alphabetic';
  g.globalAlpha = ramp(t, 20.9, 21.3); g.strokeStyle = GOLD2; g.lineWidth = 1.4 / sc; g.setLineDash([1400 * draw, 1400]); g.strokeText('1951', 0, 0); g.setLineDash([]);
  if (fill > 0) { const gr = g.createLinearGradient(0, -220, 0, 20); gr.addColorStop(0, GOLD2); gr.addColorStop(1, '#b8924f'); g.globalAlpha *= fill; g.fillStyle = gr; g.fillText('1951', 0, 0); }
  // 一根细线从中间向两边展开，像档案上的分隔线
  const hl = ramp(t, 23.0, 24.0) * (1 - up); g.globalAlpha = hl * 0.6; g.lineWidth = 1; g.beginPath(); g.moveTo(-340 * hl, 70); g.lineTo(340 * hl, 70); g.stroke();
  g.restore();
  txt('克劳德 · 香农', CX, 860, SERIF(600, 56), '#f3eee2', win(t, 24.0, 25.6, 0.4));
  txt('Claude E. Shannon  ·  信息论之父', CX, 920, SERIF(400, 28), '#a99d86', win(t, 24.3, 25.6, 0.4), 'center', 3);
  txt('香农的猜字实验', CX + 10, 238, SERIF(500, 44), '#f3eee2', ramp(t, 25.9, 26.5), 'left');
  // 2) 电报纸带：字母从打字头打出，纸带左移；每个字母下面落下几颗点 = 猜了几次
  const ta = ramp(t, 25.9, 26.4);
  if (ta > 0) {
    const head = 760, cw = 46, ty = 640;
    g.save(); g.globalAlpha = ta; const tp = g.createLinearGradient(0, 0, W, 0); tp.addColorStop(0, 'rgba(241,232,211,0)'); tp.addColorStop(0.15, 'rgba(241,232,211,0.92)'); tp.addColorStop(0.85, 'rgba(241,232,211,0.92)'); tp.addColorStop(1, 'rgba(241,232,211,0)');
    g.fillStyle = tp; g.fillRect(0, ty - 46, W, 78); g.strokeStyle = 'rgba(90,70,40,0.25)'; g.setLineDash([2, 10]); g.beginPath(); g.moveTo(0, ty - 36); g.lineTo(W, ty - 36); g.moveTo(0, ty + 22); g.lineTo(W, ty + 22); g.stroke(); g.restore();
    const hi = ramp(t, 30.8, 31.4) * (1 - ramp(t, 34.9, 35.4));
    const nt = NTYPED(t);
    for (let i = Math.max(0, Math.floor(nt - 30)); i < TAPE3.length; i++) {
      const dt = t - TAU(i); if (dt < 0) break;
      const x = head - (nt - i) * cw; if (x < -40 || x > W + 40) continue;
      const fade = clamp01(Math.min(x / 160, (W - x) / 160));
      txt(TAPE3[i] === ' ' ? '·' : TAPE3[i], x, ty + 12, TYPE(40), '#231a10', ta * fade);
      const n = GUESS3[i] || 1, shown = Math.min(n, Math.floor(dt / 0.04) + 1);
      for (let q = 0; q < shown; q++) { g.save(); g.globalAlpha = ta * fade * (n === 1 ? 0.55 + 0.45 * hi : 0.85 - 0.5 * hi); g.fillStyle = n === 1 ? (hi > 0 ? GOLD2 : GOLD) : '#a99d86'; g.beginPath(); g.arc(x, ty + 74 + q * 16, n === 1 ? 5 + 2 * hi : 4.5, 0, 7); g.fill(); g.restore(); }
    }
    // 打字头 + 猜错的字母（猜得多的地方，会闪过几个被划掉的错误答案）
    const cur = Math.ceil(NTYPED(t));
    if (cur > 0 && t < 35.1) { const n = GUESS3[cur] || 1, k = clamp01(1 - (TAU(cur) - t) / 0.12);
      g.save(); g.globalAlpha = ta; g.strokeStyle = GOLD; g.lineWidth = 2; g.beginPath(); g.moveTo(head + 26, ty - 60); g.lineTo(head + 26, ty + 40); g.stroke(); g.restore();
      if (n > 1) for (let q = 0; q < Math.min(n - 1, 4); q++) { const c = String.fromCharCode(65 + ((hash(cur * 7 + q) * 26) | 0)), x = head + 30 + (q - 1.5) * 44, y = ty - 110; txt(c, x, y, TYPE(32), '#a99d86', ta * 0.8 * k); g.save(); g.globalAlpha = ta * k; g.strokeStyle = '#c4472f'; g.lineWidth = 2; g.beginPath(); g.moveTo(x - 14, y - 12); g.lineTo(x + 14, y); g.stroke(); g.restore(); }
    }
    txt('每个字母下面的点 = 猜了几次才猜中（示意）', CX, 1010, SERIF(400, 26), '#8c8270', win(t, 27.0, 34.9));
  }
  title('很多字母，一猜就中', CX, 1150, 48, GOLD, t, 31.0, { out: 34.9, w: 500 });
  title('把猜字游戏，玩到极致', CX, 1150, 48, '#f3eee2', t, 35.3, { w: 500 });
}

// ================= 4 学习：文字沿旋涡卷入，团成一颗「字球」（暖黑）=================
const CORPUS = ['今天天气真好适合出门', '新闻报道称明天将有大雨', '他推开门外面阳光正好', '这个周末我们去看电影吧', '研究表明睡眠不足会影响记忆', '她笑着说今天心情不错', '据气象台预报今天多云转晴', '小说的最后一章让人泪目', '网友评论这家店味道真好', '天气预报说下午有雷阵雨'];
const STREAMS = Array.from({ length: 28 }, (_, i) => ({ s: CORPUS[i % CORPUS.length], a0: i / 28 * 6.283 + R() * 0.2, off: R(), spd: 0.13 + R() * 0.07 }));
const GLYPH = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经天气好今真阳光雨风';
const SPHERE = Array.from({ length: 640 }, (_, i) => { const u = 1 - 2 * (i + 0.5) / 640, th = i * 2.39996, s = Math.sqrt(1 - u * u); return [s * Math.cos(th), u, s * Math.sin(th), GLYPH[(R() * GLYPH.length) | 0], R()]; });
const NODES = { 今: [-330, -230], 天: [-170, -320], 气: [-40, -170], 真: [120, -280], 好: [300, -150], 不: [250, 70], 错: [360, 230], 热: [110, 200], 冷: [-60, 270], 阳: [-310, 110], 光: [-160, 30], 雨: [300, -400] };
const EDGES = [['今', '天', .9], ['天', '气', .95], ['气', '真', .7], ['真', '好', .85], ['真', '不', .3], ['不', '错', .8], ['真', '热', .25], ['真', '冷', .2], ['阳', '光', .9], ['天', '雨', .3], ['光', '好', .4], ['气', '冷', .2]];
const HOT = [['天', '气'], ['气', '真'], ['真', '好']];
const spiral = (a0, p, cy) => { const r = 820 * (1 - p) ** 1.3 + 230 * (1 - p) * 0, a = a0 + p * 3.4; return [CX + Math.cos(a) * r, cy + Math.sin(a) * r * 0.9]; };
function sLearn(t) {
  matDark(t);
  const cx = CX, cy = 720, toG = ramp(t, 45.2, 46.4), fa = 1 - toG, grow = ramp(t, 39.0, 44.5);
  title('读过海量的文字', CX, 260, 80, '#f3eee2', t, 40.8, { out: 45.2 });
  txt('新闻 · 小说 · 网页 · 聊天记录', CX, 330, SERIF(400, 30), '#a99d86', win(t, 41.5, 45.2), 'center', 6);
  if (fa > 0) {
    // 旋涡：每条文字沿对数螺线卷进中心，身后留一条很淡的轨迹
    for (const s of STREAMS) {
      g.save(); g.strokeStyle = 'rgba(233,199,127,0.07)'; g.lineWidth = 1; g.globalAlpha = fa; g.beginPath();
      for (let k = 0; k <= 40; k++) { const [x, y] = spiral(s.a0, k / 40 * 0.88, cy); k ? g.lineTo(x, y) : g.moveTo(x, y); } g.stroke(); g.restore();
      for (let k = 0; k < s.s.length; k++) {
        const p = ((t - 38.6) * s.spd + s.off - k * 0.018) % 1; if (p < 0 || t < 38.6) continue;
        const [x, y] = spiral(s.a0, p * 0.88, cy), e = p * 0.88;
        txt(s.s[k], x, y, SERIF(500, 30 - 20 * e), '#e2d5b8', fa * (0.2 + 0.6 * (1 - e)) * Math.min(1, (0.88 - e) * 12));
      }
    }
    // 字球：几百个小字排在球面上慢慢转，前面亮、后面暗
    const rot = t * 0.3, rad = 150 + 130 * smooth(grow), tilt = 0.35;
    const pts = SPHERE.map(([x, y, z, c, q]) => { const X = x * Math.cos(rot) - z * Math.sin(rot), Z0 = x * Math.sin(rot) + z * Math.cos(rot), Y = y * Math.cos(tilt) - Z0 * Math.sin(tilt), Z = y * Math.sin(tilt) + Z0 * Math.cos(tilt); return [X, Y, Z, c, q]; }).sort((a, b) => a[2] - b[2]);
    g.save(); g.textAlign = 'center'; g.textBaseline = 'middle';
    for (const [X, Y, Z, c, q] of pts) {
      const d = 1 / (1.6 - Z * 0.5), size = Math.round((10 + 9 * (Z + 1) / 2) * (0.7 + 0.3 * grow));
      g.globalAlpha = fa * grow * (0.12 + 0.75 * ((Z + 1) / 2) ** 1.5); g.fillStyle = q > 0.9 && Z > 0.3 ? GOLD2 : Z > 0 ? '#e9dcc0' : GOLD;
      g.font = SERIF(500, size); g.fillText(c, cx + X * rad * d * 1.25, cy + Y * rad * d * 1.25);
    }
    g.restore();
  }
  if (toG > 0) {
    const P = k => [cx + NODES[k][0], cy + NODES[k][1]], hot = ramp(t, 47.2, 48.6);
    for (const [u, v, w] of EDGES) {
      const isHot = HOT.some(([a, b]) => a === u && b === v), [x1, y1] = P(u), [x2, y2] = P(v), mx = (x1 + x2) / 2 + (y2 - y1) * 0.12, my = (y1 + y2) / 2 - (x2 - x1) * 0.12;
      g.save(); g.globalAlpha = toG * (isHot ? 0.3 + 0.7 * hot : 0.15 + 0.25 * w * (1 - 0.5 * hot)); g.strokeStyle = isHot ? GOLD2 : '#a99d86'; g.lineWidth = isHot ? 1.5 + 2.5 * hot : 1 + w;
      g.beginPath(); g.moveTo(x1, y1); g.quadraticCurveTo(mx, my, x2, y2); g.stroke(); g.restore();
      if (isHot && hot > 0) for (let j = 0; j < 3; j++) { const s = (t * 0.5 + j / 3) % 1, x = (1 - s) ** 2 * x1 + 2 * (1 - s) * s * mx + s * s * x2, y = (1 - s) ** 2 * y1 + 2 * (1 - s) * s * my + s * s * y2; g.save(); g.globalAlpha = toG * hot * Math.sin(s * 3.14); g.fillStyle = GOLD2; g.beginPath(); g.arc(x, y, 3, 0, 7); g.fill(); g.restore(); }
    }
    for (const k in NODES) { const [x, y] = P(k), isHot = HOT.flat().includes(k) && hot > 0; txt(k, x, y + 18, SERIF(600, 52), isHot ? GOLD2 : '#e8e0cf', toG * (isHot ? 1 : 0.7)); }
    title('什么字后面，最常跟着什么字', CX, 1150, 44, GOLD, t, 46.6, { stag: 0.04, w: 500 });
  }
}
// ================= 5 规模：1750 亿个参数（暖黑金尘）=================
const FIELD = Array.from({ length: 5200 }, (_, i) => ({ x: (i % 80) / 79, y: Math.floor(i / 80) / 64, h: hash(i) }));
function sScale(t) {
  matDark(t);
  title('参数', CX, 260, 104, '#f3eee2', t, 51.5);
  txt('可以调的旋钮', CX, 330, SERIF(400, 32), '#a99d86', ramp(t, 52.2, 52.8), 'center', 8);
  // 一片「旋钮」：每个点是一个小刻度线，训练时一起转向各自的目标
  const zoom = keys(t, [[51.3, 2.6], [55.0, 2.6], [57.4, 1.0], [65, 0.95]]), learn = clamp01((t - 58.8) / 5.0);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const p of FIELD) {
    const x = CX + (p.x - 0.5) * 900 * zoom, y = 740 + (p.y - 0.5) * 680 * zoom; if (x < 60 || x > W - 60 || y < 420 || y > 1080) continue;
    const ang = p.h * 6.283 * (1 - smooth(learn)) + (p.x * 3 + p.y * 2) * smooth(learn), L = 5 * zoom;
    g.globalAlpha = 0.3 + 0.5 * p.h; g.strokeStyle = p.h > 0.9 ? GOLD2 : GOLD; g.lineWidth = 1.2;
    g.beginPath(); g.moveTo(x - Math.cos(ang) * L, y - Math.sin(ang) * L); g.lineTo(x + Math.cos(ang) * L, y + Math.sin(ang) * L); g.stroke();
  }
  g.restore();
  // 数字
  const na = win(t, 55.3, 58.6);
  if (na > 0) {
    g.save(); g.globalAlpha = na * 0.85; g.fillStyle = '#0e0c0a'; g.fillRect(0, 640, W, 210); g.restore();
    const v = 1750 * smooth(clamp01((t - 55.4) / 2.2));
    txt(`${Math.round(v)}`, CX - 40, 790, '100 150px "Helvetica Neue"', GOLD2, na, 'center', 4, 30);
    txt('亿', CX + 200, 790, SERIF(600, 70), GOLD2, na, 'left');
    txt('GPT-3 · 2020', CX, 840, THIN(28), '#a99d86', na, 'center', 6);
  }
  // 猜 → 对答案 → 调
  const la = ramp(t, 58.8, 59.4);
  if (la > 0) {
    const cur = Math.floor((t - 58.8) * 1.4) % 3;
    ['猜', '对答案', '调旋钮'].forEach((s, i) => txt(s, CX + (i - 1) * 270, 1150, SERIF(600, 44), i === cur ? GOLD2 : '#6f6555', la, 'center', 0, i === cur ? 16 : 0));
    ['→', '→'].forEach((s, i) => txt(s, CX - 135 + i * 270, 1146, THIN(36), '#6f6555', la));
  }
}

// ================= 6 词语星系（暖黑 3D）=================
const CL = [
  { name: '水果', c: [-260, -170, 120], w: ['苹果', '香蕉', '橙子', '葡萄', '西瓜', '草莓', '芒果', '桃子'] },
  { name: '城市', c: [250, -230, -80], w: ['北京', '上海', '东京', '巴黎', '纽约', '伦敦', '广州', '成都'] },
  { name: '情绪', c: [-230, 290, -200], w: ['开心', '难过', '生气', '害怕', '惊喜', '焦虑', '平静', '感动'] },
  { name: '动物', c: [260, 320, 160], w: ['猫', '狗', '老虎', '狮子', '熊猫', '兔子', '大象', '猴子'] },
];
const WORDS = []; for (const cl of CL) cl.w.forEach(w => WORDS.push({ w, p: cl.c.map(v => v + (R() - 0.5) * 170) }));
const ROYAL = { 男人: [-60, 70, 200], 女人: [110, 70, 330], 国王: [-60, -60, 240], 女王: [112, -58, 372] };   // 两条平行的 3D 向量
for (const [w, p] of Object.entries(ROYAL)) WORDS.push({ w, p, royal: true });
const STARS = Array.from({ length: 1400 }, () => [(R() - 0.5) * 1500, (R() - 0.5) * 2000, (R() - 0.5) * 2000, R()]);
function proj(p, cam) { const [x, y, z] = p, c = Math.cos(cam.rot), s = Math.sin(cam.rot), X = x * c - z * s - cam.x, Z = x * s + z * c, d = cam.d / (cam.d - Z + cam.zoom); return [CX + X * d, 740 + (y - cam.y) * d, d]; }
function sGalaxy(t) {
  matDark(t);
  const focus = ramp(t, 74.4, 76.2);
  const rot = keys(t, [[65, -0.9], [74.4, 0.25], [76.2, -0.3], [82, 0.42]]), c = Math.cos(rot), sn = Math.sin(rot);
  const cam = { rot, d: 1100, zoom: keys(t, [[65, 900], [68, 0], [74.4, 0], [76.2, -360], [82, -420]]), x: focus * (25 * c - 285 * sn), y: 5 * focus };
  const spread = back((t - 65.3) / 2.2), fog = d => clamp01((d - 0.4) / 0.9);   // 近大远小 + 远处变淡
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, y, z, q] of STARS) { const [X, Y, d] = proj([x, y, z], cam); if (d <= 0 || d > 6) continue; g.globalAlpha = clamp01(spread) * (0.08 + 0.35 * q) * fog(d); g.fillStyle = GOLD; g.fillRect(X, Y, 1.4 * d, 1.4 * d); }
  g.restore();
  // 透视网格地面：给空间一个参照
  g.save(); g.strokeStyle = GOLD; g.lineWidth = 1; const gy = 430, ga = 0.2 * clamp01(spread);
  for (let i = -6; i <= 6; i++) for (const dir of [0, 1]) {
    let prev = null;
    for (let k = 0; k <= 24; k++) { const u = -900 + k * 75, q = proj(dir ? [i * 150, gy, u] : [u, gy, i * 150], cam); if (q[2] <= 0 || q[2] > 5) { prev = null; continue; } if (prev) { g.globalAlpha = ga * fog(q[2]) * Math.min(1, 1.6 / q[2]); g.beginPath(); g.moveTo(prev[0], prev[1]); g.lineTo(q[0], q[1]); g.stroke(); } prev = q; }
  }
  g.restore();
  const halo = ramp(t, 68.7, 69.7) * (1 - ramp(t, 74.2, 74.9));
  const pick = cl => cl.name === '水果' ? ramp(t, 70.3, 70.9) : cl.name === '城市' ? ramp(t, 71.8, 72.4) : 0;
  const scat = w => w.royal ? 1 : 1 + 1.6 * focus * (0.6 + hash(w.w.length * 7 + w.p[0]) * 0.8);   // 聚焦时，其它词向外散开成星尘
  const P = w => proj(w.p.map(v => v * clamp01(spread) * scat(w)), cam);
  // 星座连线：同类的词连成一个星座（不用光晕）
  for (const cl of CL) {
    const ws = WORDS.filter(w => cl.w.includes(w.w)), ps = ws.map(P), k = clamp01(halo * 1.2), pk = pick(cl);
    g.save(); g.strokeStyle = pk > 0 ? GOLD2 : GOLD; g.lineWidth = 1 + pk; g.globalAlpha = k * (0.22 + 0.5 * pk);
    for (let i = 1; i < ps.length; i++) { if (ps[i][2] <= 0 || ps[i - 1][2] <= 0) continue; const e = clamp01(k * ps.length - i); const [x1, y1] = ps[i - 1], [x2, y2] = ps[i]; g.beginPath(); g.moveTo(x1, y1 - 10); g.lineTo(x1 + (x2 - x1) * e, y1 - 10 + (y2 - y1) * e); g.stroke(); }
    g.restore();
    const [X, Y, d] = proj(cl.c, cam); if (d <= 0) continue;
    txt(cl.name, X, Y - 150 * d, SERIF(500, (26 + 10 * pk) * d + 8), pk > 0 ? GOLD2 : GOLD, halo, 'center', 6);
  }
  const order = WORDS.map(w => ({ w, q: P(w) })).filter(o => o.q[2] > 0).sort((u, v) => u.q[2] - v.q[2]);
  for (const { w, q: [X, Y, d] } of order) {
    const inPick = CL.some(cl => cl.w.includes(w.w) && pick(cl) > 0);
    if (!w.royal && focus > 0.5) { g.save(); g.globalAlpha = (1 - focus) * 2 * 0.8; g.fillStyle = GOLD; g.beginPath(); g.arc(X, Y, 1.6 * d, 0, 7); g.fill(); g.restore(); }   // 化成星点
    txt(w.w, X, Y, SERIF(w.royal ? 600 : 400, (w.royal ? 30 - 12 * focus : 30) * d), w.royal ? '#f6efe0' : inPick ? GOLD2 : '#cdbf9f', (w.royal ? (0.4 + 0.6 * focus) * (0.55 + 0.45 * fog(d)) : (1 - focus) * fog(d)));
  }
  const fs = d => (30 - 12 * focus) * d, at = (A, B, e) => { const [x1, y1, d1] = proj(ROYAL[A], cam), [x2, y2, d2] = proj(ROYAL[B], cam); return [x1 + (x2 - x1) * e, y1 - fs(d1) * 0.35 + (y2 - fs(d2) * 0.35 - y1 + fs(d1) * 0.35) * e]; };
  const arrow = (A, B, col, k, w) => {
    if (k <= 0) return; const [ax, ay] = at(A, B, 0.2), [bx, by] = at(A, B, 0.2 + 0.6 * k), an = Math.atan2(by - ay, bx - ax);
    g.save(); g.strokeStyle = col; g.lineWidth = w; g.lineCap = 'round'; g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
    if (k > 0.3) { g.beginPath(); g.moveTo(bx - 16 * Math.cos(an - 0.45), by - 16 * Math.sin(an - 0.45)); g.lineTo(bx, by); g.lineTo(bx - 16 * Math.cos(an + 0.45), by - 16 * Math.sin(an + 0.45)); g.stroke(); }
    g.restore();
  };
  arrow('男人', '女人', '#cdbf9f', ramp(t, 77.6, 78.6), 2.5); arrow('国王', '女王', GOLD2, ramp(t, 79.2, 80.2), 3);
  // 平行四边形的另外两条边（虚线）：两条箭头在空间里真的平行
  const pg = ramp(t, 80.2, 81.0);
  if (pg > 0) { g.save(); g.setLineDash([6, 8]); g.strokeStyle = 'rgba(233,199,127,0.7)'; g.lineWidth = 1.8; for (const [A, B] of [['男人', '国王'], ['女人', '女王']]) { const [ax, ay] = at(A, B, 0.28), [bx, by] = at(A, B, 0.28 + 0.44 * pg); g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke(); } g.restore(); }
  title('方向和距离，几乎一样', CX, 1150, 46, GOLD, t, 80.3, { w: 500 });
  const eq = 0;
  if (eq > 0) {
    const parts = [['国王', '#f6efe0'], [' − ', '#8c8270'], ['男人', '#f6efe0'], [' + ', '#8c8270'], ['女人', '#cdbf9f'], [' ≈ ', '#8c8270'], ['女王', GOLD2]];
    g.save(); g.globalAlpha = eq; g.font = SERIF(600, 62); const tw = parts.reduce((m, [s]) => m + g.measureText(s).width, 0); let x = CX - tw / 2;
    for (const [s, col] of parts) { g.fillStyle = col; g.fillText(s, x, 290); x += g.measureText(s).width; } g.restore();
    txt('Mikolov 等人 · 2013', CX, 340, THIN(24), '#8c8270', eq, 'center', 4);
  }
  title('意思越近，坐得越近', CX, 270, 72, '#f3eee2', t, 68.7, { out: 74.4, stag: 0.05 });
  title('每个词，都有一个座位', CX, 270, 64, '#f3eee2', t, 65.6, { out: 68.6, stag: 0.05 });
}

// ================= 7 注意力（黑板粉笔）=================
const ROWS = ['小明把伞借给了小红，', '因为她忘带了。'];
const SENT = [...ROWS.join('')];
const WGT = [0.05, 0.06, 0.02, 0.12, 0.05, 0.03, 0.02, 0.2, 0.45];
const DOTS = Array.from({ length: 9 }, (_, i) => Array.from({ length: 2 + Math.round(WGT[i] * 16) }, (_, j) => hash(i * 17 + j)));
function chalkDust(x, y, t0, t1, t, seed, n = 10) {   // 写字时掉下的粉笔灰
  g.save(); g.fillStyle = CHALK;
  for (let j = 0; j < n; j++) { const b = t0 + (t1 - t0) * hash(seed * 31 + j), dt = t - b; if (dt < 0 || dt > 1.4) continue; g.globalAlpha = (1 - dt / 1.4) * 0.55; g.fillRect((typeof x === 'function' ? x(b) : x) + (hash(seed * 7 + j) - 0.5) * 60 + (hash(seed * 13 + j) - 0.5) * 24 * dt, y + 30 + 20 * dt + 70 * dt * dt, 1.6, 1.6); }
  g.restore();
}
function sAttention(t) {
  matBoard();
  const zz = 1 + 0.06 * ramp(t, 85, 108); g.save(); g.translate(CX, 720); g.scale(zz, zz); g.translate(-CX, -720);   // 镜头缓慢推近
  // 开场：先在黑板上写「像不像」，再擦掉
  const wipe = ramp(t, 84.7, 85.3);
  if (wipe < 1) {
    g.save(); g.globalAlpha *= 1 - wipe;
    chalk('苹果', CX - 190, 600, 84, CHALK, ramp(t, 82.0, 82.6), 'center', 700); chalk('≈', CX, 600, 84, CHALKY, ramp(t, 82.6, 82.9)); chalk('香蕉', CX + 190, 600, 84, CHALK, ramp(t, 82.9, 83.5), 'center', 700);
    chalkLine(bez(CX - 190, 660, CX, 720, CX + 190, 660), 'rgba(238,238,228,0.7)', 3, ramp(t, 83.2, 83.7), 2);
    chalk('还不够', CX, 820, 64, CHALKY, ramp(t, 83.6, 84.2), 'center', 700);
    g.restore();
  }
  const cw = 82, pos = i => { const row = i < 10 ? 0 : 1, k = row ? i - 10 : i, n = [...ROWS[row]].length; return [CX - n * cw / 2 + k * cw + cw / 2, 640 + row * 170]; };
  const she = SENT.indexOf('她'), wk = clamp01((t - 85.4) / 2.6), lift = ramp(t, 96.4, 97.4), emph = ramp(t, 97.6, 98.8);
  const [hx0, hy0] = pos(she), sx = hx0 + (CX - hx0) * lift, sy = hy0 + (440 - hy0) * back((t - 96.4) / 1.0);
  // 丝线从上方垂到每个字头顶，线上的光点流向「她」——线不压字
  const bk = ramp(t, 96.9, 98.4);
  if (bk > 0) for (let i = 0; i < 9; i++) {
    const [x, y] = pos(i), w = WGT[i], pts = bez(sx, sy + 34, (sx + x) / 2, sy + 60, x, y - 52);
    chalkLine(pts, w > 0.15 ? CHALKY : 'rgba(238,238,228,0.55)', 1.2 + w * 9, clamp01(bk * 1.5 - i * 0.05), 10 + i);
    if (bk > 0.7) for (const ph of DOTS[i]) { const s = 1 - ((t * (0.35 + ph * 0.3) + ph) % 1), [px, py] = pts[Math.floor(s * 40)]; g.save(); g.globalAlpha = (bk - 0.7) / 0.3 * Math.sin(s * 3.14) * 0.9; g.fillStyle = w > 0.15 ? CHALKY : CHALK; g.beginPath(); g.arc(px, py, 1.6 + w * 6, 0, 7); g.fill(); g.restore(); }
  }
  SENT.forEach((c, i) => {
    if (i === she) return;
    const [x, y] = pos(i), w = WGT[i] ?? 0, hi = (i === 7 || i === 8) && t > 91.6, sc = 1 + 0.35 * emph * (w > 0.15 ? 1 : 0);
    g.save(); g.translate(x, y); g.scale(sc, sc); g.globalAlpha *= 1 - 0.55 * emph * (w > 0.15 ? 0 : 1);
    chalk(c, 0, 0, 66, hi ? CHALKY : CHALK, clamp01(wk * SENT.length - i), 'center', 700); g.restore();
  });
  SENT.forEach((c, i) => { const [x, y] = pos(i), a = 85.4 + i * 2.6 / SENT.length; chalkDust(x, y, a, a + 2.6 / SENT.length, t, i + 1); });
  // 回头找：一个粉笔光点从「她」往回一跳一跳，落在「小红」上
  const HOPS = [12, 11, 10, 8, 7.5], h0 = 93.5, hd = 0.32;
  if (t > h0 && t < 96.4) for (let j = 0; j < HOPS.length - 1; j++) {
    const e = clamp01((t - h0 - j * hd) / hd); if (e <= 0) continue;
    const P = v => v % 1 ? [(pos(7)[0] + pos(8)[0]) / 2, pos(7)[1]] : pos(v), [x1, y1] = P(HOPS[j]), [x2, y2] = P(HOPS[j + 1]), hh = 80 + Math.abs(y2 - y1) * 0.4;
    const arc = s => [x1 + (x2 - x1) * s, y1 - 56 + (y2 - y1) * s - Math.sin(s * Math.PI) * hh];
    g.save(); g.fillStyle = CHALKY; const fadeT = 1 - ramp(t, 95.9, 96.4);
    for (let q = 0; q < 12; q++) { const s = q / 12; if (s > e) break; const [x, y] = arc(s); g.globalAlpha = 0.75 * fadeT; g.beginPath(); g.arc(x, y, 2.6, 0, 7); g.fill(); }
    if (e < 1 || j === HOPS.length - 2) { const [x, y] = arc(e); g.globalAlpha = fadeT; g.beginPath(); g.arc(x, y, 8, 0, 7); g.fill(); }
    g.restore();
  }
  if (lift > 0) chalk('她', hx0, hy0, 66, 'rgba(238,238,228,0.18)', 1, 'center', 700);   // 原位留一个淡影
  chalk('她', sx, sy, 66 + 14 * lift, t > 89.6 ? CHALKY : CHALK, clamp01(wk * SENT.length - she), 'center', 700);
  if (t > 89.6) chalk('？', hx0 + 44, hy0 - 72, 56, CHALKY, ramp(t, 89.7, 90.1) * (1 - ramp(t, 93.4, 93.8)));
  if (t > 91.6) { const [x1, y1] = pos(7), [x2] = pos(8); chalkLine(Array.from({ length: 50 }, (_, i) => { const a = i / 49 * 6.6; return [(x1 + x2) / 2 + Math.cos(a) * 104, y1 - 4 + Math.sin(a) * 58]; }), CHALKY, 3.5, ramp(t, 91.7, 92.5) * (1 - ramp(t, 96.2, 96.8)), 3); }
  chalk('回头看一遍前面所有的字', CX, 1080, 40, CHALK, ramp(t, 98.8, 100.2), 'center', 600);
  chalk('找出最该关注的那几个', CX, 1145, 40, CHALKY, ramp(t, 100.4, 101.6), 'center', 600);
  chalk('注意力', CX, 270, 104, CHALK, ramp(t, 102.8, 103.8), 'center', 700); chalkDust(b => CX - 150 + 300 * ramp(b, 102.8, 103.8), 270, 102.8, 103.8, t, 77, 30);
  txt('Attention · 2017', CX, 345, THIN(30), 'rgba(238,238,228,0.65)', ramp(t, 103.8, 104.4), 'center', 6);
  chalk('这个字指的是谁？', CX, 290, 56, CHALK, ramp(t, 89.8, 90.8) * (1 - ramp(t, 102.0, 102.6)), 'center', 600);
  g.restore();
}
// ================= 8 温度（方格纸 + 墨水曲线）=================
const BASE = [['好', .62], ['不错', .15], ['热', .09], ['冷', .06], ['晴', .04], ['糟', .025], ['离谱', .01]];
const softT = T => { const w = BASE.map(([, p]) => Math.pow(p, 1 / T)), s = w.reduce((m, v) => m + v, 0); return w.map(v => v / s); };
function sTemp(t) {
  matPaper();
  title('温度', CX, 270, 104, INK, t, 108.7);
  txt('今天天气真 ＿', CX, 360, SERIF(600, 54), INK, ramp(t, 109.2, 109.8));
  const T = keys(t, [[108.6, 1], [111.8, 1], [112.8, 0.22], [115.6, 0.22], [116.8, 2.6], [119.9, 2.6], [121.0, 1.1], [125, 1.1]]), ps = softT(T);
  // 坐标轴 + 光滑的概率曲线（像墨水画的一座山）
  const bx = 150, by = 900, bw = 780, bh = 400, n = BASE.length, xs = i => bx + 50 + i * (bw - 100) / (n - 1);
  g.strokeStyle = INK; g.lineWidth = 2.4; g.beginPath(); g.moveTo(bx, by - bh - 30); g.lineTo(bx, by); g.lineTo(bx + bw, by); g.stroke();
  const pts = ps.map((p, i) => [xs(i), by - p * bh]);
  g.save(); g.beginPath(); g.moveTo(pts[0][0], by);
  for (let i = 0; i < n; i++) { const [x, y] = pts[i]; if (i === 0) g.lineTo(x, y); else { const [px, py] = pts[i - 1]; g.bezierCurveTo((px + x) / 2, py, (px + x) / 2, y, x, y); } }
  g.lineTo(pts[n - 1][0], by); g.closePath(); g.fillStyle = 'rgba(47,85,119,0.12)'; g.fill();
  g.strokeStyle = BLUE; g.lineWidth = 3.4; g.beginPath(); pts.forEach(([x, y], i) => { if (!i) g.moveTo(x, y); else { const [px, py] = pts[i - 1]; g.bezierCurveTo((px + x) / 2, py, (px + x) / 2, y, x, y); } }); g.stroke(); g.restore();
  BASE.forEach(([c], i) => { txt(c, xs(i), by + 54, SERIF(600, 38), i === 0 ? RED : INK, 1); g.fillStyle = i === 0 ? RED : INK; g.beginPath(); g.arc(pts[i][0], pts[i][1], i === 0 ? 7 : 5, 0, 7); g.fill(); txt(`${Math.round(ps[i] * 100)}%`, xs(i), pts[i][1] - 18, THIN(24), i === 0 ? RED : '#5d554b'); });
  // 温度刻度尺（墨水手绘）
  const sx0 = 220, sx1 = 860, sy = 1060, k = clamp01((T - 0.2) / 2.5), kx = sx0 + (sx1 - sx0) * k;
  g.strokeStyle = INK; g.lineWidth = 2; g.beginPath(); g.moveTo(sx0, sy); g.lineTo(sx1, sy); g.stroke();
  for (let i = 0; i <= 10; i++) { const x = sx0 + (sx1 - sx0) * i / 10; g.beginPath(); g.moveTo(x, sy - (i % 5 ? 8 : 16)); g.lineTo(x, sy); g.stroke(); }
  g.fillStyle = RED; g.beginPath(); g.moveTo(kx, sy - 6); g.lineTo(kx - 14, sy - 32); g.lineTo(kx + 14, sy - 32); g.closePath(); g.fill();
  txt(`T = ${T.toFixed(1)}`, kx, sy - 44, THIN(28), RED); txt('稳', sx0, sy + 44, SERIF(600, 30), BLUE); txt('野', sx1, sy + 44, SERIF(600, 30), RED);
  // 一句话说明（单独一行，不叠在图上）
  const note = t < 115.6 ? (t > 112.0 ? '老实人：每次都选「好」' : '') : t < 119.9 ? '放飞自我：冷门字也会被选中' : '同一个问题，答案可能不一样';
  if (note) txt(note, CX, 1170, SERIF(500, 40), t < 115.6 ? BLUE : RED, win(t, t < 115.6 ? 112.2 : t < 119.9 ? 116.2 : 120.3, t < 115.6 ? 115.6 : t < 119.9 ? 119.9 : 124.0, 0.3));
}

// ================= 9 一本正经地胡说（深靛夜色，编出来的书碎成沙）=================
const OPTS = [['的秘密地图》', .28, true], ['传》', .31], ['与地图》', .19]];
const FAB = ['《墨卡托的秘密地图》，', '作者约翰 · 史密斯，2015 年出版。'];
const SAND = Array.from({ length: 900 }, (_, i) => ({ u: hash(i + 2000), v: hash(i + 3000), vx: 40 + hash(i + 4000) * 160, vy: -30 - hash(i + 5000) * 90, ph: hash(i + 6000) * 6.28 }));
function matNight(t) {
  const bg = g.createLinearGradient(0, 0, 0, H); bg.addColorStop(0, '#0a0e1c'); bg.addColorStop(0.55, '#121a31'); bg.addColorStop(1, '#0c1122'); g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.save(); g.globalCompositeOperation = 'lighter';
  for (const [x, y, z, ph] of DUST) { g.globalAlpha = 0.04 + 0.14 * z * (0.6 + 0.4 * Math.sin(t * 1.1 + ph)); g.fillStyle = '#b9c6ec'; g.beginPath(); g.arc(x, (y + t * 4 * z) % H, 0.5 + z, 0, 7); g.fill(); }
  g.restore();
}
function sHallu(t) {
  matNight(t);
  const PALE = '#e8ecf6', AMB = '#f2d6a0';
  title('一本正经地胡说', CX, 270, 84, PALE, t, 116.0, { stag: 0.05 });
  txt('问：推荐一本讲墨卡托的书？', CX, 380, SERIF(500, 38), '#8f9cbf', ramp(t, 116.4, 117.0));
  txt('《墨卡托', 140, 560, SERIF(600, 56), PALE, ramp(t, 116.8, 117.3), 'left');
  OPTS.forEach(([w, p, bad], i) => {
    const k = clamp01((t - 117.2 - i * 0.15) / 0.5), y = 500 + i * 110; if (k <= 0) return;
    const pts = bez(372, 542, 410, y - 16, 466, y - 16, 30);
    g.save(); g.strokeStyle = bad ? AMB : 'rgba(200,210,235,0.3)'; g.lineWidth = bad ? 2.4 : 1.3; g.beginPath(); pts.slice(0, 1 + Math.floor(30 * k)).forEach(([x, yy], j) => j ? g.lineTo(x, yy) : g.moveTo(x, yy)); g.stroke(); g.restore();
    if (bad) { const s = ramp(t, 117.8, 118.4); if (s > 0 && s < 1) { const [x, yy] = pts[Math.floor(s * 30)]; g.save(); g.fillStyle = AMB; g.globalAlpha = Math.sin(s * 3.14); g.beginPath(); g.arc(x, yy, 4, 0, 7); g.fill(); g.restore(); } }
    txt(w, 480, y, SERIF(600, 46), bad ? AMB : 'rgba(220,226,240,0.5)', k, 'left');
    txt(`${Math.round(p * 100)}%`, 480, y + 38, THIN(22), 'rgba(200,210,235,0.5)', k, 'left');
  });
  // 逐字写出编造的书 → 读完之后，从左到右碎成沙，被风吹走
  const all = FAB.join(''), n = Math.floor(clamp01((t - 118.8) / 2.6) * all.length);
  g.font = SERIF(600, 50);
  FAB.forEach((line, j) => {
    const y = 900 + j * 80, start = j ? FAB[0].length : 0; let x = 140;
    [...line].forEach((c, k) => {
      const idx = start + k, cw = g.measureText(c).width; if (idx >= n) return;
      const d = t - 121.6 - (x - 140) / 900 * 0.9 - j * 0.15, fade = clamp01(d / 0.5);
      if (fade < 1) txt(c, x, y, SERIF(600, 50), AMB, 1 - fade, 'left');
      if (d > 0) {   // 沙粒
        g.save(); g.fillStyle = AMB;
        for (let q = idx * 20; q < idx * 20 + 20; q++) { const s = SAND[q % SAND.length], tt = d + s.u * 0.2; if (tt < 0) continue; const px = x + s.u * cw + s.vx * tt + Math.sin(tt * 3 + s.ph) * 8, py = y - 40 + s.v * 46 + s.vy * tt + 30 * tt * tt; g.globalAlpha = Math.max(0, 1 - tt / 2.2) * 0.85; g.fillRect(px, py, 2, 2); }
        g.restore();
      }
      x += cw;
    });
  });
  const st = ramp(t, 122.6, 123.4);
  if (st > 0) { g.save(); g.globalAlpha = st; g.strokeStyle = 'rgba(232,236,246,0.6)'; g.lineWidth = 1.5; rr(CX - 290, 1110 - 66, 580, 104, 10); g.stroke(); g.restore(); txt('这本书并不存在', CX, 1120, SERIF(700, 56), PALE, st); }
  txt('示意', CX + 276, 1138, SANS(300, 18), 'rgba(232,236,246,0.5)', st, 'right');
}
// ================= 10 三招（方格纸手写）=================
const TIPS = [['让它给出处，再自己点开看看', 130.2], ['提前说好：不确定，就说不知道', 133.4], ['数字、日期、人名，自己再核对', 136.6]];
function strokeDraw(polys, k) {   // 按总长度的比例，一笔一笔画出几条折线
  const len = pl => pl.slice(1).reduce((m, p, i) => m + Math.hypot(p[0] - pl[i][0], p[1] - pl[i][1]), 0), tot = polys.reduce((m, pl) => m + len(pl), 0); let left = tot * k;
  for (const pl of polys) { if (left <= 0) break; g.beginPath(); g.moveTo(...pl[0]); for (let i = 1; i < pl.length; i++) { const d = Math.hypot(pl[i][0] - pl[i - 1][0], pl[i][1] - pl[i - 1][1]); if (left >= d) { g.lineTo(...pl[i]); left -= d; } else { const e = left / d; g.lineTo(pl[i - 1][0] + (pl[i][0] - pl[i - 1][0]) * e, pl[i - 1][1] + (pl[i][1] - pl[i - 1][1]) * e); left = 0; break; } } g.stroke(); }
}
const circ = (x, y, r, a0 = -1.57, a1 = 4.71, n = 40) => Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [x + Math.cos(a) * r, y + Math.sin(a) * r]; });
const ICONS = [
  (x, y) => [circ(x - 4, y - 4, 15), [[x + 7, y + 7], [x + 18, y + 18]]],   // 放大镜：去查出处
  (x, y) => [[[x - 20, y - 14], [x + 20, y - 14], [x + 20, y + 10], [x - 4, y + 10], [x - 12, y + 20], [x - 10, y + 10], [x - 20, y + 10], [x - 20, y - 14]], circ(x, y - 5, 5, 3.4, 7.2, 12), [[x + 1, y + 0], [x, y + 3]]],   // 对话气泡 + 问号
  (x, y) => [[[x - 18, y - 18], [x + 18, y - 18], [x + 18, y + 18], [x - 18, y + 18], [x - 18, y - 18]], [[x - 9, y], [x - 2, y + 8], [x + 12, y - 10]]],   // 打勾的方框：核对
];
function sTips(t) {
  matNight(t);
  const PALE = '#e8ecf6', AMB = '#f2d6a0';
  title('少被 AI 骗的三招', CX, 290, 84, PALE, t, 127.8, { stag: 0.05 });
  // 三个圆圈之间，一条细细的虚线把它们串起来
  const line = ramp(t, 129.6, 137.6); g.save(); g.setLineDash([3, 9]); g.strokeStyle = 'rgba(242,214,160,0.35)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(165, 470); g.lineTo(165, 470 + 440 * line); g.stroke(); g.restore();
  TIPS.forEach(([s, t0], i) => {
    const k = clamp01((t - t0 + 0.2) / 1.1), y = 520 + i * 220, ic = ramp(t, t0 - 0.5, t0 + 0.6), cy = y - 18;
    if (ic > 0) {
      g.save(); g.fillStyle = '#121a31'; g.globalAlpha = Math.min(1, ic * 3); g.beginPath(); g.arc(165, cy, 50, 0, 7); g.fill(); g.restore();
      g.save(); g.strokeStyle = AMB; g.lineWidth = 2; g.lineCap = 'round'; g.lineJoin = 'round'; strokeDraw([circ(165, cy, 50)], ic); g.lineWidth = 2.6; strokeDraw(ICONS[i](165, cy), ramp(t, t0 - 0.1, t0 + 0.9)); g.restore();
      // 圆圈画完时，向外扩散一圈涟漪
      const rp = clamp01((t - t0 - 0.6) / 0.9); if (rp > 0 && rp < 1) { g.save(); g.strokeStyle = AMB; g.globalAlpha = (1 - rp) * 0.5; g.lineWidth = 1.2; g.beginPath(); g.arc(165, cy, 50 + rp * 40, 0, 7); g.stroke(); g.restore(); }
    }
    g.font = SERIF(600, 46); const w = g.measureText(s).width;
    reveal(() => txt(s, 250, y - 6, SERIF(600, 46), PALE, 1, 'left'), 250, w, k);
    txt(['第一招', '第二招', '第三招'][i], 250, y - 64, SERIF(500, 24), AMB, clamp01(k * 3), 'left', 4);
    if (k > 0.9) { const e = ramp(t, t0 + 0.9, t0 + 1.4); g.save(); g.strokeStyle = AMB; g.lineWidth = 2; g.globalAlpha = ramp(t, t0 + 0.9, t0 + 1.3) * 0.8; g.beginPath(); g.moveTo(250, y + 24); g.lineTo(250 + w * e, y + 24); g.stroke();
      g.fillStyle = AMB; g.globalAlpha = 1 - ramp(t, t0 + 1.4, t0 + 1.9); g.beginPath(); g.arc(250 + w * e, y + 24, 4, 0, 7); g.fill(); g.restore(); }
  });
}

// ================= 11 结尾：文字落地，长成金色花园（暖黑）=================
const GL = '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经';
const PLANTS = Array.from({ length: 74 }, () => ({ x: 40 + R() * 1000, h: 130 + R() * 330, bend: (R() - 0.5) * 70, ph: R() * 6.28, t0: 145.0 + R() * 3.4, petals: 5 + ((R() * 3) | 0), col: R() < 0.55 ? '#f6efe0' : GOLD2, fl: R() < 0.75 }));
const FLIES = Array.from({ length: 26 }, () => ({ x: R() * W, y: 920 + R() * 420, ph: R() * 6.28, sp: 0.3 + R() * 0.5 }));
const DROPS = Array.from({ length: 90 }, () => ({ x: 300 + R() * 480, y: 660 + R() * 50, vx: (R() - 0.5) * 60, t0: 144.4 + R() * 2.6, ch: GL[(R() * GL.length) | 0] }));
function sEnd(t) {
  matDark(t);
  title('它不是在回答你', CX, 470, 76, '#f3eee2', t, 142.2);
  title('而是在接龙', CX, 640, 136, GOLD, t, 143.6, { w: 800, glow: 24, stag: 0.1 });
  for (const d of DROPS) { const k = (t - d.t0) / 3.2; if (k <= 0 || k > 1) continue; txt(d.ch, d.x + d.vx * k + Math.sin(k * 8 + d.x) * 10, d.y + k * k * 620, SERIF(500, 22), GOLD, (1 - k) * 0.8 * (1 - ramp(t, 147.0, 147.5)), 'center', 0, 8); }
  for (const p of PLANTS) {
    const k = smooth(clamp01((t - p.t0) / 2.2)); if (k <= 0) continue;
    const tx = p.x + p.bend * k + Math.sin(t * 1.1 + p.ph) * 8, ty = H - p.h * k;
    g.save(); g.strokeStyle = 'rgba(233,199,127,0.45)'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(p.x, H); g.quadraticCurveTo(p.x + p.bend * 0.2, H - p.h * 0.55 * k, tx, ty); g.stroke();
    if (p.fl && k > 0.85) { const f = smooth((k - 0.85) / 0.15), rad = 9 * f; g.fillStyle = p.col; g.shadowColor = p.col; g.shadowBlur = 12; for (let i = 0; i < p.petals; i++) { const an = i / p.petals * 6.283 + t * 0.2; g.beginPath(); g.arc(tx + Math.cos(an) * rad, ty + Math.sin(an) * rad, 4 * f, 0, 7); g.fill(); } g.fillStyle = GOLD; g.beginPath(); g.arc(tx, ty, 3 * f, 0, 7); g.fill(); }
    g.restore();
  }
  const fa = ramp(t, 146.2, 147.6);
  for (const f of FLIES) { const x = f.x + Math.sin(t * f.sp + f.ph) * 60, y = f.y + Math.cos(t * f.sp * 1.3 + f.ph) * 40; g.save(); g.globalAlpha = fa * (0.5 + 0.5 * Math.sin(t * 3 + f.ph * 3)); g.fillStyle = '#ffe9b0'; g.shadowColor = GOLD; g.shadowBlur = 18; g.beginPath(); g.arc(x, y, 3, 0, 7); g.fill(); g.restore(); }
  // 「这条视频大部分是用代码生成的」：本片源码在背景里滚过，前景逐字打出一行注释
  const cw = win(t, 147.2, 151.0, 0.5);
  if (cw > 0) {
    g.save(); g.font = '18px Menlo, monospace'; g.fillStyle = GOLD; const sc = (t - 147.2) * 60;
    for (let i = 0; i < 64; i++) { const y = 140 + i * 30 - (sc % 30), li = (Math.floor(sc / 30) + i) % SRC.length, fy = 1 - Math.abs(y - 720) / 640; if (fy <= 0) continue; g.globalAlpha = cw * 0.16 * fy; g.fillText(SRC[li].trimStart().slice(0, 78), 70 + (SRC[li].length - SRC[li].trimStart().length) * 6, y); }
    g.restore();
    const note = '// 本片画面，大部分由代码生成', n = Math.floor(clamp01((t - 147.6) / 1.4) * [...note].length), shown = [...note].slice(0, n).join('');
    g.font = '36px Menlo, monospace'; const nw = g.measureText(note).width;
    txt(shown, CX - nw / 2, 860, '36px Menlo, "PingFang SC", monospace', GOLD2, cw, 'left');
    if (Math.floor(t * 2.4) % 2 === 0) { g.font = '36px Menlo, "PingFang SC", monospace'; g.save(); g.globalAlpha = cw; g.fillStyle = GOLD2; g.fillRect(CX - nw / 2 + g.measureText(shown).width + 4, 830, 3, 38); g.restore(); }
  }
  const c = ramp(t, 151.1, 151.9);
  txt('你被 AI 一本正经地骗过吗？', CX, 830, SERIF(600, 50), GOLD2, c);
  txt('评论区，说说看', CX, 900, SERIF(400, 34), '#a99d86', c, 'center', 8);
}

// [场景, 开始, 结束]：相邻场景交叠处，后一个淡入覆盖前一个
const SECTIONS = [[sHook, 0, 8.0, 0], [sChain, 7.6, 21.2, 0], [sHistory, 20.8, 38.9, 0], [sLearn, 38.5, 51.1, 0], [sScale, 50.7, 65.0, 0], [sGalaxy, 64.6, 82.0, 0], [sAttention, 81.6, 108.2, 0], [sTemp, 107.8, 124.0, 0], [sHallu, 123.6, 135.4, 8.5], [sTips, 135.0, 149.8, 8.2], [sEnd, 149.4, DUR, 8.2]];
const SUBS = LINES.map(line => { const parts = line.match(/[^，。：！？；…]+[，。：！？；…]*/g) || [line], o = []; for (const p of parts) { const q = p.replace(/[，。；]+$/, ''); if (o.length && (o[o.length - 1] + q).length <= 14) o[o.length - 1] += (o[o.length - 1].match(/[：！？…]$/) ? '' : '，') + q; else o.push(q); } return o; });
const LIGHT = [[7.8, 21.0], [108.0, 123.8]];   // 纸张场景
function render(n) {
  const t = n / FPS; let first = true;
  for (const [fn, s0, s1, sh] of SECTIONS) {
    if (t < s0 || t >= s1) continue;
    if (!first && fn === sChain && t < s0 + 0.9) {   // 纸从蒲公英的花心处，圆形绽开
      const r = 1700 * smooth((t - s0) / 0.9) ** 1.2; g.save(); g.beginPath(); g.arc(CX, 950, r, 0, 7); g.clip(); fn(t - sh); g.restore();
      g.save(); g.strokeStyle = 'rgba(220,244,238,0.6)'; g.lineWidth = 2; g.beginPath(); g.arc(CX, 950, r, 0, 7); g.stroke(); g.restore(); first = false; continue;
    }
    g.save(); g.globalAlpha = first ? 1 : ramp(t, s0, s0 + 0.4); fn(t - sh); g.restore(); first = false;
  }
  if (t < 0.3) { g.fillStyle = `rgba(0,0,0,${1 - t / 0.3})`; g.fillRect(0, 0, W, H); }
  if (t > DUR - 1.2) { g.fillStyle = `rgba(0,0,0,${ramp(t, DUR - 1.2, DUR)})`; g.fillRect(0, 0, W, H); }
  for (let i = 0; i < LINES.length - 1; i++) {
    const a0 = AT[i], d = VO[i].dur; if (t < a0 - 0.05 || t >= a0 + d + 0.2) continue;
    const segs = SUBS[i], tot = segs.reduce((m, x) => m + x.length, 0); let acc = 0;
    for (let k = 0; k < segs.length; k++) {
      const s0 = a0 + d * acc / tot, s1 = k === segs.length - 1 ? a0 + d + 0.2 : a0 + d * (acc + segs[k].length) / tot; acc += segs[k].length;
      if (t < s0 - 0.05 || t >= s1) continue;
      g.save(); g.globalAlpha = win(t, s0 - 0.05, s1, 0.08); g.textAlign = 'center'; g.font = SANS(500, 44); g.lineJoin = 'round';
      const light = LIGHT.some(([p0, p1]) => t >= p0 && t < p1);
      g.strokeStyle = light ? 'rgba(239,231,214,0.95)' : 'rgba(0,0,0,0.75)'; g.lineWidth = 8; g.strokeText(segs[k], CX, SUB_Y); g.fillStyle = light ? '#2b2723' : '#fff'; g.fillText(segs[k], CX, SUB_Y); g.restore();
    }
  }
}
window.renderFrame = n => { render(n); return n; };
window.TOTAL_FRAMES = Math.round(DUR * FPS);
window.ready = true;
const scrub = document.getElementById('scrub'), time = document.getElementById('time'), btn = document.getElementById('play');
scrub.max = window.TOTAL_FRAMES - 1;
let frame = 0, playing = false, last = 0;
const show = () => { render(frame); scrub.value = frame; time.textContent = (frame / FPS).toFixed(2) + 's'; };
scrub.oninput = () => { frame = +scrub.value; show(); };
btn.onclick = () => { playing = !playing; btn.textContent = playing ? '暂停' : '播放'; last = performance.now(); };
function loop(now) { if (playing) { frame = Math.min(window.TOTAL_FRAMES - 1, frame + Math.max(1, Math.round((now - last) / 1000 * FPS))); last = now; show(); } requestAnimationFrame(loop); }
if (!new URLSearchParams(location.search).has('still')) { show(); requestAnimationFrame(loop); }

// ---------- 封面（3:4）：荧光蒲公英被风吹散，种子带着字 ----------
window.renderCover = () => {
  const t = 3.2; matTeal(t);
  // 背景：本片自己的源码（只取纯代码行），很淡，越往下越淡，标题一带再压淡
  const CODE = SRC.filter(l => !/[\u4e00-\u9fff]/.test(l) && l.trim().length > 12);
  g.save(); g.font = '17px Menlo, monospace'; g.fillStyle = '#bfe8e0';
  for (let i = 0; i < 52; i++) { const y = 36 + i * 27, l = CODE[(i * 7 + 40) % CODE.length], ind = l.length - l.trimStart().length; g.globalAlpha = 0.075 * (1 - 0.55 * y / H) * (1 - 0.7 * clamp01(1 - Math.abs(y - 420) / 190)); g.fillText(l.trimStart().slice(0, 96 - ind), 36 + ind * 5, y); }
  g.restore();
  g.save(); g.strokeStyle = 'rgba(170,222,212,0.5)'; g.lineWidth = 2.4; g.beginPath(); g.moveTo(CX + 30, H); g.quadraticCurveTo(CX + 40, HY + 200, HX, HY + 6); g.stroke();
  g.fillStyle = '#d8f0e8'; g.shadowColor = 'rgba(160,240,220,0.8)'; g.shadowBlur = 10; g.beginPath(); g.arc(HX, HY, 7, 0, 7); g.fill(); g.restore();
  const flown = s => s.x + s.h * 0.5 > 0.55;
  for (const s of [...DSEED].sort((a, b) => a.z - b.z)) {
    if (flown(s)) continue; const [x, y] = tipOf(s), d = 0.5 + 0.5 * s.z;
    g.strokeStyle = `rgba(190,232,224,${0.10 + 0.25 * d})`; g.lineWidth = 0.8; g.beginPath(); g.moveTo(HX, HY); g.lineTo(x, y); g.stroke();
    g.save(); g.globalAlpha = 0.25 + 0.75 * d; g.fillStyle = '#dff3ee'; g.font = SERIF(500, Math.round(14 + 9 * d)); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(s.c, x, y); g.restore();
  }
  // 飘走的种子：在花右侧的区域里均匀散开，互相保持距离，不贴边、不压标题
  const placed = [[970, 610, 90]], r = mulberry32(77); let cnt = 0;   // 先给「好」留出位置
  for (const s of DSEED) {
    if (!flown(s) || s.h < 0.3 || cnt >= 24) continue;
    for (let k = 0; k < 30; k++) {
      const u = r(), x = 680 + u * 330 + (r() - 0.5) * 90, y = 1060 - u * 430 + (r() - 0.5) * 260, sz = 16 + 14 * s.h2 + 5 * (0.5 + 0.5 * s.z);   // 沿一条斜向上的风带散开
      if (x > W - 50 || y < 720 || placed.some(([px, py, ps]) => Math.hypot(px - x, py - y) < (ps + sz) * 1.3)) continue; cnt++;
      placed.push([x, y, sz]); seedGlyph(x, y, -Math.PI / 2 + 0.5 + Math.sin(s.ph) * 0.3, s.c, sz, 0.45 + 0.55 * (0.5 + 0.5 * s.z)); break;
    }
  }
  // 标题：字号拉开层次——「不知道」最大，「下一个字」次之
  const runs = (rs, y) => { let tw = 0; for (const [t2, sz, , w] of rs) { g.font = SERIF(w, sz); tw += g.measureText(t2).width + (t2.length) * sz * 0.04; } let x = CX - tw / 2; for (const [t2, sz, col, w] of rs) { txt(t2, x, y, SERIF(w, sz), col, 1, 'left', sz * 0.04); g.font = SERIF(w, sz); x += g.measureText(t2).width + t2.length * sz * 0.04; } return x; };
  runs([['AI 其实', 78, '#b6dcd5', 600]], 290);
  runs([['不知道', 210, '#f2faf8', 900]], 500);
  const cx2 = runs([['自己', 54, '#9ec9c1', 500], ['下一个字', 92, '#eef8f5', 800], ['要说什么', 54, '#9ec9c1', 500]], 640) + 10;
  g.fillStyle = '#cfe9e3'; g.fillRect(cx2, 572, 4, 82);   // 光标：下一个字还没想好
  // 焦点：一颗带着「好」的种子，从花上飘向光标（虚线是它飘过的路）
  const P = e => [qb(HX + 150, 1010, cx2 + 62, e), qb(HY - 180, 820, 610, e)];
  g.save(); g.fillStyle = 'rgba(220,244,238,0.55)'; for (let q = 1; q < 26; q++) { const [x, y] = P(q / 30); g.globalAlpha = 0.15 + 0.5 * q / 26; g.beginPath(); g.arc(x, y, 1.6, 0, 7); g.fill(); } g.restore();
  const [fx, fy] = P(1); seedGlyph(fx, fy, -Math.PI / 2 - 0.3, '好', 46, 1);
};
