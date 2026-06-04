// 3D progress viewer. Renders schematic per-tooth proxies (not the real scanned
// mesh - we never store or serve mesh bytes) positioned from the engine's
// frames[].poses[]. Translation is exact and exaggerated for visibility (the
// caller shows the factor). PCA tooth frames are metadata only; rotation is
// applied only when the engine has marked the pose renderable.

import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { displacement, rotationApplications } from "./core.js";
import { toothPositions } from "./state.js";

const GHOST = new THREE.MeshStandardMaterial({ color: 0xc4d0d6, transparent: true, opacity: 0.45 });
const PLANNED = new THREE.MeshStandardMaterial({ color: 0x0f766e });
const BOX = new THREE.BoxGeometry(2.4, 3.2, 1.8);
const LINE_MAT = new THREE.LineBasicMaterial({ color: 0x2563eb });

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
  camera.position.set(0, 46, 52);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 4);

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

  function update({ frames, toothFrames, stageIndex, view, exaggeration }) {
    proxies.clear();
    const frame = frames && frames[stageIndex];
    if (!frame) return;
    const showCurrent = view === "current" || view === "overlay";
    const showPlanned = view === "planned" || view === "overlay";

    for (const pose of frame.poses) {
      const base = basePosition(pose.tooth);
      if (!base) continue;

      if (showCurrent) {
        const ghost = new THREE.Mesh(BOX, GHOST);
        ghost.position.copy(base);
        proxies.add(ghost);
      }
      if (showPlanned) {
        const moved = base.clone().add(worldDelta(pose, exaggeration));
        const mesh = new THREE.Mesh(BOX, PLANNED);
        mesh.position.copy(moved);
        mesh.quaternion.copy(plannedQuaternion(pose, toothFrames?.[pose.tooth]));
        proxies.add(mesh);

        if (moved.distanceTo(base) > 0.2) {
          const geom = new THREE.BufferGeometry().setFromPoints([base, moved]);
          proxies.add(new THREE.Line(geom, LINE_MAT));
        }
      }
    }
  }

  function dispose() {
    running = false;
    controls.dispose();
    renderer.dispose();
  }

  window.addEventListener("resize", resize);
  return { update, resize, dispose };
}
