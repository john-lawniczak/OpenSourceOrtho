import { meshHash, sourcePositions, validateRepair } from "./surface_repair_mesh.js";
import { RegionEdits } from "./region_edits.js";
export function downloadJson(value,filename) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(value)],{type:"application/json"}));
  const a=document.createElement("a"); a.href=url; a.download=filename; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export function repairBundle(scan, edits, notes) {
  if(!scan.repair) throw new Error("Accept a patch or trim before exporting a repair bundle.");
  let binary=""; const bytes=new Uint8Array(scan.bytes);
  for(let i=0;i<bytes.length;i+=8192) binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
  const { bytes:ignored,...metadata }=scan;
  return { schema:"ortho-repair-bundle-v1",scan:metadata,stlBase64:btoa(binary),labels:edits.export(scan.sha256,false),notes };
}
export async function readRepairBundle(record) {
  if(record?.schema!=="ortho-repair-bundle-v1" || typeof record.stlBase64!=="string" || record.stlBase64.length>70_000_000) throw new Error("Invalid or oversized repair bundle.");
  const source=record.scan;
  if(!source || !["upper","lower"].includes(source.arch) || typeof source.filename!=="string" || source.filename.length>500 || !Array.isArray(source.rotation) || source.rotation.length!==3 || source.rotation.some(v=>v!==1&&v!==-1)) throw new Error("Invalid repaired scan metadata.");
  const bytes=Uint8Array.from(atob(record.stlBase64),c=>c.charCodeAt(0)).buffer;
  if(bytes.byteLength<84 || bytes.byteLength!==84+new DataView(bytes).getUint32(80,true)*50) throw new Error("Repair bundle requires a complete binary STL.");
  if(await meshHash(bytes)!==source.sha256) throw new Error("Repair bundle scan hash mismatch.");
  const positions=sourcePositions(bytes),count=positions.length/9;
  if(positions.some(v=>!Number.isFinite(v))) throw new Error("Non-finite repair surface.");
  validateRepair(source,count);
  if(typeof record.notes!=="string" || record.notes.length>4000) throw new Error("Invalid repair notes.");
  const scan={bytes,sha256:source.sha256,filename:source.filename,arch:source.arch,rotation:source.rotation,repair:source.repair};
  if(source.absentTeeth !== undefined) {
    if(!Array.isArray(source.absentTeeth) || source.absentTeeth.length>32 || source.absentTeeth.some(id=>!Number.isInteger(id)||!/^[1-4][1-8]$/.test(String(id)))) throw new Error("Invalid absent-tooth metadata.");
    scan.absentTeeth=[...new Set(source.absentTeeth)];
  }
  if(source.units !== undefined) {
    if(!["unverified","mm","cm","inch","meter"].includes(source.units)) throw new Error("Invalid scan units.");
    scan.units=source.units;
  }
  if(source.paintingFront) {
    for(const key of ["direction","up"]) if(!Array.isArray(source.paintingFront[key]) || source.paintingFront[key].length!==3 || !source.paintingFront[key].every(Number.isFinite) || Math.hypot(...source.paintingFront[key])<1e-9) throw new Error("Invalid repair camera.");
    scan.paintingFront=source.paintingFront;
  }
  const edits=RegionEdits.restore(record.labels,scan.sha256,count,scan.arch);
  edits.absentTeeth=scan.absentTeeth||[];
  return {scan,edits,notes:record.notes};
}
