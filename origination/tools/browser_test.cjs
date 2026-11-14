/* Browser-only tests for the line-origination desk.

   Every assertion is structural or accessibility. No NFL outcome is checked
   here and none is inferred: the browser can only confirm that the published
   pages render, navigate, filter and stay readable. */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..', '..');
const section = path.resolve(__dirname, '..');
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript',
  '.json':'application/json','.md':'text/plain','.svg':'image/svg+xml','.csv':'text/csv'};

const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://test').pathname);
  const file = path.resolve(root, '.' + pathname);
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (err, content) => {
    if (err) { res.writeHead(404).end(); return; }
    res.writeHead(200, {'Content-Type': mime[path.extname(file)] || 'application/octet-stream'});
    res.end(content);
  });
});

(async () => {
  await new Promise(resolve => server.listen(0, '0.0.0.0', resolve));
  const base = process.env.BASE_URL || `http://127.0.0.1:${server.address().port}/origination/`;
  const chromiumPackage = require('@sparticuz/chromium');
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(require('node:os').tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({executablePath: await chromium.executablePath(), args: chromium.args, headless: true});
  const errors = [];
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

    const files = fs.readdirSync(section).filter(f => f.endsWith('.html')).sort();
    assert.ok(files.length >= 12, `expected at least 12 pages, found ${files.length}`);

    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    let checks = 0;
    let rowsSeen = 0;
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      for (const file of files) {
        const response = await page.goto(new URL(file, base).href);
        assert.equal(response.status(), 200, `${file} returns 200`);
        assert.equal(await page.locator('h1').count(), 1, `${file}: exactly one h1`);
        assert.equal(await page.locator('nav[aria-label="Sections"] a[aria-current="page"]').count(), 1,
          `${file}: exactly one current nav item`);
        assert.equal(await page.locator('main').count(), 1, `${file}: one main landmark`);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
          `${file} at ${width}: no horizontal page overflow`);
        rowsSeen += await page.locator('tbody tr').count();
        await page.addScriptTag({content: axe});
        const result = await page.evaluate(async () =>
          await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
        assert.deepEqual(result.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target)})), [],
          `${file} accessibility at ${width}`);
        checks++;
      }
    }

    // The row filter must narrow and must be able to reach zero.
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(new URL('flagged.html', base).href);
    const before = await page.locator('tbody tr:visible').count();
    await page.locator('input[data-filter]').first().fill('OD-03');
    await page.waitForTimeout(300);  // the filter is debounced by 120 ms
    const after = await page.locator('tbody tr:visible').count();
    assert.ok(after >= 1 && after < before, `filter narrows the register (${before} -> ${after})`);
    await page.locator('input[data-filter]').first().fill('zzz-no-such-row');
    await page.waitForTimeout(300);
    assert.equal(await page.locator('tbody tr:visible').count(), 0, 'filter can reach zero rows');

    // The opening-price columns must be visibly blank, not zero.
    await page.goto(new URL('prices.html', base).href);
    const blanks = await page.locator('.blank').count();
    assert.ok(blanks > 0, 'unavailable values are rendered as flagged blanks');
    const body = await page.locator('main').innerText();
    assert.ok(/opening state/i.test(body), 'the store publishes an opening-state column');

    // Navigation works with JavaScript disabled.
    const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const staticPage = await nojs.newPage();
    await staticPage.goto(new URL('index.html', base).href);
    await staticPage.locator('nav[aria-label="Sections"]').getByText('Demotion gate', {exact: true}).click();
    assert.match(staticPage.url(), /demotion\.html$/);
    assert.ok(await staticPage.locator('tbody tr').count() >= 20, 'demotion page readable without JS');
    await staticPage.locator('nav[aria-label="Sections"]').getByText('Replacement depth', {exact: true}).click();
    assert.match(staticPage.url(), /depth\.html$/);

    assert.deepEqual(errors, [], 'no page errors or console errors');
    console.log(`PASS: ${files.length} pages × 2 viewports; ${checks} WCAG axe checks; ` +
      `${rowsSeen} table rows rendered; grouped nav, single current item, filter behaviour, ` +
      `flagged blanks, JS-disabled navigation, no console errors.`);
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(() => server.close());
