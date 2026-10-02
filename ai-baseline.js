// Privileged state-based baseline: reads state, acts only through normal keys.
let aiEnabled=false,aiTicks=0,aiReason='手动',aiVisits=new Map();
const aiDirs=['ArrowUp','ArrowLeft','ArrowDown','ArrowRight'];
function aiObserve(){return {phase:gamePhase,stage:stageIdx+1,score:p1Score,lives:p1Lives+1,eagle:eagleAlive,remaining:enemiesLeft+activeEnemyCount,player:entities?.[0]&&{x:entities[0].x,y:entities[0].y},reason:aiReason};}
function aiStart(seed=1){let s=seed>>>0;Math.random=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};numPlayers=1;demoMode=false;p1Score=0;p1Lives=2;p1NextLifeScore=20000;aiTicks=0;aiVisits.clear();initLevel(0);aiEnabled=true;}
function aiPolicy(){aiTicks++;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;if(gamePhase!=='play')return;const p=entities[0];if(!p.alive)return;
 const enemies=entities.slice(2).filter(e=>e.alive&&!e.spawnAnim).sort((a,b)=>(b.y*2-Math.abs(b.x-EAGLE.x))-(a.y*2-Math.abs(a.x-EAGLE.x)));
 const target=enemies[0]||{x:88,y:176};let best=-Infinity,dir=0;
 const visitKey=`${Math.round(p.x/8)},${Math.round(p.y/8)}`;aiVisits.set(visitKey,(aiVisits.get(visitKey)||0)+1);
 for(let d=0;d<4;d++){let x=p.x+DX[d]*8,y=p.y+DY[d]*8;let value=-Math.abs(x-target.x)*.5-Math.abs(y-Math.min(target.y+32,184))*.35;
  const vertical=d===0||d===2,along=vertical?(target.y-p.y)*DY[d]:(target.x-p.x)*DX[d],cross=vertical?Math.abs(target.x-p.x):Math.abs(target.y-p.y);
  if(cross<8&&along>0)value+=90;
  if(!canMove(p,d))value-=35;
  value-=(aiVisits.get(`${Math.round(x/8)},${Math.round(y/8)}`)||0)*.5;
  if(y>192&&Math.abs(x-EAGLE.x)<24)value-=80;
  for(const b of bullets){if(!b.active||b.owner<2)continue;const bx=b.x-p.x,by=b.y-p.y;const approaching=(b.dir===0&&by>0)||(b.dir===2&&by<0)||(b.dir===1&&bx>0)||(b.dir===3&&bx<0);if(approaching&&(b.dir%2===0?Math.abs(b.x-x)<10&&Math.abs(by)<60:Math.abs(b.y-y)<10&&Math.abs(bx)<60))value-=120;}
  if(value>best){best=value;dir=d;}
 }
 keys[aiDirs[dir]]=true;
 // Never shoot toward the eagle; rapid-fire requires release edges.
 const eagleAhead=(dir===2&&p.y<EAGLE.y&&Math.abs(p.x-EAGLE.x)<12)||(dir===3&&p.x<EAGLE.x&&Math.abs(p.y-EAGLE.y)<12)||(dir===1&&p.x>EAGLE.x&&Math.abs(p.y-EAGLE.y)<12);
 keys.Space=!eagleAhead&&aiTicks%8<4;aiReason=eagleAhead?'保护基地：停止射击':'拦截低位敌人 / 躲避子弹';
}
const originalUpdate=update;update=function(){if(aiEnabled)aiPolicy();originalUpdate();};
window.tankAI={start:aiStart,observe:aiObserve,step(n=1){for(let i=0;i<n;i++)update();render();return aiObserve();},stop(){aiEnabled=false;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;}};
const panel=document.createElement('div');panel.style='position:fixed;top:8px;left:8px;background:#172033;color:white;padding:12px;z-index:1000;font:14px monospace;max-width:260px';panel.innerHTML='<b>启发式 AI · 浏览器复刻版</b><br><button id="ai-on">AI 从第一关开始</button> <button id="ai-off">手动</button><pre id="ai-state"></pre>';document.body.append(panel);document.getElementById('ai-on').onclick=()=>aiStart();document.getElementById('ai-off').onclick=()=>tankAI.stop();setInterval(()=>document.getElementById('ai-state').textContent=JSON.stringify(aiObserve(),null,2),500);
