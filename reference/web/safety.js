function disciplinedFire(){return plannerConfig.fireDiscipline&&(!plannerConfig.fireDisciplineFrom||stageIdx+1>=plannerConfig.fireDisciplineFrom);}
// Local physics prediction only: never writes to live entities, bullets, or map.
function bulletSolid(x,y){const c=Math.floor((x-16)/16),r=Math.floor((y-16)/16);if(c<0||c>12||r<0||r>12)return true;const tile=grid[r][c];return tile<=9&&!passable8(x,y);}
function projectedPlayer(p,move){const q={...p},f=frameCount+1,c=Math.floor((q.x-24)/16),r=Math.floor((q.y-24)/16),ice=grid[r]?.[c]===T.ICE;if((f&3)!==2&&!p.stunTimer&&(ice||move>=0)){if(!ice&&move!==q.dir){if(move!==(q.dir^2)){q.x=(q.x+4)&0xF8;q.y=(q.y+4)&0xF8;}q.dir=move;}if(canMove(q,q.dir)){q.x+=DX[q.dir];q.y+=DY[q.dir];}}return q;}
function shotIntent(q,move){
 const d=q.dir,speed=q.starLevel>=32?4:2;
 for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim)continue;const along=(e.x-q.x)*DX[d]+(e.y-q.y)*DY[d],cross=Math.abs((e.x-q.x)*DY[d]-(e.y-q.y)*DX[d]);if(along>0&&along<(plannerConfig.shotRange||160)&&cross<9)return true;}
 for(const b of bullets){if(!b.active||b.owner<2||b.dir!==(d^2))continue;const along=(b.x-q.x)*DX[d]+(b.y-q.y)*DY[d],cross=Math.abs((b.x-q.x)*DY[d]-(b.y-q.y)*DX[d]);if(along>8&&along<96&&cross<6)return true;}
 if(move>=0&&!canMove(q,move))for(let t=8;t<=24;t+=4){const x=q.x+DX[d]*t,y=q.y+DY[d]*t,c=Math.floor((x-16)/16),r=Math.floor((y-16)/16);if(r<0||r>12||c<0||c>12)continue;if(r>=11&&c>=5&&c<=7)continue;if(grid[r][c]<=4)return true;}
 return false;
}
function predictedActionRisk(p,d,horizon,maneuver=null){
 const q={...p},bs=bullets.filter(b=>b.active).map(b=>({...b}));let risk=0,closest=999,wasFire=fireHeld[0],dead=false;
 if(plannerConfig.baseSafety&&bs.some(b=>b.owner>=2&&b.dir===2&&Math.abs(b.x-120)<12&&b.y>120))horizon=Math.max(horizon,48);
 for(let t=1;t<=horizon;t++){
  const f=frameCount+t;
  const action=maneuver&&t>maneuver.n?(q.dir!==maneuver.face?maneuver.face:-1):d;
  if(!dead&&(f&3)!==2){
   const col=Math.floor((q.x-8-16)/16),row=Math.floor((q.y-8-16)/16),ice=grid[row]?.[col]===T.ICE;
   if(ice||action>=0){if(!ice&&action!==q.dir){if(action!==(q.dir^2)){q.x=(q.x+4)&0xF8;q.y=(q.y+4)&0xF8;}q.dir=action;}if(canMove(q,q.dir)){q.x+=DX[q.dir];q.y+=DY[q.dir];}}
  }
  for(const b of bs){if(!b.active)continue;const speed=b.powered?4:2;b.x+=DX[b.dir]*speed;b.y+=DY[b.dir]*speed;if(b.x<12||b.x>228||b.y<12||b.y>228)b.active=false;else if(b.powered||((b.slot^f)&1)){if(plannerConfig.baseSafety&&Math.abs(b.x-120)<12&&Math.abs(b.y-216)<8){risk+=plannerConfig.baseSafety;b.active=false;continue;}const hor=b.dir&1;if(bulletSolid(b.x,b.y)||bulletSolid(b.x-(hor?0:1),b.y-(hor?1:0)))b.active=false;}}
  for(const a of bs){if(!a.active||a.owner>=2||![0,8].includes(a.slot))continue;for(const b of bs)if(b.active&&b.owner>=2&&Math.abs(a.x-b.x)<6&&Math.abs(a.y-b.y)<6){a.active=b.active=false;break;}}
  const shieldFrames=q.shieldTimer*64-(frameCount&63);
  for(const b of bs){if(!b.active||b.owner<2||dead)continue;const distance=Math.max(Math.abs(b.x-q.x),Math.abs(b.y-q.y));closest=Math.min(closest,distance);if(distance<10){if(t<shieldFrames){b.active=false;}else {risk+=100000+(horizon-t)*5000;if(!plannerConfig.baseSafety)return {risk,x:q.x,y:q.y,closest};dead=true;b.active=false;}}}
  // Account for the actual firing edge and the available bullet slot.
  const press=safeShot(q.x,q.y,q.dir)&&(disciplinedFire()?shotIntent(q,action)&&!wasFire:(aiTicks+t-1)%plannerConfig.fire<plannerConfig.fire/2);
  if(!dead&&press&&!wasFire){let slot=!bs.some(b=>b.active&&b.slot===0)?0:q.starLevel>=64&&!bs.some(b=>b.active&&b.slot===9)?9:-1;if(slot>=0)bs.push({slot,owner:0,dir:q.dir,x:q.x+DX[q.dir]*8,y:q.y+DY[q.dir]*8,powered:q.starLevel>=32,active:true});}wasFire=press;
  // A tank can start firing this frame. Penalize close exposed firing lanes.
  if(t>=shieldFrames&&freezeTimer===0&&plannerConfig.enemyRisk){for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim)continue;const ahead=(q.x-e.x)*DX[e.dir]+(q.y-e.y)*DY[e.dir],cross=Math.abs((q.x-e.x)*DY[e.dir]-(q.y-e.y)*DX[e.dir]);if(ahead>0&&ahead<plannerConfig.enemyRange&&cross<12&&!bullets[e.slot]?.active){risk+=plannerConfig.enemyRisk*(1-ahead/plannerConfig.enemyRange)*(1-cross/14)/horizon;}}}
  if(plannerConfig.baseCoverPenalty)for(const e of entities.slice(2)){if(!e.alive||e.spawnAnim||e.dir!==2||Math.abs(e.x-120)>=12||e.y<(plannerConfig.baseCoverY||128))continue;const covers=!dead&&q.y>e.y&&q.y<208&&Math.abs(q.x-e.x)<9;if(!covers)risk+=plannerConfig.baseCoverPenalty/horizon;}
 }
 return {risk,x:q.x,y:q.y,closest};
}
function safetyControl(nominal){
 const p=entities[0],h=plannerConfig.horizon||20;
 if(!p?.alive||p.spawnAnim||gamePhase!=='play')return;
 let best=null;
 const choices=[nominal,-1,0,1,2,3].filter((v,i,a)=>a.indexOf(v)===i).map(d=>({d}));
 if(plannerConfig.maneuvers&&(!plannerConfig.maneuversFrom||stageIdx+1>=plannerConfig.maneuversFrom)){const threats=bullets.filter(b=>b.active&&b.owner>=2&&Math.abs(b.x-p.x)+Math.abs(b.y-p.y)<96);for(const b of threats.slice(0,2)){for(const d of b.dir%2===0?[1,3]:[0,2])for(const n of [4,8,12])choices.push({d,n,face:b.dir^2});}}
 for(const choice of choices){const d=choice.d;
  const r=predictedActionRisk(p,d,h,choice.n?choice:null);
  const deviation=d===nominal?0:d===-1?2:4;
  let progress=0;if(plannerAction)progress=(Math.abs(r.x-plannerAction.x)+Math.abs(r.y-plannerAction.y))*.08;
  const value=r.risk+deviation+progress;
  if(!best||value<best.value)best={d,value,...r};
 }
 if(best.d!==nominal){aiDirs.forEach(k=>keys[k]=false);if(best.d>=0)keys[aiDirs[best.d]]=true;aiReason='预测弹道，选择安全动作';plannerAction=null;}
 const actualDir=best.d>=0?best.d:p.dir;
 keys.Space=safeShot(p.x,p.y,actualDir)&&aiTicks%plannerConfig.fire<plannerConfig.fire/2;
}
