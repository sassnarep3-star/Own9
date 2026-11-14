/* Browser tests for the consolidated ledger in ledger/ (published under /ledger/).
   Structural and accessibility checks only; no NFL outcome is inferred here. */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const mime = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.csv': 'text/csv', '.md': 'text/plain', '.svg': 'image/svg+xml'};

const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://test').pathname);
  const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (err, content) => {
    if (err) { res.writeHead(404).end(); return; }
    res.writeHead(200, {'Content-Type': mime[path.extname(file)] || 'application/octet-stream'});
    res.end(content);
  });
});

(async () => {
  await new Promise(resolve => server.listen(0, '0.0.0.0', resolve));
  const base = process.env.BASE_URL || `http://127.0.0.1:${server.address().port}/ledger/`;
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
    page.on('requestfailed', r => errors.push(`request failed: ${r.url()}`));

    const files = fs.readdirSync(path.join(root, 'ledger')).filter(f => f.endsWith('.html')).sort();
    assert.equal(files.length, 12, `expected 12 ledger pages, found ${files.length}`);

    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    let checks = 0;
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      for (const file of files) {
        const response = await page.goto(new URL(file, base).href);
        assert.equal(response.status(), 200, `${file} returns 200`);
        assert.equal(await page.locator('h1').count(), 1, `${file}: exactly one h1`);
        assert.equal(await page.locator('nav[aria-label="Main"] a[aria-current="page"]').count(), 1, `${file}: one current nav item`);
        assert.equal(await page.locator('nav[aria-label="Main"] a').count(), 12, `${file}: all 12 sections in navigation`);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
          `${file} at ${width}: no horizontal page overflow`);
        // Every data row ends with a source link (the last cell of each table row).
        const rowsWithoutSource = await page.locator('table.data tbody tr').evaluateAll(rows =>
          rows.filter(r => !r.lastElementChild || !r.lastElementChild.querySelector('a')).length);
        assert.equal(rowsWithoutSource, 0, `${file}: every row has a source link`);
        await page.addScriptTag({content: axe});
        const result = await page.evaluate(async () =>
          await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
        assert.deepEqual(result.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target)})), [],
          `${file} accessibility at ${width}`);
        checks++;
      }
    }

    // Row filter narrows rows on the price store and resets.
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(new URL('prices.html', base).href);
    const before = await page.locator('#prices-table tbody tr:visible').count();
    assert.equal(before, 48, `prices table shows 48 rows, found ${before}`);
    await page.locator('input.filter[data-table="prices-table"]').fill('CAR-NO');
    const after = await page.locator('#prices-table tbody tr:visible').count();
    assert.equal(after, 6, `filter on CAR-NO shows its 6 market rows, found ${after}`);
    await page.locator('input.filter[data-table="prices-table"]').fill('');
    assert.equal(await page.locator('#prices-table tbody tr:visible').count(), 48, 'filter resets');

    // Open and close columns must be blank in the browser.
    const openCells = await page.locator('#prices-table tbody tr td:nth-child(8), #prices-table tbody tr td:nth-child(10)')
      .evaluateAll(nodes => nodes.map(n => { const c = n.cloneNode(true); c.querySelectorAll('.sr-only').forEach(x => x.remove()); return c.textContent.replace(/—/g, '').trim(); }).filter(t => t !== ''));
    assert.deepEqual(openCells, [], 'no opening or closing value shown');

    // Fair-line column must be blank everywhere on the lines page.
    await page.goto(new URL('lines.html', base).href);
    const fair = await page.locator('#lines-table tbody tr td:nth-child(4)').evaluateAll(nodes => nodes.map(n => { const c = n.cloneNode(true); c.querySelectorAll('.sr-only').forEach(x => x.remove()); return c.textContent.replace(/—/g, '').trim(); }));
    assert.ok(fair.length === 24 && fair.every(t => t === ''), `fair line column blank (${fair.length} rows)`);

    // Navigation works with JavaScript disabled, and the filter is hidden.
    const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const staticPage = await nojs.newPage();
    await staticPage.goto(new URL('index.html', base).href);
    await staticPage.locator('nav[aria-label="Main"]').getByText('Suggestions', {exact: true}).click();
    assert.match(staticPage.url(), /suggestions\.html$/);
    assert.ok(await staticPage.locator('#suggestions-table tbody tr').count() >= 11, 'suggestions readable without JS');

    assert.deepEqual(errors, [], 'no page errors, console errors or failed requests');
    console.log(`PASS: ${files.length} ledger pages × 2 viewports; ${checks} WCAG axe checks; every row has a source link; filters, blank fair lines and open/close, JS-disabled navigation, no console or request errors.`);
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(() => server.close());
