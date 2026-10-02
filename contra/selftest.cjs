'use strict';
const assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
const { NES } = require('./core.cjs');
const { Engine, Policy, validateProfile, field } = require('./engine.js');
const { fingerprint } = require('./train.cjs');
// Original tiny 6502 program: latch controller A into RAM[0], count iterations in RAM[1].
function testROM() {
  const rom = Buffer.alloc(16 + 16384 + 8192);
  Buffer.from([0x4e, 0x45, 0x53, 0x1a, 1, 1]).copy(rom);
  const code = [0x78, 0xd8, 0xa2, 0xff, 0x9a, 0xa9, 0, 0x8d, 0, 0x20, 0x8d, 1, 0x20];
  const loop = 0x8000 + code.length;
  code.push(0xa9, 1, 0x8d, 0x16, 0x40, 0xa9, 0, 0x8d, 0x16, 0x40, 0xad, 0x16, 0x40, 0x29, 1, 0x85, 0, 0xe6, 1, 0x4c, loop & 255, loop >> 8);
  Buffer.from(code).copy(rom, 16);
  for (let offset = 0x3ffa; offset < 0x4000; offset += 2) { rom[16 + offset] = 0; rom[17 + offset] = 0x80; }
  return rom;
}
function main() {
  const rom = testROM(), engine = new Engine(NES, rom);
  for (let i = 0; i < 5; i++) engine.step(1);
  assert.equal(engine.ram()[0], 1, 'NES must receive button A');
  engine.step(0); assert.equal(engine.ram()[0], 0, 'NES must receive button release');
  const replay = new Engine(NES, rom);
  for (let i = 0; i < 5; i++) replay.step(1);
  replay.step(0);
  assert.deepEqual(fingerprint(engine), fingerprint(replay));
  assert.throws(() => validateProfile(require('./observation.template.json')), /校准/);
  assert.throws(() => field(engine.ram(), { address: 2048 }), /RAM/);
  const policy = new Policy(require('./policy.json'));
  assert.equal(policy.choose({ playing: false }), 0);
  assert.throws(() => policy.choose({ playing: true, mode: 'unknown' }), /未知关卡/);
  const masks = Array.from({ length: 150 }, (_, i) => policy.choose({ playing: true, mode: 'side', stage: 0, x: i, y: 10, progress: i }));
  assert(masks.some(m => m & 1) && masks.some(m => !(m & 1)), 'jump must be released');
  assert(masks.some(m => m & 2) && masks.some(m => !(m & 2)), 'fire must be released');
  assert(masks.every(m => !(m & 12)), 'policy must not submit START or SELECT');
  const result = { passed: true, scope: 'synthetic_original_nes_program_only', targetGameTested: false,
    inputDelivered: true, inputReleased: true, independentReplayEqual: true, uncalibratedProfileRejected: true,
    fingerprint: fingerprint(engine), createdAt: new Date().toISOString() };
  fs.mkdirSync(path.join(__dirname, 'runs'), { recursive: true });
  fs.writeFileSync(path.join(__dirname, 'runs/selftest.json'), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
}
if (require.main === module) main();
module.exports = { testROM };
