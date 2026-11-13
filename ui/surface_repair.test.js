import test from "node:test";
import assert from "node:assert/strict";
import { findSurfaceHoles } from "./surface_holes.js";
import { proposePatch } from "./surface_patch.js";
import { patchIntersectsSurface } from "./surface_patch_intersection.js";
import { appendSurfacePatch, binaryStl, meshHash, sourcePositions, validateRepair } from "./surface_repair_mesh.js";
import { repairBundle, readRepairBundle } from "./surface_repair_bundle.js";
import { RegionEdits } from "./region_edits.js";
function ring() {
  const outer=[[-10,-10,0],[10,-10,0],[10,10,0],[-10,10,0]],inner=[[-.5,-.5,0],[.5,-.5,0],[.5,.5,0],[-.5,.5,0]];
  return new Float32Array(outer.flatMap((p,i)=>[...p,...outer[(i+1)%4],...inner[(i+1)%4],...p,...inner[(i+1)%4],...inner[i]]));
}
test("finds a small inner opening, preserves outer edges, and closes only the chosen loop", async()=>{
  const positions=ring(),result=findSurfaceHoles(positions,3);
  assert.equal(result.holes.length,2);
  assert.equal(result.holes.filter(h=>h.reason).length,1);
  const hole=result.holes.find(h=>!h.reason);
  assert.equal(hole.triangles.length,36);
  const bytes=binaryStl(positions),sha256=await meshHash(bytes),labels=Uint8Array.from({length:8},()=>12);
  const scan={bytes,sha256,filename:"upper.stl",rotation:[1,1,1],arch:"upper",visit:"progress-02",capture:"upper-clean",absentTeeth:[18,28,38,48],units:"unverified"};
  const next=await appendSurfacePatch(scan,labels,hole);
  assert.deepEqual(new Uint8Array(next.scan.bytes,84,bytes.byteLength-84),new Uint8Array(bytes,84));
  assert.deepEqual(next.labels,Uint8Array.from([...labels,0,0,0,0]));
  assert.equal(next.scan.visit,undefined);
  assert.equal(next.scan.repair.sourceSha256,sha256);
  assert.equal(next.scan.repair.sourceVisit,"progress-02");
  validateRepair(next.scan,12);
  const after=findSurfaceHoles(sourcePositions(next.scan.bytes),3);
  assert.equal(after.holes.length,1); assert.equal(after.rejected,0);
  assert.match(after.holes[0].reason,/Outer/);
  const bundle=repairBundle(next.scan,new RegionEdits(next.labels,"upper"),"Model gap, estimated patch");
  const imported=await readRepairBundle(bundle);
  assert.equal(imported.scan.sha256,next.scan.sha256);
  assert.deepEqual(imported.edits.labels,next.labels);
  assert.equal(imported.notes,"Model gap, estimated patch");
  assert.deepEqual(imported.scan.absentTeeth,scan.absentTeeth);
  assert.equal(imported.scan.units,"unverified");
  assert.throws(()=>imported.edits.paint([0],18),/reported removed/);
  await assert.rejects(readRepairBundle({...bundle,scan:{...bundle.scan,absentTeeth:[99]}}),/absent-tooth/);
  await assert.rejects(readRepairBundle({...bundle,scan:{...bundle.scan,units:"verified"}}),/units/);
  await assert.rejects(readRepairBundle({...bundle,scan:{...bundle.scan,sha256:"0".repeat(64)}}),/hash/);
  await assert.rejects(readRepairBundle({...bundle,scan:{...bundle.scan,repair:{...bundle.scan.repair,originalFaceCount:7}}}),/ranges/);
});
test("rejects large, curved, concave and self crossing openings",()=>{
  assert.match(proposePatch([[0,0,0],[4,0,0],[4,4,0],[0,4,0]],3).reason,/limit/);
  assert.match(proposePatch([[0,0,0],[1,0,0],[1,1,1],[0,1,0]],3).reason,/curved/);
  assert.match(proposePatch([[0,0,0],[1,0,0],[.3,.3,0],[1,1,0],[0,1,0]],3).reason,/convex/);
  assert.ok(proposePatch([[0,0,0],[1,1,0],[0,1,0],[1,0,0]],3).reason);
  assert.throws(()=>findSurfaceHoles(new Float32Array([NaN,0,0,1,0,0,0,1,0])),/finite/);
  assert.throws(()=>findSurfaceHoles(ring(),NaN),/positive/);
});
test("rejects branching or inconsistent boundary topology",()=>{
  const tri=[0,0,0,1,0,0,0,1,0],other=[0,0,0,-1,0,0,0,-1,0];
  assert.equal(findSurfaceHoles(new Float32Array([...tri,...other])).rejected,1);
  const positions=ring(); positions.set([...positions.slice(0,3),...positions.slice(6,9),...positions.slice(3,6)],0);
  assert.ok(findSurfaceHoles(positions).rejected>0);
});
test("patch intersection checks reject surfaces through and over a proposed fill",()=>{
  const patch=proposePatch([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],3);
  assert.equal(patchIntersectsSurface(patch.triangles,new Float32Array([.2,.1,0,.8,.1,0,.5,.8,0]),2),true);
  assert.equal(patchIntersectsSurface(patch.triangles,new Float32Array([.2,.1,-1,.8,.1,1,.5,.8,1]),2),true);
  assert.equal(patchIntersectsSurface(patch.triangles,new Float32Array([2,2,0,3,2,0,2,3,0]),2),false);
});
