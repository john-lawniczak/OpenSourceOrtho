import { appendSurfacePatch, sourcePositions, validateRepair } from "./surface_repair_mesh.js";
import { repairBundle, readRepairBundle, downloadJson } from "./surface_repair_bundle.js";

export function setupSurfaceRepair(getState, replaceSurface, saving) {
  const el=id=>document.getElementById(id);
  let worker=null, epoch=0, holes=[], preview=null, busy=false, undo=[];
  const status=text=>{ el("repairStatus").textContent=text; };
  function controls() {
    const scan=getState().scan, hole=holes[el("repairHole").selectedIndex];
    el("repairFind").disabled=!scan||busy;
    el("repairHole").disabled=!holes.length||busy;
    el("repairPreview").disabled=!hole||Boolean(hole.reason)||busy;
    el("repairAccept").disabled=!preview||busy;
    el("repairCancel").disabled=!preview||busy;
    el("repairUndo").disabled=!undo.length||busy;
    el("repairExport").disabled=!scan?.repair||busy;
    el("repairEstimated").disabled=!scan?.repair;
    el("repairProvenance").textContent=scan?.repair ? `${scan.repair.patches.length} estimated patch(es) · ${scan.repair.originalFaceCount.toLocaleString()} original faces retained. Save locally stores this separate version in this browser; reopen it from My Notes. Download a repair bundle for backup.` : "Patches are estimates, not recovered tooth anatomy. Each repair becomes a separate version; new faces start unlabeled.";
  }
  function select() {
    preview=null;
    const hole=holes[el("repairHole").selectedIndex];
    getState().viewer?.showRepair(hole,false,true);
    status(hole ? hole.reason || `Opening ${hole.id} · span ${hole.diameter.toFixed(2)} scan units. Preview and inspect both sides before accepting.` : "No closed boundary candidates.");
    controls();
  }
  function reset(clearUndo=true) {
    epoch++; worker?.terminate(); worker=null; busy=false; holes=[]; preview=null;
    if(clearUndo) undo=[];
    el("repairHole").replaceChildren(); el("repairEstimated").checked=true;
    getState().viewer?.showRepair(null);
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
  el("repairMaxSize").onchange=()=>reset(false);
  el("repairPreview").onclick=()=>{
    const hole=holes[el("repairHole").selectedIndex]; if(!hole||hole.reason) return;
    preview=hole; getState().viewer.showRepair(hole,true,true);
    status("Yellow is a proposed patch. Rotate to check it; Accept creates a separate estimated surface."); controls();
  };
  el("repairCancel").onclick=select;
  el("repairAccept").onclick=async()=>{
    if(!preview||busy) return;
    const {scan,edits}=getState(), ticket=epoch, hole=preview, token=saving.savedAt();
    busy=true; controls();
    try {
      edits.endStroke();
      const next=await appendSurfacePatch(scan,edits.labels,hole);
      if(ticket!==epoch||getState().scan!==scan) return;
      // Painting can continue while hashing; preserve the latest labels on unchanged faces.
      next.labels.set(getState().edits.labels);
      undo.push({scan,token}); if(undo.length>5) undo.shift();
      replaceSurface(next.scan,next.labels,null);
      status("Patch accepted as an estimated surface. Existing labels retained; new faces need painting. Save locally to keep this version.");
    } catch(error) { status(error.message); }
    finally { if(ticket===epoch) { busy=false; controls(); } }
  };
  el("repairUndo").onclick=()=>{
    const previous=undo.pop(); if(!previous) return;
    const count=sourcePositions(previous.scan.bytes).length/9;
    replaceSurface(previous.scan,getState().edits.labels.slice(0,count),previous.token);
    status("Last patch removed. Painting on retained faces is preserved. Save this version when ready.");
  };
  el("repairEstimated").onchange=()=>getState().viewer?.setEstimatedVisible(el("repairEstimated").checked);
  el("repairExport").onclick=()=>{
    try { const {scan,edits}=getState(); downloadJson(repairBundle(scan,edits,el("reviewNotes").value),scan.filename.replace(/\.stl$/i,"-repair.json")); }
    catch(error) { status(error.message); }
  };
  el("repairImport").onchange=async()=>{
    const file=el("repairImport").files[0]; if(!file||!saving.canReplace()) return;
    const source=getState().scan,ticket=epoch;
    try {
      if(file.size>72_000_000) throw new Error("Repair bundle exceeds 72 MB.");
      const result=await readRepairBundle(JSON.parse(await file.text()));
      if(ticket!==epoch||getState().scan!==source) return;
      undo=[]; replaceSurface(result.scan,result.edits.labels,null,result.notes);
      status("Repair bundle imported. Estimated surfaces remain marked; save locally to keep a browser copy.");
    } catch(error) { status(error.message); }
    finally { el("repairImport").value=""; }
  };
  el("repairPanel").ontoggle=()=>{
    if(el("repairPanel").open) { el("reviewTool").value="orbit"; getState().viewer?.updateBrush(); }
  };
  return {reset,validate(scan) { if(scan.repair) validateRepair(scan,sourcePositions(scan.bytes).length/9); }};
}
