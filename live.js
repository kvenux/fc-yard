'use strict';
(()=>{
  const $=id=>document.getElementById(id), canvas=$('game'), ctx=canvas.getContext('2d');
  function updateClock(){const now=new Date();$('time').textContent=[now.getHours(),now.getMinutes(),now.getSeconds()].map(n=>String(n).padStart(2,'0')).join(':');}
  updateClock();setInterval(updateClock,1000);
  ctx.imageSmoothingEnabled=false;
  const controls=new ControllerFeedback();
  let engine,state,playing=false,loaded=false,accumulator=0,lastTime=performance.now();
  let session=null,lastPhase='',strategy='',strategySince=0,strategyIndex=0,sound=false;
  let autoTimer=null,settlementTick=null,restartAt=0,fpsFrames=0,fpsSince=performance.now();
  let history=[];try{history=JSON.parse(localStorage.getItem('fc-live-sessions')||'[]');if(!Array.isArray(history))history=[];}catch{}
  const params=new URLSearchParams(location.search);
  $('level').innerHTML=Array.from({length:35},(_,i)=>`<option value="${i+1}">第 ${String(i+1).padStart(2,'0')} 关</option>`).join('');
  if(params.has('seed'))$('seed').value=params.get('seed');
  if(location.hash==='#capture'||params.get('capture')==='1')document.body.classList.add('capture-mode');
  function save(){try{localStorage.setItem('fc-live-sessions',JSON.stringify(history.slice(-100)));}catch{}}
  function finish(result){if(!session||session.result)return;Object.assign(session,{result,endedAt:new Date().toISOString(),score:state.score,stage:state.stage,lives:state.lives,frames:state.ticks});history.push(session);save();try{localStorage.removeItem('fc-live-current');}catch{}}
  function saveCurrent(){if(session&&!session.result){try{localStorage.setItem('fc-live-current',JSON.stringify({...session,score:state.score,frames:state.ticks,stage:state.stage,lives:state.lives}));}catch{}}}
  function seed(){const n=Number($('seed').value);return Number.isInteger(n)&&n>=0&&n<=4294967295?n:4004;}
  function cancelRestart(){clearTimeout(autoTimer);clearInterval(settlementTick);autoTimer=null;settlementTick=null;restartAt=0;}
  function scheduleRestart(){
    cancelRestart();
    if(!$('auto-restart').checked){$('mvp-countdown').textContent='';$('mvp-next').textContent='自动重开已暂停';$('mvp-progress').style.width='0%';return;}
    restartAt=Date.now()+20000;
    const refresh=()=>{const remaining=Math.max(0,restartAt-Date.now());$('mvp-countdown').textContent=Math.ceil(remaining/1000);$('mvp-next').textContent=' 秒后从第一关再战';$('mvp-progress').style.width=remaining/200+'%';};
    refresh();settlementTick=setInterval(refresh,200);
    autoTimer=setTimeout(()=>start(1),20000);
  }
  function showSettlement(){
    const seconds=Math.floor(state.ticks/60);
    $('mvp-title').textContent=state.phase==='victory'?'全关通关':!state.eagle?'基地失守 · 再战一局':'本局结束 · 再战一局';
    $('mvp-score').textContent=state.score.toLocaleString('en-US');$('mvp-stages').textContent=session.stages.length+' / 35';
    $('mvp-time').textContent=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');
    $('mvp-lives').textContent=Math.max(0,state.lives);$('mvp-base').textContent=state.eagle?'完好':'失守';
    $('settlement').hidden=false;controls.reset();scheduleRestart();
  }
  function start(stage=1){
    if(!loaded)return;cancelRestart();$('settlement').hidden=true;finish('interrupted');
    const value=seed();$('seed').value=value;state=engine.start(value,stage);
    session={startedAt:new Date().toISOString(),seed:value,startStage:stage,policy:'full-model-speed+intent-fire-5hz-v4',mode:stage===1?'full-run':'stage-practice',stages:[]};
    strategy='';strategyIndex=0;lastPhase='';accumulator=0;lastTime=performance.now();playing=true;controls.reset();
    $('run-kind').textContent=stage===1?'完整对局':'单关起步';$('level').value=stage;saveCurrent();paint();updateUI(true);
  }
  function toggle(){if(!loaded||state.terminal)return;playing=!playing;accumulator=0;lastTime=performance.now();if(!playing)engine.quiet();updateUI(true);}
  const narratives=new StrategyNarrative();
  function classify(s){
    const plan=(id,title,copy,urgent=false)=>({id,title:title.replace(/[。．.]/g,''),urgent});
    if(s.terminal)return s.phase==='victory'?plan('victory','全部关卡突破，基地守住了','本轮作战结束，正在汇总得分与通关表现。'):!s.eagle?plan('lost','基地失守，本轮防线被突破','结束本轮作战，准备重新挑战。'):plan('over','可用生命耗尽，本轮作战结束','保留本轮成绩，准备从头再战。');
    if(s.phase==='clear')return plan('clear','本关敌人清空，准备进入下一关','完成这一轮拦截，下一关重新判断敌方路线。');
    if(s.phase==='start'||s.spawning)return plan('spawn','等待坦克就位，准备建立防线','出场后根据敌人位置，选择第一处拦截点。');
    const enemies=s.threats,fire=s.fireControl?.reason||'';
    if(enemies.some(e=>e.y>160&&Math.abs(e.x-120)<40))return plan('base','敌人逼近基地，优先封住中路','先处理基地附近的威胁，再恢复向前推进。',true);
    if(fire==='迎击子弹')return plan('bullet','前方出现来袭炮弹，先化解威胁','当前开火用于迎击子弹，避免正面承受攻击。',true);
    if(fire==='清除路径砖墙')return plan('path','前进路线被砖墙挡住，先打通通道','清除眼前障碍后，继续向选定的拦截位置移动。');
    if(fire==='清除敌人前砖墙')return plan('wall','目标被砖墙遮挡，正在打开射线','先拆掉敌我之间的掩体，再寻找直接命中的机会。');
    if(s.progress?.replanning&&enemies.length)return plan('replan','当前等待没有进展，重新选择进攻位置','调整接敌距离和落点，争取更快形成有效攻击。');
    if(!enemies.length)return plan('waiting','视野内暂时没有敌人，等待下一批出现','保留基地防线，目标出现后再决定移动和开火。');
    if(s.remaining<=3)return plan('cleanup','敌人所剩不多，进入最后清场阶段','根据残敌位置寻找拦截机会，尽快结束本关。');
    const g=s.goal,p=s.player;
    if(p&&enemies.some(e=>Math.abs(e.x-p.x)+Math.abs(e.y-p.y)<40))return plan('close','敌人进入近身范围，寻找安全交火角度','结合移动与射击处理近处威胁，避免被贴身压制。');
    if(fire==='拦截敌人')return plan('shot','敌人进入有效射线，抓住窗口开火','目标已满足射击条件，按限速节奏争取命中。');
    if(g&&p&&Math.abs(g.x-p.x)+Math.abs(g.y-p.y)>16){
      if(g.y>=160&&Math.abs(g.x-120)<32)return plan('center','向基地前方靠拢，建立中路拦截点','缩短回防距离，从中间观察两侧敌人的推进。');
      if(g.x<80||g.x>160)return plan(g.x<80?'left':'right',`向${g.x<80?'左':'右'}侧换位，寻找侧翼拦截角度`,'离开当前站位，争取在敌人深入前形成有效射线。');
      if(g.y<p.y-16)return plan('advance','向前推进接近目标，缩短等待时间','正在前往更靠前的落点，争取提早接敌。');
      return plan('align','调整站位与射线，寻找下一次命中机会','沿选定路线移动，避免在无效位置持续等待。');
    }
    if(s.lives<=1)return plan('survive','剩余生命不多，守住位置谨慎交火','当前以存活和基地安全为先，等待有效射击窗口。');
    return plan('hold','已到达拦截位置，观察敌人进入射线','保持当前防线，有明确目标才开火；无进展时再换位。');
  }
  function updateUI(force=false){
    if(!state)return;
    const s=state,duration=Number($('hold').value);
    const next=classify(s),urgent=s.terminal||s.phase!==lastPhase||next.urgent;
    if(!strategy||(urgent&&next.id!==strategy.id)||s.ticks-strategySince>=duration*60){strategy={...next,copy:narratives.next(next.id)};strategySince=s.ticks;strategyIndex++;}
    $('strategy-title').textContent=strategy.title;
    $('strategy-copy').textContent=strategy.copy;
    $('phase-number').textContent='当前决策';
    $('phase-time').textContent=s.remaining===0?'本关已清空':'剩余 '+s.remaining+' 敌';
    $('phase-progress').style.width=Math.min(100,(20-s.remaining)*5)+'%';
    $('stage').textContent=s.stage+' / 35';$('score').textContent=s.score.toLocaleString('en-US');$('lives').textContent=Math.max(0,s.lives);
    $('base-state').textContent=s.eagle?'完好':'失守';$('base-state').classList.toggle('lost',!s.eagle);
    $('play').textContent=s.terminal?'本局结束':playing?'Ⅱ 暂停':'▶ 继续';$('play').disabled=s.terminal;
    $('level').value=s.stage;$('level-prev').disabled=s.stage===1;$('level-next').disabled=s.stage===35;
    const overlay=$('status-overlay');overlay.hidden=s.terminal||playing;
    overlay.textContent=s.terminal?strategy.title+'\n'+s.score.toLocaleString('en-US')+' 分':!playing?'已暂停':'';
    $('session-state').textContent=`${session.mode==='full-run'?'完整对局':'单关起步'} · 种子 ${session.seed}\n已过 ${session.stages.length} 关 · ${s.ticks.toLocaleString()} 帧`;
  }
  function observe(){
    controls.consume(state);
    if(state.phase==='clear'&&lastPhase!=='clear'){
      session.stages.push({stage:state.stage,score:state.score,lives:state.lives,frame:state.ticks});
      saveCurrent();
    }
    if(state.terminal&&!session.result){playing=false;engine.quiet();finish(state.phase==='victory'?'victory':!state.eagle?'base-lost':'game-over');
      showSettlement();
    }
    updateUI();lastPhase=state.phase;
  }
  function paint(){engine.render();ctx.drawImage(engine.canvas,48,48,624,624,0,0,624,624);}
  function loop(now){
    const dt=Math.min(100,now-lastTime);lastTime=now;
    if(loaded&&playing){
      accumulator=Math.min(12,accumulator+dt/1000*60*Number($('speed').value));
      const deadline=performance.now()+12;let count=0;
      while(accumulator>=1&&playing){state=engine.step();accumulator--;fpsFrames++;count++;observe();if(performance.now()>deadline)break;}
      if(count)paint();
    }
    controls.render(performance.now());
    if(now-fpsSince>=1000){$('actual-speed').textContent=(fpsFrames/(now-fpsSince)*1000/60).toFixed(2)+'× 实际';fpsFrames=0;fpsSince=now;}
    requestAnimationFrame(loop);
  }
  $('play').onclick=toggle;$('hardware-start').onclick=toggle;
  $('restart').onclick=()=>start(state.stage);$('new-run').onclick=()=>start(1);
  $('level').onchange=()=>start(Number($('level').value));
  $('level-prev').onclick=()=>{if(loaded)start(Math.max(1,state.stage-1));};$('level-next').onclick=()=>{if(loaded)start(Math.min(35,state.stage+1));};
  $('hardware-select').onclick=()=>{if(loaded)start(state.stage===35?1:state.stage+1);};
  $('step').onclick=()=>{if(state.terminal)return;playing=false;engine.quiet();state=engine.step();observe();paint();};
  $('sound').onclick=()=>{sound=engine.sound(!sound);$('sound').textContent='声音：'+(sound?'开':'关');};
  $('show-probs').onchange=()=>document.querySelector('.broadcast').classList.toggle('hide-probs',!$('show-probs').checked);
  $('auto-restart').onchange=()=>{if(state?.terminal)scheduleRestart();};
  $('mvp-restart').onclick=()=>start(1);
  $('capture').onclick=()=>{document.body.classList.add('capture-mode');historyReplace('#capture');scrollTo(0,0);};
  function historyReplace(hash){window.history.replaceState(null,'',location.pathname+location.search+hash);}
  $('fullscreen').onclick=async()=>{try{await document.querySelector('.broadcast').requestFullscreen();}catch{$('capture').click();}};
  $('export').onclick=()=>{const blob=new Blob([JSON.stringify({version:1,exportedAt:new Date().toISOString(),history,current:session&&{...session,score:state.score,frames:state.ticks}},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='battle-city-live-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.body.classList.remove('capture-mode');historyReplace('');}if(e.code==='Space'&&!['INPUT','SELECT','BUTTON'].includes(document.activeElement.tagName)){e.preventDefault();toggle();}});
  window.addEventListener('pagehide',saveCurrent);setInterval(saveCurrent,5000);
  async function boot(){try{
    engine=$('engine').contentWindow.liveEngine;if(!engine)throw Error('游戏引擎未载入');await engine.load();loaded=true;
    try{const previous=JSON.parse(localStorage.getItem('fc-live-current')||'null');if(previous&&!history.some(s=>s.startedAt===previous.startedAt)){history.push({...previous,result:'interrupted'});save();}}catch{}
    for(const id of ['play','restart','new-run','step','sound'])$(id).disabled=false;
    start(Math.max(1,Math.min(35,Number(params.get('stage'))||1)));
    if(params.get('paused')==='1')toggle();
    window.liveApp={get state(){return state;},get session(){return session;},get playing(){return playing;},start,pause(){if(playing)toggle();}};
  }catch(e){$('status-overlay').textContent='载入失败\n请刷新重试';$('session-state').textContent=e.message;console.error(e);}}
  $('engine').addEventListener('load',boot,{once:true});
  requestAnimationFrame(loop);
})();
