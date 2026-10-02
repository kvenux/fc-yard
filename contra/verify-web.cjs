'use strict';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
const { testROM } = require('./selftest.cjs');
(async () => {
  const browser = await chromium.launch(require('../tools/browser.cjs'));
  try {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } }), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8787/contra/live.html');
    assert(await page.locator('#ai').isDisabled());
    assert(await page.locator('#pause').isDisabled());
    await page.screenshot({ path: path.join(__dirname, 'runs/live-1080x1920.png'), fullPage: true });
    await page.locator('#rom').setInputFiles({ name: 'original-synthetic-test.nes', mimeType: 'application/octet-stream', buffer: testROM() });
    await page.waitForFunction(() => !document.getElementById('step').disabled);
    await page.locator('#step').click();
    assert.equal(await page.locator('#frames').textContent(), '1');
    await page.locator('#screen').click();
    await page.keyboard.down('z');
    await page.locator('#step').click();
    assert(await page.locator('#keys span').nth(0).evaluate(el => el.classList.contains('active')));
    await page.keyboard.up('z');
    await page.locator('#step').click();
    assert(!(await page.locator('#keys span').nth(0).evaluate(el => el.classList.contains('active'))));
    assert(await page.locator('#ai').isDisabled(), 'ROM alone must not enable uncalibrated AI');
    const pendingDownload = page.waitForEvent('download');
    await page.locator('#capture').click();
    const download = await pendingDownload;
    const samplePath = path.join(__dirname, 'runs/synthetic-web-sample.json');
    await download.saveAs(samplePath);
    const sample = JSON.parse(fs.readFileSync(samplePath));
    assert.equal(sample.frame, 3); assert.equal(sample.ram.length, 2048); assert(sample.screenshot.startsWith('data:image/png;'));
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(__dirname, 'runs/live-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(__dirname, 'runs/web-verification.json'), JSON.stringify({ passed: true, targetGameTested: false, scope: 'synthetic_ROM_browser_integration', frameStepping: true, buttonDisplay: true, sampleExport: true, mobileNoHorizontalOverflow: true, errors }, null, 2));
    console.log('Browser verification passed; synthetic ROM only.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
