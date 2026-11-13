import { appendSurfacePatch, sourcePositions, validateRepair } from "./surface_repair_mesh.js";
import { repairBundle, readRepairBundle, downloadJson } from "./surface_repair_bundle.js";
import { setupSurfaceTrim } from "./surface_trim_controls.js";
import { restoreSurfaceLabels } from "./surface_trim.js";
import { nearestOpening } from "./surface_hole_pick.js";

export function setupSurfaceRepair(getState, replaceSurface, saving) {
  const el=id=>document.getElementById(id);
  let worker=null, epoch=0, holes=[], preview=null, busy=false, undo=[], inspectionLimit=0, importRequest=0;
  const trim=setupSurfaceTrim(getState,applyEdit,()=>busy);
  const status=text=>{ el("repairStatus").textContent=text; };
  function controls() {
    const scan=getState().scan, hole=holes[el("repairHole").selectedIndex];
    el("repairFind").disabled=!scan||busy;
    el("repairHole").disabled=!holes.length||busy;
    el("repairPick").disabled=!holes.length||busy;
    el("repairPreview").disabled=!hole||Boolean(hole.reason)||busy;
    el("repairEstimate").disabled=!hole||hole.outer||busy;
    el("repairFillShape").disabled=busy;
    el("repairSaveCopy").disabled=!scan?.repair||busy||Boolean(preview);
    el("repairAccept").disabled=!preview||busy;
    el("repairCancel").disabled=!preview||busy;
    el("repairUndo").disabled=!undo.length||busy;
    el("repairExport").disabled=!scan?.repair||busy;
    el("repairEstimated").disabled=!scan?.repair?.patches.length;
    el("repairProvenance").textContent=scan?.repair ? `${scan.repair.patches.length} estimated patch(es) · ${scan.repair.trims?.length||0} trim(s) · ${scan.repair.originalFaceCount.toLocaleString()} original faces retained. Save locally stores this separate version in this browser; reopen it from My Notes. Download a repair bundle for backup.` : "Patches are estimates, not recovered tooth anatomy. Each edit becomes a separate version; new faces start unlabeled.";
    trim.update();
  }
  function select() {
    preview=null;
    const hole=holes[el("repairHole").selectedIndex];
    getState().viewer?.showRepair(hole,false);
    status(hole ? hole.reason || `Opening ${hole.id} · span ${hole.diameter.toFixed(2)} scan units. Preview and inspect both sides before accepting.` : "No closed boundary candidates.");
    controls();
  }
  function reset(clearUndo=true) {
    epoch++; worker?.terminate(); worker=null; busy=false; holes=[]; preview=null;
    if(clearUndo) undo=[];
    el("repairHole").replaceChildren(); el("repairEstimated").checked=true;
    getState().viewer?.showRepair(null);
    el("surfaceEditStatus").textContent="";
    trim.reset();
    controls(); status("Find small holes to inspect. Large outer and ambiguous boundaries stay open.");
  }
  el("repairFind").onclick=()=>{
    if(busy||!getState().scan) return;
    reset(false); busy=true; controls(); status("Inspecting open boundaries… You can still rotate and pan.");
    const ticket=epoch, source=getState().scan;
    try {
      const positions=sourcePositions(source.bytes);
      worker=new Worker(new URL("./surface_repair_worker.js",import.meta.url),{type:"module"});
      worker.onmessage=({data})=>{
        if(ticket!==epoch||getState().scan!==source) return;
        worker.terminate(); worker=null; busy=false;
        if(data.error) { status(data.error); controls(); return; }
        holes=data.result.holes;
        inspectionLimit=data.result.limit;
        el("repairHole").replaceChildren(...holes.map(h=>new Option(`Opening ${h.id} · ${h.reason||`${h.diameter.toFixed(2)} units · patch available`}`,String(h.id))));
        const first=holes.findIndex(h=>!h.reason); if(first>=0) el("repairHole").selectedIndex=first;
        select();
        status(`${holes.filter(h=>!h.reason).length} patchable opening(s); ${holes.filter(h=>h.reason).length} kept open; ${data.result.rejected} irregular boundary group(s) excluded. Size cap: ${data.result.limit.toFixed(2)} scan units.`);
      };
      worker.onerror=()=>{ if(ticket!==epoch) return; worker?.terminate(); worker=null; busy=false; status("Hole inspection failed. Try a smaller scan."); controls(); };
      worker.postMessage({positions,maxDiameter:Number(el("repairMaxSize").value)},[positions.buffer]);
    } catch(error) { worker?.terminate(); worker=null; busy=false; status(error.message); controls(); }
  };
  el("repairHole").onchange=select;
  el("repairFillShape").oninput=()=>{
    el("repairFillAmount").textContent=`${Math.round(Number(el("repairFillShape").value)*100)}%`;
    if(preview?.method==="adjacent-quadratic-rim-fill") { select(); status("Surface following changed. Select Estimate hole fill again to preview this setting."); }
  };
  el("repairEstimate").onclick=()=>{
    const hole=holes[el("repairHole").selectedIndex]; if(!hole||hole.outer||busy) return;
    const source=getState().scan,ticket=epoch;
    preview=null; getState().viewer.showRepair(hole,false); busy=true; controls();
    status("Estimating a fill from the rim and adjoining surface…");
    try {
      const positions=sourcePositions(source.bytes);
      worker=new Worker(new URL("./surface_repair_worker.js",import.meta.url),{type:"module"});
      worker.onmessage=({data})=>{
        if(ticket!==epoch||getState().scan!==source) return;
        worker.terminate(); worker=null; busy=false;
        if(data.error) status(data.error);
        else { preview=data.result; getState().viewer.showRepair(preview,true); status("Yellow previews an estimated fill. Rotate to inspect both sides. Adjust Surface following and estimate again, or Accept fill, then Save edited copy. New faces can be painted after acceptance."); }
        controls();
      };
      worker.onerror=()=>{ if(ticket!==epoch) return; worker?.terminate();worker=null;busy=false;status("Fill estimation failed; no surface changed.");controls(); };
      worker.postMessage({action:"estimate",hole,positions,maxDiameter:inspectionLimit,strength:Number(el("repairFillShape").value)},[positions.buffer]);
    } catch(error) { worker?.terminate();worker=null;busy=false;status(error.message);controls(); }
  };
  el("repairMaxSize").onchange=()=>reset(false);
  el("repairPreview").onclick=()=>{
    const hole=holes[el("repairHole").selectedIndex]; if(!hole||hole.reason) return;
    preview=hole; getState().viewer.showRepair(hole,true);
    status("Yellow is a proposed patch. Rotate to check it; Accept creates a separate estimated surface."); controls();
  };
  el("repairCancel").onclick=select;
  async function applyEdit(operation, message, validateLabels=()=>{}) {
    if(busy||!getState().scan) return;
    const {scan,edits}=getState(), ticket=epoch, token=saving.savedAt();
    busy=true; controls();
    el("surfaceEditStatus").textContent="Creating a separate surface copy…";
    try {
      edits.endStroke();
      const next=await operation(scan,edits.labels);
      if(ticket!==epoch||getState().scan!==scan) return;
      // Painting can continue while hashing; preserve the latest labels on unchanged faces.
      const latest=getState().edits.labels; validateLabels(latest);
      if(next.parentFaces) next.labels=Uint8Array.from(next.parentFaces,f=>latest[f]);
      else next.labels.set(latest);
      undo.push({scan,token,labels:latest.slice(),parentFaces:next.parentFaces}); if(undo.length>5) undo.shift();
      replaceSurface(next.scan,next.labels,null);
      status(message); el("surfaceEditStatus").textContent=message;
    } catch(error) { status(error.message); el("surfaceEditStatus").textContent=error.message; }
    finally { if(ticket===epoch) { busy=false; controls(); } }
  }
  el("repairAccept").onclick=()=>{
    if(!preview||busy) return;
    const hole=preview;
    applyEdit((scan,labels)=>appendSurfacePatch(scan,labels,hole),"Patch accepted as an estimated surface. Existing labels retained; new faces need painting. Save locally to keep this version.");
  };
  el("repairUndo").onclick=()=>{
    if(busy) return;
    const previous=undo.pop(); if(!previous) return;
    replaceSurface(previous.scan,restoreSurfaceLabels(previous,getState().edits.labels),previous.token);
    status("Last surface edit undone. Painting on retained faces is preserved. Save this version when ready.");
    el("surfaceEditStatus").textContent="Last surface edit undone. Save this version when ready.";
  };
  el("repairEstimated").onchange=()=>getState().viewer?.setEstimatedVisible(el("repairEstimated").checked);
  el("repairSaveCopy").onclick=()=>el("reviewSaveLocal").click();
  el("repairExport").onclick=()=>{
    try { const {scan,edits}=getState(); downloadJson(repairBundle(scan,edits,el("reviewNotes").value),scan.filename.replace(/\.stl$/i,"-repair.json")); }
    catch(error) { status(error.message); }
  };
  el("repairImport").onchange=async()=>{
    const file=el("repairImport").files[0]; if(!file||!saving.canReplace()) return;
    const source=getState().scan,ticket=epoch,request=++importRequest,version=saving.revision();
    try {
      if(file.size>72_000_000) throw new Error("Repair bundle exceeds 72 MB.");
      const result=await readRepairBundle(JSON.parse(await file.text()));
      if(ticket!==epoch||getState().scan!==source||request!==importRequest) return;
      saving.requireUnchanged(version);
      undo=[]; replaceSurface(result.scan,result.edits.labels,null,result.notes);
      status("Repair bundle imported. Estimated surfaces remain marked; save locally to keep a browser copy.");
    } catch(error) { if(ticket===epoch&&request===importRequest) status(error.message); }
    finally { if(request===importRequest) el("repairImport").value=""; }
  };
  el("repairPanel").ontoggle=()=>{
    if(el("repairPanel").open) { el("reviewTool").value="orbit"; getState().viewer?.updateBrush(); }
  };
  return {reset,paint(faces,mode) {
      if(preview && !["trim","untrim"].includes(mode)) { status("Accept or cancel the fill preview before painting tooth labels. Preview geometry is not yet part of the scan."); return true; }
      return trim.paint(faces,mode);
    },
    pick(point,settings) {
      if(busy||!holes.length) return;
      const r=getState().scan.rotation;
      const raw=[point.x/r[0],-point.z/r[1],point.y/r[2]];
      const index=nearestOpening(holes,raw,settings.radius);
      if(index<0) { status("Brush closer to an opening's edge. Empty space cannot be painted; no surface is changed."); return; }
      el("repairHole").selectedIndex=index; select();
    },
    validate(scan) { if(scan.repair) validateRepair(scan,sourcePositions(scan.bytes).length/9); }};
}
