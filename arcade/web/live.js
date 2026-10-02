const $ = id => document.getElementById(id);
let state = null, imageURL = null, connected = true;
const keyboardKeys = new Set(), pointerKeys = new Map();
let stickKeys = [], stickPointer = null, stickOrigin = null, inputQueue = Promise.resolve();
const binds = {ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',KeyJ:'attack',KeyK:'jump',KeyU:'c',KeyI:'d',Digit5:'coin',Enter:'start'};
const directions = {'0,-1':'↑ 上','1,-1':'↗ 右上','1,0':'→ 右','1,1':'↘ 右下','0,1':'↓ 下','-1,1':'↙ 左下','-1,0':'← 左','-1,-1':'↖ 左上','0,0':'中立'};
const canonical = key => key === 'item' ? 'c' : key === 'menu' ? 'd' : key;
const canControl = () => state?.ready && state.mode === 'manual';

async function command(action, extra = {}) {
  try {
    const response = await fetch('/api/control', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...extra})});
    const data = await response.json();
    if (!response.ok) throw Error(data.error);
    if (data.saved) $('notice').textContent = '已保存：' + data.saved;
    else render(data);
  } catch (error) { $('notice').textContent = error.message; }
}
function sendKeys() {
  const buttons = [...new Set([...keyboardKeys,...pointerKeys.values(),...stickKeys])];
  inputQueue = inputQueue.then(() => command('keys',{buttons}));
}
function releaseControls() {
  keyboardKeys.clear(); pointerKeys.clear(); stickKeys = []; stickPointer = null; stickOrigin = null;
  $('stick-zone').classList.remove('dragging');
  if (canControl()) sendKeys();
}
function renderCabinet(s) {
  const pressed = new Set((s.display_buttons ?? s.buttons ?? []).map(canonical));
  const actual = new Set((s.buttons ?? []).map(canonical));
  document.querySelectorAll('.cabinet-button').forEach(button => {
    const active = pressed.has(button.dataset.key);
    button.classList.toggle('on',active);
    button.setAttribute('aria-pressed',String(active));
    button.disabled = !(s.ready && s.mode === 'manual');
  });
  const dx = Number(actual.has('right')) - Number(actual.has('left'));
  const dy = Number(actual.has('down')) - Number(actual.has('up'));
  const stick = $('stick-indicator');
  stick.classList.toggle('on',Boolean(dx || dy));
  stick.style.setProperty('--angle',`${Math.atan2(dx,-dy)*180/Math.PI}deg`);
  $('stick-state').textContent = '摇杆 · ' + directions[`${dx},${dy}`];
  const letters = [['attack','A'],['jump','B'],['c','C'],['d','D']].filter(([key])=>actual.has(key)).map(([,letter])=>letter);
  $('button-state').textContent = letters.length ? '按下 · ' + letters.join(' + ') : 'A 攻击 · B 跳跃 · C / D 道具操作';
  $('stick-zone').classList.toggle('interactive',Boolean(s.ready && s.mode === 'manual'));
}
function renderItems(s) {
  const items = s.observation?.inventory || [];
  $('inventory').textContent = s.items_calibrated ? (items.filter(i=>i.count>0).map(i=>`${i.name||i.id} × ${i.count}`).join(' · ')||'当前无可用道具') : '道具状态未校准';
  const event = s.item_events?.at(-1);
  const labels = {input_submitted:'已提交按键，等待核验',consumed_effect_observed:'数量减少，并观察到效果变化',consumed_unconfirmed_effect:'数量减少，效果未确认',use_unconfirmed:'未确认使用成功',selection_aborted:'使用条件变化或选取超时，已取消',context_changed_unconfirmed:'角色、关卡或生命变化，结果未确认'};
  $('item-result').textContent = event ? `${event.name||event.item_id}：${labels[event.status]||event.status}` : '尚无使用记录';
}
function render(s) {
  state = s; connected = true;
  for (const id of ['play','step','save','speed','mode']) $(id).disabled = !s.ready;
  $('mode').querySelector('[value="heuristic"]').disabled = !s.calibrated;
  if (s.mode === 'replay' && !$('mode').querySelector('[value="replay"]')) $('mode').add(new Option('纯按键回放','replay'));
  if (s.mode === 'training' && !$('mode').querySelector('[value="training"]')) $('mode').add(new Option('训练直播（只读）','training'));
  $('mode').value = s.mode; $('mode').disabled = !s.ready || s.mode === 'replay';
  if (s.mode === 'training') for (const id of ['play','step','save','speed','mode','reload']) $(id).disabled = true;
  $('play').textContent = s.playing ? '暂停' : '开始运行'; $('speed').value = s.speed;
  $('badge').textContent = s.playing ? '运行中' : s.ready ? '已暂停' : '待机';
  document.querySelector('.live-badge').classList.toggle('running',s.playing);
  $('empty').hidden = s.ready && !s.headless; $('game').hidden = !s.ready || s.headless;
  document.querySelector('#empty h3').textContent = s.headless ? '无画面高速训练' : '等待游戏载入';
  $('empty-copy').textContent = s.headless ? '直接读取内存状态，训练结束后可单独播放已记录动作' : s.error ? `等待载入 ${s.game || ''} 游戏文件` : '将游戏文件放入后，在控制台载入';
  $('reason').textContent = s.reason;
  const o = s.observation || {};
  for (const id of ['hp','lives','score','progress']) $(id).textContent = o[id] ?? '—';
  $('evidence').textContent = s.replay_result ? (s.replay_result.equal?'纯按键回放核对一致':'回放核对失败') : s.game === 'orlegend' ? '基础状态读取 · 局部策略训练 · 完整通关未验证' : s.calibrated ? '游戏状态观察器已校准 · 完整通关未验证' : '观察器未校准 · 尚未开始成绩训练';
  $('actual').textContent = s.actual_speed.toFixed(2) + '×';
  if (s.full_game_clear_verified && s.replay_result?.equal !== false) $('evidence').textContent = `完整通关回放 · ${Number.isFinite(s.deaths)?`死亡 ${s.deaths} 次 · `:''}正常续关 ${s.continues} 次 · 独立回放已核验`;
  if (s.mode === 'training') $('evidence').textContent = '已执行帧直播 · 得分/血量已校准 · 场景码不代表关卡数 · 通关未验证';
  if (s.headless) $('evidence').textContent = '视频已关闭 · 只读 RAM 决策 · 实际按键已记录 · 通关未验证';
  $('frames').textContent = s.recorded_frames.toLocaleString() + ' 帧';
  const seconds = Math.floor(s.frame / s.fps);
  $('clock').textContent = String(Math.floor(seconds/60)).padStart(2,'0') + ':' + String(seconds%60).padStart(2,'0');
  renderCabinet(s); renderItems(s);
  if (s.error) $('notice').textContent = s.error;
}
async function poll() {
  try {
    const response = await fetch('/api/status');
    if (!response.ok) throw Error('连接失败');
    render(await response.json());
  } catch {
    connected = false; state = null;
    $('badge').textContent = '已断线'; $('notice').textContent = '本地服务未连接，请运行 python arcade/serve.py';
    renderCabinet({ready:false,buttons:[]});
  }
  setTimeout(poll,state?.playing ? 60 : 250);
}
async function frame() {
  try {
    if (state?.ready && connected && !state.headless) {
      const response = await fetch('/frame.jpg');
      if (response.status === 200) {
        const next = URL.createObjectURL(await response.blob()); $('game').src = next;
        if (imageURL) URL.revokeObjectURL(imageURL); imageURL = next;
      }
    }
  } catch { connected = false; }
  finally { setTimeout(frame,50); }
}
$('play').onclick = () => {releaseControls(); command('play',{value:!state?.playing});};
$('step').onclick = () => command('step'); $('save').onclick = () => command('save'); $('reload').onclick = () => command('reload');
$('speed').onchange = e => command('speed',{value:Number(e.target.value)});
$('mode').onchange = e => {releaseControls(); command('mode',{value:e.target.value});};
function capture(value) {document.body.classList.toggle('capture',value); history.replaceState(null,'',location.pathname+(value?'?capture=1':''));}
$('capture').onclick = () => capture(true); capture(new URLSearchParams(location.search).get('capture') === '1');
document.addEventListener('keydown', e => {
  if (e.code === 'Escape') {capture(false);return;}
  const tag = document.activeElement.tagName;
  if (['INPUT','SELECT'].includes(tag) || (tag === 'BUTTON' && e.code === 'Enter')) return;
  const key = binds[e.code];
  if (key && canControl()) {e.preventDefault(); if (!keyboardKeys.has(key)) {keyboardKeys.add(key);sendKeys();}}
});
document.addEventListener('keyup', e => {const key=binds[e.code]; if(key&&keyboardKeys.delete(key)&&canControl())sendKeys();});
window.addEventListener('blur',releaseControls);
document.addEventListener('visibilitychange',()=>{if(document.hidden)releaseControls();});
for (const button of document.querySelectorAll('.cabinet-button')) {
  button.addEventListener('pointerdown',e=>{if(!canControl())return;e.preventDefault();button.setPointerCapture(e.pointerId);pointerKeys.set(e.pointerId,button.dataset.key);sendKeys();});
  const release=e=>{if(pointerKeys.delete(e.pointerId)&&canControl())sendKeys();};
  button.addEventListener('pointerup',release); button.addEventListener('pointercancel',release);button.addEventListener('lostpointercapture',release);
}
const stickZone = $('stick-zone');
stickZone.addEventListener('pointerdown',e=>{if(!canControl()||stickPointer!==null)return;e.preventDefault();stickPointer=e.pointerId;stickOrigin={x:e.clientX,y:e.clientY};stickZone.setPointerCapture(e.pointerId);stickZone.classList.add('dragging');});
stickZone.addEventListener('pointermove',e=>{
  if(e.pointerId!==stickPointer||!canControl())return;
  const threshold=Math.max(6,stickZone.clientWidth*.08),dx=e.clientX-stickOrigin.x,dy=e.clientY-stickOrigin.y;
  const next=[];if(Math.abs(dx)>threshold)next.push(dx>0?'right':'left');if(Math.abs(dy)>threshold)next.push(dy>0?'down':'up');
  if(next.join()!==stickKeys.join()){stickKeys=next;sendKeys();}
});
const releaseStick=e=>{if(e.pointerId!==stickPointer)return;stickPointer=null;stickOrigin=null;stickKeys=[];stickZone.classList.remove('dragging');if(canControl())sendKeys();};
stickZone.addEventListener('pointerup',releaseStick);stickZone.addEventListener('pointercancel',releaseStick);stickZone.addEventListener('lostpointercapture',releaseStick);
poll();frame();
