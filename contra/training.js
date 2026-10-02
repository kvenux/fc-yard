'use strict';
(() => {
  const $ = id => document.getElementById(id); let report;
  function runTime(run) {
    const native = /^native-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})$/.exec(run);
    if (native) return Date.parse(`${native[1]}-${native[2]}-${native[3]}T${native[4]}:${native[5]}:${native[6]}+08:00`);
    return Date.parse(run.replace(/^(mpc|search)-/, '').replace(/T(\d{2})-(\d{2})-(\d{2})-(\d{3})Z$/, 'T$1:$2:$3.$4Z')) || 0;
  }
  function chart(title, rows, value, best = false, container='charts', minimumMax=1) {
    const values = rows.map(value), max = Math.max(minimumMax, ...values), n = Math.max(1, rows.length - 1);
    const x = i => 55 + i / n * 850, y = v => 215 - v / max * 175;
    const points = values.map((v, i) => `${x(i)},${y(v)}`).join(' ');
    let high = 0;
    const envelope = rows.map((e, i) => { if (e.replayEqual) high = Math.max(high, value(e)); return `${x(i)},${y(high)}`; }).join(' ');
    const section = document.createElement('section'); section.className = 'chart';
    const h = document.createElement('strong'); h.textContent = title; section.append(h);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 950 265'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', title);
    svg.innerHTML = `<path d="M55 35 V215 H915" fill="none" stroke="#ad9983"/><text x="12" y="45" font-size="13">${max.toFixed(0)}</text><text x="28" y="218" font-size="13">0</text><polyline points="${points}" fill="none" stroke="#a23443" stroke-width="2"/>${best ? `<polyline points="${envelope}" fill="none" stroke="#26756d" stroke-width="2" stroke-dasharray="6 4"/>` : ''}${values.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="${rows[i].replayEqual ? '#a23443' : '#aaa'}"><title>候选 ${rows[i].episode}：${v}</title></circle>`).join('')}<text x="55" y="246" font-size="13">候选 1</text><text x="830" y="246" font-size="13">候选 ${rows.length}</text>`;
    section.append(svg); $(container).append(section);
  }
  function render() {
    $('charts').replaceChildren(); $('rows').replaceChildren();
    const g = report.groups[Number($('group').value)];
    if (!g) { $('scope').textContent = '真实训练记录为 0，暂无曲线。'; return; }
    $('scope').textContent = `当前组：${g.scope === 'native_fresh_boot_model_search' ? '原生 FCEUmm 前瞻' : g.scope === 'fresh_boot_model_search' ? 'JSNES 前瞻' : 'JSNES 参数搜索'}，${g.episodes.length} 个候选；帧预算 ${g.budget}；ROM ${g.romSha256.slice(0, 12)}。红线为各候选，绿虚线为回放通过的历史最好表现。`;
    $('rounds').textContent = (g.rounds || []).map((r, i) => `第 ${i + 1} 轮：${r.count} 候选，平均最远 ${r.meanReachedStage.toFixed(2)} 关，最好 ${r.bestReachedStage} 关，通关 ${r.victories}/${r.count}`).join('；');
    chart('最远到达关卡序号', g.episodes, e => e.reachedStage, true);
    chart('生命损失', g.episodes, e => e.deaths);
    if(g.episodes.some(e=>Number.isFinite(e.gunKills)))chart('已核验击毁炮台数',g.episodes.filter(e=>Number.isFinite(e.gunKills)),e=>e.gunKills);
    chart('模拟帧数（含开局；死亡提前结束也会缩短）', g.episodes, e => e.frames);
    for (const stage of [...new Set(g.episodes.map(e => e.reachedStage))].sort((a, b) => a - b)) chart(`第 ${stage} 关最高进度（该关候选子集）`, g.episodes.filter(e => e.reachedStage === stage), e => e.progress, true);
    for (const e of g.episodes) {
      const tr = document.createElement('tr');
      for (const value of [`${e.run.replace('search-', '')} / ${e.candidate}${e.kind==='fresh_boot_recertification'?' · 同路径复核':''}`, e.reachedStage, e.deaths, e.frames, e.replayEqual ? '一致' : '失败', e.oneLifeClearVerified ? '一命通关已核验' : e.fullGameClearVerified ? '已核验' : '未通关']) { const td = document.createElement('td'); td.textContent = value; tr.append(td); }
      $('rows').append(tr);
    }
  }
  async function refresh() {
    try {
      const response = await fetch('runs/learning-curve.json', { cache: 'no-store' }); if (!response.ok) throw Error('曲线数据尚未生成'); report = await response.json();
      const all = report.groups.flatMap(g => g.episodes);
      $('milestones').replaceChildren();
      const milestones=all.filter(e=>e.replayEqual).sort((a,b)=>runTime(a.run)-runTime(b.run)||a.candidate-b.candidate).map((e,i)=>({...e,episode:i+1}));
      if(milestones.length)chart('训练历程：已核验路径最远到达关卡（预算不同，仅表示突破历程）',milestones,e=>e.reachedStage,true,'milestones',8);
      $('count').textContent = all.length; $('victories').textContent = all.filter(e => e.fullGameClearVerified).length; $('verified').textContent = all.filter(e => e.replayEqual).length;
      if($('one-life'))$('one-life').textContent=all.filter(e=>e.oneLifeClearVerified).length;
      $('status').textContent = report.preflight?.status === 'running' ? `正在训练：本轮完成 ${report.preflight.completedCandidates} / ${report.preflight.candidatesPlanned}` : report.preflight?.status === 'completed' ? '本轮训练完成' : report.preflight?.ready ? (all.length ? '已记录训练候选；运行状态请查看训练日志' : '预检通过，尚无已完成候选') : '训练未启动：缺少运行条件';
      $('blockers').textContent = (report.preflight?.blockers || []).join('；') + ((report.interruptions||[]).length?`另有 ${report.interruptions.length} 次因策略修正中断的探索，未完成回放，不计入已核验候选。`:'');
      const selected = $('group').value; $('group').replaceChildren();
      report.groups.forEach((g, i) => { const option = document.createElement('option'); option.value = i; option.textContent = `组 ${i + 1} · ${g.objective==='zero_death'?'一命训练 · ':''}${g.combatStyle==='aggressive'?'主动清炮 · ':''}${g.episodes.length} 个候选 · ${g.budget} 帧`; $('group').append(option); });
      if (report.groups.length) $('group').value = selected!=='' && Number(selected) < report.groups.length ? selected : String(Math.max(0,report.groups.findLastIndex(g=>g.objective==='zero_death')));
      render();
      const modelResponse = await fetch('runs/model-status.json', { cache: 'no-store' });
      if(modelResponse.ok) { const m=await modelResponse.json(); $('model').textContent=`前瞻搜索最近记录：第 ${m.stage} 关，${m.frame} 帧${m.progress!==undefined?'，滚动进度 '+m.progress:''}。${m.status==='completed'?'本次已结束':'搜索中'} · ${new Date(m.updatedAt).toLocaleTimeString()}`; }
      const nativeResponse=await fetch('runs/native-status.json',{cache:'no-store'});
      if(nativeResponse.ok){const n=await nativeResponse.json();$('native').textContent=`原生核心独立实验：${n.stage>=8?'结局':`第 ${n.stage+1} 关`}，${n.frame} 帧${n.progress!==undefined?'，滚动进度 '+n.progress:''}，${n.status==='completed'?'本次已结束':'搜索中'}。旧 JSNES 输入不能跨核心复用。`;
        if(n.status==='running')$('status').textContent='原生前瞻训练正在运行';
        if(n.status==='running'&&n.objective==='zero_death')$('status').textContent=`一命通关训练中 · 当前路径死亡 ${n.deaths} 次`;
        if(n.status==='completed'&&n.objective==='zero_death')$('status').textContent=n.oneLifeClearVerified?'一命通关已核验':n.deaths>0?'本次一命候选失败，死亡记录已保留':n.replayEqual?'本段零死亡路径已核验，尚未一命通关':'本段路径回放尚未通过';
        else if(n.stage>=8 && n.replayEqual)$('status').textContent='八关通关，独立回放已核验';
        if(/^native-\d{8}-\d{6}$/.test(n.dir)){$('native-preview').hidden=false;$('native-frame').src=`runs/${n.dir}/${n.status==='completed'?'final':'latest'}.png?t=${Date.now()}`;}
      }
    } catch (error) { $('status').textContent = error.message; }
  }
  $('group').onchange = render; refresh(); setInterval(refresh, 5000);
})();
