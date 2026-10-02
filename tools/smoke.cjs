'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright'),{createServer}=require('../server.cjs');
async function main(){
 const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;let browser;
 try{
  for(const url of ['/','/live.html','/contra/replay.html','/contra/live.html','/contra/training.html','/games.json'])assert.equal((await fetch(base+url)).status,200,url);
  assert.equal((await fetch(base+'/.git/config')).status,403);
  const ranged=await fetch(base+'/games.json',{headers:{Range:'bytes=0-15'}});assert.equal(ranged.status,206);assert.equal((await ranged.arrayBuffer()).byteLength,16);
  const registry=JSON.parse(fs.readFileSync(path.join(__dirname,'../games.json')));
  for(const game of Object.values(registry.games))for(const key of ['policy','inputs','proof'])if(game[key])assert.ok(fs.existsSync(path.join(__dirname,'..',game[key])),game[key]);
  browser=await chromium.launch(require('./browser.cjs'));
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);assert.equal(await page.locator('article').count(),4);
  await page.goto(base+'/live.html?paused=1');await page.waitForFunction(()=>window.liveApp);
  const engine=page.frames().find(f=>f.url().includes('live-engine.html'));assert.ok(engine);
  await engine.waitForFunction(()=>window.liveEngine);
  await page.goto(base+'/contra/replay.html');await page.waitForFunction(()=>document.getElementById('chapter').options.length===8);
  assert.match(await page.locator('#facts').textContent(),/死亡 0 次/);
  for(const width of [390,1080]){
   await page.setViewportSize({width,height:1920});
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Contra horizontal overflow');
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: four-game registry, static routes, private paths, HTTP Range, BattleCity engine, Contra 8 chapters, desktop/mobile layout');
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
