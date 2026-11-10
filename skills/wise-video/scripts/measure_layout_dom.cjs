#!/usr/bin/env node
/**
 * Measure visible foreground DOM boxes at given times for layout hard gates.
 * Usage:
 *   node measure_layout_dom.cjs --url URL --times 4.8,26.5,35.5,54.5 --out report.json
 *
 * Chrome / puppeteer-core paths: pass --chrome / --puppeteer, or set
 * WISE_CHROME / WISE_PUPPETEER. No author-machine defaults.
 */
const fs = require('fs');
const path = require('path');

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

(async () => {
  const url = arg('--url');
  const times = String(arg('--times', '4.8,26.5,35.5,54.5'))
    .split(',')
    .map((x) => parseFloat(x.trim()))
    .filter((x) => Number.isFinite(x));
  const out = arg('--out', '');
  const chrome = arg('--chrome', process.env.WISE_CHROME || '');
  const pupPath = arg('--puppeteer', process.env.WISE_PUPPETEER || '');
  if (!url) {
    console.error('missing --url');
    process.exit(2);
  }
  if (!chrome || !pupPath) {
    console.error(
      'missing Chrome/puppeteer path: pass --chrome and --puppeteer, or set WISE_CHROME and WISE_PUPPETEER'
    );
    process.exit(2);
  }
  if (!fs.existsSync(chrome)) {
    console.error('chrome executable not found: ' + chrome);
    process.exit(2);
  }
  if (!fs.existsSync(pupPath)) {
    console.error('puppeteer-core module not found: ' + pupPath);
    process.exit(2);
  }
  const pup = require(pupPath);
  const browser = await pup.launch({
    executablePath: chrome,
    headless: true,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForFunction(() => window.renderAt, { timeout: 120000 });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

  const frames = [];
  for (const t of times) {
    const measured = await page.evaluate((time) => {
      window.renderAt(time);
      const skipIds = new Set([
        'root', 'surface', 'earth', 'motion', 'wise-brand-logo', 'caption', 'copy-scrim', 'halo', 'halo-path',
        // identity chrome shells — only count when parent group effectively visible AND they have own motion
        'channel-mask', 'rule', 'copy-scrim',
      ]);
      const skipClasses = new Set(['base', 'rel', 'scene']);
      const selectors = [
        '.prop', '.claim', '.step', '.hold', '.chip', '.challenge', '.headline', '.gauge-wrap', '.metric-card', '.qcard', '.year-chip', '.ctx-chip',
        '#portrait', '#hello', '#channel', '#name', '#welcome',
        '.series-chip',
      ];
      function effectiveOpacity(el) {
        let o = 1;
        let cur = el;
        while (cur && cur !== document.body) {
          const st = getComputedStyle(cur);
          const op = parseFloat(st.opacity || '1');
          if (Number.isFinite(op)) o *= op;
          if (st.visibility === 'hidden' || st.display === 'none') return 0;
          cur = cur.parentElement;
        }
        return o;
      }
      const nodes = [];
      const seen = new Set();
      for (const sel of selectors) {
        for (const el of document.querySelectorAll(sel)) {
          if (seen.has(el) || skipIds.has(el.id)) continue;
          seen.add(el);
          const st = getComputedStyle(el);
          const op = effectiveOpacity(el);
          if (!(op >= 0.15) || st.visibility === 'hidden' || st.display === 'none') continue;
          const r = el.getBoundingClientRect();
          if (r.width < 2 || r.height < 2) continue;
          const img = el.querySelector && el.querySelector('img');
          const label = (el.querySelector && el.querySelector('.label') && el.querySelector('.label').textContent) || '';
          const text = (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120);
          // Skip empty chrome shells (mask/rule with no visible text contribution)
          if ((el.id === 'channel-mask' || el.id === 'rule' || el.id === 'copy-scrim') && !text) continue;
          nodes.push({
            id: el.id || null,
            classes: Array.from(el.classList || []),
            tag: el.tagName.toLowerCase(),
            opacity: op,
            x: r.x,
            y: r.y,
            width: r.width,
            height: r.height,
            right: r.right,
            bottom: r.bottom,
            cx: r.x + r.width / 2,
            cy: r.y + r.height / 2,
            img_src: img ? (img.getAttribute('src') || '') : '',
            img_alt: img ? (img.getAttribute('alt') || '') : '',
            label,
            text,
          });
        }
      }
      // Exclude chrome: logo already skipped; series-chip and caption treated as chrome for center
      const content = nodes.filter((n) => !(n.classes || []).includes('series-chip') && n.id !== 'caption');
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const n of content) {
        minX = Math.min(minX, n.x);
        minY = Math.min(minY, n.y);
        maxX = Math.max(maxX, n.right);
        maxY = Math.max(maxY, n.bottom);
      }
      const union = content.length
        ? {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY,
            cx: (minX + maxX) / 2,
            cy: (minY + maxY) / 2,
            center_x_ratio: (minX + maxX) / 2 / 1920,
            center_y_ratio: (minY + maxY) / 2 / 1080,
            left_ratio: minX / 1920,
            right_ratio: maxX / 1920,
          }
        : null;
      return { t: time, canvas: { width: 1920, height: 1080 }, nodes: content, union };
    }, t);
    frames.push(measured);
  }

  await browser.close();
  const report = { schema_version: 1, url, frames };
  const text = JSON.stringify(report, null, 2);
  if (out) {
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, text);
  }
  process.stdout.write(text + '\n');
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
