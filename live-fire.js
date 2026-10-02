// Live-only fire discipline. Rates are per simulation second (60 frames).
// Frozen training policy and the game's firing rules remain unchanged.
(()=>{
  const gap=12;
  let lastPress=-Infinity,branchLast=-Infinity,branchFrame=Infinity,reason='',lastStage=-1,branchStage=-1;
  function intent(q,move){
    const d=q.dir,range=plannerConfig.shotRange||160;
    let obstacle=Infinity,brick=false;
    // Stop at the first bullet-blocking pixel; water does not block bullets.
    for(let t=8;t<=range;t+=2){
      const x=q.x+DX[d]*t,y=q.y+DY[d]*t,c=Math.floor((x-16)/16),r=Math.floor((y-16)/16);
      if(c<0||c>12||r<0||r>12){obstacle=t;break;}
      if(bulletSolid(x,y)){obstacle=t;brick=grid[r][c]<=4;break;}
    }
    for(const e of entities.slice(2)){
      if(!e.alive||e.spawnAnim)continue;
      const along=(e.x-q.x)*DX[d]+(e.y-q.y)*DY[d],cross=Math.abs((e.x-q.x)*DY[d]-(e.y-q.y)*DX[d]);
      if(along>0&&along<range&&cross<9){
        if(along-8<obstacle)return '拦截敌人';
        const c=Math.floor((q.x+DX[d]*obstacle-16)/16),r=Math.floor((q.y+DY[d]*obstacle-16)/16);
        if(brick&&!(r>=11&&c>=5&&c<=7))return '清除敌人前砖墙';
      }
    }
    for(const b of bullets){
      if(!b.active||b.owner<2||b.dir!==(d^2))continue;
      const along=(b.x-q.x)*DX[d]+(b.y-q.y)*DY[d],cross=Math.abs((b.x-q.x)*DY[d]-(b.y-q.y)*DX[d]);
      if(along>8&&along<96&&cross<6&&along<obstacle)return '迎击子弹';
    }
    if(move===d&&move>=0&&plannerAction&&brick&&obstacle<=24&&!canMove(q,move)&&Math.abs(q.x-plannerAction.x)+Math.abs(q.y-plannerAction.y)>4){
      const c=Math.floor((q.x+DX[d]*obstacle-16)/16),r=Math.floor((q.y+DY[d]*obstacle-16)/16);
      if(!(r>=11&&c>=5&&c<=7))return '清除路径砖墙';
    }
    return '';
  }
  function allowed(last){
    const p=entities[0];
    if(!keys.Space||gamePhase!=='play'||!p?.alive||p.spawnAnim||fireHeld[0]||frameCount+1-last<gap)return '';
    if(bullets[0].active&&(p.starLevel<64||bullets[9].active))return '';
    const move=aiDirs.findIndex(k=>keys[k]),q=projectedPlayer(p,move);
    return safeShot(q.x,q.y,q.dir)?intent(q,move):'';
  }
  function simulatedGate(){
    // Each MPC branch restores frameCount to the root. Reset its local cooldown
    // as well, so rejected branches cannot consume the real trigger budget.
    if(frameCount<=branchFrame)branchLast=stageIdx===lastStage?lastPress:-Infinity;
    else if(stageIdx!==branchStage)branchLast=-Infinity;
    branchStage=stageIdx;
    branchFrame=frameCount;
    keys.Space=!!allowed(branchLast);
    if(keys.Space)branchLast=frameCount+1;
  }
  const set=mpcSetInput,fast=mpcFastKeys;
  mpcSetInput=function(...args){set(...args);simulatedGate();};
  mpcFastKeys=function(...args){fast(...args);simulatedGate();};
  window.liveFire={
    save(){return {lastPress:Number.isFinite(lastPress)?lastPress:null,lastStage,reason};},
    load(s){lastPress=s?.lastPress??-Infinity;lastStage=s?.lastStage??stageIdx;reason=s?.reason||'';branchFrame=Infinity;branchLast=lastPress;},
    reset(){lastPress=-Infinity;branchLast=-Infinity;branchFrame=Infinity;lastStage=-1;reason='';},
    begin(){if(stageIdx!==lastStage){lastPress=-Infinity;lastStage=stageIdx;}branchFrame=Infinity;},
    commit(){reason=allowed(lastPress);keys.Space=!!reason;if(keys.Space)lastPress=frameCount+1;},
    get status(){return {reason,lastPress:Number.isFinite(lastPress)?lastPress:null,minIntervalFrames:gap,maxPressesPerSecond:5};}
  };
})();
