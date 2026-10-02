'use strict';
(()=>{
 const $=id=>document.getElementById(id),v=$('video'),names=['丛林','基地一','瀑布','基地二','雪地','能源区','机库','异形巢穴'];let record,telemetry,danmaku,starts=[],chapterFrames=[];v.addEventListener('error',()=>{$('status-overlay').hidden=false;$('status-overlay').textContent='回放视频未安装：运行 python tools/setup.py --video 或 python contra/native-video.py contra/runs/native-20261001-201819/result.json';});
 const fmt=s=>`${Math.floor(s/60).toString().padStart(2,'0')}:${Math.floor(s%60).toString().padStart(2,'0')}`;
 const clockFormat=new Intl.DateTimeFormat('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
 const updateClock=()=>{$('time').textContent=clockFormat.format(new Date());};updateClock();setInterval(updateClock,1000);
 const pressedUntil=new Map();let previousFrame=null,lastRatesAt=-Infinity,visualDirection='4',nextDirectionAt=0;
 v.onseeking=()=>{previousFrame=null;pressedUntil.clear();visualDirection='4';nextDirectionAt=0;lastRatesAt=-Infinity;};
 function lastIndex(rows,frame,key){let lo=0,hi=rows.length;while(lo<hi){const mid=(lo+hi)>>1;if(key(rows[mid])<=frame)lo=mid+1;else hi=mid;}return Math.max(0,lo-1);}
 function keyRates(frame){
  const end=frame+1,begin=Math.max(0,end-60),total=end-begin,counts={0:0,1:0,2:0,16:0,32:0,64:0,128:0};let covered=0;
  for(let i=lastIndex(starts,begin,x=>x);i<record.actions.length&&starts[i]<end;i++){
   const [mask,count]=record.actions[i],overlap=Math.max(0,Math.min(end,starts[i]+count)-Math.max(begin,starts[i]));covered+=overlap;
   for(const bit of [1,2,16,32,64,128])if(mask&bit)counts[bit]+=overlap;
   if(!(mask&240))counts[0]+=overlap;
  }
  counts[0]+=total-covered;
  return Object.fromEntries(Object.entries(counts).map(([bit,count])=>[bit,`${Math.round(count/total*100)}%`]));
 }
 function feedbackMask(begin,end){let mask=0;for(let i=lastIndex(starts,begin,x=>x);i<record.actions.length&&starts[i]<=end;i++)if(starts[i]+record.actions[i][1]>begin)mask|=record.actions[i][0];return mask;}
 function showController(frame,mask,now){
  const discontinuity=previousFrame===null||frame<previousFrame||frame-previousFrame>180;
  if(discontinuity)pressedUntil.clear();
  const events=discontinuity||frame===previousFrame?mask:feedbackMask(previousFrame+1,Math.min(frame,record.frames-1));
  for(const bit of [1,2,16,32,64,128])if((events|mask)&bit)pressedUntil.set(bit,now+350);
  const active=bit=>now<(pressedUntil.get(bit)||0);
  document.querySelectorAll('[data-bit]').forEach(el=>{const bit=Number(el.dataset.bit);el.classList.toggle('active',active(bit));el.dataset.actualPressed=String(!!(mask&bit));});
  const desired=mask&16?'0':mask&32?'2':mask&64?'1':mask&128?'3':'4',directionBit={'0':16,'1':64,'2':32,'3':128};
  if(desired!=='4'&&now>=nextDirectionAt){if(desired!==visualDirection)nextDirectionAt=now+200;visualDirection=desired;}
  else if(desired==='4'&&!active(directionBit[visualDirection]))visualDirection='4';
  document.querySelector('.dpad').dataset.direction=visualDirection;
  for(const [id,bit] of [['button-a',1],['button-b',2]]){const el=$(id);el.classList.toggle('active',active(bit));el.dataset.actualPressed=String(!!(mask&bit));}
  previousFrame=frame;
 }
 function toggle(){if(v.paused)v.play().catch(e=>$('status-overlay').textContent=e.message);else v.pause();}
 function jumpChapter(){if(!chapterFrames.length)return;const f=Math.round(v.currentTime*60),current=lastIndex(chapterFrames,f,x=>x.frame);v.currentTime=chapterFrames[(current+1)%chapterFrames.length].frame/60;}
 $('play').onclick=toggle;$('hardware-start').onclick=toggle;$('hardware-select').onclick=jumpChapter;$('restart').onclick=()=>{v.currentTime=0;v.play().catch(()=>{});};$('chapter').onchange=()=>v.currentTime=Number($('chapter').value)/60;
 $('speed').onchange=()=>{v.preservesPitch=true;v.playbackRate=Number($('speed').value);};$('sound').onchange=()=>{v.muted=!$('sound').checked;v.volume=.8;};$('seek').oninput=()=>{if(v.duration)v.currentTime=Number($('seek').value)/1000*v.duration;};$('back').onclick=()=>v.currentTime=Math.max(0,v.currentTime-10);$('forward').onclick=()=>v.currentTime=Math.min(v.duration||0,v.currentTime+10);
 $('capture').onclick=()=>document.body.classList.toggle('capture-mode');$('fullscreen').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else document.querySelector('.broadcast').requestFullscreen().catch(()=>{});};$('loop').onchange=()=>v.loop=$('loop').checked;
 document.addEventListener('keydown',e=>{if(e.code==='Escape')document.body.classList.remove('capture-mode');if(['INPUT','SELECT','BUTTON'].includes(e.target.tagName))return;if(e.code==='Space'||e.code==='Enter'){e.preventDefault();toggle();}if(e.code==='Escape')document.body.classList.remove('capture-mode');});v.onplay=()=>{$('play').textContent='暂停回放';$('status-overlay').hidden=true;};v.onpause=()=>{$('play').textContent='继续播放';};v.onloadedmetadata=()=>{$('speed').onchange();const start=Number(new URLSearchParams(location.search).get('t'));if(Number.isFinite(start)&&start>0)v.currentTime=Math.min(start,v.duration);};
 function update(){requestAnimationFrame(update);if(!record||!telemetry)return;const frame=Math.floor(v.currentTime*30)*2+2,row=telemetry.rows[lastIndex(telemetry.rows,frame,x=>x.frame)],idx=lastIndex(starts,frame,x=>x),mask=frame>=record.frames?0:record.actions[idx][0];
  const now=performance.now();showController(frame,mask,now);
  if(v.paused||now-lastRatesAt>=250){const rates=keyRates(frame);document.querySelectorAll('[data-bit]').forEach(el=>el.querySelector('span').textContent=rates[el.dataset.bit]);document.querySelector('.key.center span').textContent=rates[0];$('button-b').querySelector('span').textContent=rates[2];$('fire-prob').textContent=rates[1];lastRatesAt=now;}
  $('stage').textContent=row.stage<8?`${row.stage+1} / 8`:'通关';$('score').textContent=(row.score*100).toLocaleString();$('deaths').textContent=row.deaths;$('weapon').textContent=['普通','机枪','火球','散弹','激光'][row.weapon]||'普通';$('elapsed').textContent=`${fmt(v.currentTime)} / ${fmt(v.duration||0)}`;$('seek').value=v.duration?Math.round(v.currentTime/v.duration*1000):0;
  const stage=Math.min(row.stage,7),chapter=chapterFrames.find(x=>x.stage===stage);if(chapter)$("chapter").value=chapter.frame;if(danmaku)danmaku.update(frame);
 }
 async function init(){try{const meta=await(await fetch('runs/latest-video.json',{cache:'no-store'})).json();if(!/^native-\d{8}-\d{6}$/.test(meta.run))throw Error('无效回放记录');const responses=await Promise.all([fetch(`runs/${meta.run}/result.json`),fetch(`runs/${meta.run}/replay-telemetry.json`)]);if(responses.some(r=>!r.ok))throw Error('回放数据未就绪');[record,telemetry]=await Promise.all(responses.map(r=>r.json()));if(!record.oneLifeClearVerified||!record.replayEqual||!meta.replayEqual||telemetry.run!==meta.run||!telemetry.replayEqual)throw Error('一命回放尚未核验');
  const comments=await(await fetch(`runs/${meta.run}/danmaku.json`)).json();if(comments.run!==meta.run)throw Error("弹幕记录不匹配");danmaku=new ReplayDanmaku(comments);
  let frame=0;starts=record.actions.map(a=>{const start=frame;frame+=a[1];return start;});for(const row of telemetry.rows)if(row.stage<8&&!chapterFrames.some(c=>c.stage===row.stage))chapterFrames.push({stage:row.stage,frame:row.frame});$('chapter').replaceChildren(...chapterFrames.map(c=>{const o=document.createElement('option');o.value=c.frame;o.textContent=`第 ${c.stage+1} 关 · ${names[c.stage]}`;return o;}));$('chapter').disabled=false;$('play').disabled=false;$('restart').disabled=false;
  $('facts').textContent=`8 / 8 关已通关 · ${record.frames.toLocaleString()} 帧 · 死亡 ${record.deaths} 次 · 状态 / RAM / 画面哈希一致`;$('record').href=`runs/${meta.run}/result.json`;$('audit').href=`runs/${meta.run}/video-audit.json`;v.src=`runs/${meta.video}`;$('play').textContent='播放一命路线';$('status-overlay').hidden=true;v.play().catch(()=>{$('status-overlay').hidden=false;$('status-overlay').textContent='按 START 开始回放';});update();
 }catch(e){$('facts').textContent=e.message;$('status-overlay').textContent=e.message;}}init();
})();
