'use strict';
const fs = require('fs'), path = require('path');
const root = __dirname;
function buildReport() {
  const runs = path.join(root, 'runs'); fs.mkdirSync(runs, { recursive: true });
  const groups = new Map();
  const interruptions=[];
  for (const name of fs.readdirSync(runs).sort()) {
    const interruptionFile=path.join(runs,name,'interrupted.json');
    if(fs.existsSync(interruptionFile)){const record=JSON.parse(fs.readFileSync(interruptionFile,'utf8').replace(/^\uFEFF/,''));interruptions.push({run:name,reason:record.reason,lastFrame:record.lastObservation?.frame,replayVerified:false});}
    const file = path.join(runs, name, 'episodes.jsonl'), manifestFile = path.join(runs, name, 'manifest.json'), modelFile = path.join(runs, name, 'result.json');
    const native=name.startsWith('native-')&&fs.existsSync(modelFile);
    const model = (name.startsWith('mpc-')||native) && fs.existsSync(modelFile);
    if ((!name.startsWith('search-') && !model) || (!fs.existsSync(file) && !model) || !fs.existsSync(manifestFile)) continue;
    const manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
    if(native){manifest.profile??={stageOrder:[0,1,2,3,4,5,6,7],observer:'native read(), exact US ROM RAM map'};manifest.budget=manifest.args.frames;}
    // ROM, core, observation semantics and budget must match for comparable curves.
    const key = JSON.stringify([manifest.romSha256, manifest.coreSha256, manifest.profile, manifest.budget, manifest.scope,manifest.objective||'clear',manifest.combatStyle||'balanced']);
    if (!groups.has(key)) groups.set(key, { romSha256: manifest.romSha256, coreSha256: manifest.coreSha256,
      budget: manifest.budget, scope: manifest.scope, objective:manifest.objective||'clear',combatStyle:manifest.combatStyle||'balanced',stageCount: manifest.profile.stageOrder.length, episodes: [], rounds: [], best: null });
    const group = groups.get(key);
    const records = model ? [JSON.parse(fs.readFileSync(modelFile, 'utf8'))] : fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
    const combatFile=path.join(runs,name,'combat-audit.json'),combat=fs.existsSync(combatFile)?JSON.parse(fs.readFileSync(combatFile,'utf8')):null;
    for (const e of records) {
      if(model) { e.index=0;e.maxStage=Math.max(...e.stageVisits.filter(s=>s<8));e.maxProgress=Math.max(e.final.stage===e.maxStage?e.final.progress:0,...e.samples.filter(s=>s.stage===e.maxStage).map(s=>s.progress));if(native)e.config={engine:'fceumm',horizon:manifest.args.horizon}; }
      group.episodes.push({ run: name, candidate: e.index, episode: group.episodes.length + 1,
        kind: manifest.kind || 'training', sourceResult: manifest.sourceResult || null,
        reachedStage: e.maxStage + 1, progress: e.maxProgress, deaths: e.deaths,
        lives: e.final.lives, frames: e.frames, wallSeconds: e.wallSeconds,gunKills:combat?.replayEqual?combat.gunKills:null,
        replayEqual: e.replayEqual, fullGameClearVerified: e.fullGameClearVerified,oneLifeClearVerified:e.oneLifeClearVerified===true });
      const rank = [Number(e.fullGameClearVerified), Number(e.oneLifeClearVerified===true), e.maxStage, e.maxProgress, -e.deaths, combat?.replayEqual?combat.gunKills:0, e.final.score||0, -e.frames];
      const better = !group.best || rank.some((v, i) => rank.slice(0, i).every((x, j) => x === group.best.rank[j]) && v > group.best.rank[i]);
      if (e.replayEqual && better) group.best = { run: name, candidate: e.index, rank, config: e.config };
    }
    const episodes = group.episodes.filter(e => e.run === name);
    group.rounds.push({ run: name, count: episodes.length, meanReachedStage: episodes.reduce((n, e) => n + e.reachedStage, 0) / episodes.length,
      bestReachedStage: Math.max(...episodes.map(e => e.reachedStage)), victories: episodes.filter(e => e.fullGameClearVerified).length,
      meanDeaths: episodes.reduce((n, e) => n + e.deaths, 0) / episodes.length });
  }
  const preflightFile = path.join(runs, 'preflight.json');
  const report = { updatedAt: new Date().toISOString(), preflight: fs.existsSync(preflightFile) ? JSON.parse(fs.readFileSync(preflightFile, 'utf8')) : null,
    interruptions, groups: [...groups.values()], episodes: [...groups.values()].reduce((n, g) => n + g.episodes.length, 0) };
  fs.writeFileSync(path.join(runs, 'learning-curve.json'), JSON.stringify(report, null, 2));
  const latestBest = report.groups.filter(g=>g.scope==='fresh_boot_parameter_search').at(-1)?.best;
  if (latestBest) {
    fs.writeFileSync(path.join(runs, 'latest-policy.json'), JSON.stringify(latestBest.config, null, 2));
    fs.writeFileSync(path.join(runs, 'deployed-policy.json'), JSON.stringify(latestBest, null, 2));
  }
  const modelBest=report.groups.filter(g=>g.scope==='fresh_boot_model_search'&&g.best).map(g=>g.best).sort((a,b)=>{
    for(let i=0;i<a.rank.length;i++)if(a.rank[i]!==b.rank[i])return b.rank[i]-a.rank[i];return 0;
  })[0];
  if(modelBest)fs.writeFileSync(path.join(runs,'latest-model.json'),JSON.stringify({run:modelBest.run,result:modelBest.run+'/result.json',rank:modelBest.rank},null,2));
  const nativeBest=report.groups.filter(g=>g.scope==='native_fresh_boot_model_search'&&g.best).map(g=>g.best).sort((a,b)=>{for(let i=0;i<a.rank.length;i++)if(a.rank[i]!==b.rank[i])return b.rank[i]-a.rank[i];return 0;})[0];
  if(nativeBest)fs.writeFileSync(path.join(runs,'latest-native.json'),JSON.stringify({run:nativeBest.run,result:nativeBest.run+'/result.json',rank:nativeBest.rank},null,2));
  const fields = ['group', 'run', 'kind', 'candidate', 'episode', 'reachedStage', 'progress', 'deaths', 'lives', 'frames', 'wallSeconds', 'replayEqual', 'fullGameClearVerified','oneLifeClearVerified','gunKills'];
  const csv = [fields.join(',')];
  report.groups.forEach((g, i) => g.episodes.forEach(e => csv.push(fields.map(f => f === 'group' ? i + 1 : e[f]).join(','))));
  fs.writeFileSync(path.join(runs, 'episodes.csv'), '\uFEFF' + csv.join('\n') + '\n');
  return report;
}
if (require.main === module) console.log(JSON.stringify({ episodes: buildReport().episodes }));
module.exports = { buildReport };
