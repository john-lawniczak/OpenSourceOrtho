import { el, scanFile, upload } from "./progress_inputs.js";
import { createBiteViewer } from "./bite_viewer.js";
import { downloadJson } from "./progress_case_archive.js";
let pair,registration;
const viewer=createBiteViewer(el("biteCanvas"));
const identity=()=>[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];
async function action(fn){try{await fn();}catch(error){el("biteStatus").textContent=error.message;}}
function display(){
  if(!pair)return;let matrix=null;
  if(el("showBiteProposal").checked && registration){
    matrix=registration.lower_to_upper || identity();
    if(!registration.lower_to_upper)registration.lower_offset.forEach((n,i)=>matrix[i][3]=n);
  }
  viewer.setPair(pair,matrix);
}
el("inspectBite").onclick=()=>action(async()=>{
  el("biteStatus").textContent="Loading and measuring the pair…";
  const loaded=await Promise.all([el("biteUpper").files[0],el("biteLower").files[0]].map(scanFile));
  const scans=await Promise.all(loaded.map(upload));
  scans.forEach((s,i)=>s.arch=i?"mandibular":"maxillary");
  const file=el("biteRecord").files[0],review=file?JSON.parse(await file.text()):null;
  const response=await fetch("/api/occlusion",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scans,units_confirmed:el("biteUnits").checked,bite_review:review})});
  const result=await response.json();if(!response.ok || !result.ok)throw new Error(result.errors?.join("; ")||"Bite inspection failed");
  el("biteCanvas").style.visibility="visible";
  pair=loaded;registration=result.registration;el("showBiteProposal").checked=Boolean(review);display();
  el("biteStatus").textContent=`${registration.mode} · ${registration.evidence}. Shared grid coverage ${(registration.coverage*100).toFixed(1)}%. Representative gap ${registration.occlusal_gap_mm} ${el("biteUnits").checked?"mm (user confirmed)":"scan units"}. ${registration.notes}`;
});
el("showBiteProposal").onchange=display;
el("biteTemplate").onclick=()=>action(()=>{
  if(!pair)throw new Error("Inspect the pair first.");
  downloadJson({schema:"ortho-bite-review-v1",source_hashes:{upper:pair[0].sha256,lower:pair[1].sha256},lower_to_upper:identity(),accepted:false,reviewer:"",reference_description:""},"bite-review-template.json");
});
for(const id of ["biteUpper","biteLower","biteRecord","biteUnits"])el(id).onchange=()=>{pair=null;registration=null;el("biteCanvas").style.visibility="hidden";el("biteStatus").textContent="Inputs changed. Inspect again to update the frame.";};
