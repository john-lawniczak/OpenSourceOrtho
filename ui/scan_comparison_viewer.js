import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { revealFraction } from "./scan_comparison_data.js";

// One camera and viewport for both visits. Scissoring reveals original surfaces
// without morphing, opacity interpolation, or rebuilding geometry while scrubbing.
export function createScanComparison(host, { onFocus = () => {} } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  host.replaceChildren(renderer.domElement);
  renderer.domElement.setAttribute("aria-label", "Observed scan comparison; drag to rotate, scroll to zoom, double-click a crown to focus");
  const camera = new THREE.OrthographicCamera(-40, 40, 40, -40, 0.1, 2000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.minZoom = 0.5;
  controls.maxZoom = 12;
  const scenes = [new THREE.Scene(), new THREE.Scene()];
  const material = new THREE.MeshStandardMaterial({ color: 0xefe4cf, roughness: 0.68, side: THREE.DoubleSide });
  for (const scene of scenes) {
    scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 2));
    const light = new THREE.DirectionalLight(0xffffff, 2.2);
    light.position.set(20, 65, 35);
    scene.add(light);
  }
  let meshes = [], fraction = 0, span = 40, width = 1, height = 1, disposed = false;

  function render() {
    if (disposed || !host.clientWidth || !host.clientHeight) return;
    const background = document.body.dataset.theme === "dark" ? 0x14242c : 0xf4f7f8;
    scenes.forEach(scene => { scene.background = new THREE.Color(background); });
    const split = Math.round(width * (1 - fraction));
    renderer.setScissorTest(true);
    renderer.setViewport(0, 0, width, height);
    if (split > 0) {
      renderer.setScissor(0, 0, split, height);
      renderer.render(scenes[0], camera);
    }
    if (split < width) {
      renderer.setScissor(split, 0, width - split, height);
      renderer.render(scenes[1], camera);
    }
    renderer.setScissorTest(false);
  }

  function resize() {
    if (disposed) return;
    width = Math.max(host.clientWidth, 1);
    height = Math.max(host.clientHeight, 1);
    renderer.setSize(width, height);
    const aspect = width / height;
    camera.left = -span * Math.max(aspect, 1);
    camera.right = -camera.left;
    camera.top = span / Math.min(aspect, 1);
    camera.bottom = -camera.top;
    camera.updateProjectionMatrix();
    render();
  }

  function setView(view = "occlusal") {
    controls.target.set(0, 0, 0);
    const position = { occlusal: [0, 180, 0.01], front: [0, 25, 180], left: [-180, 25, 0], right: [180, 25, 0] }[view];
    camera.position.set(...(position || [0, 180, 0.01]));
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    controls.update();
    render();
  }

  function clear() {
    for (let i = 0; i < meshes.length; i++) {
      scenes[i].remove(meshes[i]);
      meshes[i].geometry.dispose();
    }
    meshes = [];
    render();
  }

  function setPair(scans) {
    const prepared = [];
    try {
      for (const scan of scans) prepared.push(new THREE.Mesh(comparisonGeometry(scan), material));
    } catch (error) {
      prepared.forEach(mesh => mesh.geometry.dispose());
      throw error;
    }
    clear();
    meshes = prepared;
    span = Math.max(...meshes.map(mesh => mesh.geometry.boundingSphere.radius), 5) * 1.08;
    meshes.forEach((mesh, index) => scenes[index].add(mesh));
    resize();
    setView();
  }

  function zoom(factor) {
    camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, controls.minZoom, controls.maxZoom);
    camera.updateProjectionMatrix();
    render();
  }

  function focus(event) {
    if (meshes.length !== 2) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(x * 2 - 1, 1 - y * 2), camera);
    const hit = ray.intersectObject(meshes[x < 1 - fraction ? 0 : 1])[0];
    if (!hit) return;
    camera.position.add(hit.point.clone().sub(controls.target));
    controls.target.copy(hit.point);
    zoom(2);
    controls.update();
    onFocus();
  }

  controls.addEventListener("change", render);
  renderer.domElement.addEventListener("dblclick", focus);
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  setView();
  return {
    setPair, clear, resize, zoom, setView,
    setReveal(value) { fraction = revealFraction(value); render(); },
    dispose() {
      disposed = true;
      observer.disconnect();
      controls.removeEventListener("change", render);
      controls.dispose();
      renderer.domElement.removeEventListener("dblclick", focus);
      clear();
      material.dispose();
      renderer.dispose();
      host.replaceChildren();
    },
  };
}
