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
const crypto = require('crypto');

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

(async () => {
  const url = arg('--url');
  const times = String(arg('--times', '0,4,26.5,35.5,54.5'))
    .split(',')
    .map((x) => x.trim() ? Number(x.trim()) : NaN);
  const out = arg('--out', '');
  const chrome = arg('--chrome', process.env.WISE_CHROME || '');
  const pupPath = arg('--puppeteer', process.env.WISE_PUPPETEER || '');
  if (!url) {
    console.error('missing --url');
    process.exit(2);
  }
  if (!times.length || times.some(t => !Number.isFinite(t) || t < 0)) throw new Error('--times needs finite nonnegative seconds');
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
  try {
  const page = await browser.newPage();
  const pageErrors = [];
  page.on('pageerror', error => { pageErrors.push(String(error)); console.error('page error: ' + error); });
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  const response = await page.goto(url, { waitUntil: 'networkidle0', timeout: 120000 });
  const documentSha = response ? crypto.createHash('sha256').update(await response.buffer()).digest('hex') : null;
  await page.waitForFunction(() => typeof window.renderAt === 'function', { timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

  const frames = [];
  for (const t of times) {
    await page.evaluate(async (time) => {
      await window.renderAt(time);
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      await Promise.all(Array.from(document.images).map(img => img.decode().catch(() => {})));
    }, t);
    const measured = await page.evaluate((time) => {
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
        while (cur) {
          const st = getComputedStyle(cur);
          const op = parseFloat(st.opacity || '1');
          if (Number.isFinite(op)) o *= op;
          if (st.visibility === 'hidden' || st.visibility === 'collapse' || st.display === 'none' || st.contentVisibility === 'hidden') return 0;
          cur = cur.parentElement;
        }
        return o;
      }
      // Keep chrome separate from the existing foreground union. Capture missing
      // and hidden roles honestly: a missing role has no node, a hidden role has
      // its measured CSS and visible=false. data-* roles select nodes, never pass gates.
      function visibleRect(el) {
        const r = el.getBoundingClientRect();
        let x = Math.max(0, r.x), y = Math.max(0, r.y);
        let right = Math.min(innerWidth, r.right), bottom = Math.min(innerHeight, r.bottom);
        for (let parent = el.parentElement; parent; parent = parent.parentElement) {
          const s = getComputedStyle(parent), p = parent.getBoundingClientRect();
          if (/(hidden|clip|scroll|auto)/.test(s.overflowX)) { x = Math.max(x, p.x); right = Math.min(right, p.right); }
          if (/(hidden|clip|scroll|auto)/.test(s.overflowY)) { y = Math.max(y, p.y); bottom = Math.min(bottom, p.bottom); }
        }
        const area = Math.max(0, right-x) * Math.max(0, bottom-y);
        return { rect: { x:r.x, y:r.y, right:r.right, bottom:r.bottom, width:r.width, height:r.height },
                 ratio: r.width*r.height > 0 ? area/(r.width*r.height) : 0 };
      }
      function visibleText(el) {
        const texts = [], walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let text;
        while ((text = walker.nextNode())) {
          if (effectiveOpacity(text.parentElement) < .15 || visibleRect(text.parentElement).ratio < .5) continue;
          texts.push(text.textContent);
        }
        return texts.join(' ').replace(/\s+/g, ' ').trim();
      }
      const roleSelectors = {
        'series-card': '[data-wise-series-chrome], #seriesCard, .series-card',
        'episode-number': '[data-episode-number], #seriesCard .num, .series-card .num',
        'series-name': '[data-series-name], #seriesCard .series, .series-card .series',
        'episode-topic': '[data-episode-topic], #seriesCard .topic, .series-card .topic',
        'signature': '[data-wise-signature], #wise-brand-logo',
        'outro-root': '[data-outro-variant], #wise-signature-outro, #signature',
        'community-image': '[data-outro-object="community-image"], #community-tg-image',
        'community-label': '[data-outro-object="community-label"], #community-group',
        'community-link': '[data-outro-object="community-link"], #community a[href*="t.me/"], #community a[href*="telegram.me/"]',
      };
      for (const role of ['portrait','brand','topics','slogan','subscribe','bookmark','support','bye','bell','interest-chip']) {
        roleSelectors[role] = `[data-outro-object="${role}"], #signature-${role}, .signature-${role}`;
      }
      // Only legacy interest chips inside an outro are relevant; other content chips are not.
      roleSelectors['interest-chip'] += ', [data-outro-variant] .interest-chip, [data-outro-variant] .interest, [data-outro-variant] .chip, [data-outro-variant] .pill, #signature .interest, #signature .chip';
      const chromeNodes = [];
      for (const [role, selector] of Object.entries(roleSelectors)) {
        for (const el of new Set(document.querySelectorAll(selector))) {
          const s = getComputedStyle(el), clipped = visibleRect(el), opacity = effectiveOpacity(el);
          const img = el.matches('img') ? el : el.querySelector('img');
          const shapes = Array.from(el.querySelectorAll('svg path, svg polygon, svg polyline')).map(shape => ({
            tag: shape.tagName.toLowerCase(), d: shape.getAttribute('d') || '', points: shape.getAttribute('points') || '',
            fill: getComputedStyle(shape).fill, visible: effectiveOpacity(shape) >= .15 && visibleRect(shape).ratio >= .5,
          }));
          chromeNodes.push({ role, id:el.id || null, ...{rect:clipped.rect},
            opacity, visible_area_ratio:clipped.ratio,
            visible:opacity >= .15 && clipped.ratio >= .5 && clipped.rect.width >= 2 && clipped.rect.height >= 2,
            text:visibleText(el), background_color:s.backgroundColor, color:s.color,
            href:el.getAttribute('href') || '',
            image_loaded:!!(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0 && effectiveOpacity(img) >= .15 && visibleRect(img).ratio > .01),
            image_src:img ? img.currentSrc : null,
            svg_shapes:shapes.filter(shape => shape.visible),
            boxed_descendants:Array.from(el.querySelectorAll('*')).some(child => {
              const cs = getComputedStyle(child);
              return effectiveOpacity(child) >= .15 && parseFloat(cs.borderRadius) > 4 && cs.backgroundColor !== 'rgba(0, 0, 0, 0)';
            }),
          });
        }
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
      return { t: time, canvas: { width: 1920, height: 1080 }, nodes: content, union,
        chrome_outro: { capture_version:1, source:'browser_computed_dom', nodes:chromeNodes } };
    }, t);
    frames.push(measured);
  }

  const report = { schema_version: 1, url, document_sha256: documentSha, page_errors:pageErrors, frames };
  const text = JSON.stringify(report, null, 2);
  if (out) {
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, text);
  }
  process.stdout.write(text + '\n');
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
