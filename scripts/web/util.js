export function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
export const clamp01 = v => Math.max(0, Math.min(1, v));
export const smooth = v => v * v * (3 - 2 * v);
export const easeInOut = v => v < 0.5 ? 4 * v * v * v : 1 - Math.pow(-2 * v + 2, 3) / 2;
// 关键帧插值：ks = [[t, v], ...]，段间 easeInOut
export function keys(t, ks) {
  if (t <= ks[0][0]) return ks[0][1];
  for (let i = 0; i < ks.length - 1; i++) {
    const [t0, v0] = ks[i], [t1, v1] = ks[i + 1];
    if (t <= t1) return v0 + (v1 - v0) * easeInOut((t - t0) / (t1 - t0));
  }
  return ks[ks.length - 1][1];
}
// 分段线性映射：ks = [[x, y], ...]
export function lerpKeys(t, ks) {
  if (t <= ks[0][0]) return ks[0][1] + (t - ks[0][0]);
  for (let i = 0; i < ks.length - 1; i++) { const [a, u] = ks[i], [b, v] = ks[i + 1]; if (t <= b) return u + (v - u) * (t - a) / (b - a); }
  const [a, u] = ks[ks.length - 1]; return u + (t - a);
}
