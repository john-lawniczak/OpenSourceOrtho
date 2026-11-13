import test from "node:test";
import assert from "node:assert/strict";
import { estimateHoleFill } from "./surface_estimate.js";
import { findSurfaceHoles } from "./surface_holes.js";
import { appendSurfacePatch, binaryStl, meshHash, sourcePositions } from "./surface_repair_mesh.js";
import { repairBundle, readRepairBundle } from "./surface_repair_bundle.js";
import { RegionEdits } from "./region_edits.js";

function curvedRing() {
  const ring=r=>Array.from({length:12},(_,i)=>{
    const x=r*Math.cos(i*Math.PI/6),y=r*Math.sin(i*Math.PI/6);return [x,y,.4*x*x+.02*y*y];
  });
  const inner=ring(1),outer=ring(1.5),positions=new Float32Array(inner.flatMap((p,i)=>{
    const j=(i+1)%inner.length;return [...outer[i],...outer[j],...inner[j],...outer[i],...inner[j],...p];
  }));
  return {positions,hole:findSurfaceHoles(positions,4).holes.find(h=>!h.outer)};
}
test("curved fills follow adjoining surface, retain complete rim, and never sample a back wall",()=>{
  const {positions,hole}=curvedRing(),fill=estimateHoleFill(hole,positions,4);
  assert.equal(fill.method,"adjacent-quadratic-rim-fill");
  const behind=new Float32Array([...positions,-10,-10,-5,10,-10,-5,0,10,-5]);
  assert.deepEqual(estimateHoleFill(hole,behind,4).triangles,fill.triangles);
  const flat=estimateHoleFill(hole,positions,4,0);
  assert.notDeepEqual(flat.triangles,fill.triangles);
  const edges=new Map(), key=p=>p.join(',');
  for(let i=0;i<fill.triangles.length;i+=9) {
    const tri=[0,3,6].map(j=>fill.triangles.slice(i+j,i+j+3));
    tri.forEach((a,j)=>{const k=[key(a),key(tri[(j+1)%3])].sort().join('|');edges.set(k,(edges.get(k)||0)+1);});
  }
  const rim=hole.points.map(p=>Array.from(new Float32Array(p)));
  rim.forEach((a,i)=>assert.equal(edges.get([key(a),key(rim[(i+1)%rim.length])].sort().join('|')),1));
  assert.equal([...edges.values()].filter(n=>n===1).length,rim.length);
  assert.ok([...edges.values()].every(n=>n===1||n===2));
  // Reject a surface through the proposed fill, without using it as fit support.
  const obstructed=new Float32Array([...positions,-.1,-2,-2,-.1,2,-2,-.1,0,2]);
  assert.throws(()=>estimateHoleFill(hole,obstructed,4),/intersect/);
});
test("estimated fills are separately persisted with parameters and source labels",async()=>{
  const {positions,hole}=curvedRing(),bytes=binaryStl(positions);
  const scan={bytes,sha256:await meshHash(bytes),arch:"upper",filename:"upper.stl",rotation:[1,1,1],visit:"progress-02"};
  const labels=new Uint8Array(positions.length/9).fill(12);
  const fill=estimateHoleFill(hole,positions,4,.7),next=await appendSurfacePatch(scan,labels,fill);
  assert.deepEqual(sourcePositions(next.scan.bytes).slice(0,positions.length),positions);
  assert.deepEqual(next.labels.slice(0,labels.length),labels);
  assert.ok(next.labels.slice(labels.length).every(n=>n===0));
  const bundle=repairBundle(next.scan,new RegionEdits(next.labels,"upper"),"Estimated fill needs review");
  const restored=await readRepairBundle(bundle);
  assert.equal(restored.scan.repair.patches[0].strength,.7);
  assert.equal(restored.scan.repair.patches[0].method,"adjacent-quadratic-rim-fill");
  assert.equal(restored.scan.visit,undefined);
  const bad=structuredClone(bundle);bad.scan.repair.patches[0].strength=2;
  await assert.rejects(readRepairBundle(bad),/parameters/);
});
test("outer, oversize and self-overlapping openings cannot be estimated",()=>{
  const {positions,hole}=curvedRing();
  assert.throws(()=>estimateHoleFill({...hole,outer:true},positions,4),/Outer/);
  assert.throws(()=>estimateHoleFill(hole,positions,.5),/size limit/);
  assert.throws(()=>estimateHoleFill(hole,positions,4,NaN),/following/);
  assert.throws(()=>estimateHoleFill({...hole,support:[]},positions,4),/support/);
  const crossing={...hole,points:[hole.points[0],hole.points[6],hole.points[3],hole.points[9]]};
  assert.throws(()=>estimateHoleFill(crossing,positions,4));
});
