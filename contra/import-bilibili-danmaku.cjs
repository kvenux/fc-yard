const fs=require('fs'),path=require('path'),crypto=require('crypto');
const sourcePath=path.resolve(process.argv[2]),base=path.resolve(process.argv[3]),read=name=>JSON.parse(fs.readFileSync(path.join(base,name),'utf8'));
const record=read('result.json'),processAudit=read('process-audit.json');if(!record.oneLifeClearVerified||!processAudit.replayEqual)throw Error('Unverified target replay');
const selection=JSON.parse(fs.readFileSync(path.join(__dirname,'bilibili-danmaku-selection.json'))),ai=JSON.parse(fs.readFileSync(path.join(__dirname,'danmaku-ai-retained.json'),'utf8').replace(/^\uFEFF/,''));
const raw=fs.readFileSync(sourcePath),hash=crypto.createHash('sha256').update(raw).digest('hex'),sourceDir=path.join(__dirname,'danmaku-sources',selection.sourceBvid);fs.mkdirSync(sourceDir,{recursive:true});fs.writeFileSync(path.join(sourceDir,'original.txt'),raw);
const normalize=text=>text.normalize('NFKC').replace(/[，,]/g,' ').replace(/\s+/g,' ').trim();
const sets=Object.fromEntries(['general','weapons','ending'].map(kind=>[kind,new Set(selection[kind].map(normalize))]));
const stages=Array.from({length:8},(_,stage)=>stage===0?780:processAudit.events.find(e=>e.kind==='stage'&&e.stage===stage).frame),anchors=selection.sourceStageAnchorsSeconds;
const mapped=[],audit=[],seen=new Set(),rows=raw.toString('utf8').split(/\r?\n/),banned=/[稳硬]|up主|阿婆|坚果|三连|投币|封面|水下|超级魂|改版|无敌|不丢枪|隐身|三个头|三巨头|站空气|影流|电话|简介|置顶|关注|4399|敖厂长|熬厂长|烟山|人在看|正在看|年前来|前来报道|你又偷我人|你等等我|组队拖死|拖死队友|坑队友|20分钟|虚空|假的|(^|\W)(wdnmd|nm|jb)(\W|$)/i;
for(let line=0;line<rows.length;line++){
 const m=rows[line].match(/^\[(\d+):(\d+)\.(\d+)\]\s*(.+)$/);if(!m)continue;
 const seconds=Number(m[1])*60+Number(m[2])+Number('0.'+m[3]),originalText=m[4],text=normalize(originalText),item={line:line+1,seconds,originalText,text};
 let category=Object.keys(sets).find(kind=>sets[kind].has(text));
 if(banned.test(text)){audit.push({...item,decision:'excluded',reason:'context_or_user_style'});continue;}
 if(!category){audit.push({...item,decision:'excluded',reason:'not_curated_for_original_rom'});continue;}
 if(text.length>30||!text){audit.push({...item,decision:'excluded',reason:'length'});continue;}
 if(seen.has(text)){audit.push({...item,decision:'excluded',reason:'duplicate'});continue;}
 let stage=seconds>=anchors[8]?8:anchors.findLastIndex(t=>t<=seconds),frame,alignment='estimated_stage_relative';
 if(category==='ending'||stage===8){frame=record.frames+60+Math.round(Math.max(0,seconds-anchors[8])/109*1680);alignment='verified_clear_then_ending';}
 else {const fraction=(seconds-anchors[stage])/(anchors[stage+1]-anchors[stage]);frame=Math.round(stages[stage]+fraction*((stages[stage+1]||record.frames)-stages[stage]));}
 if(category==='weapons'){
  const weapon=/散弹|S枪|s弹|S\+R/.test(text)?3:/F子弹/.test(text)?2:/L的/.test(text)?4:null;
  const matching=processAudit.samples.filter(e=>e.weapon===weapon&&e.playerState===1&&e.frame>900&&e.stage<8);
  if(weapon===null||!matching.length){audit.push({...item,decision:'excluded',reason:'no_verified_weapon_context'});continue;}
  const snapshot=matching.reduce((a,b)=>Math.abs(b.frame-frame)<Math.abs(a.frame-frame)?b:a);frame=snapshot.frame;stage=snapshot.stage;alignment='verified_weapon_snapshot';
 }
 if(/左右横跳|蛇皮走位|俯卧撑|背后搞偷袭|拖拉机|最好不要乱跳/.test(text)){
  const predicate=e=>e.stage===stage&&e.playerState===1&&(/俯卧撑/.test(text)?!!(e.input&32):/拖拉机/.test(text)?e.nearby.some(t=>t.type===18):/背后/.test(text)?e.nearby.some(t=>[6,14].includes(t.type)&&t.x<e.x):e.jump&&!!(e.input&192));
  const matching=processAudit.samples.filter(predicate);
  if(!matching.length){audit.push({...item,decision:'excluded',reason:'no_matching_action_context'});continue;}
  frame=matching.reduce((a,b)=>Math.abs(b.frame-frame)<Math.abs(a.frame-frame)?b:a).frame;alignment='verified_action_snapshot';
 }
 seen.add(text);mapped.push({frame,text,accent:false,category:'bilibili',source:{kind:'imported_bilibili',bvid:selection.sourceBvid,line:line+1,originalSeconds:seconds,originalText,sourceSha256:hash,alignment,stage},durationFrames:category==='ending'?360:480});
 audit.push({...item,decision:'curated',mappedFrame:frame,alignment});
}
// Spread portable reactions within their inferred stage instead of transplanting
// the original video's crowded bursts and long silent stretches.
for(let stage=0;stage<8;stage++){
 const portable=mapped.filter(e=>e.source.stage===stage&&e.source.alignment==='estimated_stage_relative').sort((a,b)=>a.frame-b.frame),start=stages[stage]+120,end=(stages[stage+1]||record.frames)-180;
 portable.forEach((e,i)=>{e.frame=Math.round(e.frame*.25+(start+(end-start)*(i+.5)/portable.length)*.75);e.source.alignment='estimated_stage_portable_reaction';audit.find(a=>a.line===e.source.line).mappedFrame=e.frame;});
}
// Keep every existing AI message at its original timing. Remove all other authored messages.
const output=ai.map(e=>({...e})),lanes=[[],[],[]];for(const e of output)lanes[e.lane].push({start:e.frame,end:e.frame+e.durationFrames});
const used=new Set(output.map(e=>e.text));mapped.sort((a,b)=>a.frame-b.frame);
for(const entry of mapped){
 if(used.has(entry.text))continue;let chosen;
 const maxFrame=entry.source.stage<8?(stages[entry.source.stage+1]||record.frames)-1:record.frames+1800-entry.durationFrames;
 for(let delay=0;delay<=900;delay+=30){const start=entry.frame+delay;if(start>maxFrame)break;const lane=lanes.findIndex(items=>items.every(t=>start>=t.end||start+entry.durationFrames<=t.start));if(lane>=0){chosen={...entry,frame:start,lane,source:{...entry.source,schedulingDelayFrames:delay}};break;}}
 const row=audit.find(e=>e.line===entry.source.line);if(!chosen){row.decision='excluded';row.reason='track_capacity_in_context';continue;}
 output.push(chosen);used.add(chosen.text);lanes[chosen.lane].push({start:chosen.frame,end:chosen.frame+chosen.durationFrames});row.decision='imported';row.scheduledFrame=chosen.frame;
}
const adaptations=JSON.parse(fs.readFileSync(path.join(__dirname,'bilibili-danmaku-adaptations.json'))),adaptationAudit=[];
for(const group of adaptations){
 const parent=mapped.find(e=>e.text===normalize(group.parent));
 for(const original of group.texts){
  const text=normalize(original);if(!parent||used.has(text)||banned.test(text)||text.length>30){adaptationAudit.push({text,parent:group.parent,decision:'excluded',reason:!parent?'parent_not_curated':'style_or_duplicate'});continue;}
  const scope=group.scope,start=scope==='ending'?record.frames+60:scope==='sourceStage'?stages[parent.source.stage]+120:900,end=scope==='ending'?record.frames+1800:scope==='sourceStage'?(stages[parent.source.stage+1]||record.frames)-120:record.frames-180,durationFrames=scope==='ending'?360:480;
  let chosen;
  // Fill quiet gaps first, preserving every imported comment and every AI reply.
  for(let frame=start;frame+durationFrames<=end;frame+=60){
   const lane=lanes.findIndex(items=>items.every(t=>frame>=t.end||frame+durationFrames<=t.start));if(lane<0)continue;
   const distance=Math.min(...output.map(e=>Math.abs(e.frame-frame)));
   if(!chosen||distance>chosen.distance)chosen={frame,lane,distance};
  }
  if(!chosen){adaptationAudit.push({text,parent:group.parent,decision:'excluded',reason:'track_capacity_in_context'});continue;}
  const stage=stages.findLastIndex(f=>f<=chosen.frame),source={...parent.source,kind:'adapted_bilibili',authored:true,parentText:parent.text,parentLine:parent.source.line,stage,alignment:scope==='ending'?'verified_clear_then_ending':scope==='sourceStage'?'same_stage_authored_reaction':'portable_authored_reaction'};
  const entry={frame:chosen.frame,lane:chosen.lane,durationFrames,text,accent:false,category:'adapted',source};output.push(entry);used.add(text);lanes[chosen.lane].push({start:chosen.frame,end:chosen.frame+durationFrames});adaptationAudit.push({text,parent:parent.text,parentLine:parent.source.line,frame:chosen.frame,decision:'scheduled'});
 }
}
output.sort((a,b)=>a.frame-b.frame);output.forEach((e,id)=>e.id=id);
const categories={},perStage={};for(const e of output){categories[e.category]=(categories[e.category]||0)+1;const stage=stages.findLastIndex(f=>f<=e.frame)+1;perStage[stage]=(perStage[stage]||0)+1;}
const gaps=output.slice(1).map((e,i)=>(e.frame-output[i].frame)/60),stats={entries:output.length,uniqueTexts:used.size,categories,perStage,maxGapSeconds:Math.max(...gaps),meanGapSeconds:gaps.reduce((a,b)=>a+b,0)/gaps.length};
const report={sourcePath,sourceSha256:hash,bvid:selection.sourceBvid,sourceVersion:'93超级魂改版',targetVersion:'Contra US original',alignmentLimit:selection.anchorBasis,parsedComments:audit.length,curated:mapped.length,imported:categories.bilibili||0,retainedAI:ai.length,removedExistingNonAI:JSON.parse(fs.readFileSync(path.join(__dirname,'danmaku-migration.json'))).removedOriginalNonAI,reasons:{},audit};
for(const e of audit)if(e.decision==='excluded')report.reasons[e.reason]=(report.reasons[e.reason]||0)+1;
report.adapted=categories.adapted||0;report.adaptationAudit=adaptationAudit;
fs.writeFileSync(path.join(sourceDir,'migration-report.json'),JSON.stringify(report,null,2));fs.writeFileSync(path.join(base,'danmaku.json'),JSON.stringify({run:processAudit.run,authored:false,mixedAuthored:true,source:'Imported historical Bilibili comments, authored adaptations and retained AI commentary',previewFrame:59548,stats,entries:output},null,2));fs.writeFileSync(path.join(base,'danmaku-density.json'),JSON.stringify(stats,null,2));console.log(JSON.stringify({...stats,parsedComments:report.parsedComments,curated:report.curated,excluded:report.reasons,retainedAI:ai.length}));
