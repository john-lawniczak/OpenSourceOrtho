// Illustrative permanent-tooth forms, not patient anatomy or measurement meshes.
// Smooth crown walls and continuous occlusal surfaces replace stacked primitives.
import * as THREE from "./vendor/three.module.js";
import { toothKind } from "./core.js";

const cache = new Map();
const SIDES = 48;

export function toothProfile(tooth) {
  const kind = toothKind(tooth);
  const upper = Number(String(tooth)[0]) < 3;
  const position = Number(String(tooth)[1]);
  const profiles = {
    incisor: { width: 1.22, depth: .74, height: 2.1, root: 2.3, power: .52 },
    canine: { width: 1.02, depth: .96, height: 1.95, root: 2.8, power: .9 },
    premolar: { width: 1.12, depth: 1.18, height: 1.55, root: 2.1, power: .85 },
    molar: { width: 1.58, depth: 1.42, height: 1.4, root: 2.0, power: .65 },
  };
  const profile = { ...profiles[kind], kind, upper, roots: 1 };
  if (kind === "incisor") {
    profile.width *= upper ? (position === 2 ? .76 : 1) : (position === 1 ? .59 : .66);
    if (position === 2) { profile.height *= .91; profile.power = .75; }
    if (!upper) profile.depth *= .84;
  }
  if (kind === "molar") profile.roots = upper ? 3 : 2;
  if (kind === "premolar" && upper && position === 4) profile.roots = 2;
  if (position === 8) { profile.width *= .9; profile.depth *= .9; }
  return profile;
}

export function syntheticToothGeometry(tooth, includeRoots = true) {
  const p = toothProfile(tooth);
  const key = JSON.stringify([p, includeRoots]);
  if (cache.has(key)) return cache.get(key);
  const vertices = [], indices = [];
  addCrown(vertices, indices, p);
  if (includeRoots) {
    for (let root = 0; root < p.roots; root++) addRoot(vertices, indices, p, root);
  } else {
    // Close the cervical surface in the crown-only map.
    const center = vertices.length / 3;
    vertices.push(0, 0, 0);
    for (let i = 0; i < SIDES; i++) indices.push(center, i, i + 1);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
  cache.set(key, geometry);
  return geometry;
}

const signedPower = (value, power) => Math.sign(value) * Math.abs(value) ** power;
const bump = (x, z, cx, cz, width) => Math.exp(-((x - cx) ** 2 + (z - cz) ** 2) / width);

function chewingSurface(x, z, p) {
  if (p.kind === "incisor") return .05 - .09 * Math.abs(x) ** 4;
  if (p.kind === "canine") return .63 * bump(x, z, -.08, -.1, .25);
  if (p.kind === "premolar") {
    return .38 * bump(x, z, 0, -.48, .15) + .3 * bump(x, z, 0, .48, .16);
  }
  // Broad rounded cusps leave intersecting grooves through the occlusal table.
  return [[-.44, -.42, .32], [.44, -.42, .36], [-.44, .42, .28], [.44, .42, .3]]
    .reduce((height, [cx, cz, rise]) => height + rise * bump(x, z, cx, cz, .12), .015);
}

function addCrown(vertices, indices, p) {
  const wallRings = 20, capRings = 16;
  const start = vertices.length / 3;
  for (let row = 0; row <= wallRings + capRings; row++) {
    const cap = row > wallRings;
    const t = Math.min(row / wallRings, 1);
    const radius = cap ? .86 * (1 - (row - wallRings) / capRings)
      : .64 + .22 * t + .19 * Math.sin(t * Math.PI);
    const blade = p.kind === "incisor" ? 1 - .76 * t ** 2 : 1;
    for (let col = 0; col <= SIDES; col++) {
      const angle = col / SIDES * Math.PI * 2;
      const x = signedPower(Math.cos(angle), p.power) * radius;
      const z = signedPower(Math.sin(angle), p.power) * radius;
      const y = t * p.height + chewingSurface(x, z, p) * t ** 6;
      vertices.push(x * p.width, y, z * p.depth * blade);
    }
  }
  // Winding follows crown-up geometry. The radial cap closes at its center.
  connectRings(indices, start, wallRings + capRings, true);
}

function addRoot(vertices, indices, p, root) {
  const rings = 24, start = vertices.length / 3;
  const angle = p.roots === 2 ? root * Math.PI : root * Math.PI * 2 / p.roots + .5;
  const spread = p.roots === 1 ? 0 : .45;
  const radius = p.roots === 1 ? .63 : .36;
  for (let row = 0; row <= rings; row++) {
    const t = row / rings;
    const taper = radius * (1 - t) ** .62;
    const diverge = spread * (.55 + .8 * Math.sin(t * Math.PI / 2));
    const curve = .16 * t ** 2;
    for (let col = 0; col <= SIDES; col++) {
      const theta = col / SIDES * Math.PI * 2;
      vertices.push(
        (Math.cos(theta) * taper + Math.cos(angle) * diverge + curve) * p.width,
        -t * p.root,
        (Math.sin(theta) * taper + Math.sin(angle) * diverge) * p.depth,
      );
    }
  }
  connectRings(indices, start, rings, false);
}

function connectRings(indices, start, rings, reverse) {
  for (let row = 0; row < rings; row++) {
    for (let col = 0; col < SIDES; col++) {
      const a = start + row * (SIDES + 1) + col;
      const b = a + SIDES + 1;
      if (reverse) indices.push(a, b, a + 1, b, b + 1, a + 1);
      else indices.push(a, a + 1, b, b, a + 1, b + 1);
    }
  }
}

// Independent arch layout for the reference map; never used for patient poses.
export function schematicToothPose(tooth) {
  const p = toothProfile(tooth);
  const position = Number(String(tooth)[1]);
  const side = ["1", "4"].includes(String(tooth)[0]) ? -1 : 1;
  const angles = p.upper ? [.075, .23, .4, .59, .79, 1.03, 1.29, 1.56]
    : [.06, .19, .35, .54, .75, .99, 1.25, 1.52];
  const angle = side * angles[position - 1];
  return { x: 13 * Math.sin(angle), y: p.upper ? 4.4 : -4.4,
    z: 15 * Math.cos(angle) - 7, angle };
}
