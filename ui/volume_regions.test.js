import test from "node:test";
import assert from "node:assert/strict";
import { growRegion,voxelPoint } from "./volume_regions.js";
test("seed growth respects thresholds, disconnected islands and explicit caps",()=>{
 const volume=new Float32Array(125);volume[62]=10;volume[63]=10;volume[0]=10;
 const region=growRegion(volume,[5,5,5],[2,2,2],{low:9,high:11,radius:2});
 assert.equal(region.voxels.length,2);assert.equal(region.truncated,false);
 assert.equal(growRegion(volume,[5,5,5],[2,2,2],{low:9,high:11,radius:2,maxVoxels:1}).truncated,true);
 assert.throws(()=>growRegion(volume,[5,5,5],[1,1,1],{low:9,high:11,radius:2}),/outside/);
 assert.deepEqual(voxelPoint([1,2,3],[[0,-2,0,10],[1,0,0,20],[0,0,3,30],[0,0,0,1]]),[6,21,39]);
});
