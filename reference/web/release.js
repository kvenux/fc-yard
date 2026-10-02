// Presentation controls; game.js remains unchanged. Replay uses only recorded keys.
(()=>{
 const seedInput=document.getElementById('ai-seed');seedInput.value='4004';
 const liveButton=document.getElementById('ai-on');liveButton.textContent='运行 35 关策略';
 const controls=document.createElement('div');controls.style='margin-top:8px';controls.innerHTML='<button id="ai-replay">通关录像（按键回放）</button> <button id="ai-pause">暂停</button> <label>速度 <select id="ai-speed"><option value="1">1×</option><option value="8">8×</option><option value="32">32×</option></select></label> <a href="/training/index.html" style="color:#7dd3fc">训练曲线</a><div style="color:#a5b4fc;margin-top:6px">已验证种子 4004 完整通关。其他种子仍可能失败；浏览器复刻版，非 NES 原版。</div>';panel.appendChild(controls);
 let paused=false,replay=null,replayIndex=0,replayLeft=0;
 const normalUpdate=update;
 update=function(){if(paused)return;const speed=Number(document.getElementById('ai-speed').value)||1;for(let i=0;i<speed;i++){if(replay){if(replayIndex>=replay.actions.length)return;const [mask,n]=replay.actions[replayIndex];if(!replayLeft)replayLeft=n;aiDirs.forEach((k,d)=>keys[k]=!!(mask&(1<<d)));keys.Space=!!(mask&16);originalUpdate();if(!--replayLeft)replayIndex++;aiReason='已验证整局按键回放 · '+replayIndex+'/'+replay.actions.length;}else normalUpdate();if(gamePhase==='victory'||!eagleAlive&&gamePhase==='play'||p1Lives<0)return;}};
 function resetControls(){paused=false;replay=null;document.getElementById('ai-pause').textContent='暂停';}
 liveButton.onclick=async()=>{try{const response=await fetch('trained-policy.json');if(!response.ok)throw Error('策略读取失败');const policy=await response.json();resetControls();aiStart(Number(seedInput.value)||4004,policy);}catch(e){aiReason=e.message;aiPanelUpdate();}};
 document.getElementById('ai-replay').onclick=async()=>{try{const response=await fetch('/training/full-verification/audit.json');if(!response.ok)throw Error('录像读取失败');const audit=await response.json();resetControls();aiStart(audit.seed);tankAI.stop();seedInput.value=audit.seed;replay=audit;replayIndex=0;replayLeft=0;document.getElementById('ai-speed').value='32';}catch(e){aiReason=e.message;aiPanelUpdate();}};
 document.getElementById('ai-pause').onclick=()=>{paused=!paused;document.getElementById('ai-pause').textContent=paused?'继续':'暂停';};
 document.getElementById('ai-off').onclick=()=>{resetControls();tankAI.stop();};
 document.getElementById('ai-static').onclick=()=>{resetControls();aiStart(Number(seedInput.value)||4004,{mode:'static'});};
})();
