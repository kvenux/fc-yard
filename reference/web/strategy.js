// Receding-horizon planner; only writes controller keys.
// Frozen after two rounds of successive elimination; see experiments/winner-refinement.json.
const plannerDefault={mode:'planner',guard:0,range:24,threat:3,dodge:300,power:180,dig:3,replan:4,fire:4,evade:false,safety:true,horizon:16,enemyRisk:300,enemyRange:56,safeFacing:true};
let plannerRootConfig={...plannerDefault},plannerConfigStage=-1;
let plannerConfig={...plannerDefault},plannerAction=null,plannerLast=0,plannerLastScore=0,plannerProgressTick=0,plannerStage=-1;
function plannerReset(config){plannerRootConfig={...plannerDefault,...config};plannerConfig={...plannerRootConfig};plannerConfigStage=-1;plannerAction=null;plannerLast=-100;plannerLastScore=0;plannerProgressTick=0;plannerStage=-1;if(typeof resetMPC==='function')resetMPC();}
function safeShot(x,y,d){
 const towardBase=(d===2&&y<216&&Math.abs(x-120)<17)||(d===3&&x<120&&Math.abs(y-216)<17)||(d===1&&x>120&&Math.abs(y-216)<17);
 if(!towardBase)return true;
 if(plannerConfig.targetedBaseFire){const speed=entities[0]?.starLevel>=32?4:2;for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim)continue;const along=(e.x-x)*DX[d]+(e.y-y)*DY[d],cross=Math.abs((e.x-x)*DY[d]-(e.y-y)*DX[d]),flight=Math.max(0,(along-16)/(speed-.5));if(along>0&&along<plannerConfig.targetedBaseFire&&cross+flight*.5<(plannerConfig.targetMargin||8)&&along<Math.abs(120-x)+Math.abs(216-y)-8)return true;}}
 return false;
}
function terrainCost(x,y){
 if(x<24||x>216||y<24||y>216||Math.abs(x-120)<24&&y>184)return Infinity;
 if(plannerConfig.avoidIce&&grid[Math.floor((y-24)/16)]?.[Math.floor((x-24)/16)]===T.ICE)return Infinity;
 let cost=1;
 for(const [ox,oy] of [[-8,-8],[7,-8],[-8,7],[7,7]]){
  if(passable8(x+ox,y+oy))continue;
  const c=Math.floor((x+ox-16)/16),r=Math.floor((y+oy-16)/16);
  if(c<0||c>=13||r<0||r>=13||grid[r][c]>4)return Infinity;
  // Preserve the protective wall; no digging into base enclosure.
  if(r>=11&&c>=5&&c<=7)return Infinity;
  cost=Math.max(cost,plannerConfig.dig);
 }
 return cost;
}
function shotLine(x,y,tx,ty){
 const d=Math.abs(tx-x)<8?(ty<y?0:2):Math.abs(ty-y)<8?(tx<x?1:3):-1;
 if(d<0||!safeShot(x,y,d))return null;
 let obstruction=0;
 for(let t=8;t<Math.abs(tx-x)+Math.abs(ty-y)-8;t+=8){
  const xx=x+DX[d]*t,yy=y+DY[d]*t,c=Math.floor((xx-16)/16),r=Math.floor((yy-16)/16);
  if(r<0||r>=13||c<0||c>=13)return null;
  if(grid[r][c]>=5&&grid[r][c]<=9)return null;
  if(!passable8(xx,yy)&&grid[r][c]<=4)obstruction++;
 }
 return {d,obstruction};
}
function dangerAt(x,y){let risk=0;for(const b of bullets){if(!b.active||b.owner<2)continue;const along=(x-b.x)*DX[b.dir]+(y-b.y)*DY[b.dir],cross=Math.abs((x-b.x)*DY[b.dir]-(y-b.y)*DX[b.dir]);if(along>=-8&&along<80&&cross<12)risk+=plannerConfig.dodge*(1-along/100)*(1-cross/16);}return risk;}
function choosePlan(p){
 const n=25,total=n*n,dist=new Float64Array(total).fill(Infinity),first=new Int8Array(total).fill(-1),used=new Uint8Array(total);
 const sx=Math.max(0,Math.min(24,Math.round((p.x-24)/8))),sy=Math.max(0,Math.min(24,Math.round((p.y-24)/8))),start=sy*n+sx;
 dist[start]=0;let best={value:-Infinity,x:24+sx*8,y:24+sy*8,dir:0,first:-1};
 const targets=entities.slice(2).filter(e=>e.alive&&!e.spawnAnim);
 if(plannerConfig.interceptBase)for(const b of bullets){if(b.active&&b.owner>=2&&b.dir===2&&Math.abs(b.x-120)<12&&b.y>80&&b.y<200)targets.push({...b,projectile:true});}
 for(let count=0;count<total;count++){
  let id=-1,dd=Infinity;for(let i=0;i<total;i++)if(!used[i]&&dist[i]<dd){dd=dist[i];id=i;}if(id<0||dd>65)break;used[id]=1;
  const x=24+(id%n)*8,y=24+Math.floor(id/n)*8;
  let value=-dd*3-plannerConfig.guard*Math.abs(y-168)*.15-dangerAt(x,y),aim=0;
  for(const e of targets){const line=shotLine(x,y,e.x,e.y);if(!line)continue;const range=Math.abs(e.x-x)+Math.abs(e.y-y);
   let reward=130+plannerConfig.threat*(e.y-100)*.35-Math.abs(range-plannerConfig.range)*.25-line.obstruction*9;
   if(plannerConfig.belowBonus&&e.y>80&&line.d===0)reward+=plannerConfig.belowBonus;
   if(e.projectile){if(line.d!==0||y<=e.y)continue;reward+=plannerConfig.interceptBase;}
   if(reward-dd*3-plannerConfig.guard*Math.abs(y-168)*.15-dangerAt(x,y)>value){value=reward-dd*3-plannerConfig.guard*Math.abs(y-168)*.15-dangerAt(x,y);aim=line.d;}
  }
  if(powerUp){const pd=Math.abs(x-powerUp.x)+Math.abs(y-powerUp.y);const reward=plannerConfig.power-pd*2-dd*3-dangerAt(x,y);if(reward>value){value=reward;aim=0;}}
  const fy=plannerConfig.fortressY||184;
  if(plannerConfig.fortressFrom&&stageIdx+1>=plannerConfig.fortressFrom&&terrainCost(plannerConfig.fortressX||120,fy)<Infinity&&(!plannerConfig.fortressTimeout||aiTicks-plannerProgressTick<plannerConfig.fortressTimeout)){
   const deepest=targets.filter(e=>!e.projectile&&e.y>96).sort((a,b)=>b.y-a.y)[0];
   const fx=plannerConfig.fortressTrack&&deepest?Math.max(72,Math.min(168,Math.round(deepest.x/8)*8)):(plannerConfig.fortressX||120);
   value=300-dd*3-(Math.abs(x-fx)+Math.abs(y-fy))*(plannerConfig.fortressWeight||8)-dangerAt(x,y);
   let priority=-Infinity;aim=0;for(const e of targets){const line=shotLine(x,y,e.x,e.y);if(!line)continue;const v=e.y*2-Math.abs(e.x-x)-Math.abs(e.y-y)-line.obstruction*8;if(v>priority){priority=v;aim=line.d;}}
  }
  if(value>best.value)best={value,x,y,dir:aim,first:first[id]};
  for(let d=0;d<4;d++){const nx=x+DX[d]*8,ny=y+DY[d]*8;if(nx<24||nx>216||ny<24||ny>216)continue;const ni=(ny-24)/8*n+(nx-24)/8,tc=terrainCost(nx,ny);const nd=dd+tc+dangerAt(nx,ny)/180;if(nd<dist[ni]){dist[ni]=nd;first[ni]=id===start?d:first[id];}}
 }
 return best;
}
function plannerPolicy(){
 aiTicks++;aiDirs.forEach(k=>keys[k]=false);keys.Space=false;if(gamePhase!=='play')return;if(plannerConfigStage!==stageIdx){const had=plannerRootConfig.stagePolicies?.[plannerConfigStage+1],next=plannerRootConfig.stagePolicies?.[stageIdx+1];plannerConfig={...plannerRootConfig,...(next||{})};plannerConfigStage=stageIdx;if(had||next)plannerAction=null;}const p=entities[0];if(!p.alive||p.spawnAnim)return;
 if(p1Score!==plannerLastScore||stageIdx!==plannerStage){plannerLastScore=p1Score;plannerProgressTick=aiTicks;plannerStage=stageIdx;}
 if(!plannerAction||aiTicks-plannerLast>=plannerConfig.replan){plannerAction=choosePlan(p);plannerLast=aiTicks;}
 const plan=plannerAction;let d=plan.first;
 if(Math.abs(p.x-plan.x)<2&&Math.abs(p.y-plan.y)<2||d<0){d=plan.dir;if(p.dir!==d)keys[aiDirs[d]]=true;aiReason='对齐射线，拦截敌人';}
 else {keys[aiDirs[d]]=true;aiReason=canMove(p,d)?'规划路径，移动拦截':'射击清除挡路砖墙';}
 // Face an imminent hostile bullet and counter-shoot when already aligned.
 const incoming=bullets.find(b=>b.active&&b.owner>=2&&((b.dir%2===0&&Math.abs(b.x-p.x)<6&&(p.y-b.y)*DY[b.dir]>0&&Math.abs(p.y-b.y)<48)||(b.dir%2===1&&Math.abs(b.y-p.y)<6&&(p.x-b.x)*DX[b.dir]>0&&Math.abs(p.x-b.x)<48)));
 if(incoming&&p.shieldTimer===0){
  if(plannerConfig.evade&&bullets[0].active){
   const perpendicular=incoming.dir%2===0?[1,3]:[0,2];let nd=-1,risk=Infinity;
   for(const side of perpendicular){const xx=p.x+DX[side]*8,yy=p.y+DY[side]*8;if(canMove(p,side)&&terrainCost(xx,yy)<Infinity){const dr=dangerAt(xx,yy);if(dr<risk){risk=dr;nd=side;}}}
   if(nd>=0){aiDirs.forEach(k=>keys[k]=false);d=nd;keys[aiDirs[d]]=true;plannerAction=null;aiReason='子弹槽占用，侧移躲弹';}
  }else {const nd=incoming.dir^2;if(safeShot(p.x,p.y,nd)){aiDirs.forEach(k=>keys[k]=false);d=nd;if(p.dir!==d)keys[aiDirs[d]]=true;aiReason='迎击近距离子弹';}}
 }
 keys.Space=safeShot(p.x,p.y,d)&&aiTicks%plannerConfig.fire<plannerConfig.fire/2;
 if(plannerConfig.safety)safetyControl(aiDirs.findIndex(k=>keys[k]));
 if(plannerConfig.safeFacing&&keys.Space){const q={...p},move=aiDirs.findIndex(k=>keys[k]),f=frameCount+1;const c=Math.floor((q.x-24)/16),r=Math.floor((q.y-24)/16),ice=grid[r]?.[c]===T.ICE;if((f&3)!==2&&!p.stunTimer){if(ice||move>=0){if(!ice&&move!==q.dir){if(move!==(q.dir^2)){q.x=(q.x+4)&0xF8;q.y=(q.y+4)&0xF8;}q.dir=move;}if(canMove(q,q.dir)){q.x+=DX[q.dir];q.y+=DY[q.dir];}}}keys.Space=safeShot(q.x,q.y,q.dir);}
 if(disciplinedFire()){const move=aiDirs.findIndex(k=>keys[k]),q=projectedPlayer(p,move);keys.Space=!fireHeld[0]&&safeShot(q.x,q.y,q.dir)&&shotIntent(q,move);}
 if(plannerConfig.mpc)mpcControl();
}
