// 3D progress viewer. Renders registered local tooth meshes when the engine
// supplies render links, otherwise schematic per-tooth proxies positioned from
// frames[].poses[]. Translation is exact and exaggerated for visibility (the
// caller shows the factor). PCA tooth frames are metadata only; rotation is
// applied only when the engine has marked the pose renderable.

import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { displacement, rotationApplications, toothKind } from "./core.js";
import { toothPositions } from "./state.js";
import { parseStlGeometry } from "./stl.js";

const GHOST = new THREE.MeshStandardMaterial({ color: 0xc4d0d6, transparent: true, opacity: 0.45, roughness: 0.7 });
const PLANNED = new THREE.MeshStandardMaterial({ color: 0xf6f1e6, roughness: 0.62, metalness: 0.02 });
const SCAN = new THREE.MeshStandardMaterial({
  color: 0x8fd3c7,
  transparent: true,
  opacity: 0.62,
  roughness: 0.58,
  metalness: 0.01,
  side: THREE.DoubleSide,
});
const ATTACHMENT = new THREE.MeshStandardMaterial({ color: 0xb45309 });
const ATTACHMENT_BOX = new THREE.BoxGeometry(0.9, 0.55, 0.45);
const LINE_MAT = new THREE.LineBasicMaterial({ color: 0x2563eb });
const meshGeometryCache = new Map();
const meshUrlCache = new Map();
const syntheticToothCache = new Map();

// Dental-arch layout. Each FDI arch is laid out as a horseshoe on its own
// horizontal plane: the maxillary (upper) arch sits above the mandibular
// (lower) arch so the pair reads as a bite rather than two flat rows. The 2D
// arch coordinates (toothPositions) drive the mesiodistal (x) spread and the
// front-back (z) curve; the curve is amplified because depth is foreshortened
// from a front view.
const ARCH = {
  widthScale: 0.052,
  depthScale: 0.14,
  gapY: 1.5,
  upperCenterY: 102,
  lowerCenterY: 414,
};

function archOf(tooth) {
  const quadrant = String(tooth)[0];
  return quadrant === "1" || quadrant === "2" ? "upper" : "lower";
}

// Map an FDI tooth to a centered world point. Upper arch elevated (+y), lower
// arch lowered (-y). The default camera sits on +z, so anterior teeth are placed
// toward +z (nearest the camera) and molars toward -z, giving a natural anterior
// "smile" view with the arch opening away from the viewer.
function basePosition(tooth) {
  const p = toothPositions[tooth];
  if (!p) return null;
  const x = (p[0] - 520) * ARCH.widthScale;
  if (archOf(tooth) === "upper") {
    return new THREE.Vector3(x, ARCH.gapY, (ARCH.upperCenterY - p[1]) * ARCH.depthScale);
  }
  return new THREE.Vector3(x, -ARCH.gapY, (p[1] - ARCH.lowerCenterY) * ARCH.depthScale);
}

// Maxillary crowns point down toward the occlusal plane; mandibular crowns point
// up. Synthetic geometry is built crown-up (+y), so flip the upper arch.
function archQuaternion(tooth) {
  return archOf(tooth) === "upper"
    ? new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI)
    : new THREE.Quaternion();
}

// A small billboarded text label rendered from a 2D canvas texture.
function makeTextSprite(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.font = "bold 34px system-ui, sans-serif";
  ctx.fillStyle = "#8a99a3";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, 128, 34);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(9, 2.25, 1);
  return sprite;
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

  // Persistent arch labels so the stacked maxillary/mandibular arches are
  // unambiguous (depthTest off keeps them readable through the teeth).
  const upperLabel = makeTextSprite("Upper arch");
  upperLabel.position.set(0, ARCH.gapY + 5, 7);
  scene.add(upperLabel);
  const lowerLabel = makeTextSprite("Lower arch");
  lowerLabel.position.set(0, -ARCH.gapY - 5, 7);
  scene.add(lowerLabel);

  const proxies = new THREE.Group();
  scene.add(proxies);
  const uploadedScans = new THREE.Group();
  scene.add(uploadedScans);
  // Per-update line geometries are freshly allocated each rebuild (unlike the
  // cached tooth/box geometries) so they must be disposed explicitly - clearing
  // the group only detaches them and leaks their GPU buffers otherwise.
  let lineGeometries = [];
  // The camera frames the arch once, on first populated render. Later updates
  // (stage scrub, view toggle) must not yank a camera the user has panned or
  // zoomed; an explicit recenter() re-frames on demand.
  let fitted = false;

  function resize() {
    const w = container.clientWidth || 1;
    const h = container.clientHeight || 1;
    // updateStyle must stay on (the default): with it off the canvas keeps no
    // CSS size and renders at its drawing-buffer pixel size, which is
    // pixelRatio x larger than the container. On a retina display the canvas
    // then overflows to 2x size and the container (overflow:hidden) shows only
    // the top-left quadrant, pushing the centered scene into a corner.
    renderer.setSize(w, h);
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
    uploadedScans.visible = view === "current" || view === "overlay";
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
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
        const ghostGeometry = meshGeometryCache.get(pose.tooth) || syntheticToothGeometry(pose.tooth);
        const ghost = new THREE.Mesh(ghostGeometry, GHOST);
        ghost.position.copy(base);
        ghost.quaternion.copy(archQuaternion(pose.tooth));
        proxies.add(ghost);
      }
      if (showPlanned) {
        const moved = base.clone().add(worldDelta(pose, exaggeration));
        const geometry = meshGeometryCache.get(pose.tooth) || syntheticToothGeometry(pose.tooth);
        const mesh = new THREE.Mesh(geometry, PLANNED);
        mesh.position.copy(moved);
        mesh.quaternion.copy(archQuaternion(pose.tooth).multiply(plannedQuaternion(pose, toothFrames?.[pose.tooth])));
        proxies.add(mesh);

        if (activeAttachments.has(pose.tooth)) {
          const attachment = new THREE.Mesh(ATTACHMENT_BOX, ATTACHMENT);
          attachment.position.copy(moved).add(new THREE.Vector3(0, 0.35, 1.05));
          attachment.quaternion.copy(mesh.quaternion);
          proxies.add(attachment);
        }

        if (moved.distanceTo(base) > 0.2) {
          const geom = new THREE.BufferGeometry().setFromPoints([base, moved]);
          lineGeometries.push(geom);
          proxies.add(new THREE.Line(geom, LINE_MAT));
        }
      }
    }
    if (!fitted) {
      fitCameraToScene();
      fitted = true;
    }
  }

  function fitCameraToScene() {
    const fitTarget = new THREE.Group();
    if (uploadedScans.visible && uploadedScans.children.length) fitTarget.add(uploadedScans.clone());
    if (proxies.children.length) fitTarget.add(proxies.clone());
    if (!fitTarget.children.length) return;
    const box = new THREE.Box3().setFromObject(fitTarget);
    if (box.isEmpty()) return;
    // Fit a bounding sphere using the limiting (narrower) of the vertical and
    // horizontal field of view so a wide dental arch is fully framed and
    // centered regardless of the viewport aspect ratio.
    const sphere = new THREE.Sphere();
    box.getBoundingSphere(sphere);
    const center = sphere.center;
    const radius = Math.max(sphere.radius, 4);
    const fovV = THREE.MathUtils.degToRad(camera.fov);
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * Math.max(camera.aspect, 0.0001));
    const distance = Math.max(24, (radius / Math.sin(Math.min(fovV, fovH) / 2)) * 1.1);
    // ~42 deg elevation: high enough to read the arch horseshoe, low enough to
    // still face the crowns.
    camera.position.set(center.x, center.y + distance * 0.7, center.z + distance * 0.74);
    controls.target.copy(center);
    camera.near = Math.max(0.1, distance / 100);
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.update();
  }

  // Dolly the camera toward (factor < 1) or away from (factor > 1) the target,
  // clamped so the user cannot zoom through the teeth or out to infinity.
  function zoomBy(factor) {
    const offset = camera.position.clone().sub(controls.target);
    const length = Math.min(Math.max(offset.length() * factor, 6), 4000);
    camera.position.copy(controls.target.clone().add(offset.setLength(length)));
    camera.updateProjectionMatrix();
    controls.update();
  }

  function recenter() {
    fitCameraToScene();
  }

  async function loadMeshes(renderMeshes = []) {
    let loaded = false;
    await Promise.all(renderMeshes.map(async (item) => {
      if (!item?.tooth || !item.url || meshGeometryCache.has(item.tooth)) return;
      // Reuse a parsed geometry across teeth that share a URL (e.g. demo crowns
      // grouped by tooth class) so identical meshes are fetched once.
      let geometry = meshUrlCache.get(item.url);
      if (!geometry) {
        const response = await fetch(item.url);
        if (!response.ok) return;
        geometry = parseStlGeometry(await response.arrayBuffer());
        centerGeometry(geometry);
        meshUrlCache.set(item.url, geometry);
      }
      meshGeometryCache.set(item.tooth, geometry);
      loaded = true;
    }));
    return loaded;
  }

  async function loadUploadedScans(files = []) {
    const scanFiles = files.filter((file) => file?.name?.toLowerCase().endsWith(".stl"));
    const key = scanFiles.map((file) => `${file.name}:${file.size}:${file.lastModified}`).join("|");
    if (uploadedScans.userData.key === key) return { loaded: false, count: uploadedScans.children.length };
    uploadedScans.userData.key = key;
    uploadedScans.traverse((child) => {
      if (child.isMesh) child.geometry.dispose();
    });
    uploadedScans.clear();
    if (!scanFiles.length) return { loaded: false, count: 0 };

    for (const file of scanFiles) {
      const geometry = parseStlGeometry(await file.arrayBuffer());
      const mesh = new THREE.Mesh(geometry, SCAN);
      mesh.name = file.name;
      uploadedScans.add(mesh);
    }

    const box = new THREE.Box3().setFromObject(uploadedScans);
    if (!box.isEmpty()) {
      const center = new THREE.Vector3();
      box.getCenter(center);
      uploadedScans.position.set(-center.x, -center.y, -center.z);
    }
    fitted = false;
    return { loaded: true, count: uploadedScans.children.length };
  }

  function dispose() {
    running = false;
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
    window.removeEventListener("resize", resize);
    controls.dispose();
    renderer.dispose();
  }

  window.addEventListener("resize", resize);
  return { update, resize, dispose, loadMeshes, loadUploadedScans, zoomBy, recenter };
}

// A material placeholder: mergeGroupGeometry only copies position/normal, so the
// per-part material is irrelevant - the render material (GHOST/PLANNED) is set
// on the final mesh. Built crown-up (+y), root-down; the caller orients per arch.
const TOOTH_MAT = new THREE.MeshBasicMaterial();

function syntheticToothGeometry(tooth) {
  const key = toothKind(tooth);
  if (syntheticToothCache.has(key)) return syntheticToothCache.get(key);
  const p = toothProfile(key);
  const group = new THREE.Group();

  // Crown: a tapered prism. CylinderGeometry(topR, bottomR, height, sides) gives
  // the natural occlusal->cervical taper; 4 sides reads as a boxy crown (incisor,
  // molar), more sides round it (premolar). Scaled to mesiodistal width and
  // buccolingual depth so each tooth class has a distinct silhouette.
  const crown = new THREE.Mesh(
    new THREE.CylinderGeometry(p.crownTop, p.crownNeck, p.crownHeight, p.sides),
    TOOTH_MAT,
  );
  if (p.sides === 4) crown.rotation.y = Math.PI / 4; // align flats mesiodistally
  crown.scale.set(p.width, 1, p.depth);
  crown.position.y = p.crownHeight / 2;
  group.add(crown);

  // Occlusal anatomy: a flat incisal edge (incisor) or pointed cusps.
  for (const c of p.cusps) {
    const cusp = new THREE.Mesh(new THREE.ConeGeometry(c.r, c.h, c.flat ? 4 : 12), TOOTH_MAT);
    if (c.flat) cusp.rotation.y = Math.PI / 4;
    cusp.scale.set(c.sx ?? 1, 1, c.sz ?? 1);
    cusp.position.set((c.x ?? 0) * p.width, p.crownHeight - (c.sink ?? 0) + c.h / 2, (c.z ?? 0) * p.depth);
    group.add(cusp);
  }

  // Root: a single tapering cone (multi-root teeth simplified) below the neck.
  const root = new THREE.Mesh(
    new THREE.CylinderGeometry(p.crownNeck * 0.92, p.rootTip, p.rootHeight, 12),
    TOOTH_MAT,
  );
  root.scale.set(p.width * 0.86, 1, p.depth * 0.86);
  root.position.y = -p.rootHeight / 2;
  group.add(root);

  const geometry = mergeGroupGeometry(group);
  geometry.computeVertexNormals();
  syntheticToothCache.set(key, geometry);
  return geometry;
}

// Per-class crown/root proportions. width = mesiodistal, depth = buccolingual.
// crownTop/crownNeck are the prism radii (occlusal vs cervical); cusp x/z are
// fractions of width/depth so they track crown size.
// Cusps are deliberately short, rounded bumps (not tall cones) and crowns use
// rounder prisms so the schematic fallback reads as teeth, not spikes.
function toothProfile(kind) {
  if (kind === "incisor") {
    // Rounded chisel blade: wide mesiodistally, shallow buccolingually, soft edge.
    return {
      sides: 8, width: 1.15, depth: 0.55, crownTop: 1.0, crownNeck: 0.7, crownHeight: 1.4,
      rootTip: 0.12, rootHeight: 1.7,
      cusps: [{ x: 0, z: 0, r: 0.95, h: 0.14, flat: true, sx: 1.0, sz: 0.55, sink: 0.06 }],
    };
  }
  if (kind === "canine") {
    // Single rounded cusp on a tapering crown (a soft point, not a spike).
    return {
      sides: 8, width: 1.0, depth: 0.85, crownTop: 0.78, crownNeck: 0.7, crownHeight: 1.45,
      rootTip: 0.12, rootHeight: 1.9,
      cusps: [{ x: 0, z: 0, r: 0.62, h: 0.32, sink: 0.16 }],
    };
  }
  if (kind === "premolar") {
    // Oval occlusal table with two low cusps (buccal + lingual).
    return {
      sides: 10, width: 1.1, depth: 1.0, crownTop: 0.85, crownNeck: 0.7, crownHeight: 1.1,
      rootTip: 0.12, rootHeight: 1.7,
      cusps: [
        { x: 0, z: -0.28, r: 0.4, h: 0.22, sink: 0.12 },
        { x: 0, z: 0.28, r: 0.4, h: 0.22, sink: 0.12 },
      ],
    };
  }
  return { // molar: broad rounded crown with four low cusps
    sides: 8, width: 1.5, depth: 1.35, crownTop: 1.0, crownNeck: 0.78, crownHeight: 1.0,
    rootTip: 0.12, rootHeight: 1.6,
    cusps: [
      { x: -0.32, z: -0.3, r: 0.4, h: 0.2, sink: 0.1 },
      { x: 0.32, z: -0.3, r: 0.4, h: 0.2, sink: 0.1 },
      { x: -0.32, z: 0.3, r: 0.4, h: 0.2, sink: 0.1 },
      { x: 0.32, z: 0.3, r: 0.4, h: 0.2, sink: 0.1 },
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
