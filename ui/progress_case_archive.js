import { validateMotionPreview } from "./scan_motion_data.js";
import { RegionEdits } from "./region_edits.js";
const MAX_SCAN_BYTES = 100 * 1024 * 1024;
function encode(bytes) {
  let binary = ""; const view = new Uint8Array(bytes);
  for (let i=0;i<view.length;i+=8192) binary += String.fromCharCode(...view.subarray(i,i+8192));
  return btoa(binary);
}
export function archiveCase(record) {
  if (!record.motion || record.pair?.length !== 2) throw new Error("Save a fitted case first.");
  return { schema: "ortho-two-visit-archive-v1", name: record.name, units: record.units,
    reference: record.reference, timing: record.timing, segmenter: record.segmenter || "active",
    motion: {...record.motion, faceLabels:undefined}, corrections:record.corrections,
    pair:record.pair.map(({bytes,filename,sha256,rotation,arch,date,label})=>({filename,sha256,rotation,arch,date,label,bytes_base64:encode(bytes)})) };
}
export async function restoreArchive(record) {
  if (record?.schema !== "ortho-two-visit-archive-v1" || record.pair?.length !== 2
      || typeof record.name !== "string" || !record.name.trim() || !["mm","cm","in"].includes(record.units)
      || record.corrections?.length !== 2 || !["active","surface-graph"].includes(record.segmenter || "active")) throw new Error("Invalid case archive.");
  const pair = await Promise.all(record.pair.map(async scan=>{
    if (typeof scan.bytes_base64 !== "string" || scan.bytes_base64.length > Math.ceil(MAX_SCAN_BYTES/3)*4) throw new Error("Archived scan exceeds size limit.");
    const bytes = Uint8Array.from(atob(scan.bytes_base64),c=>c.charCodeAt(0)).buffer;
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
    if (hash !== scan.sha256) throw new Error("Archived scan hash mismatch.");
    return {filename:scan.filename, sha256:hash,rotation:scan.rotation,arch:scan.arch,date:scan.date,label:scan.label,bytes};
  }));
  if (pair[0].arch !== pair[1].arch) throw new Error("Archived visits must have the same arch.");
  const motion = validateMotionPreview(record.motion,pair,{specimenId:"local-two-visit"});
  if (motion.units_confirmation?.unit !== record.units) throw new Error("Archive units differ from the fitted case.");
  record.corrections.forEach((correction,i)=>{
    if (correction) RegionEdits.restore(correction,pair[i].sha256,i?motion.target_face_count:motion.source_face_count,pair[i].arch);
  });
  return {name:record.name,units:record.units,reference:record.reference,timing:record.timing,
    segmenter:record.segmenter||"active",pair,corrections:record.corrections,motion:{...motion,faceLabels:undefined}};
}
export function downloadJson(record,name) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(record)],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
