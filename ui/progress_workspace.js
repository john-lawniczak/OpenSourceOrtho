import { fitConsistencyText } from "./fit_consistency.js";
import { bindFitReview } from "./progress_fit_review.js";
import { createScanComparison } from "./scan_comparison_viewer.js";
import { validateMotionPreview } from "./scan_motion_data.js";
import { geometryJob } from "./geometry_jobs.js";
import { caseStore } from "./progress_case_store.js";
import { el, scanFile, correctionFile, upload, orientation } from "./progress_inputs.js";
import { simulationFraction } from "./scan_history.js";
import { proximitySummary } from "./proximity_summary.js";
import { archiveCase, restoreArchive, downloadJson } from "./progress_case_archive.js";
import { RegionEdits } from "./region_edits.js";
import { renderMatchReview, collectMatchReview } from "./progress_match_review.js";
let matches = null;
const transfers = new Map();
let pair = [], corrections = [null, null], motion = null, week = 1, pending = null;
bindFitReview(() => motion);
const viewer = createScanComparison(el("caseCanvas"), { onTooth: id => { el("caseTooth").value = id; selectTooth(); } });
const status = message => { el("caseStatus").textContent = message; };
async function action(fn) { try { await fn(); } catch (error) { status(error.message); } }
function invalidate() {
  el("fitExplanation").replaceChildren();
  pending?.abort(); motion = null; viewer.clear(); el("caseWeeks").replaceChildren();
  el("caseTooth").replaceChildren(new Option("All teeth", "")); el("caseFitDetail").textContent = "";
  el("frameLabel").textContent = ""; status("Inputs changed. Fit again to update estimates.");
}
for (const id of ["caseSegmenter", "caseArch", "caseUnits", "unitsConfirmed", "referenceTeeth", "date0", "date1", "orientation0", "orientation1"]) el(id).onchange = invalidate;
for (let i=0;i<2;i++) {
  el(`scan${i}`).onchange = () => { invalidate(); pair[i] = null; corrections[i] = null; matches=null; el(`correction${i}`).value = ""; };
  el(`correction${i}`).onchange = () => { invalidate(); corrections[i] = null; };
}
function renderFrame() {
  if (!motion) return;
  const frame = { week, fraction: simulationFraction(week, motion.simulation, el("caseTiming").value), index: week === 1 ? 0 : week === 7 ? 1 : 2 };
  el("contactResult").textContent="";
  viewer.setFrame(frame);
  el("caseProximity").textContent = proximitySummary([{arch:pair[0].arch,simulation:motion.simulation}],week,el("caseTiming").value);
  for (const button of el("caseWeeks").children) button.setAttribute("aria-current", Number(button.dataset.week) === week ? "step" : "false");
  el("frameLabel").textContent = `Week ${week} · ${frame.index === 2 ? "SIMULATED ESTIMATE" : "Recorded endpoint"}`;
  selectTooth();
}
function selectTooth() {
  const id = el("caseTooth").value; viewer.selectTooth(id);
  const t = motion?.teeth.find(t => t.tooth === id);
  el("caseFitDetail").textContent = t ? `${t.tooth} · ${t.status} · endpoint pivot change ${Math.hypot(...t.translation).toFixed(3)} ${motion.units_confirmation.unit} (user-declared scale). Surface residual p90: ${t.fit?.p90_residual.toFixed(3) ?? "unavailable"}. ${fitConsistencyText(t)}`
    : motion ? `${motion.teeth.filter(t=>t.status.startsWith("estimated")).length}/${motion.teeth.length} draft regions fitted. ${motion.reference}` : "";
}
function mount(preview) {
  el("fitExplanation").replaceChildren();
  motion = validateMotionPreview(preview, pair, { specimenId: "local-two-visit" });
  if (!motion.simulation?.profiles?.[el("caseTiming").value]) el("caseTiming").value = "uniform";
  for (const option of el("caseTiming").options) option.disabled = option.value !== "uniform" && !motion.simulation?.profiles?.[option.value];
  renderMatchReview(el("matchReview"),motion,matches);
  for(const id of ["contactA","contactB"]) el(id).replaceChildren(...motion.teeth.map(t=>new Option(t.tooth,t.tooth)));
  if(motion.teeth.length>1)el("contactB").selectedIndex=1;
  viewer.setPair(pair, motion); week = 1;
  el("caseTooth").replaceChildren(new Option("All teeth", ""), ...motion.teeth.map(t => new Option(`${t.tooth} · ${t.status}`,t.tooth)));
  el("caseWeeks").replaceChildren(...Array.from({length:7}, (_,i) => {
    const button = document.createElement("button"); button.textContent = `Week ${i+1}`; button.dataset.week = i+1;
    button.onclick = () => { week=i+1; renderFrame(); }; return button;
  })); renderFrame();
}
el("fitVisits").onclick = () => action(async () => {
  if (!el("unitsConfirmed").checked) throw new Error("Confirm the scale used by both scans first.");
  if (pending) throw new Error("Wait for the current fit to stop.");
  const controller = new AbortController(); pending = controller;
  el("fitVisits").disabled = true; el("cancelFit").disabled = false; status("Loading scans and fitting draft regions…");
  try {
    const loaded = await Promise.all([0,1].map(async i => {
      const scan = pair[i] || await scanFile(el(`scan${i}`).files[0], i);
      return { ...scan, arch: el("caseArch").value, rotation: orientation(i), date: el(`date${i}`).value };
    }));
    const edited = await Promise.all([0,1].map(i => el(`correction${i}`).files[0] ? correctionFile(el(`correction${i}`).files[0]) : corrections[i]));
    controller.signal.throwIfAborted();
    const payload = { scans: await Promise.all(loaded.map(upload)), arch: loaded[0].arch,
      units: el("caseUnits").value, units_confirmed: true, corrections: edited, matches, segmenter: el("caseSegmenter").value,
      reference_teeth: el("referenceTeeth").value.split(",").map(s=>s.trim()).filter(Boolean) };
    const result = await geometryJob("motion", payload, { signal: controller.signal });
    controller.signal.throwIfAborted();
    if (!result.ok) throw new Error(result.errors?.join("; ") || "Fit failed");
    pair = loaded; corrections = edited; mount(result.preview); status("Fit complete. Review tooth regions and estimated motion; correct labels and regenerate as needed.");
  } finally { pending = null; el("fitVisits").disabled = false; el("cancelFit").disabled = true; }
});
el("cancelFit").onclick = () => pending?.abort();
el("caseTooth").onchange = selectTooth;
el("caseTiming").onchange = renderFrame;
el("focusTooth").onclick = () => viewer.focusTooth(el("caseTooth").value);
el("resetView").onclick = () => viewer.setView("front");
el("zoomIn").onclick = () => viewer.zoom(1.25); el("zoomOut").onclick = () => viewer.zoom(0.8);
async function listCases() { const names = await caseStore("getAllKeys"); el("savedCases").replaceChildren(...names.map(n => new Option(n,n))); }
el("saveCase").onclick = () => action(async () => {
  if (!motion || pending) throw new Error("Complete a fit before saving.");
  const name = el("caseName").value.trim(); if (!name) throw new Error("Name the case.");
  await caseStore("put", { name, pair, corrections, motion: { ...motion, faceLabels: undefined },
    segmenter: el("caseSegmenter").value, timing: el("caseTiming").value, reference: el("referenceTeeth").value, units: el("caseUnits").value });
  await listCases(); el("savedCases").value = name; status("Case saved locally, including source scans, corrections, and fit.");
});
el("openCase").onclick = () => action(async () => {
  if (pending) throw new Error("Cancel fitting before opening another case.");
  const record = await caseStore("get", el("savedCases").value); if (!record) throw new Error("Choose a saved case.");
  pair = record.pair; corrections = record.corrections; matches = record.motion.match_overrides || null;
  el("caseArch").value = pair[0].arch; el("caseUnits").value = record.units; el("unitsConfirmed").checked = true;
  el("referenceTeeth").value = record.reference; el("caseName").value = record.name;
  for (let i=0;i<2;i++) { el(`orientation${i}`).value=JSON.stringify(pair[i].rotation); el(`date${i}`).value=pair[i].date; el(`scan${i}`).value=""; el(`correction${i}`).value=""; }
  el("caseSegmenter").value = record.segmenter || "active";
  el("caseTiming").value = record.timing || "uniform";
  mount(record.motion); status(`Opened ${record.name}: ${pair.map(s=>s.filename).join(" → ")}`);
});
for (let i=0;i<2;i++) el(`exportRegions${i}`).onclick = () => action(() => {
  if (!motion) throw new Error("Fit scans first.");
  const encoded = i ? motion.target_face_labels_base64 : motion.moving_face_labels_base64;
  const mapping = Object.fromEntries(motion.teeth.map(t=>[t.face_label,Number(t.tooth)]));
  const labels = Uint8Array.from(atob(encoded), c=>mapping[c.charCodeAt(0)]||0);
  const record = new RegionEdits(labels,pair[i].arch).export(pair[i].sha256);
  const url=URL.createObjectURL(new Blob([JSON.stringify(record)],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download=`${i ? "later" : "baseline"}-draft-regions.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
void action(listCases);

for (let i=0;i<2;i++) el(`editRegions${i}`).onclick = () => action(async () => {
  if (!motion || pending) throw new Error("Complete the fit first.");
  const name=crypto.randomUUID(), scan=pair[i];
  const encoded=i?motion.target_face_labels_base64:motion.moving_face_labels_base64;
  const mapping=Object.fromEntries(motion.teeth.map(t=>[t.face_label,Number(t.tooth)]));
  const labels=corrections[i] || new RegionEdits(Uint8Array.from(atob(encoded),c=>mapping[c.charCodeAt(0)]||0),scan.arch).export(scan.sha256);
  const popup=window.open("about:blank","_blank");
  try {
    await caseStore("put",{name,scan,labels,returned:false},"edits"); transfers.set(i,name);
    if (popup) { popup.opener=null; popup.location.href=`./region-review.html?edit=${encodeURIComponent(name)}`; }
    else status("Allow a new tab to open the correction editor.");
  } catch(error) { popup?.close(); throw error; }
});
el("applyCorrections").onclick = () => action(async () => {
  if (pending) throw new Error("Cancel fitting before applying corrections.");
  const returned=[];
  for (const [i,name] of transfers) {
    const edit=await caseStore("get",name,"edits");
    if (!edit?.returned) continue;
    if (edit.scan.sha256 !== pair[i]?.sha256 || edit.scan.arch !== el("caseArch").value) throw new Error("Returned corrections belong to previous case inputs.");
    RegionEdits.restore(edit.labels,pair[i].sha256,edit.labels.face_count,pair[i].arch);
    returned.push([i,edit.labels,name]);
  }
  if (!returned.length) throw new Error("No returned corrections yet.");
  invalidate(); matches=null;
  for (const [i,labels,name] of returned) { corrections[i]=labels;el(`correction${i}`).value="";await caseStore("delete",name,"edits");transfers.delete(i); }
  status("Corrections applied. Regenerate to update matches and motion.");
});
el("backupCase").onclick = () => action(async () => {
  const record=await caseStore("get",el("savedCases").value);
  if (!record) throw new Error("Save or select a case first.");
  downloadJson(archiveCase(record),"tooth-progress.orthocase");
});
el("restoreCase").onchange = () => action(async () => {
  if (pending) throw new Error("Cancel fitting before restoring a case.");
  const file=el("restoreCase").files[0];el("restoreCase").value="";if(!file)return;
  if(file.size>280*1024*1024)throw new Error("Archive exceeds size limit.");
  const record=await restoreArchive(JSON.parse(await file.text()));
  // Preserve existing cases: import gets a unique name rather than overwriting.
  const keys=await caseStore("getAllKeys");const base=record.name;let suffix=1;
  while(keys.includes(record.name))record.name=`${base} (import ${suffix++})`;
  await caseStore("put",record);await listCases();el("savedCases").value=record.name;
  status("Backup verified and restored. Open the saved case to continue.");
});

el("applyMatches").onclick = () => action(() => { const reviewed=collectMatchReview(el("matchReview"));invalidate();matches=reviewed;status("Match mapping applied. Regenerate to fit selected pairs."); });
el("resetMatches").onclick = () => { invalidate();matches=null;status("Automatic matching selected. Regenerate to update estimates."); };

el("checkContact").onclick = () => action(async () => {
  if(!motion || pending)throw new Error("Complete a fit first.");
  const selected=motion, selectedWeek=week, selectedTiming=el("caseTiming").value;
  el("checkContact").disabled=true;el("contactResult").textContent="Checking all surface triangles…";
  try {
    const scan=await upload(pair[0]);
    const result=await geometryJob("contact",{scan,preview:{...motion,faceLabels:undefined},teeth:[el("contactA").value,el("contactB").value],fraction:simulationFraction(week,motion.simulation,selectedTiming)});
    if(motion!==selected || week!==selectedWeek || el("caseTiming").value!==selectedTiming)return;
    if(!result.ok)throw new Error(result.errors.join("; "));
    const report=result.result;
    el("contactResult").textContent=report.status==="complete"?`Fitted week ${selectedWeek}, ${result.teeth.join(" / ")}: full-surface distance ${report.distance.toFixed(4)} scan units. ${report.surface_contact_or_intersection?"Surfaces touch or intersect. ":""}${result.limitation}`:`${report.status}: ${report.reason}`;
  } finally {el("checkContact").disabled=false;}
});
