// 3D progress viewer. Renders registered local tooth meshes when the engine
// supplies render links, otherwise schematic per-tooth proxies positioned from
// frames[].poses[]. Translation is exact and exaggerated for visibility (the
// caller shows the factor). PCA tooth frames are metadata only; rotation is
// applied only when the engine has marked the pose renderable.

import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { displacement, rotationApplications } from "./core.js";
import { toothPositions } from "./state.js";
import { parseStlGeometry } from "./stl.js";

const GHOST = new THREE.MeshStandardMaterial({ color: 0xc4d0d6, transparent: true, opacity: 0.45, roughness: 0.7 });
const PLANNED = new THREE.MeshStandardMaterial({ color: 0xf6f1e6, roughness: 0.62, metalness: 0.02 });
const ATTACHMENT = new THREE.MeshStandardMaterial({ color: 0xb45309 });
const ATTACHMENT_BOX = new THREE.BoxGeometry(0.9, 0.55, 0.45);
const LINE_MAT = new THREE.LineBasicMaterial({ color: 0x2563eb });
const meshGeometryCache = new Map();
const syntheticToothCache = new Map();

// Map an arch layout point (top-down screen coords) to a centered world point
// on the ground plane (XZ), Y up.
function basePosition(tooth) {
  const p = toothPositions[tooth];
  return p ? new THREE.Vector3((p[0] - 520) * 0.05, 0, (p[1] - 258) * 0.05) : null;
}

// pose translation (x mesiodistal-ish, y front-back, z occlusogingival/vertical)
// -> world (x, up=z, depth=y), times exaggeration.
function worldDelta(pose, exaggeration) {
  const d = displacement(pose, exaggeration);
  return new THREE.Vector3(d.x, d.z, d.y);
}

function worldOffset(offset = {}, exaggeration) {
  return new THREE.Vector3(
    (offset.x || 0) * exaggeration,
    (offset.z || 0) * exaggeration,
    (offset.y || 0) * exaggeration,
  );
}

function plannedQuaternion(pose, frame) {
  const quat = new THREE.Quaternion();
  for (const { axis, angleRad } of rotationApplications(pose, frame)) {
    const worldAxis = new THREE.Vector3(axis[0], axis[2], axis[1]).normalize();
    quat.multiply(new THREE.Quaternion().setFromAxisAngle(worldAxis, angleRad));
  }
  return quat;
}

export function createViewer(container) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  container.replaceChildren(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xfbfdfe);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
  camera.position.set(0, 42, 46);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const dir = new THREE.DirectionalLight(0xffffff, 0.65);
  dir.position.set(40, 80, 40);
  scene.add(dir);
  scene.add(new THREE.GridHelper(90, 18, 0xdbe3e7, 0xeef2f4));

  const proxies = new THREE.Group();
  scene.add(proxies);

  function resize() {
    const w = container.clientWidth || 1;
    const h = container.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();

  let running = true;
  (function loop() {
    if (!running) return;
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(loop);
  })();

  function update({ frames, toothFrames, attachments, initialOffsets, stageIndex, view, exaggeration }) {
    scene.background = new THREE.Color(document.body.dataset.theme === "dark" ? 0x111a1f : 0xfbfdfe);
    proxies.clear();
    const frame = frames && frames[stageIndex];
    if (!frame) return;
    const showCurrent = view === "current" || view === "overlay";
    const showPlanned = view === "planned" || view === "overlay";
    const activeAttachments = new Set((attachments || [])
      .filter((item) => stageIndex >= item.stage_start && (item.stage_end === null || stageIndex <= item.stage_end))
      .map((item) => item.tooth?.value));

    for (const pose of frame.poses) {
      const ideal = basePosition(pose.tooth);
      if (!ideal) continue;
      const base = ideal.clone().add(worldOffset(initialOffsets?.[pose.tooth], exaggeration));

      if (showCurrent) {
        const ghost = new THREE.Mesh(syntheticToothGeometry(pose.tooth), GHOST);
        ghost.position.copy(base);
        proxies.add(ghost);
      }
      if (showPlanned) {
        const moved = base.clone().add(worldDelta(pose, exaggeration));
        const geometry = meshGeometryCache.get(pose.tooth) || syntheticToothGeometry(pose.tooth);
        const mesh = new THREE.Mesh(geometry, PLANNED);
        mesh.position.copy(moved);
        mesh.quaternion.copy(plannedQuaternion(pose, toothFrames?.[pose.tooth]));
        proxies.add(mesh);

        if (activeAttachments.has(pose.tooth)) {
          const attachment = new THREE.Mesh(ATTACHMENT_BOX, ATTACHMENT);
          attachment.position.copy(moved).add(new THREE.Vector3(0, 0.35, 1.05));
          attachment.quaternion.copy(mesh.quaternion);
          proxies.add(attachment);
        }

        if (moved.distanceTo(base) > 0.2) {
          const geom = new THREE.BufferGeometry().setFromPoints([base, moved]);
          proxies.add(new THREE.Line(geom, LINE_MAT));
        }
      }
    }
    fitCameraToProxies();
  }

  function fitCameraToProxies() {
    if (!proxies.children.length) return;
    const box = new THREE.Box3().setFromObject(proxies);
    if (box.isEmpty()) return;
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z, 8);
    const fov = THREE.MathUtils.degToRad(camera.fov);
    const distance = Math.max(28, (maxDim / (2 * Math.tan(fov / 2))) * 1.35);
    camera.position.set(center.x, center.y + distance * 0.62, center.z + distance * 0.9);
    controls.target.copy(center);
    camera.near = Math.max(0.1, distance / 100);
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.update();
  }

  async function loadMeshes(renderMeshes = []) {
    let loaded = false;
    await Promise.all(renderMeshes.map(async (item) => {
      if (!item?.tooth || !item.url || meshGeometryCache.has(item.tooth)) return;
      const response = await fetch(item.url);
      if (!response.ok) return;
      const geometry = parseStlGeometry(await response.arrayBuffer());
      centerGeometry(geometry);
      meshGeometryCache.set(item.tooth, geometry);
      loaded = true;
    }));
    return loaded;
  }

  function dispose() {
    running = false;
    controls.dispose();
    renderer.dispose();
  }

  window.addEventListener("resize", resize);
  return { update, resize, dispose, loadMeshes };
}

function syntheticToothGeometry(tooth) {
  const key = toothKind(tooth);
  if (syntheticToothCache.has(key)) return syntheticToothCache.get(key);
  const group = new THREE.Group();
  const enamel = new THREE.MeshStandardMaterial({ color: 0xf6f1e6, roughness: 0.62, metalness: 0.02 });
  const cusp = new THREE.MeshStandardMaterial({ color: 0xfffbf0, roughness: 0.58, metalness: 0.02 });
  const profile = toothProfile(key);
  const crown = new THREE.Mesh(new THREE.SphereGeometry(1, 28, 18), enamel);
  crown.scale.set(profile.width, profile.height, profile.depth);
  crown.position.y = profile.height * 0.2;
  group.add(crown);

  for (const point of profile.cusps) {
    const bump = new THREE.Mesh(new THREE.SphereGeometry(0.33, 16, 10), cusp);
    bump.scale.set(point.sx, 0.34, point.sz);
    bump.position.set(point.x, profile.height * 0.9, point.z);
    group.add(bump);
  }

  const root = new THREE.Mesh(new THREE.ConeGeometry(profile.rootWidth, 1.35, 18), enamel);
  root.position.y = -profile.height * 0.85;
  root.rotation.x = Math.PI;
  root.scale.z = profile.rootDepth;
  group.add(root);

  const geometry = mergeGroupGeometry(group);
  geometry.rotateX(Math.PI / 2);
  geometry.computeVertexNormals();
  syntheticToothCache.set(key, geometry);
  return geometry;
}

function toothKind(tooth) {
  const digit = String(tooth).slice(-1);
  if (["1", "2"].includes(digit)) return "incisor";
  if (digit === "3") return "canine";
  if (["4", "5"].includes(digit)) return "premolar";
  return "molar";
}

function toothProfile(kind) {
  if (kind === "incisor") {
    return {
      width: 1.05,
      height: 1.35,
      depth: 0.7,
      rootWidth: 0.42,
      rootDepth: 0.72,
      cusps: [{ x: 0, z: 0, sx: 1.8, sz: 0.55 }],
    };
  }
  if (kind === "canine") {
    return {
      width: 1.05,
      height: 1.55,
      depth: 0.85,
      rootWidth: 0.46,
      rootDepth: 0.78,
      cusps: [{ x: 0, z: 0, sx: 0.85, sz: 0.85 }],
    };
  }
  if (kind === "premolar") {
    return {
      width: 1.18,
      height: 1.18,
      depth: 1.0,
      rootWidth: 0.48,
      rootDepth: 0.9,
      cusps: [{ x: -0.35, z: 0, sx: 0.7, sz: 0.75 }, { x: 0.35, z: 0, sx: 0.7, sz: 0.75 }],
    };
  }
  return {
    width: 1.45,
    height: 1.08,
    depth: 1.25,
    rootWidth: 0.58,
    rootDepth: 1.05,
    cusps: [
      { x: -0.42, z: -0.32, sx: 0.68, sz: 0.68 },
      { x: 0.42, z: -0.32, sx: 0.68, sz: 0.68 },
      { x: -0.42, z: 0.32, sx: 0.68, sz: 0.68 },
      { x: 0.42, z: 0.32, sx: 0.68, sz: 0.68 },
    ],
  };
}

function mergeGroupGeometry(group) {
  group.updateMatrixWorld(true);
  const geometries = [];
  group.traverse((child) => {
    if (!child.isMesh) return;
    const cloned = child.geometry.index ? child.geometry.toNonIndexed() : child.geometry.clone();
    cloned.applyMatrix4(child.matrixWorld);
    geometries.push(cloned);
  });
  const merged = new THREE.BufferGeometry();
  const positions = [];
  const normals = [];
  for (const geometry of geometries) {
    const position = geometry.getAttribute("position");
    const normal = geometry.getAttribute("normal");
    for (let i = 0; i < position.count; i += 1) {
      positions.push(position.getX(i), position.getY(i), position.getZ(i));
      normals.push(normal.getX(i), normal.getY(i), normal.getZ(i));
    }
  }
  merged.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  merged.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  return merged;
}

function centerGeometry(geometry) {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return;
  const center = new THREE.Vector3();
  box.getCenter(center);
  geometry.translate(-center.x, -center.y, -center.z);
}
