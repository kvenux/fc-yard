// Privileged state-based baseline: reads state, acts only through normal keys.
let aiEnabled=false,aiTicks=0,aiReason='手动';
const aiDirs=['ArrowUp','ArrowLeft','ArrowDown','ArrowRight'];
function aiObserve(){return {phase:gamePhase,stage:stageIdx+1,score:p1Score,lives:p1Lives+1,eagle:eagleAlive,remaining:enemiesLeft+activeEnemyCount,player:entities?.[0]&&{x:entities[0].x,y:entities[0].y},reason:aiReason};}
function aiStart(seed=1){let s=seed>>>0;Math.random=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};numPlayers=1;demoMode=false;p1Score=0;p1Lives=2;p1NextLifeScore=20000;aiTicks=0;initLevel(0);aiEnabled=true;}
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
const originalUpdate=update;update=function(){if(aiEnabled)aiPolicy();originalUpdate();};
window.tankAI={start:aiStart,observe:aiObserve,step(n=1,draw=true){for(let i=0;i<n;i++)update();if(draw)render();return aiObserve();},stop(){aiEnabled=false;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;}};
const panel=document.createElement('div');panel.style='position:fixed;top:8px;left:8px;background:#172033;color:white;padding:12px;z-index:1000;font:14px monospace;max-width:260px';panel.innerHTML='<b>启发式 AI · 浏览器复刻版</b><br><button id="ai-on">AI 从第一关开始</button> <button id="ai-off">手动</button><pre id="ai-state"></pre>';document.body.append(panel);document.getElementById('ai-on').onclick=()=>aiStart();document.getElementById('ai-off').onclick=()=>tankAI.stop();setInterval(()=>document.getElementById('ai-state').textContent=JSON.stringify(aiObserve(),null,2),500);



