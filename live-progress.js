// Escape unproductive camping without changing the world or bypassing safety.
(()=>{
  const choose=choosePlan;
  choosePlan=function(p){
    const limit=plannerConfig.stallAfter||0;
    if(!limit||aiTicks-plannerProgressTick<limit||!entities.slice(2).some(e=>e.alive&&!e.spawnAnim))return choose(p);
    const previous=plannerConfig;
    const phase=Math.floor((aiTicks-plannerProgressTick-limit)/240)%3;
    plannerConfig={...previous,fortressFrom:0,range:[48,80,24][phase],power:Math.min(previous.power||180,100)};
    try{return choose(p);}finally{plannerConfig=previous;}
  };
})();
