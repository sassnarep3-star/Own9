/* Browser-only tests for the decision desk. Structural and accessibility checks only:
   nothing here asserts an NFL value, because a browser cannot verify a source. */
const { chromium: playwright } = require('playwright-core');
const chromiumPackage = require('@sparticuz/chromium');
const chromium = chromiumPackage.default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.json':'application/json','.md':'text/plain'};

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

const PAGES = ['index.html','requirements.html','questions.html','suggestions.html',
               'availability.html','fixtures.html','captures.html','sources.html','flagged.html'];

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = process.env.BASE_URL || `http://127.0.0.1:${server.address().port}/`;
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(os.tmpdir(), 'al2023/lib'));
  // --single-process and --no-zygote are removed: they make the bundled Chromium
  // crash on launch in this sandbox. Every other hardening flag is kept.
  const args = chromium.args.filter(a => a !== '--single-process' && a !== '--no-zygote');
  const browser = await playwright.launch({
    executablePath: await chromium.executablePath(),
    args,
    headless: true,
  });

  const problems = [];
  const axeSource = fs.readFileSync(path.resolve(root, '../node_modules/axe-core/axe.min.js'), 'utf8');

  for (const viewport of [{width:1440,height:900,name:'desktop'},{width:390,height:780,name:'mobile'}]) {
    for (const page of PAGES) {
      const ctx = await browser.newContext({viewport: {width: viewport.width, height: viewport.height}});
      const p = await ctx.newPage();
      const errors = [];
      const failed = [];
      p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      p.on('pageerror', e => errors.push(String(e)));
      p.on('response', r => { if (r.status() >= 400) failed.push(`${r.url()} ${r.status()}`); });
      const resp = await p.goto(base + page, {waitUntil: 'networkidle'});
      assert.equal(resp.status(), 200, `${page} did not return 200`);

      const h1 = await p.locator('h1').count();
      assert.equal(h1, 1, `${page} must have exactly one h1`);

      // No horizontal overflow: the dashboard must not scroll sideways.
      const overflow = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (overflow > 1) problems.push(`${page} [${viewport.name}] overflows horizontally by ${overflow}px`);

      // The active navigation item must be marked, so a reader knows where they are.
      const active = await p.locator('.nav a.active').count();
      if (active !== 1) problems.push(`${page} [${viewport.name}] has ${active} active nav items, expected 1`);

      if (errors.length) problems.push(`${page} [${viewport.name}] console errors: ${errors.join(' | ')}`);
      if (failed.length) problems.push(`${page} [${viewport.name}] failed responses: ${failed.join(' | ')}`);

      if (viewport.name === 'desktop') {
        await p.addScriptTag({content: axeSource});
        const results = await p.evaluate(async () => await window.axe.run(document, {
          runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa']},
        }));
        if (results.violations.length) {
          problems.push(`${page} axe: ` + results.violations.map(v => `${v.id}(${v.nodes.length})`).join(', '));
        }
      }
      await ctx.close();
    }
  }

  // The filter on the landing page must actually filter, and must be resettable.
  {
    const ctx = await browser.newContext({viewport: {width: 1440, height: 900}});
    const p = await ctx.newPage();
    await p.goto(base + 'index.html', {waitUntil: 'networkidle'});
    const total = await p.locator('table.filterable tbody tr').count();
    assert.ok(total >= 73, `expected at least 73 requirement rows, saw ${total}`);
    await p.fill('#q', 'opening price');
    const filtered = await p.locator('table.filterable tbody tr:not([hidden])').count();
    assert.ok(filtered > 0 && filtered < total, `search did not filter (${filtered} of ${total})`);
    await p.click('#reset');
    const reset = await p.locator('table.filterable tbody tr:not([hidden])').count();
    assert.equal(reset, total, 'reset did not restore every row');
    await p.selectOption('#status', 'not-started');
    const ns = await p.locator('table.filterable tbody tr:not([hidden])').count();
    assert.ok(ns > 0 && ns < total, `status filter did not filter (${ns} of ${total})`);
    await ctx.close();
  }

  await browser.close();
  server.close();

  if (problems.length) {
    console.error('FAILURES:\n' + problems.map(s => ' - ' + s).join('\n'));
    process.exit(1);
  }
  console.log(`browser checks passed: ${PAGES.length} pages x 2 viewports, filter and reset flows, axe WCAG 2.1 AA`);
})().catch(err => { console.error(err); server.close(); process.exit(1); });
