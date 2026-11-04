/* Browser-only tests: no NFL outcomes or external facts are inferred. */
const { chromium: playwright } = require('playwright-core');
const chromium = require('@sparticuz/chromium').default;
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../site');
const mime = {'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.json':'application/json','.md':'text/plain'};
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
  await new Promise(resolve => server.listen(0,'0.0.0.0',resolve));
  const base = process.env.BASE_URL || `http://127.0.0.1:${server.address().port}/`;
  // The minimal sandbox lacks NSS/NSPR. Use the package's bundled libraries,
  // without apt downloads or modifying the host's shared-library installation.
  const chromiumPackage = require('@sparticuz/chromium');
  const bundledLibs = path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br');
  await chromiumPackage.inflate(bundledLibs);
  chromiumPackage.setupLambdaEnvironment(path.join(require('node:os').tmpdir(), 'al2023/lib'));
  const browser = await playwright.launch({executablePath:await chromium.executablePath(),args:chromium.args,headless:true});
  const errors = [];
  try {
    const context = await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
    const page = await context.newPage();
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.type()==='error') errors.push(m.text()); });
    const files = fs.readdirSync(root).filter(p => p.endsWith('.html'));
    const axe = fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8');
    let accessibilityChecks = 0;
    for (const width of [1440,390]) {
      await page.setViewportSize({width,height:1000});
      for (const file of files) {
        const response=await page.goto(new URL(file,base).href);
        assert.equal(response.status(),200,`${file} returns 200`);
        assert.equal(await page.locator('h1').count(),1);
        assert.equal(await page.locator('nav[aria-label="Main navigation"] a').count(),9);
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,`${file} at ${width}: no page overflow`);
        await page.addScriptTag({content:axe});
        const result=await page.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));
        assert.deepEqual(result.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>n.target)})),[],`${file} accessibility at ${width}`);
        accessibilityChecks++;
      }
    }
    await page.goto(new URL('strategies.html',base).href);
    await page.locator('#table-search').fill('S06');
    assert.equal(await page.locator('tbody tr:not([hidden])').count(),1);
    assert.match(await page.locator('tbody tr:not([hidden])').innerText(),/QB \+ receiver/);
    const downloadEvent=page.waitForEvent('download');
    await page.locator('.export').first().click();
    const download=await downloadEvent;
    const csv=fs.readFileSync(await download.path(),'utf8');
    assert.ok(csv.includes('https://docs.scipy.org/'));
    assert.ok(csv.includes('S06'));
    assert.ok(!csv.includes('S01'));
    await page.locator('#table-search').fill('xyz-no-results');
    assert.equal(await page.locator('.empty:visible').count(),1);
    await page.locator('#table-search').fill('');
    await page.locator('#table-filter').selectOption('blocked');
    assert.equal(await page.locator('tbody tr:not([hidden])').count(),8);
    await page.goto(new URL('leaderboard.html',base).href);
    assert.equal(await page.locator('tbody').first().locator('.missing').count(),40);
    await page.goto(new URL('correlations.html',base).href);
    assert.equal(await page.locator('tbody .missing').count(),24);
    // Navigation uses real static hrefs and works without any JavaScript.
    const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
    const staticPage=await nojs.newPage();
    await staticPage.goto(new URL('index.html',base).href);
    await staticPage.locator('nav[aria-label="Main navigation"]').getByText('Flagged for Review').click();
    assert.match(staticPage.url(),/review\.html$/);
    assert.equal(await staticPage.locator('tbody tr').count(),JSON.parse(fs.readFileSync(path.join(root,'data/catalog.json'),'utf8')).flags.length);
    fs.mkdirSync(path.resolve(__dirname,'../build/screenshots'),{recursive:true});
    await page.setViewportSize({width:1440,height:1100});
    await page.goto(new URL('index.html',base).href);
    await page.screenshot({path:path.resolve(__dirname,'../build/screenshots/desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});
    await page.screenshot({path:path.resolve(__dirname,'../build/screenshots/mobile.png'),fullPage:true});
    assert.deepEqual(errors,[],'browser errors');
    console.log(`PASS: ${files.length} pages × 2 viewport sizes; ${accessibilityChecks} WCAG axe checks; search, status filter, CSV source URLs, blank metrics, JS-disabled navigation and no console errors.`);
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>server.close());
