/* Smoke/accessibility check for the independent ablation panel; no NFL data is fetched. */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const entry = '/ablation-lab/index.html';
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.md':'text/plain','.py':'text/plain'};

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
  const base = `http://127.0.0.1:${server.address().port}/`;
  const chromiumPackage = require('@sparticuz/chromium');
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(require('node:os').tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({executablePath: await chromium.executablePath(), args: chromium.args, headless: true});
  const errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    for (const width of [1440, 390]) {
      await page.setViewportSize({width, height: 1000});
      const response = await page.goto(new URL(entry, base).href);
      assert.equal(response.status(), 200, `page loads at ${width}px`);
      assert.equal(await page.locator('h1').count(), 1, 'one page title');
      assert.equal(await page.locator('table tbody tr').count(), 8, 'all eight sourced status/design rows render');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
        `no horizontal page overflow at ${width}px`);
      await page.addScriptTag({content: axe});
      const result = await page.evaluate(async () =>
        await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa']}}));
      assert.deepEqual(result.violations.map(v => ({id:v.id, impact:v.impact, nodes:v.nodes.map(n => n.target)})), [],
        `WCAG 2.1 AA at ${width}px`);
    }
    assert.deepEqual(errors, [], 'no browser or console errors');
    console.log('PASS: ablation page at 1440px and 390px; 2 axe WCAG 2.1 AA checks; no overflow or console errors.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => server.close());
