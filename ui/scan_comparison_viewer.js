import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { comparisonArch, arrangeComparisonArches } from "./scan_comparison_arch.js";
import { historyCamera } from "./scan_history.js";

// Original and fitted surfaces share one scene, one camera and one interaction.
export function createScanComparison(host, { onFocus = () => {}, onTooth = () => {}, defaultZoom = 1.25 } = {}) {
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
  const scene = new THREE.Scene();
  const material = new THREE.MeshStandardMaterial({ color: 0xefe4cf, roughness: 0.68, side: THREE.DoubleSide });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x667788, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2.2);
  light.position.set(20, 65, 35); scene.add(light);
  let entries = [], selected = "", activeIndex = 0, arch = "upper", span = 40, width = 1, height = 1, disposed = false;

  function render() {
    if (disposed || !host.clientWidth || !host.clientHeight) return;
    scene.background = new THREE.Color(document.body.dataset.theme === "dark" ? 0x14242c : 0xf4f7f8);
    for (const entry of entries) {
      const index = activeIndex === 0 && selected && entry.simulation ? 2 : activeIndex;
      entry.nodes.forEach((node, i) => { if (node) node.visible = i === index; });
    }
    renderer.setViewport(0, 0, width, height);
    renderer.render(scene, camera);
  }

  function resize() {
    if (disposed) return;
    width = Math.max(host.clientWidth, 1); height = Math.max(host.clientHeight, 1);
    renderer.setSize(width, height);
    const aspect = width / height;
    camera.left = -span * Math.max(aspect, 1); camera.right = -camera.left;
    camera.top = span / Math.min(aspect, 1); camera.bottom = -camera.top;
    camera.updateProjectionMatrix(); render();
  }

  function setView(view = "front") {
    controls.target.set(0, 0, 0);
    const pose = historyCamera(arch, view);
    camera.up.set(...pose.up);
    camera.position.set(...(entries.length > 1 && view === "front" ? [0, 0, 180] : pose.position));
    controls.dispose(); controls = makeControls();
    camera.zoom = defaultZoom;
    camera.updateProjectionMatrix(); controls.update(); render();
  }

  function clear() {
    entries.forEach(entry => { scene.remove(entry.group); entry.dispose(); });
    entries = []; selected = ""; render();
  }

  function setPairs(bundles) {
    const prepared = [];
    try { for (const bundle of bundles) prepared.push(comparisonArch(bundle.pair, bundle.motion, material)); }
    catch (error) { prepared.forEach(entry => entry.dispose()); throw error; }
    clear(); entries = prepared;
    entries.forEach(entry => scene.add(entry.group));
    arch = entries.length > 1 ? "both" : entries[0].arch;
    span = arrangeComparisonArches(entries);
    host.dataset.archCount = String(entries.length);
    renderer.domElement.setAttribute("aria-label", `${entries.length > 1 ? "Upper and lower teeth together" : `${arch} teeth`}; drag to rotate, scroll to zoom, double-click a crown to focus`);
    resize(); setView();
  }

  function zoom(factor) {
    camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, controls.minZoom, controls.maxZoom);
    camera.updateProjectionMatrix(); render();
  }

  function focus(event) {
    if (!entries.length || activeIndex === null) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left)/rect.width*2-1, 1-(event.clientY-rect.top)/rect.height*2), camera);
    const hits = entries.flatMap(entry => entry.nodes.filter(node => node?.visible).flatMap(node => ray.intersectObject(node, true).map(hit => ({...hit, entry}))));
    const hit = hits.sort((a,b) => a.distance-b.distance)[0];
    if (!hit) return;
    camera.position.add(hit.point.clone().sub(controls.target)); controls.target.copy(hit.point);
    zoom(2); controls.update();
    const label = hit.object === hit.entry.meshes[0] ? hit.entry.motion?.faceLabels[hit.faceIndex] : null;
    const tooth = hit.object.userData.tooth || hit.entry.motion?.teeth.find(t => t.face_label === label)?.tooth;
    if (tooth) onTooth(tooth);
    onFocus();
  }

  renderer.domElement.addEventListener("dblclick", focus);
  const observer = new ResizeObserver(resize); observer.observe(host);
  resize(); setView();
  return {
    setPairs, setPair(scans, preview = null) { setPairs([{pair:scans, motion:preview}]); }, clear, resize, zoom, setView,
    setFrame(frame) {
      activeIndex = frame.index;
      entries.forEach(entry => entry.simulation?.setFraction(frame.fraction));
      controls.enabled = frame.index !== null; render();
    },
    selectTooth(id) { selected = id; entries.forEach(entry => entry.simulation?.select(id)); render(); },
    focusTooth(id) {
      const entry = entries.find(e => e.motion?.teeth.some(t => t.tooth === id));
      const center = entry?.simulation?.center(id);
      if (!center) return;
      entry.group.localToWorld(center);
      camera.position.add(center.clone().sub(controls.target)); controls.target.copy(center);
      controls.update(); render();
    },
    dispose() {
      disposed = true; observer.disconnect(); controls.dispose();
      renderer.domElement.removeEventListener("dblclick", focus); clear();
      material.dispose(); renderer.dispose(); host.replaceChildren();
    },
  };
}
