'use strict';
const { chromium } = require('playwright'), assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
(async () => {
  const browser = await chromium.launch(require('../tools/browser.cjs'));
  try {
    const page = await browser.newPage({ viewport: { width: 1080, height: 1200 } }), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8787/contra/training.html');
    await page.waitForFunction(() => Number(document.getElementById('count').textContent) >= 12);
    const parameterGroup = await page.evaluate(async()=>{ const data=await (await fetch('runs/learning-curve.json')).json();return String(data.groups.findIndex(g=>g.scope==='fresh_boot_parameter_search')); });
    await page.locator('#group').selectOption(parameterGroup);
    assert(await page.locator('svg').count() >= 4);
    assert(await page.locator('#rows tr').count() >= 12);
    await page.screenshot({ path: path.join(__dirname, 'runs/training-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(__dirname, 'runs/training-mobile.png'), fullPage: true });
    await page.goto('http://127.0.0.1:8787/contra/live.html');
    await page.waitForFunction(() => typeof Contra === 'object');
    await page.locator('#load').click(); await page.waitForFunction(() => !document.getElementById('ai').disabled);
    await page.locator('#speed').selectOption('4'); await page.locator('#ai').click();
    await page.waitForFunction(() => Number(document.getElementById('frames').textContent) >= 1000, { timeout: 20000 });
    await page.locator('#pause').click();
    await page.screenshot({ path: path.join(__dirname, 'runs/live-actual-rom.png'), fullPage: true });
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(__dirname, 'runs/training-web-verification.json'), JSON.stringify({ passed: true, actualROM: true, curvesRendered: true, mobileNoHorizontalOverflow: true, liveAIFrame: await page.locator('#frames').textContent(), errors }, null, 2));
    console.log('Training dashboard and actual ROM live AI verified.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
