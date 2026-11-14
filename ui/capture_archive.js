import { parseStlGeometry } from "./stl.js";
import { RegionEdits } from "./region_edits.js";
const MAX_SCAN_BYTES = 100*1024*1024;
export function encodeScan({bytes,filename,sha256,rotation,arch,date,label}) {
  let binary = ""; const view = new Uint8Array(bytes);
  for (let i=0;i<view.length;i+=8192) binary += String.fromCharCode(...view.subarray(i,i+8192));
  return {filename,sha256,rotation,arch,date,label,bytes_base64:btoa(binary)};
}
export async function decodeScan(scan) {
  if (typeof scan?.bytes_base64 !== "string" || scan.bytes_base64.length > Math.ceil(MAX_SCAN_BYTES/3)*4) throw new Error("Archived scan exceeds size limit.");
  if (!["upper","lower"].includes(scan.arch) || typeof scan.filename !== "string"
      || !["[1,1,1]","[-1,1,-1]","[1,-1,-1]","[-1,-1,1]"].includes(JSON.stringify(scan.rotation))) throw new Error("Invalid capture metadata.");
  const bytes = Uint8Array.from(atob(scan.bytes_base64),c=>c.charCodeAt(0)).buffer;
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
  if (hash !== scan.sha256) throw new Error("Archived scan hash mismatch.");
  return {filename:scan.filename,sha256:hash,rotation:scan.rotation,arch:scan.arch,date:scan.date,label:scan.label,bytes};
}
export function validateCaptureCorrection(scan, correction) {
  const geometry = parseStlGeometry(scan.bytes), count = geometry.attributes.position.count/3; geometry.dispose();
  if (correction) RegionEdits.restore(correction,scan.sha256,count,scan.arch);
}
export function encodeCaptures(captures) {
  return {active:captures.active, groups:captures.groups.map(group=>group.map(c=>({...c,scan:encodeScan(c.scan)})))};
}
export async function decodeCaptures(raw) {
  if (raw?.groups?.length !== 2 || raw.active?.length !== 2 || raw.groups.some(g=>!Array.isArray(g) || g.length>8)) throw new Error("Invalid capture inventory.");
  let total = 0;
  const groups = [];
  for (const group of raw.groups) {
    const decoded = [], ids = new Set();
    for (const c of group) {
      for (const [key,limit] of [["acquired",10],["model",120],["damage",2000]]) if (typeof c[key] !== "string" || c[key].length>limit) throw new Error("Invalid capture notes.");
      total += c.scan?.bytes_base64?.length || 0;
      if (total > 240*1024*1024) throw new Error("Capture inventory exceeds size limit.");
      const scan = await decodeScan(c.scan), id = `${scan.arch}:${scan.sha256}`;
      if (id !== c.id || ids.has(id)) throw new Error("Duplicate or invalid capture ID.");
      ids.add(id); validateCaptureCorrection(scan,c.correction);
      decoded.push({id,scan,acquired:c.acquired,model:c.model,damage:c.damage,imported_at:typeof c.imported_at === "string" ? c.imported_at.slice(0,40) : "",correction:c.correction || null});
    }
    groups.push(decoded);
  }
  const pair = groups.map((group,i)=>group.find(c=>c.id===raw.active[i])?.scan);
  if (pair.some(s=>!s)) throw new Error("Active capture is missing from the inventory.");
  return {groups,active:[...raw.active]};
}
