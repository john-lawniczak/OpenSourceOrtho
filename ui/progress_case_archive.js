import { validateMotionPreview } from "./scan_motion_data.js";
import { encodeScan, decodeScan, encodeCaptures, decodeCaptures, validateCaptureCorrection } from "./capture_archive.js";
export function archiveCase(record) {
  if (record.pair?.length !== 2) throw new Error("Save a two-visit case first.");
  return { schema: record.captures ? "ortho-two-visit-archive-v2" : "ortho-two-visit-archive-v1", name: record.name, units: record.units,
    unitsConfirmed:record.unitsConfirmed ?? Boolean(record.motion), reference: record.reference, timing: record.timing, segmenter: record.segmenter || "active",
    motion: record.motion ? {...record.motion, faceLabels:undefined} : null, corrections:record.corrections,
    ...(record.captures ? {captures:encodeCaptures(record.captures)} : {pair:record.pair.map(encodeScan)}) };
}
export async function restoreArchive(record) {
  if (!["ortho-two-visit-archive-v1","ortho-two-visit-archive-v2"].includes(record?.schema)
      || typeof record.name !== "string" || !record.name.trim() || !["mm","cm","in"].includes(record.units)
      || (record.unitsConfirmed !== undefined && typeof record.unitsConfirmed !== "boolean")
      || record.corrections?.length !== 2 || !["active","surface-graph"].includes(record.segmenter || "active")) throw new Error("Invalid case archive.");
  let pair, captures;
  if (record.schema.endsWith("v2")) {
    captures = await decodeCaptures(record.captures);
    pair = captures.groups.map((group,i)=>group.find(c=>c.id===captures.active[i]).scan);
  } else {
    if (record.pair?.length !== 2) throw new Error("Invalid case archive.");
    pair = await Promise.all(record.pair.map(decodeScan));
  }
  if (pair[0].arch !== pair[1].arch) throw new Error("Archived visits must have the same arch.");
  const motion = record.motion ? validateMotionPreview(record.motion,pair,{specimenId:"local-two-visit"}) : null;
  if (motion && motion.units_confirmation?.unit !== record.units) throw new Error("Archive units differ from the fitted case.");
  record.corrections.forEach((correction,i)=>validateCaptureCorrection(pair[i],correction));
  return {name:record.name,units:record.units,unitsConfirmed:record.unitsConfirmed ?? Boolean(motion),reference:record.reference,timing:record.timing,
    segmenter:record.segmenter||"active",pair,captures,corrections:record.corrections,motion:motion ? {...motion,faceLabels:undefined} : null};
}
export function downloadJson(record,name) {
  const url=URL.createObjectURL(new Blob([JSON.stringify(record)],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
