import { sourceViewContext, visibleScanView } from "./scan_source_orientation.js";
import { frameScanView } from "./scan_view_camera.js";
import { mountScanViewToolbar } from "./scan_view_toolbar.js";
import { orientedMeshMatrix } from "./mesh_affine.js";
import { createFragmentLoader } from "./viewer_fragments.js";
import { schematicToothPose, syntheticToothGeometry } from "./tooth_geometry.js";
// 3D progress viewer. Renders registered local tooth meshes when the engine
// supplies render links, otherwise schematic per-tooth proxies positioned from
// frames[].poses[]. Translation is exact and exaggerated for visibility (the
// caller shows the factor). PCA tooth frames are metadata only; rotation is
// applied only when the engine has marked the pose renderable.

import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { displacement, rotationApplications } from "./core.js";
import { toothPositions } from "./state.js";
import { buildScanObject, isSupportedScanName, parseScanGeometry } from "./scan_geometry.js";
import { createViewerScaleBar } from "./viewer_scale_bar.js";
import { mountViewerNavigation } from "./viewer_navigation.js";
import { arrangeScanArches, archDisplayMatrix } from "./viewer_arch_layout.js";
import { makeTextSprite, makeToothNumberSprite } from "./viewer_labels.js";

const GHOST = new THREE.MeshStandardMaterial({ color: 0xd9cbb6, transparent: true, opacity: 0.5, roughness: 0.72 });
const PLANNED = new THREE.MeshStandardMaterial({ color: 0xfff4df, roughness: 0.56, metalness: 0.01 });
// Highlight for the tooth currently selected for manual target authoring.
const SELECTED = new THREE.MeshStandardMaterial({ color: 0xf4bd4b, roughness: 0.5, emissive: 0x996210, emissiveIntensity: 0.18, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
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
// Occlusal proximity overlay: red = touching/overlapping, amber = near, green =
// clearance. GEOMETRIC closeness of the registered surfaces, NOT bite force.
const PROXIMITY_COLORS = {
  contact: new THREE.Color(0xdc2626),
  near: new THREE.Color(0xf59e0b),
  clearance: new THREE.Color(0x16a34a),
};
const PROXIMITY_MAT = new THREE.MeshBasicMaterial({
  vertexColors: true,
  transparent: true,
  opacity: 0.85,
  side: THREE.DoubleSide,
});
// A true-scale ruler drawn beside a loaded scan (scan geometry is at true scale).
const meshGeometryCache = new Map();
const meshUrlCache = new Map();

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
function archQuaternion(tooth, schematic = false) {
  const flip = archOf(tooth) === "upper"
    ? new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI)
    : new THREE.Quaternion();
  if (!schematic) return flip;
  const { angle } = schematicToothPose(tooth);
  return new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), angle).multiply(flip);
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

export function createViewer(container, { schematicOnly = false } = {}) {
  let needsRender = true;
  const highlightMaterial = new THREE.MeshStandardMaterial({ roughness: 0.55, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 });
  let rootsVisible = !schematicOnly;
  const toothGeometry = (tooth) => (!schematicOnly && meshGeometryCache.get(tooth)) || syntheticToothGeometry(tooth, rootsVisible);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  container.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xfbfdfe);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
  camera.position.set(0, 42, 46);

  let controls = new OrbitControls(camera, renderer.domElement);
  controls.addEventListener("change", () => { needsRender = true; });
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);
  const navigation = mountViewerNavigation(container, () => controls, () => focusSelectedTooth());

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
    camera.updateMatrixWorld(true);
    proxies.updateMatrixWorld(true);
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObjects(proxies.children, false);
    const shell = uploadedScans.visible ? raycaster.intersectObjects(visibleScanChildren(), false)[0] : null;
    for (const hit of hits) {
      if (shell && hit.distance > shell.distance + 0.15) continue;
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
    if (event.button !== 0 || navigation.mode === "pan" || !selectionEnabled || !onSelect) return;
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
  grid.visible = !schematicOnly;
  scene.add(grid);

  // Persistent arch labels so the stacked maxillary/mandibular arches are
  // unambiguous (depthTest off keeps them readable through the teeth).
  const UPPER_LABEL_POS = new THREE.Vector3(0, ARCH.gapY + (schematicOnly ? 6 : 5), 7);
  const LOWER_LABEL_POS = new THREE.Vector3(0, -ARCH.gapY - (schematicOnly ? 6 : 5), 7);
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
  // Occlusal proximity overlay (red/amber/green clearance tiles). A sibling group
  // that mirrors uploadedScans' placement offset, so the tiles sit between the
  // rendered arches at the registered meeting plane. Built by loadProximity.
  const proximityOverlay = new THREE.Group();
  proximityOverlay.visible = false;
  scene.add(proximityOverlay);
  let proximityMesh = null;
  let proximityVisible = false;
  const scaleBar = createViewerScaleBar(scene);
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
  const fragments = createFragmentLoader(parseScanGeometry, orientScanGeometry);
  const fragmentCache = fragments.cache;
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
  let visibleArchFilter = "both";
  const scanViews = mountScanViewToolbar(container.parentElement, command => {
    controls = frameScanView(camera, controls, renderer.domElement, visibleScanBox(), command, () => { needsRender = true; }, visibleScanView(visibleScanChildren()));
    navigation.apply();
  }, { defaultView: true });
  scanViews.after(navigation.element);
  scanViews.hidden = true;

  function resize() {
    needsRender = true;
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
    if (container.clientWidth && container.clientHeight) {
      controls.update();
      if (needsRender) { renderer.render(scene, camera); needsRender = false; }
    }
    requestAnimationFrame(loop);
  })();

  function update({ frames, toothFrames, attachments, initialOffsets, stageIndex, view, exaggeration, showToothLabels, showScale, unitsConfirmed, excluded, highlightTeeth = [], highlightColor = "#2563eb", labelTeeth = null, showRoots = !schematicOnly }) {
    needsRender = true;
    rootsVisible = showRoots;
    const highlighted = new Set(highlightTeeth.map(String));
    const labels = labelTeeth === null ? null : new Set(labelTeeth.map(String));
    const showLabel = (tooth) => showToothLabels && (!labels || labels.has(String(tooth)));
    highlightMaterial.color.set(highlightColor);
    const withHighlight = (tooth, material) => highlighted.has(String(tooth)) ? highlightMaterial : material;
    scene.background = new THREE.Color(document.body.dataset.theme === "dark" ? 0x111a1f : 0xfbfdfe);
    uploadedScans.visible = view === "current" || view === "overlay";
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
    proxies.clear();
    positionArchLabels();
    // Independent of the plan frame: the ruler only needs a loaded scan, so build
    // it before the early return below (a scan can be loaded with no plan yet).
    scaleBar.update(visibleScanBox(), showScale, unitsConfirmed);
    navigation.setFocusAvailable(fragmentCache.has(String(selectedTooth)));
    const frame = frames?.[stageIndex] || { poses: [] };
    const poses = [...frame.poses];
    const present = new Set(poses.map(pose => String(pose.tooth)));
    for (const tooth of fragmentCache.keys()) {
      if (!present.has(tooth)) poses.push({ tooth });
    }
    const visibleScanCount = visibleScanChildren().length;
    const hasExactScan = visibleScanCount > 0;
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
    const fragmentMode = fragmentCache.size > 0 && visibleScanCount > 0;
    const scanBase = uploadedScans.position;
    const activeAttachments = new Set((attachments || [])
      .filter((item) => stageIndex >= item.stage_start && (item.stage_end === null || stageIndex <= item.stage_end))
      .map((item) => item.tooth?.value));

    for (const pose of poses) {
      if (!archVisible(archOf(pose.tooth))) continue;
      // Render the exact affine transform supplied by the engine.
      if (fragmentMode) {
        const fragment = fragmentCache.get(String(pose.tooth));
        if (!fragment) continue; // no real crown for this tooth; shell covers it
        const fragBase = scanBase.clone();
        const delta = showPlanned ? worldDeltaOriented(pose, exaggeration) : new THREE.Vector3();
        const matrix = new THREE.Matrix4().set(...orientedMeshMatrix(
          showPlanned ? frame.mesh_transforms?.[pose.tooth] : null, showPlanned ? pose : {}, exaggeration));
        const display = archDisplayMatrix(uploadedScans.children, archOf(pose.tooth));
        matrix.premultiply(display).premultiply(new THREE.Matrix4().makeTranslation(...fragBase.toArray()));
        // Transform the visible centroid with the same matrix as its crown
        // so labels follow both rotation and translation.
        const toothAt = fragmentCentroid(fragment).applyMatrix4(display).add(fragBase);
        const toothMoved = fragmentCentroid(fragment).applyMatrix4(matrix);
        if (showLabel(pose.tooth)) {
          let label = toothLabelSprites.get(pose.tooth);
          if (!label) {
            label = makeToothNumberSprite(String(pose.tooth));
            toothLabelSprites.set(pose.tooth, label);
          }
          label.position.copy(toothMoved).add(new THREE.Vector3(0, 2.4, 0));
          proxies.add(label);
        }
        {
          const material = excludedSet.has(String(pose.tooth))
            ? HELD
            : (selectedTooth === pose.tooth ? SELECTED : PLANNED);
          const crown = new THREE.Mesh(fragment, withHighlight(pose.tooth, material));
          crown.matrixAutoUpdate = false;
          crown.matrix.copy(matrix);
          crown.userData.tooth = pose.tooth;
          proxies.add(crown);
          if (delta.length() > 0.2) {
            const geom = new THREE.BufferGeometry().setFromPoints([toothAt, toothMoved]);
            lineGeometries.push(geom);
            proxies.add(new THREE.Line(geom, LINE_MAT));
          }
        }
        continue;
      }

      if (hasExactScan && !fragmentMode) continue;
      const anchor = scanAnchors.get(String(pose.tooth));
      const mapPose = schematicOnly ? schematicToothPose(pose.tooth) : null;
      const ideal = mapPose ? new THREE.Vector3(mapPose.x, mapPose.y, mapPose.z)
        : anchor ? anchor.pos.clone() : basePosition(pose.tooth);
      if (!ideal) continue;
      const proxyScale = anchor ? anchor.scale : 1;
      // The anchor (or schematic position) is the tooth's aligned/ideal spot; a
      // demo crowding offset shifts the start away from it, and the per-stage
      // movement (worldDelta) carries it back. Anchoring just moves that whole
      // start->end path onto the scan surface.
      const base = ideal.clone().add(worldOffset(initialOffsets?.[pose.tooth], exaggeration));

      if (showCurrent) {
        const ghostGeometry = toothGeometry(pose.tooth);
        const ghost = new THREE.Mesh(ghostGeometry, withHighlight(pose.tooth, GHOST));
        ghost.position.copy(base);
        ghost.scale.setScalar(proxyScale);
        ghost.quaternion.copy(archQuaternion(pose.tooth, schematicOnly));
        ghost.userData.tooth = pose.tooth;
        proxies.add(ghost);
      }
      // Optional FDI tooth-number label, floating above the tooth at its
      // currently-displayed position, so a user can see which tooth is which.
      if (showLabel(pose.tooth)) {
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
        const geometry = toothGeometry(pose.tooth);
        const material = excludedSet.has(String(pose.tooth))
          ? HELD
          : (selectedTooth === pose.tooth ? SELECTED : PLANNED);
        const mesh = new THREE.Mesh(geometry, withHighlight(pose.tooth, material));
        mesh.position.copy(moved);
        mesh.scale.setScalar(proxyScale);
        mesh.quaternion.copy(archQuaternion(pose.tooth, schematicOnly).multiply(plannedQuaternion(pose, toothFrames?.[pose.tooth])));
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
    let box = visibleScanBox();
    if (box && !box.isEmpty()) {
      controls = frameScanView(camera, controls, renderer.domElement, box, "auto", () => { needsRender = true; }, visibleScanView(visibleScanChildren()));
      navigation.apply();
      return;
    }
    // When a scan is visible, frame the scan geometry itself. Movement overlays
    // can be intentionally exaggerated or stage-shifted; using them as the fit
    // target makes a selected upper/lower STL feel off-center when the user zooms.
    if (!box && proxies.children.length) {
      box = new THREE.Box3();
      box.setFromObject(proxies);
    }
    if (!box || box.isEmpty()) {
      return;
    }
    if (schematicOnly) {
      box.expandByPoint(UPPER_LABEL_POS.clone().add(new THREE.Vector3(5, 1.5, 0)));
      box.expandByPoint(LOWER_LABEL_POS.clone().add(new THREE.Vector3(-5, -1.5, 0)));
    }
    // Fit a bounding sphere using the limiting (narrower) of the vertical and
    // horizontal field of view so a wide dental arch is fully framed and
    // centered regardless of the viewport aspect ratio.
    const sphere = new THREE.Sphere();
    box.getBoundingSphere(sphere);
    const center = sphere.center;
    const radius = Math.max(sphere.radius, 4);
    const fovV = THREE.MathUtils.degToRad(camera.fov);
    const fovH = 2 * Math.atan(Math.tan(fovV / 2) * Math.max(camera.aspect, 0.0001));
    let distance = Math.max(24, (radius / Math.sin(Math.min(fovV, fovH) / 2)) * 1.1);
    if (schematicOnly) {
      const size = box.getSize(new THREE.Vector3());
      const height = size.y * 0.916 + size.z * 0.4;
      distance = (Math.max(size.x / (2 * Math.tan(fovH / 2)), height / (2 * Math.tan(fovV / 2)))
        + (size.z * 0.916 + size.y * 0.4) / 2) * 1.15;
    }
    distance *= 0.82 ** 2; // Start two zoom-in steps closer; Reset uses the same framing.
    // ~42 deg elevation: high enough to read the arch horseshoe, low enough to
    // still face the crowns.
    camera.position.set(center.x, center.y + distance * (schematicOnly ? 0.4 : 0.7),
      center.z + distance * (schematicOnly ? 0.916 : 0.74));
    controls.target.copy(center);
    camera.near = Math.max(0.1, distance / 100);
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.update();
  }

  function positionArchLabels() {
    const arches = new Set(visibleScanChildren().map(mesh => mesh.userData.arch));
    upperLabel.visible = uploadedScans.children.length ? arches.has("upper") : visibleArchFilter !== "lower";
    lowerLabel.visible = uploadedScans.children.length ? arches.has("lower") : visibleArchFilter !== "upper";
    upperLabel.position.copy(archLabelPos.upper || UPPER_LABEL_POS);
    lowerLabel.position.copy(archLabelPos.lower || LOWER_LABEL_POS);
  }

  function visibleScanChildren() {
    return uploadedScans.children.filter((child) => child.visible !== false);
  }

  function visibleScanBox() {
    const visible = visibleScanChildren();
    if (!visible.length) return null;
    const box = new THREE.Box3();
    for (const child of visible) box.expandByObject(child);
    return box.isEmpty() ? null : box;
  }

  // One anchor point per tooth on the uploaded scan, used to place the arrow-mode
  // marker dot (and the arrow origin) on each tooth's buccal face. The schematic
  // arch layout (correct RELATIVE tooth order/spread) is fitted into each scan
  // arch's world bounding box in x/z; a vertical ray finds the occlusal height,
  // then the point is pushed onto the visible face at mid-crown (anchorArchTeeth).
  function computeScanAnchors() {
    const anchors = new Map();
    archLabelPos = {};
    if (!visibleScanChildren().length) return anchors;
    uploadedScans.updateMatrixWorld(true);
    const ray = new THREE.Raycaster();
    for (const arch of ["upper", "lower"]) {
      const mesh = uploadedScans.children.find(
        (m) => m.visible !== false && (m.userData.arch || normalizeArch(m.name)) === arch,
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
    const span = Math.max(box.max.y - box.min.y, 1); // arch height
    const scale = THREE.MathUtils.clamp((scanHx / sx.half) * ANCHOR_TOOTH_SCALE, 1, 4);
    for (const { tooth, p } of schematic) {
      const wx = center.x + ((p.x - sx.mid) / sx.half) * scanHx;
      const wz = center.z + ((p.z - sz.mid) / sz.half) * scanHz;
      ray.set(new THREE.Vector3(wx, box.max.y + 12, wz), new THREE.Vector3(0, -1, 0));
      const hits = ray.intersectObject(mesh, false);
      // Occlusal surface faces the opposing arch: lowest hit for the upper arch,
      // highest hit for the lower. Fall back to the box face if the ray misses.
      const occlusal = hits.length
        ? (up ? hits[hits.length - 1].point.y : hits[0].point.y)
        : (up ? box.min.y : box.max.y);
      // Place the marker on the tooth's BUCCAL face at mid-crown, not on the
      // incisal edge: push outward from the arch centre (so dots sit on the
      // visible faces) and lift toward the crown body (so the upper and lower
      // rows separate instead of bunching in the central bite gap).
      const ox = wx - center.x;
      const oz = wz - center.z;
      const olen = Math.hypot(ox, oz) || 1;
      const push = scanHx * 0.1;
      const mx = wx + (ox / olen) * push;
      const mz = wz + (oz / olen) * push;
      const my = occlusal + (up ? span * 0.22 : -span * 0.22);
      anchors.set(String(tooth), { pos: new THREE.Vector3(mx, my, mz), scale });
    }
    // Float each label well OUTSIDE its arch - above the upper, below the lower,
    // toward the camera - scaled to the arch so it clears the crowns and the two
    // never collide in the bite gap or read as swapped.
    archLabelPos[arch] = new THREE.Vector3(
      center.x,
      up ? box.max.y + span * 0.18 : box.min.y - span * 0.18,
      box.max.z + scanHz * 0.35,
    );
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
        geometry = parseScanGeometry(await response.arrayBuffer());
        centerGeometry(geometry);
        meshUrlCache.set(item.url, geometry);
      }
      meshGeometryCache.set(item.tooth, geometry);
      loaded = true;
    }));
    return loaded;
  }

  // Fragments retain original scan coordinates and are keyed by tooth + URL.
  const loadToothFragments = fragments.load;

  let scanRevision = 0, scanPending = null;
  function loadScanSources(sources = []) {
    const key = sources.filter(source => isSupportedScanName(source?.name)).map(sourceKey).join("|");
    if (key === uploadedScans.userData.key && scanPending) return scanPending;
    const token = ++scanRevision;
    scanPending = loadScanBatch(sources, token).finally(() => { if (token === scanRevision) scanPending = null; });
    return scanPending;
  }

  async function loadScanBatch(sources, token) {
    const scanSources = sources.filter((source) => isSupportedScanName(source?.name));
    const key = scanSources.map(sourceKey).join("|");
    if (uploadedScans.userData.key === key) return { loaded: false, count: uploadedScans.children.length };
    uploadedScans.userData.key = key;
    // Per-tooth fragments belong to the previous scan/segmentation; drop them so
    // a new scan never renders stale crowns.
    fragments.clear();
    uploadedScans.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
    });
    uploadedScans.clear();
    scanViews.hidden = !scanSources.length;
    // The proximity overlay belongs to the previous scan pair; drop it so a new
    // scan never shows a stale, misaligned occlusion map.
    clearProximity();
    if (!scanSources.length) {
      scanAnchors = new Map();
      archLabelPos = {};
      return { loaded: false, count: 0 };
    }

    const prepared = [];
    try {
      for (const source of scanSources) {
        const bytes = await sourceBuffer(source);
        if (token !== scanRevision) { for (const mesh of prepared) mesh.geometry.dispose(); return { loaded: false, stale: true, count: 0 }; }
        const arch = normalizeArch(source.arch) || normalizeArch(source.name);
        const scanView = await sourceViewContext(bytes, arch);
        if (token !== scanRevision) { for (const mesh of prepared) mesh.geometry.dispose(); return { loaded: false, stale: true, count: 0 }; }
        const geometry = parseScanGeometry(bytes);
        orientScanGeometry(geometry);
        const mesh = buildScanObject(geometry, SCAN);
        mesh.name = source.name;
        mesh.userData.arch = arch; mesh.userData.scanView = scanView; mesh.userData.displayArchStack = Boolean(source.displayArchStack);
        mesh.visible = archVisible(mesh.userData.arch);
        prepared.push(mesh);
      }
    } catch (error) {
      for (const mesh of prepared) mesh.geometry.dispose();
      if (token !== scanRevision) return { loaded: false, stale: true, count: 0 };
      uploadedScans.userData.key = null;
      throw error;
    }
    uploadedScans.position.set(0, 0, 0);
    arrangeScanArches(prepared);
    for (const mesh of prepared) uploadedScans.add(mesh);

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

  function setVisibleArchFilter(filter) {
    const next = normalizeArch(filter) || "both";
    const changed = next !== visibleArchFilter;
    if (!changed) return;
    visibleArchFilter = next;
    for (const mesh of uploadedScans.children) {
      mesh.visible = archVisible(mesh.userData.arch || normalizeArch(mesh.name));
    }
    scanAnchors = computeScanAnchors();
    positionArchLabels();
    if (changed) fitted = false;
  }

  function archVisible(arch) {
    return visibleArchFilter === "both" || arch === visibleArchFilter;
  }

  function loadUploadedScans(files = []) {
    return loadScanSources(files.map((file) => ({ name: file.name, file })));
  }

  function clearProximity() {
    if (proximityMesh) {
      proximityMesh.geometry.dispose();
      proximityOverlay.remove(proximityMesh);
      proximityMesh = null;
    }
    proximityOverlay.userData.map = null;
    proximityOverlay.visible = false;
  }

  // Build the occlusal proximity overlay from a server-classified map. Each cell is
  // a small tile at the registered meeting plane, coloured by clearance band. Scan
  // space (x, y, z) maps to viewer-local (x, z, -y) - the same baked rotation the
  // scans use - and the group copies uploadedScans' offset so the tiles align with
  // the rendered arches. Only painted for an as-scanned registration: an estimated
  // alignment moved the lower arch, so its coordinates would not match the scans.
  function loadProximity(map) {
    // Rebuild only when the map actually changes; update() re-renders on every
    // stage scrub, and re-tessellating hundreds of cells each time would be wasteful.
    if (map && proximityMesh && proximityOverlay.userData.map === map) {
      proximityOverlay.position.copy(uploadedScans.position);
      proximityOverlay.visible = proximityVisible;
      return true;
    }
    clearProximity();
    if (!map || !map.aligned_to_scan || !map.cells?.length) return false;
    const half = (map.cell_size || 1) / 2;
    const positions = [];
    const colors = [];
    for (const cell of map.cells) {
      const color = PROXIMITY_COLORS[cell.band] || PROXIMITY_COLORS.clearance;
      const x0 = cell.x - half;
      const x1 = cell.x + half;
      const z0 = -(cell.y - half);
      const z1 = -(cell.y + half);
      const y = cell.z;
      const corners = [
        [x0, y, z0], [x1, y, z0], [x1, y, z1],
        [x0, y, z0], [x1, y, z1], [x0, y, z1],
      ];
      for (const [px, py, pz] of corners) {
        positions.push(px, py, pz);
        colors.push(color.r, color.g, color.b);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    proximityMesh = new THREE.Mesh(geometry, PROXIMITY_MAT);
    proximityOverlay.add(proximityMesh);
    proximityOverlay.userData.map = map;
    proximityOverlay.position.copy(uploadedScans.position);
    proximityOverlay.visible = proximityVisible;
    return true;
  }

  function setProximityVisible(visible) {
    proximityVisible = Boolean(visible);
    proximityOverlay.visible = proximityVisible && Boolean(proximityMesh);
  }

  // Show the true registered occlusion by moving the LOWER arch mesh by the
  // registration offset (already mapped to viewer-local axes by the caller). An
  // as-scanned export already occludes, so the caller passes null/zero there and
  // the arch sits at its scanned position. Idempotent: called every render.
  function setArchRegistration(offset) {
    const x = offset?.x || 0;
    const y = offset?.y || 0;
    const z = offset?.z || 0;
    for (const mesh of uploadedScans.children) {
      if (mesh.userData.arch === "lower") {
        const base = mesh.userData.layoutPosition || new THREE.Vector3();
        mesh.position.copy(base).add(new THREE.Vector3(x, y, z)); mesh.updateMatrix();
      }
    }
  }

  // World-axis size of the loaded scan in scan units (mm when confirmed): x =
  // mediolateral width, y = vertical height, z = anteroposterior depth. The status
  // strip reads this; null when no scan is loaded.
  function scanExtentMm() {
    const box = visibleScanBox();
    if (!box) return null;
    const size = new THREE.Vector3();
    box.getSize(size);
    return { x: size.x, y: size.y, z: size.z };
  }

  function focusSelectedTooth() {
    const crown = proxies.children.find(node => node.isMesh && node.userData.tooth === selectedTooth);
    if (!crown) return;
    const box = new THREE.Box3().setFromObject(crown);
    controls = frameScanView(camera, controls, renderer.domElement, box, "fit", () => { needsRender = true; });
    navigation.apply();
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
    scanRevision++;
    running = false;
    highlightMaterial.dispose();
    for (const label of [upperLabel, lowerLabel]) {
      label.material.map?.dispose();
      label.material.dispose();
    }
    renderer.domElement.removeEventListener("pointerdown", onPointerDown);
    renderer.domElement.removeEventListener("pointerup", onPointerUp);
    for (const geom of lineGeometries) geom.dispose();
    lineGeometries = [];
    for (const sprite of toothLabelSprites.values()) {
      sprite.material.map?.dispose();
      sprite.material.dispose();
    }
    toothLabelSprites.clear();
    // Per-viewer fragment crowns own GPU buffers; free them (the shared
    // synthetic/class caches are module-level and intentionally retained).
    fragments.clear();
    uploadedScans.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
    });
    clearProximity();
    scaleBar.dispose();
    scanViews.remove(); navigation.dispose();
    window.removeEventListener("resize", resize);
    controls.dispose();
    renderer.dispose(); renderer.domElement.remove();
  }

  window.addEventListener("resize", resize);
  return {
    update, resize, dispose, loadMeshes, loadToothFragments, loadScanSources, loadUploadedScans,
    fragmentError: () => fragments.error,
    loadProximity, setProximityVisible, scanExtentMm, setArchRegistration, setVisibleArchFilter,
    setAutoRotate: (enabled) => { controls.autoRotate = enabled; controls.autoRotateSpeed = .65; },
    zoomBy, recenter, setSelectionHandler, setSelectionEnabled, setSelectedTooth,
  };
}

// Centre of a fragment's bounding box, cached on the geometry: the tooth's
// location within the scan (fragment vertices stay in scan-oriented space).
function fragmentCentroid(geometry) {
  if (!geometry.userData.centroid) {
    if (!geometry.boundingBox) geometry.computeBoundingBox();
    geometry.userData.centroid = geometry.boundingBox.getCenter(new THREE.Vector3());
  }
  return geometry.userData.centroid.clone();
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
  if (source.file) return `${source.name}:${source.arch || ""}:${source.file.size}:${source.file.lastModified}`;
  return `${source.name}:${source.arch || ""}:${source.url}`;
}

async function sourceBuffer(source) {
  if (source.file) return source.file.arrayBuffer();
  const response = await fetch(source.url);
  if (!response.ok) throw new Error(`could not load ${source.name}`);
  return response.arrayBuffer();
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
