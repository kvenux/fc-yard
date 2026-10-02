// Stage-by-stage policy selection on natural saved states. NOT a full-run proof.
const {chromium}=require('playwright'),fs=require('fs'),crypto=require('crypto');
const name=process.argv[2]||'curriculum001',dir=`training/${name}`;
fs.mkdirSync(dir,{recursive:true});
const base=JSON.parse(fs.readFileSync('training/round009/winner.json'));
let saved=JSON.parse(fs.readFileSync(process.argv[3]||'training/checkpoints/stage13-4004.json'));
let root=fs.existsSync(`${dir}/policy.json`)?JSON.parse(fs.readFileSync(`${dir}/policy.json`)):structuredClone(saved.config||base);
const seed=saved.seed;
const source=['strategy.js','safety.js','ai.js','checkpoint.js','mpc.js','game.js'];
for(const file of source)fs.copyFileSync(`reference/web/${file}`,`${dir}/${file}`);
fs.writeFileSync(`${dir}/provenance.json`,JSON.stringify({seed,checkpoint:process.argv[3]||'training/checkpoints/stage13-4004.json',kind:'curriculum selection, must replay from stage 1',hashes:Object.fromEntries(source.map(x=>[x,crypto.createHash('sha256').update(fs.readFileSync(`${dir}/${x}`)).digest('hex')]))},null,2));
(async()=>{const browser=await chromium.launch(require('./tools/browser.cjs'));const page=await browser.newPage();await page.addInitScript(()=>window.requestAnimationFrame=()=>0);await page.goto('http://127.0.0.1:8787/reference/web/index.html');
for(let stage=saved.observation.stage;stage<=35;stage++){
 const round=`scenario-stage${String(stage).padStart(2,'0')}-${name}`,out=`training/${round}`;fs.mkdirSync(out,{recursive:true});fs.writeFileSync(`${dir}/stage${stage}-entry.json`,JSON.stringify(saved));
 const candidates=[{...base,stagePolicies:undefined,id:'attack'},{...base,stagePolicies:undefined,id:'camp176',fortressFrom:1,fortressY:176,fortressTimeout:0,fortressTrack:false,mpcHorizon:96}];
 for(const y of [176,184,168])for(const horizon of [64,128,240])candidates.push({...base,stagePolicies:undefined,id:`nav-${y}-${horizon}`,fortressFrom:1,fortressY:y,fortressTimeout:0,mpcHorizon:horizon,mpcNav:true});
 for(const y of [184,168,176,152])for(const timeout of [600,1800,0])for(const horizon of [64,128])candidates.push({...base,stagePolicies:undefined,id:`camp-${y}-${timeout}-${horizon}`,fortressFrom:1,fortressY:y,fortressTimeout:timeout,fortressTrack:false,mpcHorizon:horizon});
 if(stage===32)candidates.unshift({...base,stagePolicies:undefined,id:'avoid-ice',avoidIce:true});
 const records=[];let success=null;
 fs.writeFileSync(`${out}/spec.json`,JSON.stringify({round,startStage:stage,seeds:[seed],cap:40000,candidates,checkpoint:`${dir}/stage${stage}-entry.json`,adaptive:true},null,2));
 for(const config of candidates){
  const policy={...root,stagePolicies:{...root.stagePolicies,[stage]:config}};
  const r=await page.evaluate(({saved,policy,stage})=>{tankAI.start(saved.seed,policy);checkpoint.load(saved.state,policy);const initialScore=p1Score;let deaths=0,life=p1Lives,clear=false,f=0;for(;f<40000;f++){tankAI.step(1,false);if(p1Lives<life)deaths++;life=p1Lives;if(gamePhase==='clear')clear=true;if(stageIdx+1>stage||gamePhase==='victory'||!eagleAlive||p1Lives<0)break;}const observation=tankAI.observe();return {run:{seed:saved.seed,frames:f,initialScore,scoreGain:p1Score-initialScore,clears:clear?1:0,deaths,victory:false,scenarioVictory:gamePhase==='victory',...observation},next:{seed:saved.seed,state:checkpoint.save(),observation,config:policy}};},{saved,policy,stage});
  const run=r.run,summary={n:1,mean:run.score,meanGain:run.scoreGain,median:run.score,min:run.score,max:run.score,meanClears:run.clears,maxClears:run.clears,victories:0,scenarioVictories:Number(run.scenarioVictory),baseLoss:Number(!run.eagle),meanDeaths:run.deaths};
  records.push({round,config,summary,runs:[run]});fs.appendFileSync(`${out}/episodes.jsonl`,JSON.stringify({round,config,run})+'\n');fs.appendFileSync(`${dir}/episodes.jsonl`,JSON.stringify({round,config,run})+'\n');fs.writeFileSync(`${out}/results.json`,JSON.stringify(records,null,2));console.log(JSON.stringify({stage,id:config.id,score:run.score,gain:run.scoreGain,lives:run.lives,clear:run.clears,eagle:run.eagle,frames:run.frames}));
  if(run.clears&&run.eagle&&run.lives>0&&(run.stage>stage||run.scenarioVictory)){success=r;root=policy;fs.writeFileSync(`${dir}/policy.json`,JSON.stringify(root,null,2));fs.writeFileSync(`${out}/winner.json`,JSON.stringify(config,null,2));break;}
 }
 if(!success){console.log('NO SUCCESS at '+stage);break;}
 saved=success.next;fs.writeFileSync(`${dir}/latest.json`,JSON.stringify(saved));
 if(saved.observation.phase==='victory'){await page.evaluate(()=>{render();aiPanelUpdate();});await page.screenshot({path:`${dir}/curriculum-victory.png`});console.log('CURRICULUM COMPLETE — full replay required');break;}
}
await browser.close();require('child_process').execFileSync('python',['training/plot.py'],{stdio:'inherit'});
})();
