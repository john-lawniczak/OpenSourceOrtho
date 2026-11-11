import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { comparisonGeometry } from "./scan_comparison_geometry.js";
import { historyCamera } from "./scan_history.js";

// One camera persists across full-surface visits and missing-week states.
export function createScanComparison(host, { onFocus = () => {} } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  host.replaceChildren(renderer.domElement);
  renderer.domElement.setAttribute("aria-label", "Scan history; drag to rotate, scroll to zoom, double-click a crown to focus");
  const camera = new THREE.OrthographicCamera(-40, 40, 40, -40, 0.1, 2000);
  function makeControls() {
    const control = new OrbitControls(camera, renderer.domElement);
    control.enableDamping = false;
    control.minZoom = 0.5;
    control.maxZoom = 12;
    control.addEventListener("change", render);
    return control;
  }
  let controls = makeControls();
  const scenes = [new THREE.Scene(), new THREE.Scene()];
  const material = new THREE.MeshStandardMaterial({ color: 0xefe4cf, roughness: 0.68, side: THREE.DoubleSide });
  for (const scene of scenes) {
    scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 2));
    const light = new THREE.DirectionalLight(0xffffff, 2.2);
    light.position.set(20, 65, 35);
    scene.add(light);
  }
  let meshes = [], activeIndex = 0, arch = "upper", span = 40, width = 1, height = 1, disposed = false;

  function render() {
    if (disposed || !host.clientWidth || !host.clientHeight) return;
    const background = document.body.dataset.theme === "dark" ? 0x14242c : 0xf4f7f8;
    scenes.forEach(scene => { scene.background = new THREE.Color(background); });
    renderer.setViewport(0, 0, width, height);
    if (activeIndex === null || !meshes.length) {
      renderer.setClearColor(background);
      renderer.clear();
    } else renderer.render(scenes[activeIndex], camera);
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

  function setView(view = "front") {
    controls.target.set(0, 0, 0);
    const pose = historyCamera(arch, view);
    camera.up.set(...pose.up);
    camera.position.set(...pose.position);
    // OrbitControls caches the camera-up basis at construction.
    controls.dispose();
    controls = makeControls();
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
    arch = scans[0].arch;
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
    if (meshes.length !== 2 || activeIndex === null) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(x * 2 - 1, 1 - y * 2), camera);
    const hit = ray.intersectObject(meshes[activeIndex])[0];
    if (!hit) return;
    camera.position.add(hit.point.clone().sub(controls.target));
    controls.target.copy(hit.point);
    zoom(2);
    controls.update();
    onFocus();
  }

  renderer.domElement.addEventListener("dblclick", focus);
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  setView();
  return {
    setPair, clear, resize, zoom, setView,
    setVisit(index) {
      if (index !== null && index !== 0 && index !== 1) throw new Error("Unknown visit.");
      activeIndex = index;
      controls.enabled = index !== null;
      render();
    },
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
