const VERSION = 5;
const SIZE = 17 + VERSION * 4;
const DATA_CODEWORDS = 108;
const ECC_CODEWORDS = 26;

export function qrSvg(payload, { moduleSize = 4, quiet = 4 } = {}) {
  const modules = makeQrModules(String(payload));
  const fullSize = (SIZE + quiet * 2) * moduleSize;
  const cells = [];
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      if (modules[y][x]) {
        cells.push(`M${(x + quiet) * moduleSize} ${(y + quiet) * moduleSize}h${moduleSize}v${moduleSize}h-${moduleSize}z`);
      }
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${fullSize} ${fullSize}" role="img" aria-label="Case handoff QR code"><rect width="100%" height="100%" fill="#fff"/><path fill="#111" d="${cells.join("")}"/></svg>`;
}

export function makeQrModules(payload) {
  const data = encodeData(payload);
  const ecc = reedSolomon(data, ECC_CODEWORDS);
  const bits = [...data, ...ecc].flatMap((byte) => byteBits(byte));
  const modules = Array.from({ length: SIZE }, () => Array(SIZE).fill(false));
  const reserved = Array.from({ length: SIZE }, () => Array(SIZE).fill(false));
  drawFunctionPatterns(modules, reserved);
  placeDataBits(modules, reserved, bits);
  drawFormatBits(modules, reserved);
  return modules;
}

function encodeData(payload) {
  const bytes = new TextEncoder().encode(payload);
  if (bytes.length > DATA_CODEWORDS - 2) {
    throw new Error("QR payload is too long for the handoff code");
  }
  const bits = [0, 1, 0, 0, ...byteBits(bytes.length)];
  for (const byte of bytes) bits.push(...byteBits(byte));
  bits.push(...Array(Math.min(4, DATA_CODEWORDS * 8 - bits.length)).fill(0));
  while (bits.length % 8) bits.push(0);
  const out = [];
  for (let i = 0; i < bits.length; i += 8) out.push(bitsToByte(bits.slice(i, i + 8)));
  for (let pad = 0; out.length < DATA_CODEWORDS; pad += 1) out.push(pad % 2 === 0 ? 0xec : 0x11);
  return out;
}

function drawFunctionPatterns(modules, reserved) {
  drawFinder(modules, reserved, 0, 0);
  drawFinder(modules, reserved, SIZE - 7, 0);
  drawFinder(modules, reserved, 0, SIZE - 7);
  drawAlignment(modules, reserved, SIZE - 7, SIZE - 7);
  for (let i = 8; i < SIZE - 8; i += 1) {
    set(modules, reserved, i, 6, i % 2 === 0);
    set(modules, reserved, 6, i, i % 2 === 0);
  }
  set(modules, reserved, 8, 4 * VERSION + 9, true);
  for (let i = 0; i < 9; i += 1) {
    reserve(reserved, 8, i);
    reserve(reserved, i, 8);
    reserve(reserved, SIZE - 1 - i, 8);
    reserve(reserved, 8, SIZE - 1 - i);
  }
}

function drawFinder(modules, reserved, x0, y0) {
  for (let y = -1; y <= 7; y += 1) {
    for (let x = -1; x <= 7; x += 1) {
      const xx = x0 + x;
      const yy = y0 + y;
      if (xx < 0 || yy < 0 || xx >= SIZE || yy >= SIZE) continue;
      const dark = x >= 0 && x <= 6 && y >= 0 && y <= 6 && (x === 0 || x === 6 || y === 0 || y === 6 || (x >= 2 && x <= 4 && y >= 2 && y <= 4));
      set(modules, reserved, xx, yy, dark);
    }
  }
}

function drawAlignment(modules, reserved, cx, cy) {
  for (let y = -2; y <= 2; y += 1) {
    for (let x = -2; x <= 2; x += 1) {
      set(modules, reserved, cx + x, cy + y, Math.max(Math.abs(x), Math.abs(y)) !== 1);
    }
  }
}

function placeDataBits(modules, reserved, bits) {
  let bitIndex = 0;
  let upward = true;
  for (let right = SIZE - 1; right >= 1; right -= 2) {
    if (right === 6) right -= 1;
    for (let vert = 0; vert < SIZE; vert += 1) {
      const y = upward ? SIZE - 1 - vert : vert;
      for (let dx = 0; dx < 2; dx += 1) {
        const x = right - dx;
        if (reserved[y][x]) continue;
        const bit = bitIndex < bits.length ? bits[bitIndex] === 1 : false;
        modules[y][x] = bit !== ((x + y) % 2 === 0);
        bitIndex += 1;
      }
    }
    upward = !upward;
  }
}

function drawFormatBits(modules) {
  const bits = formatBits();
  for (let i = 0; i <= 5; i += 1) modules[i][8] = bit(bits, i);
  modules[7][8] = bit(bits, 6);
  modules[8][8] = bit(bits, 7);
  modules[8][7] = bit(bits, 8);
  for (let i = 9; i < 15; i += 1) modules[14 - i][8] = bit(bits, i);
  for (let i = 0; i < 8; i += 1) modules[8][SIZE - 1 - i] = bit(bits, i);
  for (let i = 8; i < 15; i += 1) modules[SIZE - 15 + i][8] = bit(bits, i);
}

function formatBits() {
  let value = 0b01000 << 10;
  const generator = 0b10100110111;
  for (let i = 14; i >= 10; i -= 1) {
    if (((value >> i) & 1) === 1) value ^= generator << (i - 10);
  }
  return (((0b01000 << 10) | value) ^ 0b101010000010010) & 0x7fff;
}

function reedSolomon(data, degree) {
  const generator = rsGenerator(degree);
  const result = Array(degree).fill(0);
  for (const byte of data) {
    const factor = byte ^ result.shift();
    result.push(0);
    for (let i = 0; i < degree; i += 1) result[i] ^= gfMul(generator[i + 1], factor);
  }
  return result;
}

function rsGenerator(degree) {
  let poly = [1];
  for (let i = 0; i < degree; i += 1) {
    const next = Array(poly.length + 1).fill(0);
    for (let j = 0; j < poly.length; j += 1) {
      next[j] ^= poly[j];
      next[j + 1] ^= gfMul(poly[j], gfPow(i));
    }
    poly = next;
  }
  return poly;
}

function gfPow(power) {
  let value = 1;
  for (let i = 0; i < power; i += 1) value = gfMul(value, 2);
  return value;
}

function gfMul(a, b) {
  let result = 0;
  for (let i = 0; i < 8; i += 1) {
    if ((b & 1) !== 0) result ^= a;
    const high = (a & 0x80) !== 0;
    a = (a << 1) & 0xff;
    if (high) a ^= 0x1d;
    b >>= 1;
  }
  return result;
}

function set(modules, reserved, x, y, value) {
  modules[y][x] = value;
  reserved[y][x] = true;
}

function reserve(reserved, x, y) {
  if (x >= 0 && y >= 0 && x < SIZE && y < SIZE) reserved[y][x] = true;
}

function byteBits(byte) {
  return Array.from({ length: 8 }, (_, i) => (byte >> (7 - i)) & 1);
}

function bitsToByte(bits) {
  return bits.reduce((acc, b) => (acc << 1) | b, 0);
}

function bit(value, index) {
  return ((value >> index) & 1) === 1;
}
