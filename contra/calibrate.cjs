'use strict';
const fs = require('fs'), path = require('path'), crypto = require('crypto'), assert = require('assert/strict');
const { NES, corePath } = require('./core.cjs'), { Engine, observe } = require('./engine.js');
const { picture } = require('./picture.cjs');
const root = __dirname, rom = fs.readFileSync(path.join(root, 'roms/contra.nes'));
const hash = (b, type = 'sha256') => crypto.createHash(type).update(b).digest('hex');
assert.equal(hash(rom, 'md5'), '7bdad8b4a7a56a634c9649d20bd3011b', 'Only the documented unmodified US ROM is supported');
const evidence = path.join(root, 'runs/calibration'); fs.mkdirSync(evidence, { recursive: true });
const profile = {
  verified: true, verificationScope: 'exact_ROM_source_mapping_plus_runtime_play_movement_death_gameover; stageTransition_and_victory_source_only',
  romSha256: hash(rom), coreSha256: hash(fs.readFileSync(corePath)), bootFrames: 120,
  startSequence: [{ mask: 8, frames: 1 }, { mask: 0, frames: 29 }, { mask: 8, frames: 1 }, { mask: 0, frames: 629 }],
  fields: { stage: { address: 0x30 }, progress: { address: 0x64, bytes: 2, endian: 'big' }, lives: { address: 0x32 },
    x: { address: 0x334 }, y: { address: 0x31a }, status: { address: 0x18 }, levelRoutine: { address: 0x2c },
    gameOverFlag: { address: 0x38 }, playerState: { address: 0x90 }, jumpStatus: { address: 0xa0, mask: 1 },
    barrierOpen: { address: 0x37, mask: 128 }, completions: { address: 0x31 }, bossDefeated: { address: 0x3b } },
  playing: { field: 'status', values: [5] }, terminal: { victory: { field: 'status', values: [6] }, gameOver: { field: 'gameOverFlag', values: [1] } },
  stageOrder: [0,1,2,3,4,5,6,7], stageModes: { 0:'side',1:'base',2:'vertical',3:'base',4:'side',5:'side',6:'side',7:'side' },
  evidence: { play: 'runs/calibration/play.json + play.png', death: 'runs/calibration/death.json + death.png', gameOver: 'runs/calibration/gameover.json + gameover.png',
    stageTransition: 'reference/ram.asm CURRENT_LEVEL; exact-ROM MD5 match. Source verified; runtime pending.',
    victory: 'reference/control-flow.md game_routine_06; exact-ROM MD5 match. Source verified; runtime pending.' }
};
function snapshot(engine, name) { picture(engine, path.join(evidence, name + '.png')); fs.writeFileSync(path.join(evidence, name + '.json'), JSON.stringify({ frame: engine.frame, observation: observe(engine, profile), ram: engine.ram() }, null, 2)); }
const engine = new Engine(NES, rom);
for (let f = 0; f < profile.bootFrames; f++) engine.step(0);
for (const a of profile.startSequence) for (let f = 0; f < a.frames; f++) engine.step(a.mask);
assert.equal(engine.ram()[0x18], 5); assert.equal(engine.ram()[0x2c], 4); assert.equal(engine.ram()[0x32], 2);
snapshot(engine, 'play');
const saved = engine.save(), startX = engine.ram()[0x334];
for (let f = 0; f < 20; f++) engine.step(128);
assert(engine.ram()[0x334] > startX); snapshot(engine, 'right');
engine.restore(saved);
let death = false, over = false;
for (let f = 0; f < 18000; f++) {
  engine.step(128);
  if (!death && engine.ram()[0x90] === 2) { death = true; snapshot(engine, 'death'); }
  if (engine.ram()[0x38] === 1) { over = true; snapshot(engine, 'gameover'); break; }
}
assert(death && over, 'Need observed natural death and game over');
const provenance = { romSource: 'https://github.com/VyperGroup/astroid-assets/blob/main/Contra.nes.zip',
  md5: hash(rom, 'md5'), sha256: profile.romSha256, sourceRepository: 'https://github.com/vermiceli/nes-contra-us',
  sourceCommit: '687d651c021fd7020f10d05b970ccb62663c94bd', coreSha256: profile.coreSha256,
  runtimeChecks: ['first_stage', 'three_lives_two_reserves', 'move_right', 'natural_death', 'game_over'], sourceOnlyChecks: ['stage_transition', 'final_victory'], createdAt: new Date().toISOString() };
fs.writeFileSync(path.join(evidence, 'provenance.json'), JSON.stringify(provenance, null, 2));
fs.writeFileSync(path.join(root, 'observation.json'), JSON.stringify(profile, null, 2));
console.log(JSON.stringify(provenance, null, 2));
