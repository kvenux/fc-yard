'use strict';
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{
 const root=__dirname,meta=JSON.parse(fs.readFileSync(path.join(root,'runs/latest-video.json'))),r=JSON.parse(fs.readFileSync(path.join(root,'runs',meta.run,'result.json')));
 assert(r.fullGameClearVerified&&r.replayEqual);assert.equal(r.final.status,6);assert.deepEqual(r.stageVisits,[0,1,2,3,4,5,6,7]);assert.deepEqual(meta.actual,r.expected);
 if(process.argv.includes('--one-life')){const audit=JSON.parse(fs.readFileSync(path.join(root,'runs',meta.run,'independent-audit.json')));assert.equal(r.oneLifeClearVerified,true);assert.equal(r.deaths,0);assert.equal(audit.deaths,0);assert.equal(audit.deathCountEqual,true);assert.deepEqual(audit.stageVisits,r.stageVisits);}
 const browser=await chromium.launch(require('../tools/browser.cjs'));
 try{
  const page=await browser.newPage({viewport:{width:1000,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8787/contra/replay.html');await page.waitForFunction(()=>document.querySelector('video').duration>1100);
  assert.match(await page.locator('#facts').textContent(),/8 \/ 8/);
  if(process.argv.includes('--one-life')){await page.waitForFunction(()=>document.querySelector('h1').textContent.includes('一命'));assert.match(await page.locator('#facts').textContent(),/死亡 0 次/);}
  await page.evaluate(async()=>{const v=document.querySelector('video');await new Promise(resolve=>{v.addEventListener('seeked',resolve,{once:true});v.currentTime=v.duration-10;});await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
  const video=await page.locator('video').evaluate(v=>({width:v.videoWidth,height:v.videoHeight,duration:v.duration,currentTime:v.currentTime,readyState:v.readyState}));assert(video.width===256&&video.height===224&&video.readyState>=2);assert(Math.abs(video.currentTime-(video.duration-10))<1,'Video seek did not reach ending');
  await page.screenshot({path:path.join(root,'runs/clear-replay-browser.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.goto('http://127.0.0.1:8787/contra/training.html');await page.waitForFunction(()=>Number(document.getElementById('victories').textContent)>=1);
  if(process.argv.includes('--one-life')){await page.waitForFunction(()=>Number(document.getElementById('one-life').textContent)>=1);assert.match(await page.locator('#status').textContent(),/一命通关已核验/);await page.screenshot({path:path.join(root,'runs/one-life-training-browser.png'),fullPage:true});}
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(root,'runs/clear-web-verification.json'),JSON.stringify({passed:true,run:meta.run,oneLifeVerified:r.oneLifeClearVerified===true,video,allStages:true,mobileNoOverflow:true,errors},null,2));console.log('Full clear replay and training page verified.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
