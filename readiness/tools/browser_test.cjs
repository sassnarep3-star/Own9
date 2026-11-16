/* Browser test for the decision-readiness pages: desktop and mobile, axe WCAG checks,
   search and status filter behaviour, every local link resolves, no console errors.
   Structural and accessibility checks only; no NFL outcome is inferred here.
   Run from the repository root: node readiness/tools/browser_test.cjs */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const axeSource = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');

const root = path.resolve(__dirname, '..', '..');
const mime = {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json'};
const pages = ['readiness/index.html', 'readiness/repo-review.html', 'readiness/decisions.html'];

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
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/`;
  const chromiumPackage = require('@sparticuz/chromium');
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(require('node:os').tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({executablePath: await chromium.executablePath(), args: chromium.args, headless: true});
  const errors = [];
  let checks = 0;
  try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
    for (const viewport of [{width: 1440, height: 1000}, {width: 390, height: 844}]) {
      await page.setViewportSize(viewport);
      {
      for (const file of pages) {
        const response = await page.goto(base + file, {waitUntil: 'load'});
        assert.equal(response.status(), 200, `${file} returns 200`);
        await page.addScriptTag({content: axeSource});
        const axe = await page.evaluate(() =>
          axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
        assert.deepEqual(axe.violations.map(v => v.id), [], `${file} axe violations at ${viewport.width}px`);
        checks += 1;
        // Every local link must resolve to a served file (anchors are checked by the Python test).
        const hrefs = await page.$$eval('a[href]', els => els.map(a => a.getAttribute('href')));
        for (const href of hrefs) {
          if (/^(https?:|mailto:|#)/.test(href)) continue;
          const target = path.resolve(path.dirname(path.join(root, file)), href.split('#')[0]);
          assert.ok(fs.existsSync(target), `${file}: local link ${href} missing`);
        }
      }
      }
    }

    // Behaviour: search and status filter on the register (desktop viewport).
    await page.setViewportSize({width: 1440, height: 1000});
    await page.goto(base + 'readiness/index.html', {waitUntil: 'load'});
    const total = await page.locator('table.register tbody tr').count();
    assert.ok(total >= 80, `register renders every requirement, found ${total}`);
    await page.fill('#q', 'X-PARLAY');
    const searched = await page.locator('table.register tbody tr:not([hidden])').count();
    assert.ok(searched >= 1 && searched < total, `search narrows the register (${searched} of ${total})`);
    await page.fill('#q', '');
    await page.selectOption('#status', 'Not met');
    const byStatus = await page.locator('table.register tbody tr:not([hidden])').count();
    assert.ok(byStatus >= 1 && byStatus < total, `status filter narrows the register (${byStatus})`);
    const wrong = await page.$$eval('table.register tbody tr:not([hidden])',
      rows => rows.filter(r => r.getAttribute('data-status') !== 'Not met').length);
    assert.equal(wrong, 0, 'every visible row has the selected status');
    await page.selectOption('#status', '');
    assert.equal(await page.locator('table.register tbody tr:not([hidden])').count(), total, 'reset shows every row');
    checks += 1;

    // Every "Decision readiness" row must carry at least one source link.
    const unsourced = await page.$$eval('table.register tbody tr', rows =>
      rows.filter(r => r.querySelectorAll('ul.links a').length === 0).length);
    assert.equal(unsourced, 0, 'every row has a source link');
    await context.close();
    console.log(`PASS: ${pages.length} readiness pages × 2 viewports; ${checks} WCAG and behaviour checks; `
      + `${total} register rows filter correctly; every local link resolves; no console errors.`);
  } catch (error) {
    console.error('FAIL:', error.message);
    process.exitCode = 1;
  } finally {
    await browser.close();
    server.close();
  }
  if (errors.length) {
    console.error('console or page errors:', errors.slice(0, 5));
    process.exitCode = 1;
  }
})();
