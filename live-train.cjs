const {chromium}=require('playwright'),fs=require('fs'),crypto=require('crypto');
const dir=process.env.HF_DIR||'training/human-fire';fs.mkdirSync(dir,{recursive:true});
const mode=process.argv[2]||'full',policyPath=process.argv[3]||'reference/web/trained-policy.json';
const config=JSON.parse(fs.readFileSync(policyPath));
const sourceFiles=['live-fire.js','live-engine.js','live-mpc.js','live-progress.js','reference/web/game.js','reference/web/strategy.js','reference/web/safety.js'];
const sourceHashes=Object.fromEntries(sourceFiles.map(file=>[file,crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex')]));
(async()=>{
 const browser=await chromium.launch(require('./tools/browser.cjs'));
 const p=await browser.newPage();await p.goto('http://127.0.0.1:8787/live.html?paused=1');await p.waitForFunction(()=>window.liveApp);
 const f=p.frames().find(f=>f.url().includes('live-engine.html'));
 if(mode==='full'){
  await f.evaluate(config=>{liveEngine.start(4004,1,config);window.run={actions:[],shots:[],stages:[],stats:{},previous:'start',done:false};window.recordStats=s=>{if(s.phase!=='play'){run.position=null;run.idle=0;run.quiet=0;return;}const r=run.stats[s.stage]??={stage:s.stage,frames:0,maxIdle:0,maxNoScore:0};r.frames++;run.idle=run.position&&run.position.x===s.player.x&&run.position.y===s.player.y?(run.idle||0)+1:0;run.quiet=run.position&&run.position.score===s.score?(run.quiet||0)+1:0;r.maxIdle=Math.max(r.maxIdle,run.idle);r.maxNoScore=Math.max(r.maxNoScore,run.quiet);run.position={...s.player,score:s.score};};},config);
  let status;
  do{status=await f.evaluate(()=>{for(let i=0;i<3000&&!run.done;i++){const s=liveEngine.step();recordStats(s);const m=s.keys.reduce((v,k,d)=>v+(k?1<<d:0),s.fire?16:0),last=run.actions.at(-1);if(last&&last[0]===m)last[1]++;else run.actions.push([m,1]);if(s.fire)run.shots.push({frame:s.ticks,reason:s.fireControl.reason});if(s.phase==='clear'&&run.previous!=='clear')run.stages.push({stage:s.stage,score:s.score,lives:s.lives,frame:s.ticks});run.previous=s.phase;run.done=s.terminal||s.ticks>=600000;}return {cleared:run.stages.length,...liveEngine.snapshot()};});console.log(JSON.stringify({stage:status.stage,cleared:status.cleared,score:status.score,lives:status.lives,ticks:status.ticks}));}while(!status.terminal&&status.ticks<600000);
  const audit=await f.evaluate(()=>({...run,final:liveEngine.snapshot(),rng:aiRngState}));audit.config=config;audit.seed=4004;audit.sourceHashes=sourceHashes;
  const stamp=Date.now();fs.writeFileSync(`${dir}/full-${stamp}.json`,JSON.stringify(audit));fs.appendFileSync(`${dir}/full-results.jsonl`,JSON.stringify({file:`full-${stamp}.json`,score:status.score,cleared:audit.stages.length,frames:status.ticks,victory:status.phase==='victory',config:policyPath})+'\n');
  console.log('FINAL '+JSON.stringify({file:`full-${stamp}.json`,state:status}));
 }else if(mode==='curriculum'){
  let root=config,saved=fs.existsSync(`${dir}/latest.json`)?JSON.parse(fs.readFileSync(`${dir}/latest.json`)):null;
  if(saved&&fs.existsSync(`${dir}/policy.json`))root=JSON.parse(fs.readFileSync(`${dir}/policy.json`));
  if(!saved)saved=await f.evaluate(config=>{liveEngine.start(4004,1,config);return {checkpoint:liveEngine.save(),observation:liveEngine.snapshot()};},root);
  for(let stage=saved.observation.stage;stage<=35;stage++){
   fs.writeFileSync(`${dir}/entry-${stage}.json`,JSON.stringify(saved));
   const base={...root,...root.stagePolicies?.[stage]};delete base.stagePolicies;
   const candidates=[{...base,id:'current'}];
   for(const horizon of [64,96,128])candidates.push({...base,id:`close-defense-${horizon}`,fortressFrom:0,mpcNav:false,mpcHorizon:horizon,shotRange:208,targetedBaseFire:80,targetMargin:6});
   for(const y of [184,168,152])candidates.push({...base,id:`track-defense-${y}`,fortressFrom:1,fortressY:y,fortressTrack:true,fortressTimeout:900,mpcHorizon:96,mpcNav:true,shotRange:208,targetedBaseFire:80,targetMargin:6});
   for(const y of [176,184,168,152])for(const horizon of [96,160,240])candidates.push({...base,id:`long-nav-${y}-${horizon}`,fortressFrom:1,fortressY:y,fortressTimeout:0,mpcHorizon:horizon,mpcNav:true,shotRange:208});
   for(const horizon of [96,128,192,64])for(const y of [184,168,176])candidates.push({...base,id:`nav-${y}-${horizon}`,fortressFrom:1,fortressY:y,fortressTimeout:0,mpcHorizon:horizon,mpcNav:true});
   for(const horizon of [96,128,192,64])for(const range of [96,160,208])candidates.push({...base,id:`attack-${horizon}-${range}`,fortressFrom:0,mpcNav:false,mpcHorizon:horizon,shotRange:range});
   for(const y of [152,168,176,184])for(const x of [88,120,152])candidates.push({...base,id:`camp-${x}-${y}`,fortressFrom:1,fortressX:x,fortressY:y,fortressTimeout:0,mpcHorizon:128,mpcNav:true,mpcGoals:true});
   let winner=null;
   const tried=fs.existsSync(`${dir}/episodes.jsonl`)?fs.readFileSync(`${dir}/episodes.jsonl`,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).filter(r=>r.stage===stage).map(r=>r.id):[];
   for(const candidate of candidates){
    if(tried.includes(candidate.id))continue;
    const policy={...root,stagePolicies:{...root.stagePolicies,[stage]:candidate}};
    const r=await f.evaluate(({saved,policy,stage})=>{liveEngine.restore(saved.checkpoint,policy);const begin=liveEngine.snapshot().ticks;let s,clear=false;for(let i=0;i<40000;i++){s=liveEngine.step();if(s.phase==='clear')clear=true;if(s.terminal||s.stage>stage)break;}return {observation:s,checkpoint:liveEngine.save(),clear,frames:s.ticks-begin};},{saved,policy,stage});
    const record={stage,id:candidate.id,score:r.observation.score,lives:r.observation.lives,eagle:r.observation.eagle,clear:r.clear,frames:r.frames,config:candidate};fs.appendFileSync(`${dir}/episodes.jsonl`,JSON.stringify(record)+'\n');console.log(JSON.stringify({...record,config:undefined}));
    if(r.clear&&r.observation.eagle&&r.observation.lives>0&&(r.observation.stage>stage||r.observation.phase==='victory')){winner=r;root=policy;break;}
   }
   if(!winner){console.log('BLOCKED STAGE '+stage);break;}
   saved=winner;fs.writeFileSync(`${dir}/policy.json`,JSON.stringify(root,null,2));fs.writeFileSync(`${dir}/latest.json`,JSON.stringify(saved));
   if(saved.observation.phase==='victory'){console.log('CURRICULUM COMPLETE');break;}
  }
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
