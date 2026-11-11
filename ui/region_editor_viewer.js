import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { historyCamera } from "./scan_history.js";

export function createRegionEditor(host, scan, { onPaint, brushSettings }) {
  const renderer = new THREE.WebGLRenderer({ antialias: true }); host.replaceChildren(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x172830);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x506070, 3));
  const geometry = comparisonGeometry(scan), material = new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide });
  const mesh = new THREE.Mesh(geometry, material); scene.add(mesh);
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 2000);
  const pose = historyCamera(scan.arch); camera.up.set(...pose.up); camera.position.set(...pose.position).multiplyScalar(0.55);
  const controls = new OrbitControls(camera, renderer.domElement); controls.addEventListener("change", render);
  const p = geometry.attributes.position, colors = new Float32Array(p.count * 3);
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const centers = new Float32Array(p.count), normals = new Float32Array(p.count);
  for (let face = 0; face < p.count / 3; face++) for (let axis = 0; axis < 3; axis++) {
    centers[face * 3 + axis] = (p.array[face * 9 + axis] + p.array[face * 9 + axis + 3] + p.array[face * 9 + axis + 6]) / 3;
    normals[face * 3 + axis] = geometry.attributes.normal.array[face * 9 + axis];
  }
  function render() { renderer.render(scene, camera); }
  function resize() { renderer.setSize(host.clientWidth, host.clientHeight); camera.aspect = host.clientWidth / host.clientHeight; camera.updateProjectionMatrix(); render(); }
  function paint(event) {
    const settings = brushSettings(); if (settings.mode === "orbit") return;
    const box = renderer.domElement.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((event.clientX - box.left) / box.width * 2 - 1, 1 - (event.clientY - box.top) / box.height * 2), camera);
    const hit = ray.intersectObject(mesh)[0]; if (!hit) return;
    const faces = [], normal = hit.face.normal;
    for (let i = 0; i < centers.length; i += 3) {
      const distance = (centers[i] - hit.point.x) ** 2 + (centers[i + 1] - hit.point.y) ** 2 + (centers[i + 2] - hit.point.z) ** 2;
      if (distance <= settings.radius ** 2 && normals[i] * normal.x + normals[i + 1] * normal.y + normals[i + 2] * normal.z > 0.3) faces.push(i / 3);
    }
    onPaint(faces, settings);
  }
  let drawing = false;
  renderer.domElement.addEventListener("pointerdown", event => {
    drawing = brushSettings().mode !== "orbit"; controls.enabled = !drawing;
    if (drawing) { renderer.domElement.setPointerCapture(event.pointerId); paint(event); }
  }, true);
  renderer.domElement.addEventListener("pointermove", event => { if (drawing && event.buttons) paint(event); });
  renderer.domElement.addEventListener("pointerup", () => { drawing = false; controls.enabled = true; });
  renderer.domElement.addEventListener("pointercancel", () => { drawing = false; controls.enabled = true; });
  const observer = new ResizeObserver(resize); observer.observe(host); resize();
  return {
    colorLabels(labels) {
      const palette = new Map([[0, new THREE.Color(0x8a989d)]]);
      for (const id of new Set(labels)) if (id) palette.set(id, new THREE.Color().setHSL((id * 0.6180339) % 1, 0.65, 0.55));
      labels.forEach((id, face) => { const color = palette.get(id); for (let i = 0; i < 3; i++) colors.set([color.r, color.g, color.b], face * 9 + i * 3); });
      geometry.attributes.color.needsUpdate = true; render();
    },
    dispose() { observer.disconnect(); controls.dispose(); geometry.dispose(); material.dispose(); renderer.dispose(); host.replaceChildren(); },
  };
}
