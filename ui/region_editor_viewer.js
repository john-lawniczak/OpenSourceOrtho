import { createRegionSelection } from "./region_selection_view.js";
import { createBoundaryView } from "./region_boundary_view.js";
import { createFragmentView } from "./region_fragment_view.js";
import { frameScanView } from "./scan_view_camera.js";
import { scanFrontPose } from "./scan_view_pose.js";
import { mountScanViewToolbar } from "./scan_view_toolbar.js";
import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { historyCamera } from "./scan_history.js";

export function createRegionEditor(host, scan, { onPaint, brushSettings, onStrokeStart = () => {}, onStrokeEnd = () => {}, onSelectTooth = () => {} }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true }); host.replaceChildren(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x172830);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x506070, 3));
  const geometry = comparisonGeometry(scan), material = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
  const mesh = new THREE.Mesh(geometry, material); scene.add(mesh);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 2000);
  const pose = historyCamera(scan.arch); camera.up.set(...pose.up); camera.position.set(...pose.position).multiplyScalar(0.55);
  const selection = createRegionSelection(host, scene, geometry, camera);
  const boundaries = createBoundaryView(scene, geometry);
  const fragments = createFragmentView(scene, geometry);
  let activeLabels = [], pointerStart = null, lastHit = null, focused = false, pointBounds = null, selectedLabel = 0;
  let controls = new OrbitControls(camera, renderer.domElement); controls.addEventListener("change", render);
  const box = geometry.boundingBox.clone();
  const viewControls = mountScanViewToolbar(host.closest(".review-viewport") || host, command => {
    if (command === "default") {
      focused = false; pointBounds = null; lastHit = null; cursor.visible = false;
      const front = scanFrontPose(scan.rotation), center = box.getCenter(new THREE.Vector3());
      camera.up.fromArray(front.up); controls.target.copy(center);
      camera.position.copy(center).add(new THREE.Vector3(...front.direction));
      command = "fit";
    }
    if (["auto", "fit"].includes(command)) focused = false;
    const viewBox = focused ? pointBounds || selection.focusBounds() || box : box;
    controls = frameScanView(camera, controls, renderer.domElement, viewBox, command, render);
    configureNavigation();
  }, { compact: true, defaultView: true });
  const cursor = new THREE.Mesh(new THREE.RingGeometry(0.94, 1, 48), new THREE.MeshBasicMaterial({ color: 0xffbf47, side: THREE.DoubleSide, depthTest: false }));
  cursor.visible = false; cursor.renderOrder = 10; scene.add(cursor);
  const p = geometry.attributes.position, colors = new Float32Array(p.count * 3);
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const centers = new Float32Array(p.count), normals = new Float32Array(p.count);
  for (let face = 0; face < p.count / 3; face++) for (let axis = 0; axis < 3; axis++) {
    centers[face * 3 + axis] = (p.array[face * 9 + axis] + p.array[face * 9 + axis + 3] + p.array[face * 9 + axis + 6]) / 3;
    normals[face * 3 + axis] = geometry.attributes.normal.array[face * 9 + axis];
  }
  function render() { camera.updateMatrixWorld(); selection.positionMarker(); fragments.positionMarker(camera, host.clientHeight); renderer.render(scene, camera); }
  function resize() { renderer.setSize(host.clientWidth, host.clientHeight); camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); render(); }
  function hitAt(event) {
    const rect = renderer.domElement.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1,
      1 - (event.clientY - rect.top) / rect.height * 2), camera);
    return ray.intersectObject(mesh)[0];
  }
  function navigating() { return ["orbit", "pan"].includes(brushSettings().mode); }
  function configureNavigation() {
    const pan = brushSettings().mode === "pan";
    controls.mouseButtons.LEFT = pan ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
    controls.touches.ONE = pan ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
    controls.screenSpacePanning = true;
  }
  function paint(event, apply = true) {
    const settings = brushSettings(); if (navigating()) { cursor.visible = false; render(); return; }
    const hit = hitAt(event); lastHit = hit || null; cursor.visible = Boolean(hit);
    if (!hit) { render(); return; }
    updateBrush(); if (!apply) return;
    const faces = [], normal = hit.face.normal;
    for (let i = 0; i < centers.length; i += 3) {
      const distance = (centers[i] - hit.point.x) ** 2 + (centers[i + 1] - hit.point.y) ** 2 + (centers[i + 2] - hit.point.z) ** 2;
      if (distance <= settings.radius ** 2 && normals[i] * normal.x + normals[i + 1] * normal.y + normals[i + 2] * normal.z > 0.3) faces.push(i / 3);
    }
    onPaint(faces, settings);
  }
  function updateBrush() {
    const settings = brushSettings();
    configureNavigation();
    cursor.visible = Boolean(lastHit && !navigating());
    if (cursor.visible) {
      cursor.position.copy(lastHit.point); cursor.scale.setScalar(settings.radius);
      cursor.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), lastHit.face.normal.clone().normalize());
    }
    render();
  }
  function focusSelected() {
    const selectedBox = selection.focusBounds();
    if (!selectedBox) return;
    focused = true; pointBounds = null; lastHit = null; cursor.visible = false;
    controls = frameScanView(camera, controls, renderer.domElement, selectedBox, "fit", render);
    configureNavigation();
  }
  renderer.domElement.addEventListener("dblclick", event => {
    if (!navigating()) return;
    const hit = hitAt(event);
    if (!hit) return;
    const id = activeLabels[hit.faceIndex];
    if (id) onSelectTooth(id);
    // Focus the clicked surface, even if unlabeled or part of a broad draft region.
    const size = box.getSize(new THREE.Vector3()).length() * 0.1;
    pointBounds = new THREE.Box3().setFromCenterAndSize(hit.point, new THREE.Vector3(size, size, size));
    focused = true; lastHit = null; cursor.visible = false;
    controls = frameScanView(camera, controls, renderer.domElement, pointBounds, "fit", render);
    configureNavigation();
  });
  let drawing = false;
  renderer.domElement.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;
    pointerStart = [event.clientX, event.clientY];
    drawing = !navigating(); controls.enabled = !drawing;
    if (drawing) { onStrokeStart(); renderer.domElement.setPointerCapture(event.pointerId); paint(event); }
  }, true);
  renderer.domElement.addEventListener("pointermove", event => paint(event, Boolean(drawing && event.buttons)));
  function finishStroke() { if (drawing) onStrokeEnd(); drawing = false; controls.enabled = true; }
  renderer.domElement.addEventListener("pointerup", event => {
    if (!drawing && event.button === 0 && pointerStart && navigating()
      && Math.hypot(event.clientX - pointerStart[0], event.clientY - pointerStart[1]) < 5) {
      const hit = hitAt(event);
      if (hit) onSelectTooth(activeLabels[hit.faceIndex] || 0);
    }
    pointerStart = null; finishStroke();
  });
  renderer.domElement.addEventListener("pointercancel", finishStroke);
  renderer.domElement.addEventListener("pointerleave", () => { cursor.visible = false; render(); });
  const observer = new ResizeObserver(resize); observer.observe(host); resize();
  controls = frameScanView(camera, controls, renderer.domElement, box, scan.autoView ? "auto" : "fit", render);
  return {
    colorLabels(labels, selected = 0, showOtherColors = true) {
      const changedSelection = selectedLabel !== selected; selectedLabel = selected;
      activeLabels = labels;
      const palette = new Map([[0, new THREE.Color(0x8a989d)]]);
      for (const id of new Set(labels)) if (id) palette.set(id, showOtherColors ? new THREE.Color().setHSL((id * 0.6180339) % 1, 0.65, 0.55) : new THREE.Color(0x607c8b));
      if (selected) palette.set(selected, new THREE.Color(0xffbf47));
      labels.forEach((id, face) => { const color = palette.get(id); for (let i = 0; i < 3; i++) colors.set([color.r, color.g, color.b], face * 9 + i * 3); });
      selection.update(labels, selected);
      boundaries.update(labels);
      geometry.attributes.color.needsUpdate = true;
      if (focused && changedSelection && !pointBounds) focusSelected();
      render();
    },
    setMarkerVisible(visible) { selection.setMarkerVisible(visible); render(); },
    setBoundariesVisible(visible) { boundaries.visible(visible); render(); },
    showFragments(groups, visible = true) { fragments.update(groups); fragments.visible(visible); render(); },
    focusFragment(group) {
      const patch = fragments.bounds(group), center = patch.box.getCenter(new THREE.Vector3());
      fragments.focus(group);
      const minimum = box.getSize(new THREE.Vector3()).length() * 0.12;
      const size = patch.box.getSize(new THREE.Vector3()).max(new THREE.Vector3(minimum, minimum, minimum));
      pointBounds = new THREE.Box3().setFromCenterAndSize(center, size); focused = true;
      if (patch.normal.lengthSq() > 0) {
        controls.target.copy(center); camera.position.copy(center).add(patch.normal);
        if (Math.abs(camera.up.dot(patch.normal)) > 0.95) camera.up.set(1, 0, 0);
      }
      lastHit = null; cursor.visible = false;
      controls = frameScanView(camera, controls, renderer.domElement, pointBounds, "fit", render);
      configureNavigation();
    },
    zoom(factor) {
      const offset = camera.position.clone().sub(controls.target);
      const min = Math.max(box.getBoundingSphere(new THREE.Sphere()).radius * 0.02, camera.near * 2);
      offset.setLength(Math.max(min, Math.min(camera.far * 0.4, offset.length() * factor)));
      camera.position.copy(controls.target).add(offset); controls.update(); render();
    },
    focusSelected, updateBrush,
    dispose() { fragments.dispose(); boundaries.dispose(); selection.dispose(); viewControls.remove(); cursor.geometry.dispose(); cursor.material.dispose(); observer.disconnect(); controls.dispose(); geometry.dispose(); material.dispose(); renderer.dispose(); host.replaceChildren(); },
  };
}
