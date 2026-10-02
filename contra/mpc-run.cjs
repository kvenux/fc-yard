'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {NES}=require('./core.cjs'),{Engine,observe}=require('./engine.js'),{MPC,read}=require('./mpc.cjs');
const {boot,fingerprint}=require('./train.cjs'),{picture}=require('./picture.cjs');
const root=__dirname,profile=require('./observation.json'),rom=fs.readFileSync(path.join(root,'roms/contra.nes'));
const args=process.argv.slice(2),arg=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const budget=Number(arg('--frames',8000)),stopStage=Number(arg('--stop-stage',8)),resumePath=arg('--resume',null),prefixLimit=Number(arg('--prefix-frames',Infinity));
const dir=path.join(root,'runs','mpc-'+new Date().toISOString().replace(/[:.]/g,'-'));fs.mkdirSync(dir,{recursive:true});
const config={horizon:Number(arg('--horizon',80)),commit:Number(arg('--commit',16))};
const manifest={scope:'fresh_boot_model_search',profile,config,budget,romSha256:profile.romSha256,coreSha256:profile.coreSha256,sourceHashes:{}};
manifest.resumePath=resumePath;manifest.prefixLimit=Number.isFinite(prefixLimit)?prefixLimit:null;
for(const name of ['engine.js','core.cjs','mpc.cjs','mpc-run.cjs','picture.cjs']){const b=fs.readFileSync(path.join(root,name));manifest.sourceHashes[name]=crypto.createHash('sha256').update(b).digest('hex');fs.writeFileSync(path.join(dir,name),b);}
fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2));
const engine=new Engine(NES,rom),policy=new MPC(config),actions=[],samples=[],visits=[0];let deaths=0,previous,plans=0;
const submit=mask=>{engine.step(mask);const a=actions.at(-1);if(a&&a[0]===mask)a[1]++;else actions.push([mask,1]);};
if(resumePath){
  const prefix=JSON.parse(fs.readFileSync(resumePath,'utf8'));
  if(!prefix.replayEqual||prefix.romSha256!==profile.romSha256||prefix.coreSha256!==profile.coreSha256)throw Error('Resume requires matching verified input replay');
  for(const [mask,frames]of prefix.actions){for(let f=0;f<frames&&engine.frame<prefixLimit;f++){submit(mask);const s=read(engine);if(s.status===5&&s.stage<8&&s.stage!==visits.at(-1))visits.push(s.stage);if(previous&&s.dead&&!previous.dead)deaths++;previous=s;}if(engine.frame>=prefixLimit)break;}
  manifest.prefixFrames=engine.frame;
  fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2));
} else boot(engine,profile,submit);
previous=read(engine);fs.writeFileSync(path.join(dir,`entry-${previous.stage}.state.json`),JSON.stringify(engine.save()));
fs.writeFileSync(path.join(root,'runs/model-status.json'),JSON.stringify({status:'running',dir:path.basename(dir),frame:engine.frame,stage:previous.stage+1,progress:previous.progress,lives:previous.lives+1,updatedAt:new Date().toISOString()}));
const started=performance.now();
while(engine.frame<budget){
  if(fs.existsSync(path.join(dir,'stop.request')))break;
  const o=read(engine);if(o.over||o.victory||o.stage>=stopStage)break;
  const sequence=policy.choose(engine);plans++;
  for(const mask of sequence){submit(mask);const s=read(engine);if(s.dead&&!previous.dead)deaths++;if(s.stage!==previous.stage){visits.push(s.stage);fs.writeFileSync(path.join(dir,`entry-${s.stage}.state.json`),JSON.stringify(engine.save()));picture(engine,path.join(dir,`entry-${s.stage}.png`));}previous=s;if(s.over||s.victory||s.stage>=stopStage)break;}
  if(plans%8===0){const row={frame:engine.frame,...read(engine),reason:policy.reason,choices:policy.lastChoices};samples.push(row);fs.appendFileSync(path.join(dir,'trace.jsonl'),JSON.stringify(row)+'\n');console.log(JSON.stringify({frame:row.frame,stage:row.stage,progress:row.progress,x:row.x,y:row.y,lives:row.lives,reason:row.reason}));picture(engine,path.join(dir,'latest.png'));fs.writeFileSync(path.join(dir,'latest.state.json'),JSON.stringify(engine.save()));fs.writeFileSync(path.join(root,'runs/model-status.json'),JSON.stringify({status:'running',dir:path.basename(dir),frame:row.frame,stage:row.stage+1,progress:row.progress,lives:row.lives+1,updatedAt:new Date().toISOString()}));}
}
picture(engine,path.join(dir,'final.png'));fs.writeFileSync(path.join(dir,'final.state.json'),JSON.stringify(engine.save()));
const final=observe(engine,profile),expected=fingerprint(engine),replay=new Engine(NES,rom);
for(const [mask,frames]of actions)for(let i=0;i<frames;i++)replay.step(mask);
const actual=fingerprint(replay),replayEqual=JSON.stringify(expected)===JSON.stringify(actual);
const result={config,frames:engine.frame,final,deaths,stageVisits:visits,romSha256:profile.romSha256,coreSha256:profile.coreSha256,
  replayEqual,expected,actual,fullGameClearVerified:final.victory&&replayEqual&&profile.stageOrder.every((s,i)=>visits[i]===s),wallSeconds:(performance.now()-started)/1000,actions,samples};
fs.writeFileSync(path.join(dir,'result.json'),JSON.stringify(result));console.log(JSON.stringify({...result,actions:undefined,samples:undefined}));console.log('RESULTS '+dir);
fs.writeFileSync(path.join(root,'runs/model-status.json'),JSON.stringify({status:'completed',dir:path.basename(dir),frame:engine.frame,stage:final.stage+1,replayEqual,updatedAt:new Date().toISOString()}));
require('./report.cjs').buildReport();
