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

const GHOST = new THREE.MeshStandardMaterial({ color: 0xd9cbb6, transparent: true, opacity: 0.5, roughness: 0.72 });
const PLANNED = new THREE.MeshStandardMaterial({ color: 0xfff4df, roughness: 0.56, metalness: 0.01 });
// Highlight for the tooth currently selected for manual target authoring.
const SELECTED = new THREE.MeshStandardMaterial({ color: 0xfff4df, roughness: 0.5, emissive: 0x0f766e, emissiveIntensity: 0.55 });
// "Held still" teeth (the guided user unchecked them, so the engine fixes them):
// a muted blue-grey so it is obvious at a glance which teeth will not move.
const HELD = new THREE.MeshStandardMaterial({ color: 0x9fb2bd, roughness: 0.7, emissive: 0x1f3a45, emissiveIntensity: 0.2 });
const SCAN = new THREE.MeshPhysicalMaterial({
  color: 0xf6ead6,
  roughness: 0.38,
  metalness: 0,
  clearcoat: 0.18,
  clearcoatRoughness: 0.58,
  side: THREE.DoubleSide,
});
const ATTACHMENT = new THREE.MeshStandardMaterial({ color: 0xb45309 });
const ATTACHMENT_BOX = new THREE.BoxGeometry(0.9, 0.55, 0.45);
const LINE_MAT = new THREE.LineBasicMaterial({ color: 0x2563eb });
// Honest movement indicators for an un-segmented whole-arch scan: a small marker
// dot per tooth (the pickable, selection-aware target) plus an arrow showing
// where that tooth is planned to move. No fake crowns - the scan stays the teeth.
const MARKER = new THREE.MeshStandardMaterial({ color: 0x0f766e, roughness: 0.5, metalness: 0.0 });
const MARKER_GEO = new THREE.SphereGeometry(0.7, 16, 12);
const ARROW_MAT = new THREE.MeshBasicMaterial({ color: 0x2563eb });
const ARROW_HEAD = new THREE.ConeGeometry(0.5, 1.4, 12);
const ARROW_MIN_MM = 0.3; // below this displacement, show only the marker
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

// When the per-tooth proxies are anchored onto an uploaded scan, they are scaled
// up from their schematic size to read as crowns sitting on that scan (rather
// than tiny markers floating below it). This multiplies the per-arch fit scale;
// tune it if the anchored crowns look too large or too small on a real scan.
const ANCHOR_TOOTH_SCALE = 1.35;

function normalizeArch(arch = "") {
  const a = String(arch).toLowerCase();
  if (a === "upper" || a.includes("maxill")) return "upper";
  if (a === "lower" || a.includes("mandib")) return "lower";
  if (a.includes("top")) return "upper";
  if (a.includes("bottom")) return "lower";
  return null;
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

// A readable FDI tooth-number badge: white text on an accent pill, drawn from a
// 2D canvas texture and billboarded. depthTest off keeps it legible through the
// teeth/scan. Reused per update (cleared with the proxies group).
function makeToothNumberSprite(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 72;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "rgba(15,118,110,0.94)";
  const w = canvas.width;
  const h = canvas.height;
  const r = 22;
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(8, 8, w - 16, h - 16, r);
    ctx.fill();
  } else {
    ctx.fillRect(8, 8, w - 16, h - 16);
  }
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 44px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, w / 2, h / 2 + 2);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(3.4, 1.9, 1);
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

// Movement for meshes that live in SCAN-ORIENTED space (the segmented per-tooth
// fragments). orientScanGeometry rotates the scan by rotateX(-90), mapping a
// scan-local point (x, y, z) -> world (x, z, -y); applying the same map to a
// pose displacement keeps a fragment's motion consistent with the scan it was
// cut from (front-back is negated vs the schematic-proxy worldDelta).
function worldDeltaOriented(pose, exaggeration) {
  const d = displacement(pose, exaggeration);
  return new THREE.Vector3(d.x, d.z, -d.y);
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
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  container.replaceChildren(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xfbfdfe);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
  camera.position.set(0, 42, 46);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  // Manual tooth selection. Picking is enabled only when the host turns it on
  // (e.g. after scan units are confirmed). A pointer press that moves more than
  // a few pixels is an orbit drag, not a click, so it never steals selection
  // from OrbitControls.
  const raycaster = new THREE.Raycaster();
  let selectionEnabled = false;
  let selectedTooth = null;
  let onSelect = null;
  let pressX = 0;
  let pressY = 0;

  function pickToothAt(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    const ndc = new THREE.Vector2(
      ((event.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1,
      -((event.clientY - rect.top) / Math.max(rect.height, 1)) * 2 + 1,
    );
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObjects(proxies.children, false);
    for (const hit of hits) {
      const tooth = hit.object?.userData?.tooth;
      if (tooth) return tooth;
    }
    return null;
  }

  function onPointerDown(event) {
    pressX = event.clientX;
    pressY = event.clientY;
  }

  function onPointerUp(event) {
    if (!selectionEnabled || !onSelect) return;
    if (Math.hypot(event.clientX - pressX, event.clientY - pressY) > 5) return; // orbit drag
    const tooth = pickToothAt(event);
    if (tooth) onSelect(tooth);
  }

  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x8fa2ad, 0.78));
  scene.add(new THREE.AmbientLight(0xffffff, 0.36));
  const key = new THREE.DirectionalLight(0xfffbf2, 1.18);
  key.position.set(34, 58, 42);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xe4f2ff, 0.58);
  fill.position.set(-38, 26, -22);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xffffff, 0.48);
  rim.position.set(0, 24, -55);
  scene.add(rim);
  const grid = new THREE.GridHelper(90, 18, 0xd5dde2, 0xe8edf0);
  grid.material.transparent = true;
  grid.material.opacity = 0.52;
  scene.add(grid);

  // Persistent arch labels so the stacked maxillary/mandibular arches are
  // unambiguous (depthTest off keeps them readable through the teeth).
  const UPPER_LABEL_POS = new THREE.Vector3(0, ARCH.gapY + 5, 7);
  const LOWER_LABEL_POS = new THREE.Vector3(0, -ARCH.gapY - 5, 7);
  const upperLabel = makeTextSprite("Upper arch");
  upperLabel.position.copy(UPPER_LABEL_POS);
  scene.add(upperLabel);
  const lowerLabel = makeTextSprite("Lower arch");
  lowerLabel.position.copy(LOWER_LABEL_POS);
  scene.add(lowerLabel);

  const proxies = new THREE.Group();
  scene.add(proxies);
  const uploadedScans = new THREE.Group();
  scene.add(uploadedScans);
  // Per-tooth anchor points sampled from the uploaded scan surface, so the
  // moving proxies sit ON the scan's crowns instead of floating in the schematic
  // arch space below it. Recomputed whenever the scan changes; empty when no scan
  // is loaded (then proxies fall back to the schematic arch layout).
  let scanAnchors = new Map();
  // Where to float each arch's text label (over the scan when one is loaded).
  let archLabelPos = {};
  // Segmented per-tooth crown geometries, keyed by FDI value, in scan-oriented
  // space (NOT centered) so they assemble into the arch at their true positions.
  // Populated by loadToothFragments after the user applies segmentation; when
  // present the planned layer draws these real crowns moving instead of proxies.
  const fragmentCache = new Map();
  // Per-update line geometries are freshly allocated each rebuild (unlike the
  // cached tooth/box geometries) so they must be disposed explicitly - clearing
  // the group only detaches them and leaks their GPU buffers otherwise.
  let lineGeometries = [];
  // Tooth-number label sprites are cached by FDI value and reused across updates.
  // Each sprite owns a GPU texture; proxies.clear() only detaches it, so creating
  // a fresh sprite per update (every stage scrub / view toggle) would leak a
  // texture each time. Caching keeps exactly one sprite per tooth for the viewer's
  // lifetime; dispose() frees them.
  const toothLabelSprites = new Map();
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

  function update({ frames, toothFrames, attachments, initialOffsets, stageIndex, view, exaggeration, showToothLabels, excluded }) {
    scene.background = new THREE.Color(document.body.dataset.theme === "dark" ? 0x111a1f : 0xfbfdfe);
    uploadedScans.visible = view === "current" || view === "overlay";
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
    proxies.clear();
    positionArchLabels();
    const frame = frames && frames[stageIndex];
    if (!frame) return;
    const hasExactScan = uploadedScans.visible && uploadedScans.children.length > 0;
    // The scan itself is the baseline, so the translucent "current" ghost layer
    // is only the schematic fallback shown when there is no exact scan. The
    // planned proxies are anchored onto the scan (see computeScanAnchors), so
    // they read as the scan's own teeth being moved.
    const showCurrent = (view === "current" || view === "overlay") && !hasExactScan;
    const showPlanned = view === "planned" || view === "overlay";
    const excludedSet = new Set((excluded || []).map((tooth) => String(tooth)));
    // Fragment mode: the user applied segmentation, so real per-tooth crowns are
    // loaded. Draw THOSE moving at their true scan positions instead of schematic
    // proxies. The whole-arch shell stays as the static baseline (shown in
    // current/overlay, hidden in planned by the visibility rule above).
    const fragmentMode = fragmentCache.size > 0 && uploadedScans.children.length > 0;
    const scanBase = uploadedScans.position;
    // Arrow mode: a scan is loaded but NOT segmented, so there are no real crowns
    // to move. Rather than float synthetic peg crowns (which read as "the anchors
    // move, not the teeth"), mark each tooth on the scan and draw an arrow showing
    // its planned movement. Segmented scans use real crowns (fragmentMode); a
    // scan-less demo keeps the schematic proxies below.
    const arrowMode = !fragmentMode && scanAnchors.size > 0 && uploadedScans.children.length > 0;
    const activeAttachments = new Set((attachments || [])
      .filter((item) => stageIndex >= item.stage_start && (item.stage_end === null || stageIndex <= item.stage_end))
      .map((item) => item.tooth?.value));

    for (const pose of frame.poses) {
      // Real segmented crown moving at its true scan position (translation only;
      // per-tooth rotation needs a trusted oriented frame and is left to a later
      // pass). The fragment geometry already encodes the within-scan location, so
      // its base is just the scan's placement offset.
      if (fragmentMode) {
        const fragment = fragmentCache.get(String(pose.tooth));
        if (!fragment) continue; // no real crown for this tooth; shell covers it
        const fragBase = scanBase.clone();
        const fragMoved = showPlanned
          ? fragBase.clone().add(worldDeltaOriented(pose, exaggeration))
          : fragBase;
        if (showToothLabels) {
          let label = toothLabelSprites.get(pose.tooth);
          if (!label) {
            label = makeToothNumberSprite(String(pose.tooth));
            toothLabelSprites.set(pose.tooth, label);
          }
          label.position.copy(fragMoved).add(new THREE.Vector3(0, 2.4, 0));
          proxies.add(label);
        }
        if (showPlanned) {
          const material = excludedSet.has(String(pose.tooth))
            ? HELD
            : (selectedTooth === pose.tooth ? SELECTED : PLANNED);
          const crown = new THREE.Mesh(fragment, material);
          crown.position.copy(fragMoved);
          crown.userData.tooth = pose.tooth;
          proxies.add(crown);
          if (fragMoved.distanceTo(fragBase) > 0.2) {
            const geom = new THREE.BufferGeometry().setFromPoints([fragBase, fragMoved]);
            lineGeometries.push(geom);
            proxies.add(new THREE.Line(geom, LINE_MAT));
          }
        }
        continue;
      }

      // Un-segmented scan: a marker dot at the tooth + an arrow for its movement.
      if (arrowMode) {
        const spot = scanAnchors.get(String(pose.tooth));
        if (!spot) continue;
        const held = excludedSet.has(String(pose.tooth));
        const markerMat = held ? HELD : (selectedTooth === pose.tooth ? SELECTED : MARKER);
        const marker = new THREE.Mesh(MARKER_GEO, markerMat);
        marker.position.copy(spot.pos);
        marker.scale.set(spot.scale, spot.scale * 0.5, spot.scale);
        marker.userData.tooth = pose.tooth;
        proxies.add(marker);
        const delta = showPlanned && !held ? worldDeltaOriented(pose, exaggeration) : new THREE.Vector3();
        if (showToothLabels) {
          let label = toothLabelSprites.get(pose.tooth);
          if (!label) {
            label = makeToothNumberSprite(String(pose.tooth));
            toothLabelSprites.set(pose.tooth, label);
          }
          label.position.copy(spot.pos).add(delta).add(new THREE.Vector3(0, 2.4, 0));
          proxies.add(label);
        }
        if (delta.length() > ARROW_MIN_MM) addMovementArrow(spot.pos, delta);
        continue;
      }

      const anchor = scanAnchors.get(String(pose.tooth));
      const ideal = anchor ? anchor.pos.clone() : basePosition(pose.tooth);
      if (!ideal) continue;
      const proxyScale = anchor ? anchor.scale : 1;
      // The anchor (or schematic position) is the tooth's aligned/ideal spot; a
      // demo crowding offset shifts the start away from it, and the per-stage
      // movement (worldDelta) carries it back. Anchoring just moves that whole
      // start->end path onto the scan surface.
      const base = ideal.clone().add(worldOffset(initialOffsets?.[pose.tooth], exaggeration));

      if (showCurrent) {
        const ghostGeometry = meshGeometryCache.get(pose.tooth) || syntheticToothGeometry(pose.tooth);
        const ghost = new THREE.Mesh(ghostGeometry, GHOST);
        ghost.position.copy(base);
        ghost.scale.setScalar(proxyScale);
        ghost.quaternion.copy(archQuaternion(pose.tooth));
        ghost.userData.tooth = pose.tooth;
        proxies.add(ghost);
      }
      // Optional FDI tooth-number label, floating above the tooth at its
      // currently-displayed position, so a user can see which tooth is which.
      if (showToothLabels) {
        const labelAt = showPlanned ? base.clone().add(worldDelta(pose, exaggeration)) : base;
        let label = toothLabelSprites.get(pose.tooth);
        if (!label) {
          label = makeToothNumberSprite(String(pose.tooth));
          toothLabelSprites.set(pose.tooth, label);
        }
        label.position.copy(labelAt).add(new THREE.Vector3(0, 2.4, 0));
        proxies.add(label);
      }

      if (showPlanned) {
        const moved = base.clone().add(worldDelta(pose, exaggeration));
        const geometry = meshGeometryCache.get(pose.tooth) || syntheticToothGeometry(pose.tooth);
        const material = excludedSet.has(String(pose.tooth))
          ? HELD
          : (selectedTooth === pose.tooth ? SELECTED : PLANNED);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.copy(moved);
        mesh.scale.setScalar(proxyScale);
        mesh.quaternion.copy(archQuaternion(pose.tooth).multiply(plannedQuaternion(pose, toothFrames?.[pose.tooth])));
        mesh.userData.tooth = pose.tooth;
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

  function positionArchLabels() {
    upperLabel.position.copy(archLabelPos.upper || UPPER_LABEL_POS);
    lowerLabel.position.copy(archLabelPos.lower || LOWER_LABEL_POS);
  }

  // A blue shaft + cone arrowhead from `origin` along `delta` (movement vector).
  // The shaft geometry is per-update (tracked for disposal); the cone reuses a
  // shared geometry. Used by arrow mode to show planned movement on a scan.
  function addMovementArrow(origin, delta) {
    const tip = origin.clone().add(delta);
    const geom = new THREE.BufferGeometry().setFromPoints([origin, tip]);
    lineGeometries.push(geom);
    proxies.add(new THREE.Line(geom, LINE_MAT));
    const cone = new THREE.Mesh(ARROW_HEAD, ARROW_MAT);
    cone.position.copy(tip);
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.clone().normalize());
    cone.scale.setScalar(Math.min(Math.max(delta.length() * 0.18, 0.5), 2.0));
    proxies.add(cone);
  }

  // Sample one anchor point per tooth on the uploaded scan's occlusal surface so
  // the moving proxies sit on the real crowns. The schematic arch layout (which
  // has the correct RELATIVE tooth order/spread) is fitted into each scan arch's
  // world bounding box in x/z, then a vertical ray finds the scan surface height.
  // Result: proxies are attached to the scan teeth, not floating beneath them.
  function computeScanAnchors() {
    const anchors = new Map();
    archLabelPos = {};
    if (!uploadedScans.children.length) return anchors;
    uploadedScans.updateMatrixWorld(true);
    const ray = new THREE.Raycaster();
    for (const arch of ["upper", "lower"]) {
      const mesh = uploadedScans.children.find(
        (m) => (m.userData.arch || normalizeArch(m.name)) === arch,
      );
      if (!mesh) continue;
      anchorArchTeeth(arch, mesh, ray, anchors);
    }
    return anchors;
  }

  function anchorArchTeeth(arch, mesh, ray, anchors) {
    const teeth = Object.keys(toothPositions).filter((tooth) => archOf(tooth) === arch);
    const schematic = teeth.map((tooth) => ({ tooth, p: basePosition(tooth) })).filter((t) => t.p);
    if (!schematic.length) return;
    const sx = extent(schematic.map((t) => t.p.x));
    const sz = extent(schematic.map((t) => t.p.z));
    const box = new THREE.Box3().setFromObject(mesh);
    const center = box.getCenter(new THREE.Vector3());
    const scanHx = Math.max((box.max.x - box.min.x) / 2, 0.001);
    const scanHz = Math.max((box.max.z - box.min.z) / 2, 0.001);
    const up = arch === "upper";
    const scale = THREE.MathUtils.clamp((scanHx / sx.half) * ANCHOR_TOOTH_SCALE, 1, 4);
    for (const { tooth, p } of schematic) {
      const wx = center.x + ((p.x - sx.mid) / sx.half) * scanHx;
      const wz = center.z + ((p.z - sz.mid) / sz.half) * scanHz;
      ray.set(new THREE.Vector3(wx, box.max.y + 12, wz), new THREE.Vector3(0, -1, 0));
      const hits = ray.intersectObject(mesh, false);
      // Occlusal surface faces the opposing arch: lowest hit for the upper arch,
      // highest hit for the lower. Fall back to the box face if the ray misses.
      let y = hits.length ? (up ? hits[hits.length - 1].point.y : hits[0].point.y) : (up ? box.min.y : box.max.y);
      y += up ? -0.3 : 0.3; // sit slightly proud toward the bite
      anchors.set(String(tooth), { pos: new THREE.Vector3(wx, y, wz), scale });
    }
    // Float each label on the OUTSIDE (gingival side) of its arch - above the
    // upper, below the lower - so the two never collide in the bite gap or sit
    // on the crowns (which read as swapped).
    archLabelPos[arch] = new THREE.Vector3(center.x, up ? box.max.y + 5 : box.min.y - 5, box.max.z + 5);
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

  // Load segmented per-tooth crown fragments (from applied segmentation). Each
  // fragment STL carries the ORIGINAL scan-space triangles, so it is oriented
  // exactly like the scan (loadScanSources) and deliberately NOT centered - the
  // fragments then sit on the real crowns and, together, reconstruct the arch.
  async function loadToothFragments(fragments = []) {
    let loaded = false;
    await Promise.all(fragments.map(async (item) => {
      const tooth = item?.tooth != null ? String(item.tooth) : null;
      if (!tooth || !item.url || fragmentCache.has(tooth)) return;
      const response = await fetch(item.url);
      if (!response.ok) return;
      const geometry = parseStlGeometry(await response.arrayBuffer());
      orientScanGeometry(geometry);
      fragmentCache.set(tooth, geometry);
      loaded = true;
    }));
    return loaded;
  }

  async function loadScanSources(sources = []) {
    const scanSources = sources.filter((source) => source?.name?.toLowerCase().endsWith(".stl"));
    const key = scanSources.map(sourceKey).join("|");
    if (uploadedScans.userData.key === key) return { loaded: false, count: uploadedScans.children.length };
    uploadedScans.userData.key = key;
    // Per-tooth fragments belong to the previous scan/segmentation; drop them so
    // a new scan never renders stale crowns.
    fragmentCache.clear();
    uploadedScans.traverse((child) => {
      if (child.isMesh) child.geometry.dispose();
    });
    uploadedScans.clear();
    if (!scanSources.length) {
      scanAnchors = new Map();
      archLabelPos = {};
      return { loaded: false, count: 0 };
    }

    for (const source of scanSources) {
      const geometry = parseStlGeometry(await sourceBuffer(source));
      orientScanGeometry(geometry);
      const mesh = new THREE.Mesh(geometry, SCAN);
      mesh.name = source.name;
      mesh.userData.arch = normalizeArch(source.arch) || normalizeArch(source.name);
      uploadedScans.add(mesh);
    }

    const box = new THREE.Box3().setFromObject(uploadedScans);
    if (!box.isEmpty()) {
      const center = new THREE.Vector3();
      box.getCenter(center);
      uploadedScans.position.set(-center.x, -box.min.y + 0.6, -center.z);
    }
    // Anchor the per-tooth proxies onto the freshly placed scan surface so the
    // moving teeth ride the real crowns (see computeScanAnchors).
    scanAnchors = computeScanAnchors();
    fitted = false;
    return { loaded: true, count: uploadedScans.children.length };
  }

  function loadUploadedScans(files = []) {
    return loadScanSources(files.map((file) => ({ name: file.name, file })));
  }

  function setSelectionHandler(fn) {
    onSelect = fn;
  }

  function setSelectionEnabled(enabled) {
    selectionEnabled = Boolean(enabled);
    if (!selectionEnabled) selectedTooth = null;
  }

  // Records which tooth is highlighted. The highlight is applied on the next
  // update() rebuild, so callers that change selection should re-render.
  function setSelectedTooth(tooth) {
    selectedTooth = tooth || null;
  }

  function dispose() {
    running = false;
    renderer.domElement.removeEventListener("pointerdown", onPointerDown);
    renderer.domElement.removeEventListener("pointerup", onPointerUp);
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
    for (const sprite of toothLabelSprites.values()) {
      sprite.material.map?.dispose();
      sprite.material.dispose();
    }
    toothLabelSprites.clear();
    window.removeEventListener("resize", resize);
    controls.dispose();
    renderer.dispose();
  }

  window.addEventListener("resize", resize);
  return {
    update, resize, dispose, loadMeshes, loadToothFragments, loadScanSources, loadUploadedScans,
    zoomBy, recenter, setSelectionHandler, setSelectionEnabled, setSelectedTooth,
  };
}

function orientScanGeometry(geometry) {
  // OrthoCAD/STL exports commonly use Z as vertical height. Three.js uses Y as
  // up in this viewer, so rotate the scan into the dental floor plane:
  // source (x, y, z) -> world (x, z, -y).
  geometry.rotateX(-Math.PI / 2);
  geometry.computeVertexNormals();
  geometry.computeBoundingBox();
}

function sourceKey(source) {
  if (source.file) return `${source.name}:${source.file.size}:${source.file.lastModified}`;
  return `${source.name}:${source.url}`;
}

async function sourceBuffer(source) {
  if (source.file) return source.file.arrayBuffer();
  const response = await fetch(source.url);
  if (!response.ok) throw new Error(`could not load ${source.name}`);
  return response.arrayBuffer();
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

// Min/max/mid and half-span of a list of numbers (half clamped away from zero so
// it is safe to divide by when mapping schematic coords into a scan bounding box).
function extent(values) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, max, mid: (min + max) / 2, half: Math.max((max - min) / 2, 0.001) };
}

function centerGeometry(geometry) {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return;
  const center = new THREE.Vector3();
  box.getCenter(center);
  geometry.translate(-center.x, -center.y, -center.z);
}
