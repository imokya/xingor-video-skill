// 逐帧导出影片：node render_film.mjs <out.mp4> [起始秒] [结束秒]      node render_film.mjs --total（打印总帧数）
// 页面需提供 window.renderFrame(n)、window.TOTAL_FRAMES、window.ready，画布 id="c"。环境变量：PAGE、PORT、FPS、CHROME
import { spawn } from 'child_process';
import { openFilm } from './browser.mjs';
const [out, a = '0', b] = process.argv.slice(2), FPS = +(process.env.FPS || 60);
const { browser, page } = await openFilm();
const total = await page.evaluate(() => TOTAL_FRAMES);
if (out === '--total') { console.log(total); await browser.close(); process.exit(0); }
const f0 = Math.round(+a * FPS), f1 = b ? Math.min(total, Math.round(+b * FPS)) : total;
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16', '-preset', 'medium', out], { stdio: ['pipe', 'inherit', 'inherit'] });
for (let n = f0; n < f1; n++) {
  const url = await page.evaluate(n => { renderFrame(n); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, n);
  if (!ff.stdin.write(Buffer.from(url.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
  if ((n - f0) % 120 === 0) process.stdout.write(`${(n / FPS).toFixed(0)}s `);
}
ff.stdin.end(); await new Promise(r => ff.on('close', r)); await browser.close();
console.log('\ndone', out);
