'use strict';
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const { NES } = require('./core.cjs');
const { Engine, Policy, observe, validateProfile, validatePolicy } = require('./engine.js');
const { buildReport } = require('./report.cjs');
const { picture } = require('./picture.cjs');
const root = __dirname;
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const read = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
function fingerprint(engine) {
  return { state: sha(JSON.stringify(engine.save())), ram: sha(Buffer.from(engine.ram())), pixels: sha(Buffer.from(engine.pixels.buffer)) };
}
function boot(engine, profile, submit) {
  for (let i = 0; i < profile.bootFrames; i++) submit(0);
  for (const { mask, frames } of profile.startSequence) for (let i = 0; i < frames; i++) submit(mask);
}
function main() {
  const args = process.argv.slice(2), option = (key, fallback) => {
    const i = args.indexOf(key); return i === -1 ? fallback : args[i + 1];
  };
  const romPath = option('--rom', path.join(root, 'roms/contra.nes'));
  const profilePath = option('--profile', path.join(root, 'observation.json'));
  const preflight = { romPath: path.resolve(romPath), profilePath: path.resolve(profilePath), ready: false,
    trainingStarted: false, fullGameClearVerified: false, blockers: [] };
  if (!fs.existsSync(romPath)) preflight.blockers.push('缺少魂斗罗 .nes ROM');
  if (!fs.existsSync(profilePath)) preflight.blockers.push('缺少已校准的 observation.json');
  let rom, profile;
  if (!preflight.blockers.length) {
    try {
      rom = fs.readFileSync(romPath); profile = read(profilePath); validateProfile(profile);
      if (profile.romSha256 !== sha(rom)) throw Error('ROM SHA256 不匹配');
      if (profile.coreSha256 !== sha(fs.readFileSync(require.resolve('jsnes')))) throw Error('JSNES SHA256 不匹配');
      const engine = new Engine(NES, rom); boot(engine, profile, mask => engine.step(mask));
      const o = observe(engine, profile);
      if (!o.playing || o.victory || o.gameOver || o.stage !== profile.stageOrder[0]) throw Error('开局流程未进入首关');
      preflight.ready = true;
    } catch (error) { preflight.blockers.push(error.message); }
  }
  fs.mkdirSync(path.join(root, 'runs'), { recursive: true });
  fs.writeFileSync(path.join(root, 'runs/preflight.json'), JSON.stringify(preflight, null, 2));
  buildReport();
  console.log(JSON.stringify(preflight));
  if (!preflight.ready) { process.exitCode = 2; return; }
  if (args.includes('--preflight')) return;
  const budget = Number(option('--frames', '18000')), count = Number(option('--candidates', '12'));
  if (!Number.isInteger(budget) || budget < 1 || !Number.isInteger(count) || count < 1 || count > 12) throw Error('frames >= 1，candidates 为 1–12');
  const baseline = read(option('--policy', path.join(root, 'policy.json')));
  const dir = path.join(root, 'runs', 'search-' + new Date().toISOString().replace(/[:.]/g, '-'));
  fs.mkdirSync(dir, { recursive: true });
  const gridPath = option('--grid', null);
  const grid = gridPath ? read(gridPath) : null;
  if (grid && (!Array.isArray(grid) || !grid.length)) throw Error('grid 必须是候选参数数组');
  const manifest = { createdAt: new Date().toISOString(), scope: 'fresh_boot_parameter_search', romSha256: sha(rom),
    coreSha256: profile.coreSha256, profile, baseline, grid, budget, count, sourceHashes: {} };
  for (const name of ['engine.js', 'train.cjs', 'core.cjs', 'picture.cjs', 'report.cjs']) {
    const content = fs.readFileSync(path.join(root, name)); manifest.sourceHashes[name] = sha(content); fs.writeFileSync(path.join(dir, name), content);
  }
  fs.writeFileSync(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2));
  const candidates = [];
  if (grid) candidates.push(...grid.map(p => ({ ...baseline, ...p })));
  else for (const firePeriod of [6, 10]) for (const jumpPeriod of [45, 70, 100]) for (const jumpHold of [8, 20]) candidates.push({ ...baseline, firePeriod, jumpPeriod, jumpHold });
  candidates.slice(0, count).forEach(validatePolicy);
  Object.assign(preflight, { trainingStarted: true, status: 'running', run: path.basename(dir), candidatesPlanned: Math.min(count, candidates.length), completedCandidates: 0 });
  fs.writeFileSync(path.join(root, 'runs/preflight.json'), JSON.stringify(preflight, null, 2)); buildReport();
  let best = null;
  for (const [index, config] of candidates.slice(0, count).entries()) {
    const begin = performance.now(), engine = new Engine(NES, rom), policy = new Policy(config), actions = [], samples = [];
    const submit = mask => { engine.step(mask); const last = actions.at(-1); if (last && last[0] === mask) last[1]++; else actions.push([mask, 1]); };
    boot(engine, profile, submit);
    let o = observe(engine, profile), before = o, deaths = 0, maxStage = 0, maxProgress = o.progress;
    const stageVisits = [o.stage];
    for (let f = 0; f < budget && !o.victory && !o.gameOver; f++) {
      submit(policy.choose(o)); o = observe(engine, profile);
      if (o.playerState !== undefined) { if (o.playerState === 2 && before.playerState !== 2) deaths++; }
      else if (o.lives < before.lives) deaths += before.lives - o.lives;
      const stageIndex = profile.stageOrder.indexOf(o.stage);
      if (o.playing && stageIndex === -1) throw Error('观察到未校准的关卡值：' + o.stage);
      if (o.playing && o.stage !== stageVisits.at(-1)) stageVisits.push(o.stage);
      if (stageIndex > maxStage) { maxStage = stageIndex; maxProgress = o.progress; }
      else if (stageIndex === maxStage) maxProgress = Math.max(maxProgress, o.progress);
      if (f % 120 === 0) samples.push({ ...o, reason: policy.reason });
      before = o;
    }
    picture(engine, path.join(dir, `candidate-${index}-final.png`));
    const expected = fingerprint(engine), replay = new Engine(NES, rom);
    for (const [mask, frames] of actions) for (let f = 0; f < frames; f++) replay.step(mask);
    const actual = fingerprint(replay), replayEqual = JSON.stringify(expected) === JSON.stringify(actual);
    const visitedAll = profile.stageOrder.every((stage, i) => stageVisits[i] === stage) && stageVisits.length === profile.stageOrder.length;
    const result = { index, config, romSha256: manifest.romSha256, coreSha256: manifest.coreSha256, frames: engine.frame, maxStage, maxProgress, deaths, final: o, stageVisits,
      victoryObserved: o.victory, fullGameClearVerified: o.victory && visitedAll && replayEqual,
      replayEqual, expected, actual, wallSeconds: (performance.now() - begin) / 1000 };
    fs.writeFileSync(path.join(dir, `candidate-${index}.json`), JSON.stringify({ ...result, actions, samples }));
    fs.appendFileSync(path.join(dir, 'episodes.jsonl'), JSON.stringify(result) + '\n');
    console.log(JSON.stringify(result));
    // Lexicographic objective: verified victory, stage, progress, fewer deaths, less time.
    const rank = [Number(result.fullGameClearVerified), maxStage, maxProgress, -deaths, -engine.frame];
    const better = !best || rank.some((v, i) => rank.slice(0, i).every((x, j) => x === best.rank[j]) && v > best.rank[i]);
    if (replayEqual && better) best = { rank, result };
    fs.writeFileSync(path.join(dir, 'results.json'), JSON.stringify({ completedCandidates: index + 1, best: best?.result || null }, null, 2));
    if (best) fs.writeFileSync(path.join(dir, 'best-policy.json'), JSON.stringify(best.result.config, null, 2));
    preflight.completedCandidates = index + 1;
    fs.writeFileSync(path.join(root, 'runs/preflight.json'), JSON.stringify(preflight, null, 2));
    buildReport();
  }
  Object.assign(preflight, { status: 'completed', fullGameClearVerified: !!best?.result.fullGameClearVerified });
  fs.writeFileSync(path.join(root, 'runs/preflight.json'), JSON.stringify(preflight, null, 2)); buildReport();
  console.log('RESULTS ' + dir);
}
if (require.main === module) { try { main(); } catch (error) { console.error(error.stack); process.exitCode = 1; } }
module.exports = { fingerprint, boot };
