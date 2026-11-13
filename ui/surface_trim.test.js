import test from "node:test";
import assert from "node:assert/strict";
import { trimSurface, restoreSurfaceLabels } from "./surface_trim.js";
import { appendSurfacePatch, binaryStl, meshHash, validateRepair } from "./surface_repair_mesh.js";
import { repairBundle, readRepairBundle } from "./surface_repair_bundle.js";
import { proposePatch } from "./surface_patch.js";
import { nearestOpening } from "./surface_hole_pick.js";
import { RegionEdits } from "./region_edits.js";

async function fixture() {
  const bytes=binaryStl(new Float32Array([0,0,0,1,0,0,0,1,0, 5,0,0,6,0,0,5,1,0, 10,0,0,11,0,0,10,1,0]));
  return { bytes,sha256:await meshHash(bytes),arch:"upper",filename:"upper.stl",rotation:[1,1,1],visit:"progress-02",capture:"upper-clean" };
}
const hole=()=>proposePatch([[0,0,1],[1,0,1],[1,1,1],[0,1,1]],3);

test("trim protects painted teeth, rejects invalid or complete removal, preserves source bytes and labels",async()=>{
  const scan=await fixture(),labels=new Uint8Array([12,0,22]),before=new Uint8Array(scan.bytes).slice();
  await assert.rejects(trimSurface(scan,labels,[0]),/protected/);
  for(const faces of [[],[-1],[3],[.5]]) await assert.rejects(trimSurface(scan,labels,faces),/Brush/);
  await assert.rejects(trimSurface(scan,labels,[0,1,2],true),/entire/);
  const next=await trimSurface(scan,labels,[1]);
  assert.deepEqual(next.labels,new Uint8Array([12,22]));
  assert.deepEqual(next.parentFaces,new Uint32Array([0,2]));
  assert.deepEqual(new Uint8Array(scan.bytes),before);
  assert.deepEqual(new Uint8Array(next.scan.bytes,84,50),new Uint8Array(scan.bytes,84,50));
  assert.deepEqual(new Uint8Array(next.scan.bytes,134,50),new Uint8Array(scan.bytes,184,50));
  assert.equal(next.scan.visit,undefined);
  assert.equal(next.scan.repair.sourceSha256,scan.sha256);
  assert.equal(next.scan.repair.sourceCapture,"upper-clean");
  validateRepair(next.scan,2);
  const restored=restoreSurfaceLabels({labels,parentFaces:next.parentFaces},new Uint8Array([13,23]));
  assert.deepEqual(restored,new Uint8Array([13,0,23]));
});
test("patch/trim combinations retain estimated ranges and survive bundle roundtrip",async()=>{
  const scan=await fixture(),labels=new Uint8Array([12,0,22]);
  const patched=await appendSurfacePatch(scan,labels,hole());
  const trimmed=await trimSurface(patched.scan,patched.labels,[1,3,4,5]);
  assert.equal(trimmed.scan.repair.originalFaceCount,2);
  assert.equal(trimmed.scan.repair.patches[0].firstFace,2);
  assert.equal(trimmed.scan.repair.patches[0].faceCount,1);
  assert.deepEqual(trimmed.labels,new Uint8Array([12,22,0]));
  const added=await appendSurfacePatch(trimmed.scan,trimmed.labels,hole());
  assert.equal(added.scan.repair.trims.length,1);
  assert.equal(added.scan.repair.patches[1].firstFace,3);
  validateRepair(added.scan,7);
  const bundle=repairBundle(added.scan,new RegionEdits(added.labels,"upper"),"Trimmed mold; estimated patch");
  const imported=await readRepairBundle(bundle);
  assert.deepEqual(imported.scan.repair,added.scan.repair);
  assert.deepEqual(imported.edits.labels,added.labels);
  await assert.rejects(readRepairBundle({...bundle,scan:{...bundle.scan,repair:{...bundle.scan.repair,trims:[]}}}),/trim record/);
  const noPatches=await trimSurface(trimmed.scan,trimmed.labels,[2]);
  validateRepair(noPatches.scan,2);
  assert.equal(noPatches.scan.repair.patches.length,0);
  const undo=restoreSurfaceLabels({labels:trimmed.labels},new Uint8Array([13,23,21,11,11,11,11]));
  assert.deepEqual(undo,new Uint8Array([13,23,21]));
});
test("brush selects the nearest rim within its radius, never a distant opening",()=>{
  const holes=[{points:[[0,0,0],[2,0,0],[0,2,0]]},{points:[[8,0,0],[10,0,0],[8,2,0]]}];
  assert.equal(nearestOpening(holes,[1,.1,0],.2),0);
  assert.equal(nearestOpening(holes,[9,.1,0],.2),1);
  assert.equal(nearestOpening(holes,[5,0,0],.2),-1);
});
