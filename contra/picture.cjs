'use strict';
const fs = require('fs'), zlib = require('zlib');
function crc(bytes) { let c = 0xffffffff; for (const b of bytes) { c ^= b; for (let n = 0; n < 8; n++) c = (c >>> 1) ^ ((c & 1) ? 0xedb88320 : 0); } return (c ^ 0xffffffff) >>> 0; }
function chunk(type, data) { const body = Buffer.concat([Buffer.from(type), data]), out = Buffer.alloc(data.length + 12); out.writeUInt32BE(data.length); body.copy(out, 4); out.writeUInt32BE(crc(body), data.length + 8); return out; }
function picture(engine, file) {
  const raw = Buffer.alloc(240 * (256 * 3 + 1));
  for (let y = 0; y < 240; y++) for (let x = 0; x < 256; x++) { const c = engine.pixels[y * 256 + x], i = y * 769 + 1 + x * 3; raw[i] = c & 255; raw[i + 1] = c >> 8 & 255; raw[i + 2] = c >> 16 & 255; }
  const header = Buffer.alloc(13); header.writeUInt32BE(256); header.writeUInt32BE(240, 4); header[8] = 8; header[9] = 2;
  fs.writeFileSync(file, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', header), chunk('IDAT', zlib.deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]));
}
module.exports = { picture };
