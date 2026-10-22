// 静帧检查：node shot.mjs <前缀> <秒...>  → 前缀_秒.png（每张先画前 12 帧暖机，和连续播放的状态一致）
// 拼成一排看：ffmpeg -i a_1.png -i a_2.png -filter_complex "hstack=2,scale=2000:-1" sheet.jpg
import { writeFileSync } from 'fs';
import { openFilm } from './browser.mjs';
const [prefix, ...secs] = process.argv.slice(2), FPS = +(process.env.FPS || 60);
const { browser, page } = await openFilm();
for (const s of secs) {
  const url = await page.evaluate(n => { for (let k = 12; k > 0; k--) renderFrame(Math.max(0, n - k)); renderFrame(n); return document.getElementById('c').toDataURL('image/png'); }, Math.round(+s * FPS));
  writeFileSync(`${prefix}_${s}.png`, Buffer.from(url.split(',')[1], 'base64'));
}
await browser.close(); console.log('ok', secs.length);
