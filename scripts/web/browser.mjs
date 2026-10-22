// 共用：启动无头 Chromium（优先用 Playwright 缓存里的 chrome-headless-shell + Metal），打开影片页面并等它就绪
import { chromium } from 'playwright';
import { existsSync, readdirSync } from 'fs';
export async function openFilm() {
  const cache = process.env.HOME + '/Library/Caches/ms-playwright';
  const shell = existsSync(cache) && readdirSync(cache).filter(d => d.startsWith('chromium_headless_shell')).sort().pop();
  const exe = process.env.CHROME || (shell && `${cache}/${shell}/chrome-headless-shell-mac-arm64/chrome-headless-shell`);
  const browser = await chromium.launch({ ...(exe && existsSync(exe) ? { executablePath: exe } : {}), args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto(`http://localhost:${process.env.PORT || 5180}/${process.env.PAGE || 'film.html'}?still=1`);
  await page.waitForFunction(() => window.ready, null, { timeout: 60000 });
  return { browser, page };
}
