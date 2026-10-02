// Presentation adapter; game and frozen policy sources remain untouched.
(()=>{
  soundEnabled=false;
  const policyTick=plannerPolicy;
  // Speculative branches must never emit audio; only the committed update can.
  plannerPolicy=function(){const enabled=soundEnabled;soundEnabled=false;liveFire.begin();try{policyTick();liveFire.commit();}finally{soundEnabled=enabled;}};
  let ticks=0,policy=null;
  function snapshot(){
    const o=aiObserve(),p=entities[0];
    return {...o,ticks,keys:aiDirs.map(k=>!!keys[k]),fire:!!keys.Space,fireControl:liveFire.status,
      goal:plannerAction&&{x:plannerAction.x,y:plannerAction.y},
      progress:{quietFrames:Math.max(0,aiTicks-plannerProgressTick),replanning:!!plannerConfig.stallAfter&&aiTicks-plannerProgressTick>=plannerConfig.stallAfter},
      threats:entities.slice(2).filter(e=>e.alive&&!e.spawnAnim).map(e=>({x:e.x,y:e.y})),
      spawning:!!p?.spawnAnim,ready:!!chrOff,terminal:!eagleAlive||p1Lives<0||gamePhase==='victory'};
  }
  window.liveEngine={
    canvas, snapshot,
    async load(){const response=await fetch('/live-policy.json');if(!response.ok)throw Error('策略文件读取失败');policy=await response.json();const start=performance.now();while(!chrOff){if(performance.now()-start>15000)throw Error('游戏图像读取超时');await new Promise(r=>setTimeout(r,50));}},
    start(seed,stage=1,config=policy){stopAllSounds();liveFire.reset();Object.keys(keys).forEach(k=>delete keys[k]);frameCount=0;fireHeld=[false,false];customMap=null;aiStart(seed,config);if(stage!==1)initLevel(stage-1);ticks=0;render();return snapshot();},
    save(){return {state:checkpoint.save(),fire:liveFire.save(),ticks};},
    restore(saved,config=policy){checkpoint.load(saved.state,config);liveFire.load(saved.fire);ticks=saved.ticks;return snapshot();},
    step(){update();ticks++;return snapshot();},
    render(){render();},
    sound(enabled){if(enabled)initAudio();soundEnabled=enabled&&audioInited;if(!soundEnabled)stopAllSounds();if(audioCtx?.state==='suspended'&&soundEnabled)audioCtx.resume();return soundEnabled;},
    quiet(){stopAllSounds();}
  };
})();
