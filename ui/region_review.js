import { loadObservedPair } from "./scan_comparison_data.js";
import { loadMotionPreview } from "./scan_motion_data.js";
import { RegionEdits } from "./region_edits.js";
import { createRegionEditor } from "./region_editor_viewer.js";
import { parseStlGeometry } from "./stl.js";
const el = id => document.getElementById(id);
let scan, edits, viewer, generation = 0;
function refresh() { viewer?.colorLabels(edits.labels); el("reviewChecked").checked = false; el("reviewStatus").textContent = `${edits.undoStack.length} correction operations · original scan unchanged`; }
function mount() {
  viewer?.dispose();
  viewer = createRegionEditor(el("regionCanvas"), scan, {
    brushSettings: () => ({ mode: el("reviewTool").value, radius: Math.max(0.1, Math.min(10, Number(el("reviewRadius").value) || 1)) }),
    onPaint: (faces, settings) => action(() => { edits.paint(faces, settings.mode === "erase" ? 0 : Number(el("reviewTo").value), settings.mode === "split" ? Number(el("reviewFrom").value) : null); refresh(); }),
  }); refresh();
}
async function action(fn) { try { await fn(); } catch (error) { el("reviewStatus").textContent = error.message; } }
el("loadSample").onclick = () => action(async () => {
  const current = ++generation; el("reviewStatus").textContent = "Loading baseline regions…";
  const pair = await loadObservedPair(el("reviewArch").value), motion = await loadMotionPreview(pair);
  if (current !== generation) return;
  scan = pair[0]; const mapping = Object.fromEntries(motion.teeth.map(t => [t.face_label, Number(t.tooth)]));
  edits = new RegionEdits(motion.faceLabels.map(id => mapping[id] || 0), scan.arch); mount();
});
el("reviewScan").onchange = () => action(async () => {
  const file = el("reviewScan").files[0]; if (!file) return; const current = ++generation;
  const bytes = await file.arrayBuffer(), hash = await crypto.subtle.digest("SHA-256", bytes);
  if (current !== generation) return;
  scan = { bytes, arch: el("reviewArch").value, rotation: [1,1,1], sha256: Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2,"0")).join("") };
  const geometry = parseStlGeometry(bytes); const count = geometry.attributes.position.count / 3; geometry.dispose();
  edits = new RegionEdits(new Uint8Array(count), scan.arch); mount();
});
el("reviewLabels").onchange = () => action(async () => {
  if (!scan) throw new Error("Load the matching scan first.");
  const record = JSON.parse(await el("reviewLabels").files[0].text());
  edits = RegionEdits.restore(record, scan.sha256, edits.labels.length, scan.arch); refresh();
});
for (const [id, fn] of [["reviewUndo", () => edits.undo()], ["reviewRedo", () => edits.redo()], ["reviewMerge", () => edits.merge(Number(el("reviewFrom").value),Number(el("reviewTo").value))]]) {
  el(id).onclick = () => action(() => { if (!edits) throw new Error("Load a scan first."); fn(); refresh(); });
}
el("reviewExport").onclick = () => action(() => {
  if (!edits) throw new Error("Load a scan first.");
  const blob = new Blob([JSON.stringify(edits.export(scan.sha256, el("reviewChecked").checked))], {type:"application/json"});
  const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href=url; a.download="tooth-corrections.json"; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
});
