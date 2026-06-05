import * as THREE from "./vendor/three.module.js";

export function parseStlGeometry(buffer) {
  return looksBinary(buffer) ? parseBinaryStl(buffer) : parseAsciiStl(new TextDecoder().decode(buffer));
}

function looksBinary(buffer) {
  if (buffer.byteLength < 84) return false;
  const view = new DataView(buffer);
  const count = view.getUint32(80, true);
  return buffer.byteLength === 84 + count * 50;
}

function parseBinaryStl(buffer) {
  const view = new DataView(buffer);
  const count = view.getUint32(80, true);
  const positions = new Float32Array(count * 9);
  let sourceOffset = 84;
  let targetOffset = 0;
  for (let i = 0; i < count; i += 1) {
    sourceOffset += 12; // normal
    for (let vertex = 0; vertex < 3; vertex += 1) {
      positions[targetOffset++] = view.getFloat32(sourceOffset, true);
      positions[targetOffset++] = view.getFloat32(sourceOffset + 4, true);
      positions[targetOffset++] = view.getFloat32(sourceOffset + 8, true);
      sourceOffset += 12;
    }
    sourceOffset += 2;
  }
  return geometryFromPositions(positions);
}

function parseAsciiStl(text) {
  const values = [];
  for (const line of text.split(/\r?\n/)) {
    const parts = line.trim().split(/\s+/);
    if (parts[0] === "vertex" && parts.length >= 4) {
      values.push(Number(parts[1]), Number(parts[2]), Number(parts[3]));
    }
  }
  return geometryFromPositions(new Float32Array(values));
}

function geometryFromPositions(positions) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  return geometry;
}
