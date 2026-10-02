const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright');
(async () => {
  const browser = await chromium.launch(require('../tools/browser.cjs'));
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => {
      window.audioAudit = {starts:0, nonzero:0, rates:[], contextState:null};
      const originalStart = AudioBufferSourceNode.prototype.start;
      AudioBufferSourceNode.prototype.start = function(...args) {
        audioAudit.starts++;
        audioAudit.contextState = this.context.state;
        audioAudit.rates.push(this.playbackRate.value);
        if (this.buffer.getChannelData(0).some(value => value !== 0)) audioAudit.nonzero++;
        return originalStart.apply(this, args);
      };
    });
    await page.goto('http://127.0.0.1:8796/live.html');
    await page.waitForFunction(() => document.getElementById('mode').value === 'replay');
    assert.equal(await page.locator('#sound-toggle').textContent(), '声音：关');
    await page.locator('#sound-toggle').click();
    await page.waitForFunction(() => audioAudit.nonzero > 0, {timeout:15000});
    assert.equal(await page.locator('#sound-toggle').getAttribute('aria-pressed'), 'true');
    await page.locator('#speed').selectOption('2');
    await page.waitForFunction(() => audioAudit.rates.includes(2));
    await page.locator('#sound-toggle').click();
    await page.waitForTimeout(100);
    const mutedStarts = await page.evaluate(() => audioAudit.starts);
    await page.waitForTimeout(250);
    assert.equal(await page.evaluate(() => audioAudit.starts), mutedStarts);
    await page.locator('#sound-toggle').click();
    await page.waitForFunction(starts => audioAudit.starts > starts, mutedStarts);
    await page.locator('#play').click();
    await page.waitForFunction(() => document.getElementById('play').textContent === '开始运行');
    await page.waitForTimeout(150);
    const pausedStarts = await page.evaluate(() => audioAudit.starts);
    await page.waitForTimeout(250);
    assert.equal(await page.evaluate(() => audioAudit.starts), pausedStarts);
    await page.locator('#seek-go').click();
    await page.waitForFunction(starts => audioAudit.starts > starts, pausedStarts);
    await page.locator('#speed').selectOption('1');
    await page.locator('#capture').click();
    assert.equal(await page.locator('.controls #sound-toggle').count(), 1);
    assert.equal(await page.locator('#sound-toggle').isVisible(), false);
    await page.keyboard.press('Escape');
    assert.equal(await page.locator('#sound-toggle').isVisible(), true);
    await page.locator('#sound-toggle').click();
    assert.equal(errors.length, 0);
    const result = {...await page.evaluate(() => audioAudit), rates:'verified 1x and 2x', muted:true, pause_flush:true,
      seek_resume:true, sound_in_controls:true, errors};
    fs.writeFileSync('arcade/runs/kovsh/playback-audio-verification.json', JSON.stringify(result,null,2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
