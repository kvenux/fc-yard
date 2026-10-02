const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch(require('../tools/browser.cjs'));
 const page=await browser.newPage(); const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8796/live.html');
 await page.waitForFunction(()=>document.getElementById('mode').value==='replay');
 console.log(JSON.stringify({title:await page.title(),heading:await page.locator('h1').textContent(),seekOptions:await page.locator('#seek-preset option').count(),proof:await page.locator('#evidence').textContent(),saveDisabled:await page.locator('#save').isDisabled(),errors}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
