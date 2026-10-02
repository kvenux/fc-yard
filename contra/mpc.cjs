'use strict';
function read(engine) {
  const m = engine.nes.cpu.mem;
  const enemies = [];
  for (let i = 0; i < 16; i++) if (m[0x4b8 + i]) enemies.push({ slot: i, type: m[0x528+i], routine: m[0x4b8+i], hp: m[0x578+i], realHP:m[0x5b8+i], x:m[0x33e+i], y:m[0x324+i], flags:m[0x598+i] });
  return { stage:m[0x30], progress:m[0x64]*256+m[0x65], x:m[0x334],y:m[0x31a],lives:m[0x32],dead:m[0x90]===2,over:m[0x38]===1,
    state:m[0x90], routine:m[0x2c], location:m[0x40], victory:m[0x18]===6, status:m[0x18], score:m[0x7e2]+256*m[0x7e3], weapon:m[0xaa]&15,
    jump:m[0xa0]&1, water:m[0xb2], barrier:m[0x37], boss:m[0x3b], enemies };
}
function actionMask(action, f) {
  const direction=action.moveFrames!==undefined&&f>=action.moveFrames?(action.afterDirection||0):action.direction;
  return direction | (action.continuousFire || f % 8 < 4 ? 2 : 0) | (action.jump && (f+(action.phase||0)) % 32 < (action.hold||1) ? 1 : 0);
}
class MPC {
  constructor(config={}) { this.config={horizon:80,commit:16,...config}; this.reason=''; this.lastChoices=[]; }
  choose(engine) {
    const start=read(engine),indoor=[1,3].includes(start.stage),vertical=start.stage===2;
    const horizon=indoor&&start.location!==128?(this.config.indoorHorizon||160):this.config.horizon,commit=indoor&&start.location!==128?32:this.config.commit;
    if (start.status!==5 || ![4,8].includes(start.routine) || start.state!==1) return Array(commit).fill(0);
    const cores=start.enemies.filter(e=>e.type===0x14&&e.hp>0);
    const alignedClosed=cores.length>0&&cores.every(e=>(e.flags&128)!==0)&&Math.abs(start.x-Math.max(16,Math.min(240,128+(cores[0].x-128)*2)))<=3;
    if(indoor&&start.location===1&&(alignedClosed||start.barrier===128)){
      const action={name:start.barrier===128?'advance-cleared-room':'wait-core-open',direction:start.barrier===128?16:32,jump:false,continuousFire:start.weapon===4};
      const saved=engine.save();let safe=true;
      for(let f=0;f<80;f++){engine.step(actionMask(action,f));const o=read(engine);if(o.dead||o.over||o.lives<start.lives){safe=false;break;}}
      engine.restore(saved);
      if(safe){this.reason=action.name;this.lastChoices=[{action,verifiedSafeFrames:80}];return Array.from({length:commit},(_,f)=>actionMask(action,f));}
    }
    let actions=[{name:'right',direction:128,jump:false},{name:'right-jump',direction:128,jump:true},
      {name:'hold-fire',direction:0,jump:false},{name:'hold-jump',direction:0,jump:true},
      {name:'right-up',direction:144,jump:false},{name:'left-jump',direction:64,jump:true}];
    if(indoor) actions=[{name:'hold-fire',direction:0,jump:false},{name:'left-fire',direction:64,jump:false},{name:'right-fire',direction:128,jump:false},
      {name:'duck-fire',direction:32,jump:false},{name:'jump-fire',direction:0,jump:true}];
    if(indoor) {
      if(start.barrier===128||start.location===128)actions.push({name:'advance',direction:16,jump:false});
      const core=start.enemies.find(e=>e.type===0x14&&e.hp>0);
      if(core){const aim=Math.max(16,Math.min(240,128+(core.x-128)*2)),delta=aim-start.x;
        if(delta!==0)for(const afterDirection of [0,32])actions.push({name:'align-core-'+afterDirection,direction:delta<0?64:128,jump:false,moveFrames:Math.min(64,Math.abs(delta)),afterDirection});}
      for(const frames of [16,32]) {
        actions.push({name:'shoot-duck-'+frames,direction:0,jump:false,moveFrames:frames,afterDirection:32});
      }
      if(start.location===128){
        const targets=start.enemies.filter(e=>[0x0a,0x08,0x10].includes(e.type)&&e.hp>0&&e.hp<240&&(e.type!==0x10||e.realHP>0)).sort((a,b)=>Math.abs(a.x-start.x)-Math.abs(b.x-start.x));
        if(targets.length){const delta=targets[0].x-start.x;if(delta)actions.push({name:'align-boss-up',direction:delta<0?64:128,jump:false,moveFrames:Math.min(64,Math.abs(delta)),afterDirection:16});}
        actions.push({name:'jump-up',direction:16,jump:true},{name:'up-left',direction:80,jump:false},{name:'up-right',direction:144,jump:false});
        for(const direction of [64,128,80,144])for(const phase of [0,16])actions.push({name:'boss-move-jump-'+direction+'-'+phase,direction,jump:true,phase});
      }
    }
    if(vertical){
      actions.push({name:'up-fire',direction:16,jump:false},{name:'left',direction:64,jump:false});
      for(const phase of [8,16,24])actions.push({name:'left-jump-phase-'+phase,direction:64,jump:true,phase});
      for(const direction of [64,128])for(const moveFrames of [32,64])for(const phase of [0,16])actions.push({name:'steer-jump-'+direction+'-'+moveFrames+'-'+phase,direction,jump:true,phase,moveFrames,afterDirection:0});
      const dragon=start.enemies.find(e=>e.type===20&&e.realHP>0);
      if(dragon){const delta=dragon.x-start.x;if(delta)actions.push({name:'align-dragon',direction:delta<0?64:128,jump:false,moveFrames:Math.min(64,Math.abs(delta)),afterDirection:16});}
    }
    if(!indoor) for(const phase of [8,16,24]) actions.push({name:'right-jump-phase-'+phase,direction:128,jump:true,phase});
    if(start.weapon===4)actions.forEach(a=>a.continuousFire=true);
    const saved=engine.save();
    const rows=[];
    for(const action of actions) {
      engine.restore(saved); let deaths=0, previous=start, o=start, score=0;
      for(let f=0;f<horizon;f++) {
        engine.step(actionMask(action,f)); o=read(engine);
        if(o.dead&&!previous.dead) deaths++;
        previous=o;
        if(o.over||o.victory||o.stage>start.stage)break;
      }
      score=(o.stage<8&&!o.over?(o.stage-start.stage)*100000:0)+(o.progress-start.progress)*3+(indoor||vertical?0:(o.x-start.x)*2) -deaths*20000 -(o.over?100000:0);
      score+=(indoor?0:(start.y-o.y)*0.15)+(o.score-start.score)*3;
      if(o.y>220)score-=200;
      if(o.water)score-=40;
      if(start.stage===0) for(const target of start.enemies.filter(e=>e.type===0x11)) {
        const after=o.enemies.find(e=>e.slot===target.slot&&e.type===target.type);
        score+=(target.hp-(after?after.hp:0))*40;
      }
      if(indoor) {
        for(const target of start.enemies.filter(e=>[0x14,0x0a,0x08,0x13].includes(e.type)&&e.hp>0&&e.hp<240)) {
          const after=o.enemies.find(e=>e.slot===target.slot&&e.type===target.type);
          score+=(target.hp-(after?after.hp:0))*40;
        }
        const target=start.enemies.find(e=>e.type===0x14&&e.hp>0);
        if(target) { const aim=Math.max(16,Math.min(240,128+(target.x-128)*2));score+=(Math.abs(start.x-aim)-Math.abs(o.x-aim))*1.5; }
        if(o.barrier===128&&start.barrier!==128) score+=500;
        if(start.stage===1&&start.location===128)for(const target of start.enemies.filter(e=>e.type===0x10&&e.realHP>0)){
          const after=o.enemies.find(e=>e.slot===target.slot&&e.type===target.type);
          score+=(target.realHP-(after?after.realHP:0))*80;
        }
        if(start.location===128){const targets=start.enemies.filter(e=>[0x0a,0x08,0x10].includes(e.type)&&e.hp>0&&e.hp<240&&(e.type!==0x10||e.realHP>0));
          if(targets.length)score+=(Math.min(...targets.map(e=>Math.abs(start.x-e.x)))-Math.min(...targets.map(e=>Math.abs(o.x-e.x))))*1.5;
        }
      }
      if(vertical) score+=(start.y-o.y)*2;
      if(vertical)for(const target of start.enemies.filter(e=>e.type===20&&e.realHP>0)){
        const after=o.enemies.find(e=>e.slot===target.slot&&e.type===target.type);
        score+=(target.realHP-(after?after.realHP:0))*80+(Math.abs(start.x-target.x)-Math.abs(o.x-target.x));
      }
      if(o.boss&&!start.boss)score+=10000;
      if(o.weapon===3&&start.weapon!==3)score+=200;
      rows.push({action,score,end:{stage:o.stage,progress:o.progress,x:o.x,y:o.y,lives:o.lives,deaths}});
    }
    engine.restore(saved);
    rows.sort((a,b)=>b.score-a.score); this.lastChoices=rows;this.reason=rows[0].action.name;
    return Array.from({length:commit},(_,f)=>actionMask(rows[0].action,f));
  }
}
module.exports={MPC,read,actionMask};
