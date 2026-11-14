/* Browser-only tests for the ROOT dashboard, which is what GitHub Pages publishes.
   No NFL outcome is inferred here; every assertion is structural or accessibility. */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.md':'text/plain','.svg':'image/svg+xml'};

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
  const base = process.env.BASE_URL || `http://127.0.0.1:${server.address().port}/`;
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

    // Only the hand-written root pages; subtrees are separate dashboards.
    const files = fs.readdirSync(root).filter(f => f.endsWith('.html')).sort();
    assert.ok(files.length >= 13, `expected at least 13 root pages, found ${files.length}`);

    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    let checks = 0;
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      for (const file of files) {
        const response = await page.goto(new URL(file, base).href);
        assert.equal(response.status(), 200, `${file} returns 200`);
        assert.equal(await page.locator('h1').count(), 1, `${file}: exactly one h1`);
        assert.equal(await page.locator('nav[aria-label="Main navigation"] a[aria-current="page"]').count(), 1,
          `${file}: exactly one current nav item`);
        const navCount = await page.locator('nav[aria-label="Main navigation"] a').count();
        assert.ok(navCount >= 13, `${file}: full navigation present, found ${navCount}`);
        assert.equal(await page.locator('nav[aria-label="Main navigation"] .nav-group').count(), 4,
          `${file}: navigation is grouped by intent`);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
          `${file} at ${width}: no horizontal page overflow`);
        await page.addScriptTag({content: axe});
        const result = await page.evaluate(async () =>
          await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
        assert.deepEqual(result.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target)})), [],
          `${file} accessibility at ${width}`);
        checks++;
      }
    }

    // Progressive enhancement: the row filter must be hidden without JS and work with it.
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(new URL('decision.html', base).href);
    assert.equal(await page.locator('#row-search').isVisible(), true, 'filter shown when JS runs');
    const before = await page.locator('tbody tr:visible').count();
    await page.locator('#row-search').fill('S-11');
    const after = await page.locator('tbody tr:visible').count();
    assert.ok(after >= 1 && after < before, `filter narrows the decision queue (${before} -> ${after})`);
    await page.locator('#row-search').fill('zzz-no-such-row');
    assert.equal(await page.locator('tbody tr:visible').count(), 0, 'filter can reach zero rows');

    // Availability: the published depth-tier column must stay empty in the browser too.
    await page.goto(new URL('availability.html', base).href);
    const tierCells = await page.locator('tbody td').evaluateAll(nodes =>
      nodes.map(n => n.textContent.trim()).filter(t => /string/i.test(t) && !/What each/.test(t)));
    assert.ok(tierCells.every(t => t === ''), `no depth tier rendered: ${JSON.stringify(tierCells)}`);
    assert.ok(await page.locator('table').count() >= 5, 'availability tables render');

    // Navigation works with JavaScript disabled.
    const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const staticPage = await nojs.newPage();
    await staticPage.goto(new URL('index.html', base).href);
    assert.equal(await staticPage.locator('.filter:visible').count(), 0, 'filter hidden without JS');
    await staticPage.locator('nav[aria-label="Main navigation"]').getByText('Suggestions', {exact: true}).click();
    assert.match(staticPage.url(), /suggestions\.html$/);
    assert.ok(await staticPage.locator('tbody tr').count() >= 16, 'suggestion register readable without JS');
    await staticPage.locator('nav[aria-label="Main navigation"]').getByText('Decision brief', {exact: true}).click();
    assert.match(staticPage.url(), /decision\.html$/);

    assert.deepEqual(errors, [], 'no page errors or console errors');
    console.log(`PASS: ${files.length} root pages × 2 viewports; ${checks} WCAG axe checks; grouped nav, single current item, filter behaviour, blank depth tiers, JS-disabled navigation, no console errors.`);
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; }).finally(() => server.close());
