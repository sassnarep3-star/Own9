/* Browser-only tests for the session-00cf851d section.
   Every assertion is structural or accessibility; no NFL value is asserted here. */
const { chromium: playwright } = require('playwright-core');
const chromiumPackage = require('@sparticuz/chromium');
const chromium = chromiumPackage.default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript',
              '.json':'application/json','.md':'text/plain','.svg':'image/svg+xml'};

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
  const base = `http://127.0.0.1:${server.address().port}/`;
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')),
                                   '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(require('node:os').tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({executablePath: await chromium.executablePath(),
                                           args: chromium.args, headless: true});
  const problems = [];
  let loads = 0, axeRuns = 0;
  let files = [];
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await context.newPage();
    page.on('pageerror', e => problems.push('pageerror: ' + e.message));
    page.on('console', m => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
    page.on('requestfailed', r => problems.push('requestfailed: ' + r.url()));

    files = fs.readdirSync(root).filter(f => f.endsWith('.html')).sort();
    assert.equal(files.length, 13, `expected 13 section pages, found ${files.length}`);
    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      for (const file of files) {
        const response = await page.goto(new URL(file, base).href);
        assert.equal(response.status(), 200, `${file} returns 200`);
        assert.equal(await page.locator('h1').count(), 1, `${file}: exactly one h1`);
        assert.equal(await page.locator('nav[aria-label="Section pages"] a[aria-current="page"]').count(), 1,
          `${file}: exactly one current nav item`);
        const navCount = await page.locator('nav[aria-label="Section pages"] a').count();
        assert.equal(navCount, 13, `${file}: all 13 pages in the nav, found ${navCount}`);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
          `${file} at ${width}: no horizontal page overflow`);
        loads += 1;
      }
    }

    // Accessibility sweep at desktop width only.
    await page.setViewportSize({width: 1440, height: 1000});
    for (const file of files) {
      await page.goto(new URL(file, base).href);
      await page.addScriptTag({content: axe});
      const result = await page.evaluate(async () => await axe.run(document, {
        runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
      axeRuns += 1;
      for (const v of result.violations) {
        problems.push(`axe ${file}: ${v.id} (${v.impact}) x${v.nodes.length}`);
      }
    }

    // The filter must narrow rows and restore them.
    await page.goto(new URL('verification.html', base).href);
    const before = await page.locator('tbody tr:not(.hidden)').count();
    await page.fill('#q', 'Allegretti');
    await page.waitForTimeout(120);
    const during = await page.locator('tbody tr:not(.hidden)').count();
    assert.ok(during > 0, 'filter finds the Allegretti rows');
    assert.ok(during < before, `filter narrows ${before} rows to ${during}`);
    await page.fill('#q', '');
    await page.waitForTimeout(120);
    const after = await page.locator('tbody tr:not(.hidden)').count();
    assert.equal(after, before, 'clearing the filter restores every row');

    // Every nav link resolves.
    await page.goto(new URL('index.html', base).href);
    const hrefs = await page.locator('nav a').evaluateAll(as => as.map(a => a.getAttribute('href')));
    for (const href of hrefs) {
      const res = await page.goto(new URL(href, base).href);
      assert.equal(res.status(), 200, `nav link ${href} resolves`);
    }
  } finally {
    await browser.close();
    server.close();
  }

  if (problems.length) {
    console.log('FAIL: %d problem(s)', problems.length);
    for (const p of problems.slice(0, 30)) console.log('  - ' + p);
    process.exit(1);
  }
  console.log(`PASS: ${files.length} pages x 2 viewports (${loads} loads); ${axeRuns} axe WCAG 2.1 AA scans; ` +
              'filter narrows and restores; every nav link resolves; no console errors, no failed requests.');
})().catch(err => { console.error(err); server.close(); process.exit(1); });
