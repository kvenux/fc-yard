const{chromium}=require('playwright'),fs=require('fs');
const dir=process.env.HF_DIR||'training/human-speed';fs.mkdirSync(dir,{recursive:true});
(async()=>{const b=await chromium.launch(require('./tools/browser.cjs'));try{
 const p=await b.newPage();await p.goto('http://127.0.0.1:8787/live.html?paused=1');await p.waitForFunction(()=>window.liveApp);const f=p.frames().find(f=>f.url().includes('live-engine.html'));
 let root=JSON.parse(fs.readFileSync(fs.existsSync(`${dir}/policy.json`)?`${dir}/policy.json`:`${dir}/baseline-policy.json`));
 let saved=fs.existsSync(`${dir}/latest.json`)?JSON.parse(fs.readFileSync(`${dir}/latest.json`)):await f.evaluate(c=>{liveEngine.start(4004,1,c);return {checkpoint:liveEngine.save(),observation:liveEngine.snapshot()};},root);
 for(let stage=saved.observation.stage;stage<=35;stage++){
  fs.writeFileSync(`${dir}/entry-${stage}.json`,JSON.stringify(saved));const base={...root,...root.stagePolicies[stage]};delete base.stagePolicies;
  const candidates=[{...base,id:'baseline'}];
  if(process.env.OPTIMIZE_EARLY)for(const stall of [180,300,480])candidates.push({...base,id:`fast-progress-${stall}`,stallAfter:stall,earlyReward:4,iceTrapPenalty:1000000});
  if(process.env.OPTIMIZE_EARLY&&stage===32)for(const y of [152,136,120,200])for(const x of [120,88,152])for(const h of [96,192])candidates.push({...base,id:`cover-${x}-${y}-${h}`,fortressFrom:1,fortressX:x,fortressY:y,fortressTimeout:0,avoidIce:false,mpcNav:true,mpcGoals:true,mpcHorizon:h,stallAfter:0,earlyReward:4,interceptBase:2000,shotRange:208});
  for(const h of [64,96,160])candidates.push({...base,id:`ice-mobility-${h}`,iceTrapPenalty:1000000,mpcHorizon:h,stallAfter:300,earlyReward:4});
  for(const h of [96,160,240,384])candidates.push({...base,id:`ice-route-${h}`,avoidIce:false,iceTrapPenalty:1000000,mpcHorizon:h,stallAfter:300,earlyReward:4});
  for(const y of [184,168,176])for(const h of [128,240,384])candidates.push({...base,id:`guard-${y}-${h}`,fortressFrom:1,fortressY:y,fortressTimeout:0,mpcNav:true,shotRange:208,mpcHorizon:h,stallAfter:0,earlyReward:0,iceTrapPenalty:1000000});
  for(const stall of [300,600])for(const reward of [4,12])candidates.push({...base,id:`progress-${stall}-${reward}`,stallAfter:stall,earlyReward:reward});
  for(const h of [64,96,128])candidates.push({...base,id:`pursuit-${h}`,fortressFrom:0,mpcNav:false,shotRange:208,mpcHorizon:h,stallAfter:300,earlyReward:4,targetedBaseFire:80,targetMargin:6});
  for(const y of [176,184,168])for(const h of [96,160,240])candidates.push({...base,id:`nav-${y}-${h}`,fortressFrom:1,fortressY:y,fortressTimeout:600,mpcNav:true,shotRange:208,mpcHorizon:h,stallAfter:600,earlyReward:4});
  let best=null,bestPolicy=null;
  const tried=fs.existsSync(`${dir}/episodes.jsonl`)?fs.readFileSync(`${dir}/episodes.jsonl`,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).filter(r=>r.stage===stage&&!r.success).map(r=>r.id):[];
  for(const c of candidates){
   if(tried.includes(c.id))continue;
   if(!process.env.OPTIMIZE_EARLY&&stage<=12&&c.id!=='baseline')break;
   const policy={...root,stagePolicies:{...root.stagePolicies,[stage]:c}},cap=c.id==='baseline'?32000:Math.min(best?best.frames-1:24000,24000);
   const r=await f.evaluate(({saved,policy,stage,cap})=>{
    liveEngine.restore(saved.checkpoint,policy);const begin=liveEngine.snapshot().ticks;let s,clear=false,idle=0,quiet=0,maxIdle=0,maxNoScore=0,prev=null;
    for(let i=0;i<cap;i++){s=liveEngine.step();if(s.phase==='play'){idle=prev&&prev.x===s.player.x&&prev.y===s.player.y?idle+1:0;quiet=prev&&prev.score===s.score?quiet+1:0;maxIdle=Math.max(maxIdle,idle);maxNoScore=Math.max(maxNoScore,quiet);prev={...s.player,score:s.score};}else{idle=quiet=0;prev=null;}if(s.phase==='clear')clear=true;if(s.terminal||s.stage>stage)break;}
    return {observation:s,checkpoint:liveEngine.save(),clear,frames:s.ticks-begin,maxIdle,maxNoScore};
   },{saved,policy,stage,cap});
   const success=r.clear&&r.observation.eagle&&r.observation.lives>0&&(r.observation.stage>stage||r.observation.phase==='victory');
   const acceptable=success&&(!best||r.observation.lives>=Math.max(2,best.observation.lives-2))&&(!best||r.frames<best.frames);
   const record={stage,id:c.id,frames:r.frames,maxIdle:r.maxIdle,maxNoScore:r.maxNoScore,score:r.observation.score,lives:r.observation.lives,success,accepted:acceptable,config:c};
   fs.appendFileSync(`${dir}/episodes.jsonl`,JSON.stringify(record)+'\n');console.log(JSON.stringify({...record,config:undefined}));
   if(acceptable){best=r;bestPolicy=policy;}
   if(best&&(stage===Number(process.env.LOCK_STAGE)||(!process.env.OPTIMIZE_EARLY&&stage<=12)||(best.frames<6500&&best.maxNoScore<1200&&best.maxIdle<600)))break;
  }
  if(!best){console.log('NO WINNER '+stage);break;}
  saved=best;root=bestPolicy;fs.writeFileSync(`${dir}/latest.json`,JSON.stringify(saved));fs.writeFileSync(`${dir}/policy.json`,JSON.stringify(root,null,2));
  if(saved.observation.phase==='victory'){console.log('SPEED CURRICULUM COMPLETE');break;}
 }
 }finally{await b.close();}})().catch(e=>{console.error(e);process.exit(1);});
