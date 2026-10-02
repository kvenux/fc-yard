(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Contra = api;
})(globalThis, function () {
  'use strict';
  const buttons = { A: 0, B: 1, SELECT: 2, START: 3, UP: 4, DOWN: 5, LEFT: 6, RIGHT: 7 };
  class Engine {
    constructor(NES, rom, onFrame = () => {}) {
      this.frame = 0;
      this.pixels = new Uint32Array(256 * 240);
      this.nes = new NES({ emulateSound: false, onFrame: pixels => {
        this.pixels.set(pixels); onFrame(pixels);
      }});
      this.nes.loadROM(rom);
    }
    step(mask = 0) {
      for (let i = 0; i < 8; i++) {
        if (mask & (1 << i)) this.nes.buttonDown(1, i);
        else this.nes.buttonUp(1, i);
        this.nes.buttonUp(2, i);
      }
      this.nes.frame(); this.frame++;
    }
    ram() { return Array.from(this.nes.cpu.mem.slice(0, 2048)); }
    save() { return JSON.parse(JSON.stringify({ frame: this.frame, state: this.nes.toJSON(), pixels: Array.from(this.pixels) })); }
    restore(saved) { this.nes.fromJSON(JSON.parse(JSON.stringify(saved.state))); this.frame = saved.frame; this.pixels.set(saved.pixels); }
  }
  function field(ram, spec) {
    if (!spec || !Number.isInteger(spec.address) || spec.address < 0 || spec.address + (spec.bytes || 1) > 2048)
      throw Error('观察字段缺少有效的 2 KB RAM 地址');
    const bytes = spec.bytes || 1;
    if (![1, 2, 3, 4].includes(bytes)) throw Error('观察字段 bytes 必须是 1–4');
    let value = 0;
    for (let i = 0; i < bytes; i++) value += ram[spec.address + i] * 256 ** (spec.endian === 'big' ? bytes - 1 - i : i);
    return spec.mask === undefined ? value : value & spec.mask;
  }
  function observe(engine, profile) {
    const ram = engine.ram(), out = {};
    for (const [key, spec] of Object.entries(profile.fields)) out[key] = field(ram, spec);
    out.victory = profile.terminal.victory.values.includes(out[profile.terminal.victory.field]);
    out.gameOver = profile.terminal.gameOver.values.includes(out[profile.terminal.gameOver.field]);
    out.playing = profile.playing.values.includes(out[profile.playing.field]);
    if (out.levelRoutine !== undefined) out.playing = out.playing && [4, 8].includes(out.levelRoutine);
    if (profile.fields.barrierOpen?.mask === 128) out.barrierOpen = out.barrierOpen ? 1 : 0;
    out.mode = profile.stageModes[String(out.stage)];
    out.frame = engine.frame;
    return out;
  }
  function validateProfile(profile) {
    if (profile.verified !== true || !/^[a-f0-9]{64}$/.test(profile.romSha256 || '') ||
        !/^[a-f0-9]{64}$/.test(profile.coreSha256 || '')) throw Error('需要已校准且绑定 ROM/模拟器 SHA256 的观察器');
    for (const key of ['stage', 'progress', 'lives', 'x', 'y', 'status']) {
      if (!profile.fields?.[key]) throw Error('缺少观察字段：' + key);
    }
    for (const spec of Object.values(profile.fields)) field(new Array(2048).fill(0), spec);
    for (const rule of [profile.playing, profile.terminal?.victory, profile.terminal?.gameOver]) {
      if (!rule || !profile.fields[rule.field] || !Array.isArray(rule.values) || !rule.values.length)
        throw Error('缺少经校准的游戏中/终局判定');
    }
    if (!Array.isArray(profile.stageOrder) || !profile.stageOrder.length || new Set(profile.stageOrder).size !== profile.stageOrder.length)
      throw Error('需要按实际 ROM 配置 stageOrder');
    for (const stage of profile.stageOrder) {
      if (!['side', 'base', 'vertical'].includes(profile.stageModes?.[String(stage)])) throw Error('关卡模式未配置：' + stage);
    }
    for (const key of ['play', 'death', 'stageTransition', 'gameOver', 'victory']) {
      if (typeof profile.evidence?.[key] !== 'string' || !profile.evidence[key].trim()) throw Error('缺少校准证据：' + key);
    }
    if (!Number.isInteger(profile.bootFrames) || profile.bootFrames < 1 || !Array.isArray(profile.startSequence) || !profile.startSequence.length)
      throw Error('缺少经过验证的开局按键流程');
    for (const action of profile.startSequence) {
      if (!Number.isInteger(action.mask) || action.mask < 0 || action.mask > 255 || !Number.isInteger(action.frames) || action.frames < 1)
        throw Error('开局按键流程无效');
    }
  }
  function validatePolicy(config) {
    for (const c of [config, ...Object.values(config.stagePolicies || {}).map(override => ({ ...config, ...override }))]) {
      for (const key of ['firePeriod', 'fireHold', 'jumpPeriod', 'jumpHold', 'stallFrames', 'sweepPeriod']) {
        if (!Number.isInteger(c[key]) || c[key] < 1) throw Error('策略参数无效：' + key);
      }
      if (c.fireHold >= c.firePeriod || c.jumpHold >= c.jumpPeriod) throw Error('射击/跳跃必须包含松开帧');
      if (!Number.isInteger(c.verticalCenter) || c.verticalCenter < 0 || c.verticalCenter > 255) throw Error('落点中心无效');
    }
  }
  class Policy {
    constructor(config) { validatePolicy(config); this.config = config; this.reason = ''; this.previous = null; this.stall = 0; this.tick = 0; }
    choose(o) {
      const c = { ...this.config, ...this.config.stagePolicies?.[String(o.stage)] };
      if (!o.playing || o.gameOver || o.victory) { this.reason = '等待游戏状态'; return 0; }
      if (o.playerState !== undefined && o.playerState !== 1) { this.reason = '等待角色落地或复活'; return 0; }
      if (!['side', 'base', 'vertical'].includes(o.mode)) throw Error('未知关卡，停止自动输入');
      if (this.previous && this.previous.stage === o.stage && this.previous.progress === o.progress && this.previous.x === o.x && this.previous.y === o.y) this.stall++;
      else this.stall = 0;
      this.previous = { ...o };
      const t = this.tick++;
      let mask = t % c.firePeriod < c.fireHold ? 2 : 0;
      const jump = t % c.jumpPeriod < c.jumpHold;
      if (o.mode === 'side') {
        mask |= 128; if (jump || this.stall >= c.stallFrames) mask |= 1;
        this.reason = this.stall >= c.stallFrames ? '受阻跳跃脱困' : jump ? '前进跳跃射击' : '向前推进，节奏射击';
      } else if (o.mode === 'base') {
        // Target status must be calibrated; absence means firing in place, not assuming an open barrier.
        if (o.barrierOpen === 1) { mask |= 16; this.reason = '屏障已打开，向纵深推进'; }
        else { if (t % c.sweepPeriod < c.sweepPeriod / 4) mask |= 64;
          else if (t % c.sweepPeriod >= c.sweepPeriod * 3 / 4) mask |= 128;
          this.reason = '横向调整射线，攻击屏障目标'; }
      } else {
        mask |= o.x < c.verticalCenter ? 128 : 64;
        if (jump || this.stall >= c.stallFrames) mask |= 1;
        if (o.targetAbove === 1) mask = (mask & ~192) | 16;
        this.reason = '跳跃向上推进，调整落点';
      }
      return mask;
    }
  }
  return { Engine, Policy, observe, validateProfile, validatePolicy, buttons, field };
});
