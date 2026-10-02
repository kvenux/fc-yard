'use strict';
(() => {
  const $ = id => document.getElementById(id), ctx = $('screen').getContext('2d'), image = ctx.createImageData(256, 240);
  const names = ['A', 'B', 'SELECT', 'START', '↑', '↓', '←', '→'];
  $('keys').innerHTML = names.map(name => `<span>${name}</span>`).join('');
  let engine, romBytes, romSha256, coreSha256, profile, config, policy, playing = false, auto = false, manual = 0, pulse = 0, history = [], replay, ri = 0, left = 0;
  let accumulator = 0, last = performance.now();
  const hash = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
  const jsonFile = async input => JSON.parse(await input.files[0].text());
  const draw = pixels => { for (let i = 0; i < pixels.length; i++) { const c = pixels[i]; image.data[i * 4] = c & 255; image.data[i * 4 + 1] = c >> 8 & 255; image.data[i * 4 + 2] = c >> 16 & 255; image.data[i * 4 + 3] = 255; } ctx.putImageData(image, 0, 0); };
  const message = text => { $('message').textContent = text; };
  const safe = fn => async event => { try { await fn(event); } catch (error) { playing = false; message(error.message); } };
  const download = (name, value) => { const url = URL.createObjectURL(new Blob([JSON.stringify(value)], { type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  const refreshAI = () => { $('ai').disabled = !(engine && config && profile && profile.romSha256 === romSha256 && profile.coreSha256 === coreSha256); };
  function reset() { engine = new Contra.Engine(jsnes.NES, romBytes, draw); history = []; manual = 0; pulse = 0; playing = false; auto = false; accumulator = 0; replay = null; policy = null; $('mode').textContent = '手动校准'; $('pause').textContent = '运行'; $('ai').textContent = '启用 AI'; }
  $('rom').onchange = safe(async () => {
    romBytes = new Uint8Array(await $('rom').files[0].arrayBuffer());
    romSha256 = await hash(romBytes); reset();
    for (const id of ['pause', 'step', 'start', 'capture']) $(id).disabled = false;
    message('ROM SHA256：' + romSha256); refreshAI();
  });
  $('load').onclick = safe(async () => {
    const r = await fetch('roms/contra.nes'); if (!r.ok) throw Error('项目 ROM 不存在');
    romBytes = new Uint8Array(await r.arrayBuffer()); romSha256 = await hash(romBytes);
    const p = await fetch('observation.json'); if (!p.ok) throw Error('观察器不存在');
    profile = await p.json(); Contra.validateProfile(profile);
    if (profile.romSha256 !== romSha256 || profile.coreSha256 !== coreSha256) throw Error('ROM / 核心哈希不匹配');
    const latest = await fetch('runs/latest-policy.json', { cache: 'no-store' });
    if (latest.ok) config = await latest.json(); Contra.validatePolicy(config);
    reset(); for (const id of ['pause', 'step', 'start', 'capture']) $(id).disabled = false;
    refreshAI(); message('已载入美版初代及当前策略。点击启用 AI 从开机运行。');
  });
  $('profile').onchange = safe(async () => { const next = await jsonFile($('profile')); Contra.validateProfile(next); if (romSha256 && next.romSha256 !== romSha256) throw Error('观察器与当前 ROM 不匹配'); if (next.coreSha256 !== coreSha256) throw Error('观察器与当前 JSNES 不匹配'); profile = next; auto = false; refreshAI(); message('观察器已载入；启用 AI 时从开机重跑。'); });
  $('policy').onchange = safe(async () => { const next = await jsonFile($('policy')); Contra.validatePolicy(next); config = next; auto = false; refreshAI(); message('策略已载入。'); });
  $('pause').onclick = () => { playing = !playing; accumulator = 0; $('pause').textContent = playing ? '暂停' : '运行'; };
  $('step').onclick = safe(() => { playing = false; tick(); });
  $('start').onclick = () => { if (!auto && !replay) pulse = 8; };
  $('ai').onclick = safe(() => {
    if (auto) { auto = false; policy = null; $('ai').textContent = '启用 AI'; return; }
    reset(); policy = new Contra.Policy(config); auto = true; playing = true;
    replay = { boot: true, actions: [[0, profile.bootFrames], ...profile.startSequence.map(a => [a.mask, a.frames])] }; ri = 0; left = replay.actions[0][1];
    $('ai').textContent = '停止 AI'; $('pause').textContent = '暂停';
  });
  $('replay').onchange = safe(async () => {
    if (!romBytes) throw Error('先载入训练时使用的 ROM');
    const candidate = await jsonFile($('replay'));
    startReplay(candidate);
  });
  function startReplay(candidate) {
    if (candidate.romSha256 !== romSha256 || candidate.coreSha256 !== coreSha256) throw Error('回放 ROM 或模拟器哈希不匹配');
    if (!Array.isArray(candidate.actions) || !candidate.actions.length || candidate.actions.some(a => !Array.isArray(a) || !Number.isInteger(a[0]) || a[0] < 0 || a[0] > 255 || !Number.isInteger(a[1]) || a[1] < 1)) throw Error('按键记录格式错误');
    reset(); replay = candidate; ri = 0; left = replay.actions[0][1]; playing = true; $('pause').textContent = '暂停'; message('纯按键回放，不调用策略。');
  }
  $('model-replay').onclick = safe(async()=>{
    await $('load').onclick();
    if(!romBytes)throw Error('ROM 未载入');
    const descriptorResponse=await fetch('runs/latest-model.json',{cache:'no-store'});if(!descriptorResponse.ok)throw Error('尚无已核验的前瞻结果');
    const descriptor=await descriptorResponse.json(),response=await fetch('runs/'+descriptor.result,{cache:'no-store'});if(!response.ok)throw Error('回放记录不存在');
    const candidate=await response.json();if(!candidate.replayEqual)throw Error('该记录尚未通过回放核验');startReplay(candidate);
    message(`前瞻路径回放：最远第 ${Math.max(...candidate.stageVisits.filter(s=>s<8))+1} 关，${candidate.fullGameClearVerified?'已完整通关':'仍在训练，尚未完整通关'}。`);
  });
  $('capture').onclick = () => download(`contra-frame-${engine.frame}.json`, { romSha256, coreSha256, frame: engine.frame, ram: engine.ram(), screenshot: $('screen').toDataURL(), saved: engine.save(), actions: history });
  const binds = { KeyZ: 0, KeyX: 1, ShiftRight: 2, Enter: 3, ArrowUp: 4, ArrowDown: 5, ArrowLeft: 6, ArrowRight: 7 };
  onkeydown = e => { if (e.code === 'Escape') document.body.classList.remove('capture'); if (e.target.matches('input,select,button')) return; if (e.code in binds && !auto && !replay) { e.preventDefault(); manual |= 1 << binds[e.code]; } };
  onkeyup = e => { if (e.code in binds) manual &= ~(1 << binds[e.code]); };
  onblur = () => { manual = 0; pulse = 0; };
  document.addEventListener('visibilitychange', () => { manual = 0; pulse = 0; accumulator = 0; });
  $('clean').onclick = () => document.body.classList.add('capture');
  if (new URLSearchParams(location.search).get('capture') === '1') document.body.classList.add('capture');
  function tick() {
    if (!engine) return;
    let mask = manual | pulse; pulse = 0;
    if (replay) mask = replay.actions[ri][0];
    else if (auto) {
      const o = Contra.observe(engine, profile);
      if (o.victory || o.gameOver) { playing = false; $('reason').textContent = o.victory ? '观察到胜利；完整通关以训练审计为准' : '本局结束'; return; }
      mask = policy.choose(o); $('reason').textContent = policy.reason;
    }
    engine.step(mask);
    const previous = history.at(-1); if (previous && previous[0] === mask) previous[1]++; else history.push([mask, 1]);
    [...$('keys').children].forEach((el, i) => el.classList.toggle('active', !!(mask & 1 << i)));
    $('frames').textContent = engine.frame; $('mode').textContent = auto ? 'AI 策略' : replay ? '按键回放' : '手动校准';
    if (profile && profile.romSha256 === romSha256) { const o = Contra.observe(engine, profile); const stage = profile.stageOrder.indexOf(o.stage) + 1; $('stats').textContent = `${stage || '—'} / ${o.gameOver ? 0 : o.lives + 1}`; }
    if (replay && --left === 0) {
      ri++;
      if (ri < replay.actions.length) left = replay.actions[ri][1];
      else { const boot = replay.boot; replay = null; if (!boot) { playing = false; message('按键回放结束；哈希核验结果请查训练记录。'); }
        else { const o = Contra.observe(engine, profile); if (!o.playing || o.stage !== profile.stageOrder[0]) throw Error('开局流程未进入首关'); } }
    }
  }
  function loop(now) {
    const elapsed = Math.min(100, now - last); last = now;
    if (playing && engine && !document.hidden) {
      accumulator += elapsed * Number($('speed').value);
      let steps = 0;
      try { while (accumulator >= 1000 / 60 && steps++ < 8 && playing) { tick(); accumulator -= 1000 / 60; } } catch (error) { playing = false; message(error.message); }
      if (steps >= 8) accumulator = Math.min(accumulator, 1000 / 60);
    }
    requestAnimationFrame(loop);
  }
  Promise.all([fetch('policy.json').then(r => r.json()), fetch('/node_modules/jsnes/dist/jsnes.js').then(r => r.arrayBuffer()).then(hash)])
    .then(([c, h]) => { Contra.validatePolicy(c); config = c; coreSha256 = h; refreshAI(); }).catch(e => message(e.message));
  requestAnimationFrame(loop);
})();
