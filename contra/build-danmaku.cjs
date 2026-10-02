const fs=require('fs'),path=require('path');
const migrationPath=path.join(__dirname,'danmaku-migration.json');
if(fs.existsSync(migrationPath)){const migration=JSON.parse(fs.readFileSync(migrationPath));if(path.basename(path.resolve(process.argv[2]))===migration.run){require('child_process').execFileSync(process.execPath,[path.join(__dirname,'import-bilibili-danmaku.cjs'),path.resolve(__dirname,'..',migration.sourcePath),process.argv[2]],{stdio:'inherit'});process.exit(0);}}
const base=path.resolve(process.argv[2]),read=name=>JSON.parse(fs.readFileSync(path.join(base,name))),r=read('result.json'),p=read('process-audit.json'),c=read('combat-audit.json');
if(!p.replayEqual||!c.replayEqual||!r.oneLifeClearVerified)throw Error('Unverified source');
const copy=JSON.parse(fs.readFileSync(path.join(__dirname,'danmaku-copy.json'))),entries=[];
const burst=(frame,texts,source)=>texts.forEach((text,i)=>entries.push({frame:frame+i*90,text,source,accent:i===1,category:'event',priority:3}));
burst(840,['小时候卡在第一关的集合','先别奶，看到结局再说'],{kind:'opening'});
const stageLines=[[],['这关我以前只会乱扫','原来真得对着核心打'],['瀑布来了，手心开始出汗','先落稳，别急着连跳'],['又到这个双头了','这关当年是真的坐牢'],['雪地的坦克我有阴影','看看它怎么处理'],['火焰区，懂的都懂','这关先把命保住'],['到机库了，别在这翻车','枪别停，路慢慢走'],['最后一关了','现在别急着庆祝']];
for(let stage=1;stage<8;stage++){const event=p.events.find(e=>e.kind==='stage'&&e.stage===stage);if(event)burst(event.frame+90,stageLines[stage],{kind:'stage',frame:event.frame,stage});}
const weapons=['普通','机枪','火球','散弹','激光'];let lastWeapon=-Infinity;
for(const e of p.events.filter(e=>e.kind==='weapon'&&e.weapon>0)){if(e.frame-lastWeapon<1800)continue;lastWeapon=e.frame;burst(e.frame+30,e.weapon===3?['S来了！','这下枪口有排面了']:e.weapon===4?['激光拿到了','这声音一出来，童年回来了']:[`换${weapons[e.weapon]}了`],{kind:'weapon',frame:e.frame,weapon:e.weapon});}
const gunLines=['这炮台得拆，不然背后一直有人打','打掉了，走走走','终于不绕着它走了','枪口转过去了哈哈','这个架枪的先处理','停下来打也行，活着最要紧'];let gunIndex=0,lastGun=-Infinity;
for(const e of c.events.filter(e=>e.kind==='gun')){if(e.frame-lastGun<900||e.frame>59000&&e.frame<60000)continue;lastGun=e.frame;burst(e.frame+24,[gunLines[gunIndex++%gunLines.length]],{kind:'confirmed_gun_kill',frame:e.frame,type:e.type});}
let lastLanding=-Infinity;
for(const e of p.events.filter(e=>e.kind==='landing'&&e.stage===2&&e.nearby.some(t=>[4,6,7,14].includes(t.type)))){if(e.frame-lastLanding<3600)continue;lastLanding=e.frame;burst(e.frame+20,['这落点还真站住了','我跳这儿一般就没了'],{kind:'landing',frame:e.frame,x:e.x,y:e.y});}
const drop=r.samples.find(s=>s.decision?.name==='drop'&&s.decision.combatValue>0);
if(drop){const begin=drop.frame-drop.decision.commitFrames;burst(begin+20,['诶？怎么往下走了','下面也有个架枪的，先拆'],{kind:'decision',frame:begin,decision:'drop'});const kills=c.events.filter(e=>e.kind==='gun'&&e.frame>=begin&&e.frame<=drop.frame);kills.forEach((e,i)=>burst(e.frame+35,[i?'下面这个也没了':'上面那个打掉了'],{kind:'confirmed_gun_kill',frame:e.frame,type:e.type}));burst(drop.frame+25,['哦，换一层把两个都收了','这一段我真学会了'],{kind:'decision_end',frame:drop.frame});}
burst(r.frames+60,['真一命打完了','现在可以开香槟了','小时候两个人都没打到这儿'],{kind:'verified_clear',frame:r.frames});
const stageStarts=Array.from({length:8},(_,stage)=>stage===0?780:p.events.find(e=>e.kind==='stage'&&e.stage===stage).frame);
const add=(frame,text,source,category,priority)=>entries.push({frame:Math.round(frame),text,source,category,priority,accent:category==='operation'});
for(let stage=0;stage<8;stage++){
 const start=stageStarts[stage]+360,end=(stageStarts[stage+1]||r.frames)-300;
 copy.stage[stage].forEach((text,i)=>add(start+(end-start)*(i+.5)/copy.stage[stage].length,text,{kind:'stage_context',stage,frame:stageStarts[stage]},'stage',1));
}
const aiDialogues=JSON.parse(fs.readFileSync(path.join(__dirname,'danmaku-ai-dialogues.json')));
aiDialogues.forEach((texts,index)=>{
 const stage=Math.floor(index/3),fraction=[.2,.5,.8][index%3],start=stageStarts[stage]+600,end=(stageStarts[stage+1]||r.frames)-600,frame=Math.round(start+(end-start)*fraction);
 texts.forEach((text,reply)=>{add(frame+reply*150,text,{kind:'authored_ai_commentary',stage,frame,notViewerQuote:true},'ai',2.5);entries.at(-1).replyGroup=`ai-${index}`;entries.at(-1).accent=reply===1;});
});
copy.ambient.forEach((text,i)=>{const frame=900+(r.frames-1200)*(i+.5)/copy.ambient.length,snapshot=p.samples.reduce((a,b)=>Math.abs(b.frame-frame)<Math.abs(a.frame-frame)?b:a);add(frame,text,{kind:'replay_context',frame:snapshot.frame,stage:snapshot.stage},'chat',0);});
const landings=p.events.filter(e=>e.kind==='landing'&&e.frame>1000&&e.stage>=0&&e.stage<8);let lastLand=-Infinity,landIndex=0;
for(const e of landings){if(e.frame-lastLand<3000||landIndex>=copy.landing.length)continue;lastLand=e.frame;add(e.frame+18,copy.landing[landIndex++],{kind:'landing',frame:e.frame,x:e.x,y:e.y,stage:e.stage},'operation',2);}
let killIndex=0,sniperIndex=0;
for(const e of c.events){if(e.kind==='gun'&&killIndex<copy.gun.length)add(e.frame+30,copy.gun[killIndex++],{kind:'confirmed_gun_kill',frame:e.frame,type:e.type,stage:e.stage-1},'operation',2);else if(e.kind==='sniper'&&sniperIndex<copy.sniper.length)add(e.frame+30,copy.sniper[sniperIndex++],{kind:'confirmed_sniper_kill',frame:e.frame,type:e.type,stage:e.stage-1},'operation',2);}
// Reserve specific reactions first. Generic chat fills the remaining free tracks.
// A deterministic spread avoids using only early-game chat when the cap is reached.
entries.forEach((e,i)=>{e.text=e.text.replace(/[，,]/g,' ');e.spread=(i*37)%entries.length;if(e.source.kind==='verified_clear')e.priority=5;else if(e.category==='event'&&e.frame>=59300&&e.frame<=59900)e.priority=4;});
entries.sort((a,b)=>b.priority-a.priority||(a.priority>=2.5?a.frame-b.frame:a.spread-b.spread));
const lanes=[[],[],[]],scheduled=[],used=new Set(),groupsSeen=new Set(),durationFrames=480,target=300;
for(const entry of entries){
 if(entry.replyGroup&&groupsSeen.has(entry.replyGroup))continue;
 const batch=entry.replyGroup?entries.filter(e=>e.replyGroup===entry.replyGroup).sort((a,b)=>a.frame-b.frame):[entry];
 if(entry.replyGroup)groupsSeen.add(entry.replyGroup);
 if(batch.some(e=>used.has(e.text)||/[稳硬]/.test(e.text))||scheduled.length+batch.length>target)continue;
 const reservations=lanes.map(items=>[...items]),messages=[];
 for(const item of batch){const lane=reservations.findIndex(items=>items.every(t=>item.frame>=t+durationFrames||item.frame+durationFrames<=t));if(lane<0)break;reservations[lane].push(item.frame);const {priority,spread,...message}=item;messages.push({...message,lane,durationFrames});}
 if(messages.length!==batch.length)continue;
 for(const message of messages){scheduled.push(message);lanes[message.lane].push(message.frame);used.add(message.text);}
}
scheduled.sort((a,b)=>a.frame-b.frame);scheduled.forEach((e,id)=>e.id=id);
const categories={},perStage={};for(const e of scheduled){categories[e.category]=(categories[e.category]||0)+1;const stage=stageStarts.findLastIndex(f=>f<=e.frame)+1;perStage[stage]=(perStage[stage]||0)+1;}
const gaps=scheduled.slice(1).map((e,i)=>(e.frame-scheduled[i].frame)/60),stats={entries:scheduled.length,uniqueTexts:used.size,categories,perStage,maxGapSeconds:Math.max(...gaps),meanGapSeconds:gaps.reduce((a,b)=>a+b,0)/gaps.length};
fs.writeFileSync(path.join(base,'danmaku.json'),JSON.stringify({run:p.run,authored:true,source:'verified replay events',previewFrame:drop?drop.frame-80:2400,stats,entries:scheduled},null,2));
fs.writeFileSync(path.join(base,'danmaku-density.json'),JSON.stringify(stats,null,2));console.log(JSON.stringify({...stats,sourceEvents:p.events.length}));
