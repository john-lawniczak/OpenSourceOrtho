// Bounded six-connected intensity growth in an explicit voxel ROI; never tissue classification.
export function growRegion(volume, dimensions, seed, {low,high,radius,maxVoxels=100000}) {
  const [nx,ny,nz]=dimensions;
  if(dimensions.length!==3 || !dimensions.every(n=>Number.isInteger(n)&&n>0) || volume.length!==nx*ny*nz || !Array.isArray(seed) || seed.length!==3 || !seed.every((v,i)=>Number.isInteger(v)&&v>=0&&v<dimensions[i])
    || !Number.isFinite(low)||!Number.isFinite(high)||low>high||!Number.isInteger(radius)||radius<1||radius>100||!Number.isInteger(maxVoxels)||maxVoxels<1||maxVoxels>200000)throw new Error("Invalid growth limits or seed.");
  const index=([x,y,z])=>x+nx*(y+ny*z), start=index(seed), seen=new Set([start]),queue=[seed],voxels=[];
  if(volume[start]<low || volume[start]>high)throw new Error("Seed intensity is outside the selected range.");
  let boundary=false;
  for(let head=0;head<queue.length;head++){
    const point=queue[head];voxels.push(point);
    if(voxels.length>=maxVoxels)return {voxels,truncated:true,touches_roi_boundary:boundary};
    for(let axis=0;axis<3;axis++)for(const step of [-1,1]){
      const next=[...point];next[axis]+=step;
      if(next.some((v,i)=>v<0||v>=dimensions[i]||Math.abs(v-seed[i])>radius)){boundary=true;continue;}
      const id=index(next);if(seen.has(id))continue;seen.add(id);
      if(volume[id]>=low && volume[id]<=high)queue.push(next);
    }
  }
  return {voxels,truncated:false,touches_roi_boundary:boundary};
}
export function voxelPoint(point,affine){return affine.slice(0,3).map(row=>row[0]*point[0]+row[1]*point[1]+row[2]*point[2]+row[3]);}
export function validateVoxelAffine(matrix,spacing) {
  if(!Array.isArray(matrix)||matrix.length!==4||matrix.some(row=>!Array.isArray(row)||row.length!==4||!row.every(Number.isFinite))||JSON.stringify(matrix[3])!=="[0,0,0,1]"
     ||!Array.isArray(spacing)||spacing.length!==3||spacing.some(n=>!Number.isFinite(n)||n<=0))throw new Error("Invalid voxel coordinates.");
  for(let i=0;i<3;i++)for(let j=0;j<3;j++){
    const dot=matrix.slice(0,3).reduce((sum,row)=>sum+row[i]*row[j],0);
    const expected=i===j?spacing[i]**2:0;
    if(Math.abs(dot-expected)>spacing[i]*spacing[j]*1e-5)throw new Error("Voxel affine and spacing disagree.");
  }
}
