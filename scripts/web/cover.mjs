// 封面：node cover.mjs out.png  → 调用页面里的 window.renderCover()（和影片共用素材与函数）
import { writeFileSync } from 'fs';
import { openFilm } from './browser.mjs';
const { browser, page } = await openFilm();
const url = await page.evaluate(() => { renderCover(); return document.getElementById('c').toDataURL('image/png'); });
writeFileSync(process.argv[2], Buffer.from(url.split(',')[1], 'base64')); await browser.close(); console.log('ok', process.argv[2]);
