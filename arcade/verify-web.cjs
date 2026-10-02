const {chromium}=require('playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const base=process.env.ARCADE_URL||'http://127.0.0.1:8789';
(async()=>{
 const browser=await chromium.launch(require('../tools/browser.cjs'));
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results=[];
 try{
  for(const [name,width,height,capture] of [['capture',1080,1920,true],['desktop',1440,1000,false],['mobile',390,844,false]]){
   await page.setViewportSize({width,height});
   await page.goto(base+'/live.html'+(capture?'?capture=1':''));
   await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('ROM'));
   await page.waitForFunction(()=>document.querySelector('.cabinet-art').naturalWidth===2172);
   assert.equal(await page.locator('.cabinet-button').count(),4);
   assert(await page.locator('#play').isDisabled());
   const dimensions=await page.evaluate(()=>({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight}));
   assert(dimensions.width<=width,`${name} has horizontal overflow`);
   if(capture)assert.equal(dimensions.height,height);
   await page.screenshot({path:path.join(__dirname,'runs',`live-${name}.png`),fullPage:true});
   results.push({name,width,height,dimensions});
  }
  const invalid=await page.request.post(base+'/api/control',{data:{action:'play',value:true}});
  assert.equal(invalid.status(),400);
  await page.setViewportSize({width:1080,height:1920});
  await page.goto(base+'/live.html?capture=1');
  await page.keyboard.press('Escape');
  assert(await page.locator('.controls').isVisible());
  // Explicitly mocked frontend feedback; this is not a target-game execution test.
  const fixture={...await page.request.get(base+'/api/status').then(r=>r.json()),ready:true,error:'',buttons:[],display_buttons:[]};
  const commands=[];
  await page.route('**/api/status',route=>route.fulfill({json:fixture}));
  await page.route('**/api/control',route=>{
   const data=route.request().postDataJSON();commands.push(data);
   if(data.action==='keys'){fixture.buttons=data.buttons;fixture.display_buttons=data.buttons;}
   return route.fulfill({json:fixture});
  });
  await page.goto(base+'/live.html?capture=1');
  await page.waitForFunction(()=>!document.querySelector('.button-a').disabled);
  const a=await page.locator('.button-a').boundingBox();
  await page.mouse.move(a.x+a.width/2,a.y+a.height/2);await page.mouse.down();
  await page.waitForFunction(()=>document.querySelector('.button-a').getAttribute('aria-pressed')==='true');
  await page.keyboard.press('ArrowRight',{delay:120});
  await page.mouse.up();
  await page.waitForFunction(()=>document.querySelector('.button-a').getAttribute('aria-pressed')==='false');
  const stick=await page.locator('#stick-zone').boundingBox();
  await page.mouse.move(stick.x+stick.width/2,stick.y+stick.height/2);await page.mouse.down();
  await page.mouse.move(stick.x+stick.width*.85,stick.y+stick.height*.15);
  await page.waitForFunction(()=>document.querySelector('#stick-state').textContent.includes('右上'));
  await page.keyboard.down('KeyJ');
  await page.waitForFunction(()=>document.querySelector('.button-a').getAttribute('aria-pressed')==='true');
  await page.locator('.cabinet').screenshot({path:path.join(__dirname,'runs/controller-active-fixture.png')});
  await page.mouse.up();await page.keyboard.up('KeyJ');
  await page.waitForFunction(()=>document.querySelector('#stick-state').textContent.includes('中立')&&document.querySelector('.button-a').getAttribute('aria-pressed')==='false');
  await page.keyboard.down('KeyU');
  await page.waitForFunction(()=>document.querySelector('.button-c').getAttribute('aria-pressed')==='true');
  await page.evaluate(()=>window.dispatchEvent(new Event('blur')));
  await page.waitForFunction(()=>document.querySelector('.button-c').getAttribute('aria-pressed')==='false');
  assert(commands.some(c=>c.action==='keys'&&c.buttons.includes('attack')));
  assert(commands.some(c=>c.action==='keys'&&c.buttons.includes('right')&&c.buttons.includes('up')));
  assert.deepEqual(commands.at(-1).buttons,[]);
  assert.deepEqual(errors,[]);
  const result={scope:'missing_rom_ui_and_mocked_controller_feedback',passed:true,gameplay_tested:false,viewports:results,controller_checks:['image_loaded','four_physical_buttons','pointer_press_release','eight_way_stick','keyboard_pointer_combination','blur_releases_inputs'],pageErrors:errors};
  fs.writeFileSync(path.join(__dirname,'runs/web-verification.json'),JSON.stringify(result,null,2));
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
