// Exact-model tactical search. Only the chosen controller input is committed.
// Branch state includes RNG, so this is privileged model-based planning.
let mpcDecision=null,mpcLast=-1000,mpcStage=-1;
function resetMPC(){mpcDecision=null;mpcLast=-1000;mpcStage=-1;}
function mpcGoal(x,y){
 x=Math.max(24,Math.min(216,Math.round(x/8)*8));y=Math.max(24,Math.min(216,Math.round(y/8)*8));
 const dist=new Float64Array(625).fill(Infinity),cost=new Float64Array(625),buckets=Array.from({length:4096},()=>[]);
 for(let i=0;i<625;i++)cost[i]=Math.ceil(terrainCost(24+(i%25)*8,24+Math.floor(i/25)*8));
 const start=(y-24)/8*25+(x-24)/8;if(!Number.isFinite(cost[start]))return null;dist[start]=0;buckets[0].push(start);
 for(let k=0;k<buckets.length;k++)while(buckets[k].length){const i=buckets[k].pop();if(dist[i]!==k)continue;const cx=i%25,cy=Math.floor(i/25);for(let d=0;d<4;d++){const xx=cx+DX[d],yy=cy+DY[d];if(xx<0||xx>24||yy<0||yy>24)continue;const ni=yy*25+xx,nd=k+cost[i];if(Number.isFinite(cost[ni])&&nd<dist[ni]&&nd<4096){dist[ni]=nd;buckets[nd].push(ni);}}}
 return {x,y,nav:dist,cost};
}
function mpcNavDirection(p,goal){
 const sx=Math.max(0,Math.min(24,Math.round((p.x-24)/8))),sy=Math.max(0,Math.min(24,Math.round((p.y-24)/8)));let best=Infinity,direction=-1;
 for(let d=0;d<4;d++){const x=sx+DX[d],y=sy+DY[d];if(x<0||x>24||y<0||y>24)continue;const i=y*25+x,v=goal.nav[i]+goal.cost[i];if(v<best){best=v;direction=d;}}
 return direction;
}
function mpcFastKeys(goal){
 const p=entities[0];aiDirs.forEach(k=>keys[k]=false);keys.Space=false;if(!p?.alive||p.spawnAnim||gamePhase!=='play')return;
 if(goal.nav){let d=mpcNavDirection(p,goal);if(Math.abs(p.x-goal.x)<5&&Math.abs(p.y-goal.y)<5){let priority=-1e9,aim=p.dir;for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim)continue;const line=shotLine(p.x,p.y,e.x,e.y);if(line){const value=e.y*2-Math.abs(e.x-p.x)-Math.abs(e.y-p.y)-line.obstruction*8;if(value>priority){priority=value;aim=line.d;}}}d=aim===p.dir?-1:aim;}if(d>=0)keys[aiDirs[d]]=true;const q=projectedPlayer(p,d);keys.Space=!fireHeld[0]&&safeShot(q.x,q.y,q.dir)&&(shotIntent(q,d)||d>=0&&!canMove(q,d));return;}
 let d=-1,best=-1e9;
 for(let dir=0;dir<4;dir++){const q=projectedPlayer(p,dir);let v=-Math.abs(q.x-goal.x)-Math.abs(q.y-goal.y);if(!canMove(p,dir))v-=8;for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim)continue;const along=(e.x-p.x)*DX[dir]+(e.y-p.y)*DY[dir],cross=Math.abs((e.x-p.x)*DY[dir]-(e.y-p.y)*DX[dir]);if(along>0&&along<80&&cross<8)v+=45;}if(v>best){best=v;d=dir;}}
 const e=entities.slice(2).find(e=>e.alive&&!e.spawnAnim&&shotLine(p.x,p.y,e.x,e.y)?.d===p.dir);
 if(e&&Math.abs(e.x-p.x)+Math.abs(e.y-p.y)<80)d=-1;
 if(d>=0)keys[aiDirs[d]]=true;const q=projectedPlayer(p,d);keys.Space=!fireHeld[0]&&safeShot(q.x,q.y,q.dir)&&(shotIntent(q,d)||!canMove(q,q.dir));
}
function mpcSetInput(d,shoot){aiDirs.forEach(k=>keys[k]=false);let q=projectedPlayer(entities[0],d);if(plannerConfig.avoidIce&&grid[Math.floor((q.y-24)/16)]?.[Math.floor((q.x-24)/16)]===T.ICE){d=-1;q=projectedPlayer(entities[0],d);}if(d>=0)keys[aiDirs[d]]=true;keys.Space=shoot&&!fireHeld[0]&&safeShot(q.x,q.y,q.dir)&&(!plannerConfig.mpcGoals||shotIntent(q,d)||d>=0&&!canMove(q,d));}
function mpcControl(){
 const p=entities[0];if(!p?.alive||p.spawnAnim||gamePhase!=='play')return;
 const every=plannerConfig.mpcEvery||8;
 if(mpcStage!==stageIdx||aiTicks<mpcLast){mpcDecision=null;mpcLast=-1000;mpcStage=stageIdx;}
 if(!mpcDecision||aiTicks-mpcLast>=every){
  const current=checkpoint.save(),before={score:p1Score,lives:p1Lives,stage:stageIdx,x:p.x,y:p.y};let goal=plannerAction?{x:plannerAction.x,y:plannerAction.y}:{x:120,y:176};
  if(plannerConfig.mpcNav)goal=mpcGoal(goal.x,goal.y)||goal;
  const nominal=aiDirs.findIndex(k=>keys[k]);let choices=[];for(const d of [nominal,-1,0,1,2,3].filter((x,i,a)=>a.indexOf(x)===i))for(const n of [4,12])choices.push({d,n,shoot:true});choices.push({d:nominal,n:8,shoot:false});
  if(plannerConfig.mpcGoals){const goals=[mpcGoal(goal.x,goal.y),mpcGoal(120,184),mpcGoal(88,184),mpcGoal(152,184)];if(powerUp)goals.push(mpcGoal(powerUp.x,powerUp.y));choices=[];for(const g of goals.filter(Boolean)){const d=mpcNavDirection(p,g);for(const initial of [d,-1,nominal].filter((x,i,a)=>a.indexOf(x)===i))choices.push({d:initial,n:4,shoot:true,goal:g});}}
  let best=null;const horizon=plannerConfig.mpcHorizon||64;
  const restore=()=>{checkpointWrite(structuredClone(current.values));Object.keys(keys).forEach(k=>delete keys[k]);Object.assign(keys,current.keys);};
  for(const choice of choices){restore();let lost=false,dead=false;
   for(let t=0;t<horizon;t++){if(gamePhase==='play'&&entities[0].alive&&!entities[0].spawnAnim){if(t<choice.n)mpcSetInput(choice.d,choice.shoot);else mpcFastKeys(choice.goal||goal);}else{aiDirs.forEach(k=>keys[k]=false);keys.Space=false;}aiTicks++;originalUpdate();if(!eagleAlive){lost=true;break;}if(p1Lives<0){dead=true;break;}if(gamePhase==='victory')break;}
   const q=entities[0];let value=(p1Score-before.score)*12+(stageIdx-before.stage)*50000+(gamePhase==='clear'?30000:0)+(p1Lives-before.lives)*15000;
   if(lost)value-=1e8;if(dead)value-=2e7;
   const g=choice.goal||goal;value-=(Math.abs(q.x-g.x)+Math.abs(q.y-g.y))*1.5;
   if(plannerConfig.mpcNav&&g.nav){const ix=Math.max(0,Math.min(24,Math.round((q.x-24)/8))),iy=Math.max(0,Math.min(24,Math.round((q.y-24)/8)));value-=Math.min(200,g.nav[iy*25+ix])*(plannerConfig.navWeight||16);}
   for(const e of entities.slice(2))if(e.alive)value-=Math.max(0,e.y-120)*(Math.abs(e.x-120)<32?8:2);
   if(choice.d===nominal)value+=2;
   if(!best||value>best.value)best={...choice,value};
  }
  restore();mpcDecision=best;mpcLast=aiTicks;
 }
 mpcSetInput(mpcDecision.d,mpcDecision.shoot);aiReason='游戏模型前瞻，选择存活与基地安全的动作';
}
