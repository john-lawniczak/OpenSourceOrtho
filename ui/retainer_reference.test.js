import test from "node:test";
import assert from "node:assert/strict";
import { prepareRetainerReference } from "./retainer_reference.js";
import { binaryStl, meshHash } from "./surface_repair_mesh.js";
import { sampleViewForStep } from "./sample_view.js";
const options={arch:"upper",units:"unverified",currentScan:true,filename:"upper.stl",captureDate:"2026-11-13"};
const source=()=>binaryStl(new Float32Array([0,0,0,1,0,0,0,1,0]));
test("retainer preparation retains exact source bytes and cannot inherit proposed movement",async()=>{
  const bytes=source(),before=bytes.slice(0),result=await prepareRetainerReference(bytes,{...options,proposed_movements:[{tooth:12,mm:1}]});
  assert.deepEqual(bytes,before);assert.equal(result.reference_model.sha256,await meshHash(bytes));
  assert.deepEqual(result.proposed_movements,[]);assert.equal(result.stage_count,0);assert.equal(result.wearable_output,false);
  assert.equal(result.source.declared_units,"unverified");assert.equal(result.review_status,"unreviewed-reference-only");
});
test("retainer reference requires a current finite scan and valid metadata",async()=>{
  for(const override of [{currentScan:false},{arch:"both"},{units:"unknown"},{captureDate:"2026-02-30"}]) await assert.rejects(prepareRetainerReference(source(),{...options,...override}));
  await assert.rejects(prepareRetainerReference(new TextEncoder().encode("not a scan").buffer,options),/triangles/);
  const invalid=source();new DataView(invalid).setFloat32(96,NaN,true);
  await assert.rejects(prepareRetainerReference(invalid,options),/finite/);
  await assert.rejects(prepareRetainerReference(source(),{...options,captureDate:"2026-13-01"}),/valid scan date/);
});
test("guided detail views do not overwrite the section 2 sample preference",()=>{
  const sample={active:true,view:"observed"};
  for(const step of ["details","review","preview","print"]) assert.equal(sampleViewForStep(sample,"simple",step),"simulation");
  assert.equal(sampleViewForStep(sample,"simple","plan"),"observed");assert.equal(sample.view,"observed");
  sample.view="simulation";assert.equal(sampleViewForStep(sample,"simple","plan"),"simulation");
});
