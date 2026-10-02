const {chromium}=require('playwright'),fs=require('fs'),assert=require('node:assert/strict');
const path=process.argv[2],audit=JSON.parse(fs.readFileSync(path));
(async()=>{const browser=await chromium.launch(require('./tools/browser.cjs'));try{
 const p=await browser.newPage();await p.goto('http://127.0.0.1:8787/live.html?paused=1');await p.waitForFunction(()=>window.liveApp);
 const f=p.frames().find(f=>f.url().includes('live-engine.html'));
 const replay=await f.evaluate(a=>{liveEngine.start(a.seed);tankAI.stop();let frame=0,previous='start';const stages=[];let last=-Infinity,minGap=Infinity,presses=0,held=false;for(const [mask,n]of a.actions){aiDirs.forEach((k,d)=>keys[k]=!!(mask&(1<<d)));keys.Space=!!(mask&16);for(let j=0;j<n;j++){if(keys.Space&&!held){minGap=Math.min(minGap,frame-last);last=frame;presses++;}held=keys.Space;originalUpdate();frame++;if(gamePhase==='clear'&&previous!=='clear')stages.push({stage:stageIdx+1,score:p1Score,lives:p1Lives+1,frame});previous=gamePhase;}}render();return {frame,stages,final:aiObserve(),rng:aiRngState,minGap,presses};},audit);
 const clean=s=>({phase:s.phase,stage:s.stage,score:s.score,lives:s.lives,eagle:s.eagle,remaining:s.remaining,player:s.player});
 assert.deepEqual(clean(replay.final),clean(audit.final));assert.deepEqual(replay.stages,audit.stages);assert.equal(replay.rng,audit.rng);assert.ok(replay.minGap>=12);assert.equal(replay.presses,audit.shots.length);assert.ok(audit.shots.every(s=>s.reason));
 const result={controllerOnlyReplayMatches:true,allShotsHaveIntent:true,rateLimitPassed:true,...replay};fs.writeFileSync(path.replace('.json','-replay.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
