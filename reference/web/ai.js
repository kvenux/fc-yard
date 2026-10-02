// Privileged state-based baseline: reads state, acts only through normal keys.
let aiEnabled=false,aiTicks=0,aiReason='手动',aiRngState=1;
let aiTraceEnabled=false,aiTraceFrames=[],aiTraceEvents=[];
const aiDirs=['ArrowUp','ArrowLeft','ArrowDown','ArrowRight'];
function aiObserve(){return {phase:gamePhase,stage:stageIdx+1,score:p1Score,lives:p1Lives+1,eagle:eagleAlive,remaining:enemiesLeft+activeEnemyCount,player:entities?.[0]&&{x:entities[0].x,y:entities[0].y},reason:aiReason};}
function aiStart(seed=1,config={}){aiRngState=seed>>>0;Math.random=()=>{aiRngState=(Math.imul(aiRngState,1664525)+1013904223)>>>0;return aiRngState/4294967296;};plannerReset(config);aiTraceEnabled=!!config.trace;aiTraceFrames=[];aiTraceEvents=[];numPlayers=1;demoMode=false;p1Score=0;p1Lives=2;p1NextLifeScore=20000;aiTicks=0;initLevel(0);aiEnabled=true;}
function aiPolicy(){
 aiTicks++;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;if(gamePhase!=='play')return;
 const p=entities[0];if(!p.alive||p.spawnAnim)return;
 const threats=entities.slice(2).filter(e=>e.alive&&!e.spawnAnim).sort((a,b)=>(b.y-Math.abs(b.x-120)*.3)-(a.y-Math.abs(a.x-120)*.3));
 const incoming=bullets.filter(b=>b.active&&b.owner>=2&&b.dir===2&&b.y<p.y&&Math.abs(b.x-120)<16).sort((a,b)=>b.y-a.y)[0];
 const threat=threats[0];const tx=120;
 let d=0,move=true;
 if(p.y>184){d=0;aiReason='返回基地上方防线';}
 else if(p.y<182){d=2;aiReason='返回防线';}
 else if(Math.abs(p.x-tx)>0){d=tx<p.x?1:3;aiReason=incoming?'拦截射向基地的子弹':'沿防线对齐敌人';}
 else {d=0;move=p.dir!==0;aiReason='驻守，向上射击';}
 if(move)keys[aiDirs[d]]=true;
 const eagleAhead=(d===2&&p.y<216&&Math.abs(p.x-120)<16)||(d===3&&p.x<120&&Math.abs(p.y-216)<16)||(d===1&&p.x>120&&Math.abs(p.y-216)<16);
 keys.Space=!eagleAhead&&aiTicks%4<2;
}
const originalUpdate=update;update=function(){if(aiEnabled){if(plannerConfig.mode==='static')aiPolicy();else plannerPolicy();}const before=aiTraceEnabled&&aiEnabled&&gamePhase==='play'?{frame:aiTicks,...aiObserve(),player:{...entities[0]},keys:aiDirs.filter(k=>keys[k]),fire:!!keys.Space,enemies:entities.slice(2).filter(e=>e.alive).map(e=>({x:e.x,y:e.y,dir:e.dir})),bullets:bullets.filter(b=>b.active).map(b=>({x:b.x,y:b.y,dir:b.dir,owner:b.owner})),powerUp:powerUp&&{...powerUp}}:null;originalUpdate();if(before){aiTraceFrames.push(before);if(aiTraceFrames.length>60)aiTraceFrames.shift();const after=aiObserve();if(before.score!==after.score||before.lives!==after.lives||before.eagle!==after.eagle||after.phase==='clear'){aiTraceEvents.push({before,after,context:before.lives!==after.lives||before.eagle!==after.eagle?[...aiTraceFrames]:undefined});}}};
window.tankAI={start:aiStart,observe:aiObserve,trace(){return aiTraceEvents;},step(n=1,draw=true){for(let i=0;i<n;i++)update();if(draw){render();aiPanelUpdate();}return aiObserve();},stop(){aiEnabled=false;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;}};
const panel=document.createElement('div');panel.style='background:#172033;color:white;padding:10px;margin:8px auto;font:14px monospace;max-width:750px';panel.innerHTML='<b>单人启发式 AI · 浏览器复刻版</b> <label>种子 <input id="ai-seed" type="number" value="1" min="1" style="width:60px"></label> <button id="ai-on">筛选优胜策略</button> <button id="ai-static">旧版守中路</button> <button id="ai-off">手动</button><div id="ai-state" style="margin-top:8px"></div>';document.body.insertBefore(panel,document.getElementById('screen'));document.getElementById('ai-on').onclick=()=>aiStart(Number(document.getElementById('ai-seed').value)||1);document.getElementById('ai-static').onclick=()=>aiStart(Number(document.getElementById('ai-seed').value)||1,{mode:'static'});document.getElementById('ai-off').onclick=()=>tankAI.stop();function aiPanelUpdate(){const o=aiObserve();document.getElementById('ai-state').textContent=`第 ${o.stage||1} 关 · ${o.score} 分 · 生命 ${Math.max(0,o.lives)} · 基地 ${o.eagle===false?'被毁':'存活'} · ${o.reason}`;}setInterval(aiPanelUpdate,500);




// Rendering must not consume gameplay random state.
const originalRender=render;render=function(){const state=aiRngState;try{return originalRender();}finally{aiRngState=state;}};
