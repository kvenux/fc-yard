const {chromium}=require('playwright');
const fs=require('fs'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch(require('../tools/browser.cjs'));
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto('http://127.0.0.1:8791/live.html');
  await page.waitForFunction(()=>document.querySelector('#evidence').textContent.includes('死亡 123 次'));
  await page.waitForFunction(async()=>{const s=await fetch('/api/status').then(r=>r.json());return s.frame>3000},{},{timeout:30000});
  const s=await page.request.get('http://127.0.0.1:8791/api/status').then(r=>r.json());
  const title=await page.title(),evidence=await page.locator('#evidence').textContent();
  assert(title.includes('西游释厄传'));assert(s.ready && !s.error && s.full_game_clear_verified);assert.equal(s.deaths,123);assert.equal(s.continues,61);assert(evidence.includes('正常续关 61 次'));assert.deepEqual(errors,[]);
  await page.screenshot({path:'arcade/runs/orlegend/bt/live-verified.png',fullPage:true});
  const result={passed:true,title,evidence,frame:s.frame,deaths:s.deaths,continues:s.continues,errors};fs.writeFileSync('arcade/runs/orlegend/bt/live-verified.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
