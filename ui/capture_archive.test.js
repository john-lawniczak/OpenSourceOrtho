import test from "node:test";
import assert from "node:assert/strict";
import { archiveCase, restoreArchive } from "./progress_case_archive.js";
async function scan(height=1) {
  const bytes=new ArrayBuffer(134), view=new DataView(bytes);view.setUint32(80,1,true);
  view.setFloat32(108,1,true);view.setFloat32(124,height,true);
  const sha256=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
  return {bytes,sha256,filename:`capture-${height}.stl`,arch:"upper",rotation:[1,1,1],date:"2026-11-10",label:"Baseline"};
}
const metadata = {name:"Local",units:"mm",unitsConfirmed:false,corrections:[null,null],reference:"",timing:"uniform",motion:null};
test("v1 intake archives remain readable without inventing a fit or scale confirmation",async()=>{
  const source=await scan(), record={...metadata,pair:[source,source]};
  const restored=await restoreArchive(archiveCase(record));
  assert.equal(restored.motion,null);assert.equal(restored.unitsConfirmed,false);
  assert.deepEqual(restored.pair[0].bytes,source.bytes);
});
test("v2 preserves alternatives and selected capture; rejects tampering and missing active IDs",async()=>{
  const first=await scan(), second=await scan(2);
  const capture=s=>({id:`upper:${s.sha256}`,scan:s,acquired:"2026-11-10",model:"cast-1",damage:"chip",imported_at:"2026-11-14T12:00:00Z",correction:null});
  const a=capture(first), b=capture(second);
  const record={...metadata,pair:[second,first],captures:{groups:[[a,b],[a]],active:[b.id,a.id]}};
  const archived=archiveCase(record), restored=await restoreArchive(archived);
  assert.equal(restored.captures.groups[0].length,2);assert.equal(restored.pair[0].sha256,second.sha256);
  assert.equal(restored.captures.groups[0][1].damage,"chip");
  const corrupt=structuredClone(archived);corrupt.captures.groups[0][0].scan.sha256="0".repeat(64);
  await assert.rejects(restoreArchive(corrupt),/hash mismatch/);
  const missing=structuredClone(archived);missing.captures.active[0]="absent";
  await assert.rejects(restoreArchive(missing),/missing/);
});
