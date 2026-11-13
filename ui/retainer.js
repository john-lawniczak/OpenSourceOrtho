import { prepareRetainerReference } from "./retainer_reference.js";
import { createRegionEditor } from "./region_editor_viewer.js";
import { downloadJson } from "./surface_repair_bundle.js";
const el=id=>document.getElementById(id);
let generation=0,reference=null,bytes=null,viewer=null,mode="orbit";
function clear() {
  generation++;reference=null;bytes=null;viewer?.dispose();viewer=null;
  el("retainerResult").hidden=true;el("retainerStatus").textContent="Scan details changed. Prepare the reference again.";
  el("retainerPrepare").disabled=false;
}
for(const id of ["retainerFile","retainerArch","retainerUnits","retainerDate","retainerCurrent"]) el(id).addEventListener("change",clear);
el("retainerForm").onsubmit=async event=>{
  event.preventDefault();clear();const ticket=generation,file=el("retainerFile").files[0];
  const options={filename:file?.name,arch:el("retainerArch").value,units:el("retainerUnits").value,captureDate:el("retainerDate").value,currentScan:el("retainerCurrent").checked};
  el("retainerPrepare").disabled=true;el("retainerStatus").textContent="Checking the current scan and preparing an unchanged reference…";
  try {
    if(!file||!file.name.toLowerCase().endsWith(".stl")||file.size>50_000_000) throw new Error("Choose an STL of up to 50 MB.");
    const source=await file.arrayBuffer(),record=await prepareRetainerReference(source,options);
    if(ticket!==generation) return;
    el("retainerResult").hidden=false;
    viewer=createRegionEditor(el("retainerCanvas"),{bytes:source,arch:options.arch,rotation:[1,1,1],autoView:true},
      {brushSettings:()=>({mode,radius:1}),onPaint:()=>{}});
    viewer.colorLabels(new Uint8Array(record.source.face_count));
    bytes=source;reference=record;
    el("retainerSummary").textContent=`${record.source.filename} · ${options.arch} · ${record.source.face_count.toLocaleString()} faces · units ${options.units} · 0 proposed movements`;
    el("retainerStatus").textContent="Reference ready for review. Source geometry is unchanged; no wearable retainer was generated.";
  } catch(error) { if(ticket===generation) {clear();el("retainerStatus").textContent=error.message;} }
  finally { if(ticket===generation) el("retainerPrepare").disabled=false; }
};
for(const [id,value] of [["retainerRotate","orbit"],["retainerPan","pan"]]) el(id).onclick=()=>{
  mode=value;viewer?.updateBrush();el("retainerRotate").setAttribute("aria-pressed",String(mode==="orbit"));el("retainerPan").setAttribute("aria-pressed",String(mode==="pan"));
};
el("retainerRecord").onclick=()=>{if(reference) downloadJson(reference,"retainer-preparation.json");};
el("retainerDownload").onclick=()=>{
  if(!reference||!bytes) return;
  const url=URL.createObjectURL(new Blob([bytes],{type:"model/stl"})),link=document.createElement("a");
  link.href=url;link.download=reference.reference_model.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
if(window.parent!==window && new URLSearchParams(location.search).get("embedded")==="1") {
  el("retainerBack").onclick=event=>{event.preventDefault();parent.postMessage({type:"retainer-return"},location.origin);};
  document.addEventListener("keydown",event=>{if(event.key==="Escape") parent.postMessage({type:"retainer-return"},location.origin);});
}
