/* Browser-only checks for the verification section (verification/*.html).
 *
 * Structural and accessibility assertions only: no NFL outcome is inferred and no external
 * page is fetched. The section is served from a local static server so the same file://
 * problems (root-relative assets, fragments) that a reader would hit are actually exercised.
 */
const { chromium: playwright } = require('playwright-core');
const chromiumPkg = require('@sparticuz/chromium');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const mime = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json' };

const server = http.createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://test').pathname);
  const file = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (err, content) => {
    if (err) { res.writeHead(404).end(); return; }
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    res.end(content);
  });
});

(async () => {
  await new Promise(resolve => server.listen(0, '0.0.0.0', resolve));
  const base = `http://127.0.0.1:${server.address().port}/`;
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPkg.inflate(bundledLibs);
  chromiumPkg.setupLambdaEnvironment(path.join(os.tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({
    executablePath: await chromium.executablePath(), args: chromium.args, headless: true });

  const errors = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
    page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
    page.on('requestfailed', r => errors.push(`requestfailed: ${r.url()}`));

    const dir = path.join(root, 'verification');
    const files = fs.readdirSync(dir).filter(f => f.endsWith('.html')).sort();
    assert.ok(files.length >= 7, `expected at least 7 verification pages, found ${files.length}`);

    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
    let axeChecks = 0;
    let rowChecks = 0;

    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const file of files) {
        const response = await page.goto(new URL(`verification/${file}`, base).href);
        assert.equal(response.status(), 200, `${file} returns 200`);
        assert.equal(await page.locator('h1').count(), 1, `${file}: exactly one h1`);
        assert.equal(
          await page.locator('nav[aria-label="Section navigation"] a[aria-current="page"]').count(), 1,
          `${file}: exactly one current nav item`);
        assert.ok(
          await page.locator('nav[aria-label="Section navigation"] a').count() >= 9,
          `${file}: full section navigation present`);
        assert.equal(
          await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true,
          `${file} at ${width}: no horizontal page overflow`);

        // Every table must be a named, keyboard-reachable scroll region with a caption.
        const wraps = await page.locator('.table-wrap').count();
        for (let i = 0; i < wraps; i++) {
          const w = page.locator('.table-wrap').nth(i);
          assert.equal(await w.getAttribute('tabindex'), '0', `${file}: table wrap ${i} is focusable`);
          assert.equal(await w.getAttribute('role'), 'region', `${file}: table wrap ${i} has a role`);
          assert.ok((await w.getAttribute('aria-label') || '').length > 0,
            `${file}: table wrap ${i} has an accessible name`);
          assert.ok(await w.locator('caption').count() >= 1, `${file}: table wrap ${i} has a caption`);
        }

        // Every data row must carry an evidence cell that is not empty.
        const rows = page.locator('table tbody tr');
        const n = await rows.count();
        for (let i = 0; i < n; i++) {
          const last = rows.nth(i).locator('td').last();
          const text = (await last.innerText()).trim();
          assert.ok(text.length > 0, `${file}: row ${i + 1} carries an evidence cell`);
          const anchors = await last.locator('a[href]').count();
          assert.ok(anchors >= 1, `${file}: row ${i + 1} links to a source`);
          rowChecks++;
        }

        await page.addScriptTag({ content: axe });
        const result = await page.evaluate(async () => {
          const r = await axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
          });
          return r.violations.map(v => `${v.id}: ${v.nodes.length} node(s)`);
        });
        assert.deepEqual(result, [], `${file}: axe WCAG violations at ${width}px`);
        axeChecks++;
      }
    }

    // Links out of the section must resolve to files that exist in the checkout.
    await page.goto(new URL('verification/index.html', base).href);
    const hrefs = await page.locator('a[href]').evaluateAll(as =>
      as.map(a => a.getAttribute('href')).filter(h => !/^https?:/.test(h)));
    for (const href of hrefs) {
      const target = path.resolve(dir, href.split('#')[0]);
      assert.ok(fs.existsSync(target), `local link ${href} resolves in the checkout`);
    }

    // JavaScript disabled: the section must remain fully readable. The bundled chromium runs
    // single-process, which cannot host a second context, so this uses its own launch.
    const noJsBrowser = await playwright.launch({
      executablePath: await chromium.executablePath(), args: chromium.args, headless: true });
    try {
      const noJs = await noJsBrowser.newContext({ javaScriptEnabled: false,
        viewport: { width: 1440, height: 1000 } });
      const noJsPage = await noJs.newPage();
      for (const file of files) {
        await noJsPage.goto(new URL(`verification/${file}`, base).href);
        assert.equal(await noJsPage.locator('table tbody tr').count() > 0, true,
          `${file}: tables render without JavaScript`);
      }
      await noJs.close();
    } finally {
      await noJsBrowser.close();
    }

    assert.deepEqual(errors, [], `console/page/request errors: ${errors.join('; ')}`);
    console.log(`PASS: ${files.length} verification pages x 2 viewports; ${axeChecks} axe checks; ` +
      `${rowChecks} rows carry an evidence link; local links, no-JS rendering, no console errors.`);
  } finally {
    await browser.close();
    server.close();
  }
})().catch(err => { console.error(err); process.exit(1); });
