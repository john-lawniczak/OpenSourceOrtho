import { parseStlGeometry } from "./stl.js";

export function sourcePositions(bytes) {
  const geometry = parseStlGeometry(bytes);
  try { return geometry.attributes.position.array.slice(); } finally { geometry.dispose(); }
}
export async function meshHash(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)), b=>b.toString(16).padStart(2,"0")).join("");
}
export function binaryStl(positions) {
  if (!positions.length || positions.length%9 || positions.some(v=>!Number.isFinite(v))) throw new Error("Invalid patch geometry.");
  const count=positions.length/9, bytes=new ArrayBuffer(84+count*50), view=new DataView(bytes);
  new Uint8Array(bytes).set(new TextEncoder().encode("OpenSource Ortho estimated surface; retain repair record"));
  view.setUint32(80,count,true);
  for(let f=0;f<count;f++) for(let c=0;c<9;c++) view.setFloat32(84+f*50+12+c*4,positions[f*9+c],true);
  return bytes;
}
export async function appendSurfacePatch(scan, labels, hole) {
  if (!hole?.triangles || hole.reason) throw new Error("Choose a supported small hole and preview it first.");
  if (scan.repair?.patches.length >= 100) throw new Error("This version already has 100 patches; inspect it before adding more.");
  if (scan.repair) validateRepair(scan, labels.length);
  const original=sourcePositions(scan.bytes), added=new Float32Array(hole.triangles);
  if (labels.length!==original.length/9) throw new Error("Painting does not match this surface.");
  let bytes;
  // Preserve every original binary face record, including normals and attributes.
  if (scan.bytes.byteLength === 84+labels.length*50 && new DataView(scan.bytes).getUint32(80,true)===labels.length) {
    bytes=new ArrayBuffer(scan.bytes.byteLength+added.length/9*50);
    new Uint8Array(bytes).set(new Uint8Array(scan.bytes));
    new Uint8Array(bytes).set(new Uint8Array(binaryStl(added),84),scan.bytes.byteLength);
    new DataView(bytes).setUint32(80,labels.length+added.length/9,true);
  } else { const all=new Float32Array(original.length+added.length); all.set(original); all.set(added,original.length); bytes=binaryStl(all); }
  const patched = sourcePositions(bytes);
  for (let i = original.length; i < patched.length; i += 9) {
    const a = [0,1,2].map(j => patched[i+3+j]-patched[i+j]), b = [0,1,2].map(j => patched[i+6+j]-patched[i+j]);
    if (Math.hypot(a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]) === 0) throw new Error("Patch collapses at STL precision; source left unchanged.");
  }
  const nextLabels=new Uint8Array(labels.length+added.length/9); nextLabels.set(labels);
  const repair={ ...scan.repair, schema:scan.repair?.schema||"ortho-surface-repair-v1", sourceSha256:scan.repair?.sourceSha256||scan.sha256,
    sourceFilename:scan.repair?.sourceFilename||scan.filename, originalFaceCount:scan.repair?.originalFaceCount??labels.length,
    sourceVisit:scan.repair?.sourceVisit||scan.visit||null, sourceCapture:scan.repair?.sourceCapture||scan.capture||null,
    patches:[...(scan.repair?.patches||[]),{ firstFace:labels.length, faceCount:added.length/9, method:hole.method||"convex-planar-boundary-fan", diameter:hole.diameter,
      ...(hole.method==="adjacent-quadratic-rim-fill"?{strength:hole.strength,fitRms:hole.fitRms}:{}),createdAt:new Date().toISOString(), estimated:true }] };
  const { visit, baseline, capture, ...rest }=scan;
  const filename=`${(repair.sourceFilename||"scan").split('/').at(-1).replace(/\.stl$/i,"")}-repaired-${repair.patches.length}${repair.trims?.length ? `-trimmed-${repair.trims.length}` : ""}.stl`;
  return { scan:{...rest, bytes, sha256:await meshHash(bytes), filename, repair}, labels:nextLabels };
}
export function validateRepair(scan, count) {
  if(!Number.isInteger(count)||count<1) throw new Error("Invalid edited surface face count.");
  const r=scan.repair;
  const trimmed=r?.schema==="ortho-surface-repair-v2";
  if(!r || !["ortho-surface-repair-v1","ortho-surface-repair-v2"].includes(r.schema) || !/^[a-f0-9]{64}$/.test(r.sourceSha256) || typeof r.sourceFilename!=="string" || !Number.isInteger(r.originalFaceCount) || r.originalFaceCount<(trimmed?0:1) || r.originalFaceCount>count || !Array.isArray(r.patches) || (!trimmed&&!r.patches.length) || r.patches.length>100) throw new Error("Invalid estimated-surface record.");
  if(trimmed && (!Array.isArray(r.trims) || !r.trims.length || r.trims.length>100 || r.trims.some(t=> !/^[a-f0-9]{64}$/.test(t.parentSha256) || !Number.isInteger(t.parentFaceCount) || !Number.isInteger(t.removedFaceCount) || t.removedFaceCount<1 || t.removedFaceCount>=t.parentFaceCount || typeof t.allowedPainted!=="boolean"))) throw new Error("Invalid trim record.");
  let end=r.originalFaceCount;
  for(const p of r.patches) {
    const curved=p.method==="adjacent-quadratic-rim-fill";
    if(p.firstFace!==end || !Number.isInteger(p.faceCount) || p.faceCount<(trimmed?1:3) || p.faceCount>(curved?4096:256) || p.estimated!==true || !["convex-planar-boundary-fan","adjacent-quadratic-rim-fill"].includes(p.method)) throw new Error("Invalid patch face ranges.");
    if(curved && (!Number.isFinite(p.strength)||p.strength<0||p.strength>1||!Number.isFinite(p.fitRms)||p.fitRms<0)) throw new Error("Invalid estimated fill parameters.");
    end+=p.faceCount;
  }
  if(end!==count || scan.visit) throw new Error("Repair must be a separate surface version.");
}
