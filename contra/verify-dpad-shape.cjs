const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch(require('../tools/browser.cjs'));try{
 const page=await browser.newPage({viewport:{width:1200,height:1040}});
 await page.addInitScript(()=>{const raf=window.requestAnimationFrame.bind(window);window.requestAnimationFrame=fn=>raf(t=>{if(!window.freezeController)fn(t);});});
 await page.goto('http://127.0.0.1:8787/contra/replay.html');await page.waitForFunction(()=>document.querySelector('video').readyState>=2&&!document.getElementById('chapter').disabled);
 await page.evaluate(()=>{document.querySelector('video').pause();window.freezeController=true;});
 const before=process.argv.includes('--before'),rows=[];
 for(const width of (before?[1200]:[1200,390])){
  await page.setViewportSize({width,height:1040});
  for(const [direction,bit] of [['4',0],['0',16],['1',64],['2',32],['3',128]]){
   await page.evaluate(({direction,bit})=>{document.querySelector('.dpad').dataset.direction=direction;document.querySelectorAll('[data-bit]').forEach(e=>e.classList.toggle('active',Number(e.dataset.bit)===bit));},{direction,bit});await page.waitForTimeout(240);
   const state=await page.locator('.dpad').evaluate(e=>{const b=e.getBoundingClientRect();return{direction:e.dataset.direction,transform:getComputedStyle(e).transform,width:b.width,height:b.height,shade:getComputedStyle(e,'::after').backgroundImage};});
   if(!before)assert.equal(state.transform,'none');rows.push({viewport:width,...state});
   await page.locator('.controller').screenshot({path:path.join(__dirname,`runs/dpad-${before?'before':'fixed'}-${width}-${direction}.png`)});
  }
 }
 let transition;
 if(!before){
  await page.setViewportSize({width:1200,height:1040});await page.evaluate(()=>document.querySelector('.dpad').dataset.direction='3');await page.waitForTimeout(320);
  const position=()=>page.locator('.dpad').evaluate(e=>getComputedStyle(e,'::after').backgroundPosition);
  const right=await position();await page.locator('.controller').screenshot({path:path.join(__dirname,'runs/dpad-transition-right.png')});
  await page.evaluate(()=>document.querySelector('.dpad').dataset.direction='0');await page.waitForTimeout(90);const middle=await position();await page.locator('.controller').screenshot({path:path.join(__dirname,'runs/dpad-transition-middle.png')});await page.waitForTimeout(320);const up=await position();
  assert.match(right,/^105\.556% 50%$/);assert.match(up,/^50% -5\.55556%$/);assert.notEqual(middle,right);assert.notEqual(middle,up);transition={right,middle,up};
  await page.locator('.controller').screenshot({path:path.join(__dirname,'runs/dpad-transition-up.png')});
 }
 fs.writeFileSync(path.join(__dirname,`runs/dpad-${before?'before':'shape-verification'}.json`),JSON.stringify({passed:true,rows,transition},null,2));
 console.log(before?'Captured original directional distortion.':'Four directions verified without perspective or shape deformation on desktop and mobile.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
