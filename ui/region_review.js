import { setupSurfaceRepair } from "./surface_repair.js";
import { setupEmbeddedPrecision } from "./precision_embedded.js";
import { loadBrowserPainting, browserSaveSummary } from "./region_browser_saves.js";
import { sourceRotation } from "./scan_source_orientation.js";
import { setupReviewShortcuts } from "./region_review_shortcuts.js";
import { loadBaselineCaseData } from "./region_case_data.js";
import { setupRegionSaving, fetchBaselineSave } from "./region_review_save.js";
import { setupReviewControls } from "./region_review_controls.js";
import { setupFragmentReview } from "./region_fragment_review.js";
import { inferArchFromName } from "./core.js";
import { loadWeekEighteenScan, suggestedPaintingCapture } from "./scan_week_eighteen.js";
import { loadObservedPair } from "./scan_comparison_data.js";
import { loadMotionPreview } from "./scan_motion_data.js";
import { RegionEdits } from "./region_edits.js";
import { createRegionEditor } from "./region_editor_viewer.js";
import { parseStlGeometry } from "./stl.js";
import { caseStore } from "./progress_case_store.js";
const el = id => document.getElementById(id);
let scan, edits, viewer, generation = 0;
const saving = setupRegionSaving(() => ({ scan, edits }));
setupEmbeddedPrecision(saving);
setupReviewShortcuts(() => viewer?.updateBrush());
const panel = setupReviewControls({ selectTooth: selectionChanged, changeMode: () => { panel.update(Boolean(scan), selectedCount()); viewer?.updateBrush(); } });
const fragments = setupFragmentReview(() => ({ scan, edits, viewer }), id => {
  el("reviewTo").value = id; el("reviewTool").value = "orbit"; selectionChanged(); viewer?.updateBrush();
});
const repair = setupSurfaceRepair(() => ({ scan, edits, viewer }), (nextScan, labels, token, notes = el("reviewNotes").value) => {
  const sameSource = nextScan.repair?.sourceSha256 === (scan?.repair?.sourceSha256 || scan?.sha256) || nextScan.sha256 === scan?.repair?.sourceSha256;
  const pose = sameSource ? viewer?.navigationPose() : null;
  generation++; scan = nextScan; edits = new RegionEdits(labels, scan.arch);
  mount(true); if (pose) viewer.restoreNavigation(pose); saving.setSaved({ saved_at: token, notes }); saving.markDirty();
  const url = new URL(location.href); for (const key of ["baseline", "visit", "capture", "edit"]) url.searchParams.delete(key);
  history.replaceState(null, "", url);
}, saving);
function selectedCount() { return edits ? edits.labels.reduce((count, id) => count + (id === Number(el("reviewTo").value)), 0) : 0; }
function selectionChanged() { viewer?.colorLabels(edits.labels, Number(el("reviewTo").value), el("reviewOtherColors").checked); panel.update(Boolean(scan), selectedCount()); }
function refresh(changed = false) { if (changed) { saving.markDirty(); el("reviewChecked").checked = false; fragments.invalidate(); } selectionChanged(); el("reviewStatus").textContent = `${edits.undoStack.length} correction operations · ${scan?.repair ? "edited surface copy · original scan preserved" : "original scan unchanged"}`; }
function mount(repairTransition = false) {
  repair.validate(scan);
  el("reviewExport").textContent = scan.repair ? "Download repair bundle" : "Download JSON";
  viewer?.dispose();
  el("reviewSuggestedSource").hidden = scan.visit !== "progress-02";
  el("reviewCaptureNote").hidden = scan.visit !== "progress-02";
  el("reviewWorkspaceLink").href = scan.visit ? "./?chat_case=user_one" : "./";
  panel.arch(scan.arch, scan.absentTeeth || []); edits.absentTeeth = scan.absentTeeth || []; el("reviewTool").value = "orbit";
  el("reviewSource").textContent = `${scan.visit ? `USER_ONE ${scan.visit === "initial" ? "week 1 baseline" : scan.visit === "progress-01" ? "week 7 observed scan" : "week 18 observed scan"} · ` : ""}${scan.repair ? scan.repair.patches.length ? "Estimated repaired surface · " : "Trimmed surface copy · " : ""}${scan.capture === "upper-clean" ? "cleaned version · " : ""}${scan.filename || "scan"} · ${scan.arch} · ${edits.labels.length.toLocaleString()} faces`;
  el("returnCorrections").hidden = true;
  viewer = createRegionEditor(el("regionCanvas"), scan, {
    brushSettings: () => ({ mode: el("reviewEditing").disabled ? "orbit" : el("reviewTool").value, radius: Math.max(0.1, Math.min(10, Number(el("reviewRadius").value) || 1)) }),
    onSelectTooth: id => {
      if (el("reviewEditing").disabled) return;
      if (!id) { el("reviewStatus").textContent = "This surface is unlabeled. Choose its tooth number using the guide, then paint."; return; }
      el("reviewTo").value = id; selectionChanged();
    },
    onStrokeStart: () => edits.beginStroke(),
    onStrokeEnd: () => { edits.endStroke(); refresh(); },
    onSurfaceHit: (point, settings) => repair.pick(point, settings),
    onPaint: (faces, settings) => action(() => { if (repair.paint(faces, settings.mode)) return; const changed = edits.paint(faces, settings.mode === "erase" ? 0 : Number(el("reviewTo").value), settings.mode === "split" ? Number(el("reviewFrom").value) : null); refresh(changed > 0); }),
  }); fragments.reset(); repair.reset(!repairTransition); viewer.setMarkerVisible(el("reviewShowLabel").checked); viewer.setBoundariesVisible(el("reviewShowEdges").checked); refresh(); saving.update();
}
async function action(fn) { try { await fn(); } catch (error) { el("reviewStatus").textContent = error.message; } }
async function loadBaseline(arch, visit = el("reviewVisit").value, requestedCapture = null) {
  if (!["upper", "lower"].includes(arch)) throw new Error("Choose Upper or Lower first.");
  if (!saving.canReplace()) { el("reviewArch").value = scan?.arch || ""; el("reviewVisit").value = scan?.visit || "initial"; return; }
  const capture = requestedCapture || suggestedPaintingCapture(arch, visit);
  const current = ++generation, version = saving.revision();
  el("reviewStatus").textContent = `Loading USER_ONE week ${visit === "initial" ? 1 : visit === "progress-01" ? 7 : 18} ${arch}…`;
  el("reviewEditing").disabled = true; el("reviewSaveLocal").disabled = true; el("reviewExport").disabled = true;
  try {
    const [pair, saved, caseData] = await Promise.all([visit === "progress-02" ? loadWeekEighteenScan(arch, { capture }).then(scan => [scan]) : loadObservedPair(arch), fetchBaselineSave(arch, visit, capture), loadBaselineCaseData(arch, visit)]);
    const corrections = saved.saved ? saved.corrections : caseData.corrections;
    const motion = corrections || visit !== "initial" ? null : await loadMotionPreview(pair);
    if (current !== generation) return;
    saving.requireUnchanged(version);
    const nextScan = { ...pair[visit === "progress-01" ? 1 : 0], baseline: visit === "initial", visit, absentTeeth: caseData.absentTeeth };
    const mapping = motion && Object.fromEntries(motion.teeth.map(t => [t.face_label, Number(t.tooth)]));
    const count = parseStlFaceCount(nextScan.bytes);
    const nextEdits = corrections ? RegionEdits.restore(corrections, nextScan.sha256, count, arch)
      : new RegionEdits(motion ? motion.faceLabels.map(id => caseData.absentTeeth.includes(mapping[id]) ? 0 : mapping[id] || 0) : new Uint8Array(count), arch);
    scan = nextScan; edits = nextEdits; mount(); saving.setSaved(saved);
    el("reviewVisit").value = visit; void saving.refreshSummary();
    if (!saved.saved && visit !== "initial") el("reviewSaveStatus").textContent = `Week ${visit === "progress-01" ? 7 : 18} · ${capture === "upper-clean" ? "unpainted cleaned surface" : "unpainted original surface"} · choose a tooth to begin`;
    if (!saved.saved && corrections) el("reviewSaveStatus").textContent = "Published draft · boundaries need review";
    const url = new URL(location.href); url.searchParams.delete("edit"); url.searchParams.set("baseline", arch); url.searchParams.set("visit", visit); url.searchParams.set("capture", capture);
    history.replaceState(null, "", url);
  } finally {
    if (current === generation) { el("reviewArch").value = scan?.arch || ""; el("reviewVisit").value = scan?.visit || "initial"; panel.update(Boolean(scan), selectedCount()); saving.update(); }
  }
}
function parseStlFaceCount(bytes) {
  const geometry = parseStlGeometry(bytes), count = geometry.attributes.position.count / 3;
  geometry.dispose(); return count;
}
el("reviewReload").onclick = () => action(() => loadBaseline(scan?.arch, scan?.visit, scan?.capture));
el("loadSample").onclick = () => action(() => loadBaseline(el("reviewArch").value));
for (const arch of ["upper", "lower"]) el(`reviewLoad${arch}`).onclick = () => action(() => loadBaseline(arch));
for (const id of ["reviewLoadupper", "reviewLoadlower", "loadSample"]) el(id).disabled = false;
el("reviewScan").onchange = () => action(async () => {
  const file = el("reviewScan").files[0]; if (!file || !saving.canReplace()) return; const current = ++generation, version = saving.revision();
  const bytes = await file.arrayBuffer(), hash = await crypto.subtle.digest("SHA-256", bytes);
  if (current !== generation) return;
  const inferred = inferArchFromName(file.name);
  const arch = inferred ? (inferred === "mandibular" ? "lower" : "upper") : el("reviewArch").value;
  if (!["upper", "lower"].includes(arch)) throw new Error("Choose the scan arch before importing this file.");
  const sha256 = Array.from(new Uint8Array(hash), n => n.toString(16).padStart(2,"0")).join("");
  const rotation = await sourceRotation(sha256, arch);
  if (current !== generation) return;
  const nextScan = { bytes, filename: file.name, arch, autoView: true, rotation, sha256 };
  const geometry = parseStlGeometry(bytes); const count = geometry.attributes.position.count / 3; geometry.dispose();
  if (!count) throw new Error("This scan has no triangles to paint.");
  const saved = await loadBrowserPainting(nextScan).catch(() => null);
  if (current !== generation) return;
  saving.requireUnchanged(version);
  const nextEdits = saved ? RegionEdits.restore(saved.labels, sha256, count, arch) : new RegionEdits(new Uint8Array(count), arch);
  scan = saved?.scan?.repair ? { ...nextScan, repair: saved.scan.repair, rotation: saved.scan.rotation, paintingFront: saved.scan.paintingFront, absentTeeth: saved.scan.absentTeeth, units: saved.scan.units } : nextScan; edits = nextEdits; mount(); saving.setSaved(browserSaveSummary(saved));
});
el("reviewLabels").onchange = () => action(async () => {
  if (!scan) throw new Error("Load the matching scan first.");
  const file = el("reviewLabels").files[0]; if (!file || !saving.canReplace()) return;
  const target = scan, version = saving.revision(), current = ++generation;
  const record = JSON.parse(await file.text());
  if (scan !== target || current !== generation) return;
  saving.requireUnchanged(version);
  const restored = RegionEdits.restore(record, scan.sha256, edits.labels.length, scan.arch); restored.absentTeeth = scan.absentTeeth || []; edits = restored; refresh(true); el("reviewChecked").checked = record.reviewed;
});
for (const [id, fn] of [["reviewUndo", () => edits.undo()], ["reviewRedo", () => edits.redo()], ["reviewMerge", () => edits.merge(Number(el("reviewFrom").value),Number(el("reviewTo").value))]]) {
  el(id).onclick = () => action(() => {
    if (!edits) throw new Error("Load a scan first.");
    edits.endStroke();
    if (id === "reviewUndo" && !edits.undoStack.length) return;
    if (id === "reviewRedo" && !edits.redoStack.length) return;
    fn(); refresh(true);
  });
}
el("reviewExport").onclick = () => action(() => {
  if (scan?.repair) { el("repairExport").click(); return; }
  if (!edits) throw new Error("Load a scan first.");
  const blob = new Blob([JSON.stringify(edits.export(scan.sha256, el("reviewChecked").checked))], {type:"application/json"});
  const url = URL.createObjectURL(blob), a = document.createElement("a"); a.href=url; a.download=`${(scan.filename || "scan").replace(/\.stl$/i, "")}-tooth-corrections.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000); saving.exported();
});

const transferId = new URLSearchParams(location.search).get("edit");
if (transferId) void action(async () => {
  const current = ++generation, version = saving.revision();
  const record = await caseStore("get",transferId,"edits");
  if (current !== generation) return;
  saving.requireUnchanged(version);
  if (!record) throw new Error("Correction session expired. Reopen from the case.");
  scan=record.scan; edits=RegionEdits.restore(record.labels,scan.sha256,parseStlFaceCount(scan.bytes),scan.arch);
  mount(); saving.setSaved(browserSaveSummary(record)); el("reviewChecked").checked = record.labels.reviewed; el("returnCorrections").hidden = record.returnToCase === false;
});
el("reviewArch").onchange = () => {
  if (scan?.visit) void action(() => loadBaseline(el("reviewArch").value));
  else if (scan) el("reviewStatus").textContent = `Currently editing ${scan.arch}. Choose an Upper/Lower button or import another scan to change arches.`;
};
el("returnCorrections").onclick = () => action(async () => {
  const record=await caseStore("get",transferId,"edits");
  if (!record || record.scan.sha256 !== scan.sha256) throw new Error("The editor scan no longer matches the case.");
  await caseStore("put",{...record,labels:edits.export(scan.sha256,el("reviewChecked").checked),returned:true},"edits");
  el("reviewStatus").textContent="Corrections returned. In the case, click Apply returned corrections, then regenerate.";
});

el("reviewFocus").onclick = () => viewer?.focusSelected();
el("reviewOtherColors").onchange = selectionChanged;

el("reviewShowLabel").onchange = () => viewer?.setMarkerVisible(el("reviewShowLabel").checked);
el("reviewShowEdges").onchange = () => viewer?.setBoundariesVisible(el("reviewShowEdges").checked);
el("reviewZoomIn").onclick = () => viewer?.zoom(1 / 1.25);
el("reviewZoomOut").onclick = () => viewer?.zoom(1.25);
el("reviewVisit").onchange = () => {
  if (scan?.visit) void action(() => loadBaseline(scan.arch));
  else void saving.refreshSummary();
};
const requestedVisit = new URLSearchParams(location.search).get("visit") || "initial";
const requestedCapture = new URLSearchParams(location.search).get("capture") || null;
if (["initial", "progress-01", "progress-02"].includes(requestedVisit)) el("reviewVisit").value = requestedVisit;
void saving.refreshSummary();
const requestedBaseline = new URLSearchParams(location.search).get("baseline");
if (!transferId && ["upper", "lower"].includes(requestedBaseline)) void action(() => loadBaseline(requestedBaseline, requestedVisit, requestedCapture));
