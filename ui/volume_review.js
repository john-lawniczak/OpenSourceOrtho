import { growRegion, voxelPoint, validateVoxelAffine } from "./volume_regions.js";
import { downloadJson } from "./progress_case_archive.js";
const el=id=>document.getElementById(id),canvas=el("volumeCanvas"),context=canvas.getContext("2d");
let packet,volume,seed,masks=[],overlay=new Set(),loadGeneration=0;
async function action(fn){try{await fn();}catch(error){el("volumeStatus").textContent=error.message;}}
function axes(){return {axial:[0,1,2],coronal:[0,2,1],sagittal:[1,2,0]}[el("volumePlane").value];}
function draw(){
  if(!volume)return;const [a,b,c]=axes(),dims=packet.dimensions_xyz,slice=Number(el("volumeSlice").value);
  canvas.width=dims[a];canvas.height=dims[b];const image=context.createImageData(canvas.width,canvas.height);
  const low=Number(el("windowLow").value),high=Number(el("windowHigh").value);if(!Number.isFinite(low)||!Number.isFinite(high)||high<=low)throw new Error("Choose a valid display window.");
  for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++){
    const p=[];p[a]=x;p[b]=y;p[c]=slice;const id=p[0]+dims[0]*(p[1]+dims[1]*p[2]);
    const gray=Math.max(0,Math.min(255,(volume[id]-low)/(high-low)*255)),i=(x+y*canvas.width)*4;
    image.data.set(overlay.has(id)?[40,Math.max(gray,160),120,255]:[gray,gray,gray,255],i);
  }
  context.putImageData(image,0,0);el("sliceLabel").textContent=`${slice+1}/${dims[c]} · ${el("volumePlane").value}`;
  if(seed && seed[c]===slice){context.strokeStyle="#ff5050";context.strokeRect(seed[a]-2,seed[b]-2,5,5);}
}
function setPlane(){if(!packet)return;el("volumeSlice").max=packet.dimensions_xyz[axes()[2]]-1;el("volumeSlice").value=Math.floor(Number(el("volumeSlice").max)/2);draw();}
function updateMasks(){
  overlay=new Set();const [nx,ny]=packet.dimensions_xyz;
  for(const mask of masks)for(const [x,y,z] of mask.voxels)overlay.add(x+nx*(y+ny*z));
  el("volumeStatus").textContent=`${masks.length} draft regions · ${overlay.size} labeled voxels. ${masks.some(m=>m.truncated||m.touches_roi_boundary)?"A region reached its ROI or computation limit; inspect and refine it.":"Unreviewed intensity proposals."}`;draw();
}
el("volumeFile").onchange=()=>action(async()=>{
  const generation=++loadGeneration;
  packet=null;volume=null;seed=null;masks=[];overlay.clear();context.clearRect(0,0,canvas.width,canvas.height);
  el("seedPosition").textContent="";el("volumeStatus").textContent="Loading local volume…";
  const file=el("volumeFile").files[0];if(!file)return;if(file.size>115*1024*1024)throw new Error("Review packet exceeds size limit.");
  const data=JSON.parse(await file.text());
  if(data.schema!=="ortho-volume-review-v1"||data.dtype!=="float32-le"||data.frame!=="dicom-patient-lps-mm"||data.dimensions_xyz?.length!==3
    ||!data.dimensions_xyz.every(n=>Number.isInteger(n)&&n>0)||data.dimensions_xyz.reduce((a,b)=>a*b,1)>20000000)throw new Error("Unsupported volume packet.");
  validateVoxelAffine(data.voxel_to_patient_mm,data.voxel_spacing_mm);
  if(!/^[a-f0-9]{64}$/.test(data.source_digest)||!Array.isArray(data.intensity_range)||data.intensity_range.length!==2||!data.intensity_range.every(Number.isFinite))throw new Error("Invalid volume provenance or intensity range.");
  const raw=Uint8Array.from(atob(data.pixels_base64),c=>c.charCodeAt(0));
  if(raw.length!==data.dimensions_xyz.reduce((a,b)=>a*b,4))throw new Error("Pixel dimensions do not match packet.");
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",raw)),n=>n.toString(16).padStart(2,"0")).join("");
  if(hash!==data.pixel_sha256)throw new Error("Volume pixel hash mismatch.");
  const view=new DataView(raw.buffer),pixels=new Float32Array(raw.length/4);
  for(let i=0;i<pixels.length;i++){pixels[i]=view.getFloat32(i*4,true);if(!Number.isFinite(pixels[i]))throw new Error("Non-finite volume pixels.");}
  if(generation!==loadGeneration)return;
  packet=data;volume=pixels;seed=null;masks=[];overlay.clear();
  el("windowLow").value=data.intensity_range[0];el("windowHigh").value=Math.max(data.intensity_range[1],data.intensity_range[0]+1);
  setPlane();el("volumeStatus").textContent=`Loaded ${data.source_slices} source slices · review stride ${data.stride} · ${data.dimensions_xyz.join(" × ")} voxels. Unreviewed.`;
});
canvas.onclick=event=>action(()=>{
  if(!packet)return;const rect=canvas.getBoundingClientRect(),[a,b,c]=axes();seed=[];
  seed[a]=Math.min(canvas.width-1,Math.floor((event.clientX-rect.left)/rect.width*canvas.width));seed[b]=Math.min(canvas.height-1,Math.floor((event.clientY-rect.top)/rect.height*canvas.height));seed[c]=Number(el("volumeSlice").value);
  el("seedPosition").textContent=`Seed voxel ${seed.join(", ")} · patient LPS ${voxelPoint(seed,packet.voxel_to_patient_mm).map(n=>n.toFixed(2)).join(", ")} mm`;draw();
});
for(const id of ["volumeSlice","windowLow","windowHigh"])el(id).oninput=()=>action(draw);
el("volumePlane").onchange=()=>action(setPlane);
el("growVolume").onclick=()=>action(()=>{
  if(!seed)throw new Error("Place a seed first.");const tooth=el("volumeTooth").value.trim();
  if(tooth!=="bone"&&!/^[1-4][1-8]$/.test(tooth))throw new Error("Use an FDI tooth number or bone.");
  if(masks.some(m=>m.tooth===tooth))throw new Error("Undo the existing region before replacing this label.");
  const result=growRegion(volume,packet.dimensions_xyz,seed,{low:Number(el("growLow").value),high:Number(el("growHigh").value),radius:Number(el("growRadius").value)});
  const occupied=new Set(masks.filter(m=>m.tooth!=="bone").flatMap(m=>m.voxels.map(p=>p.join(","))));
  if(tooth!=="bone"&&result.voxels.some(p=>occupied.has(p.join(","))))throw new Error("Root regions overlap; refine the threshold or ROI.");
  masks.push({...result,tooth});updateMasks();
});
el("undoVolume").onclick=()=>action(()=>{if(masks.length){masks.pop();updateMasks();}});
el("exportVolumeMasks").onclick=()=>action(()=>{
  if(!masks.length)throw new Error("Propose a region first.");if(masks.some(m=>m.truncated))throw new Error("A region reached the computation cap. Reduce its ROI before exporting.");
  if(masks.reduce((sum,m)=>sum+m.voxels.length,0)>150000)throw new Error("Combined masks exceed the import budget. Refine the regions or use a larger downsampling stride.");
  downloadJson({schema:"ortho-volume-mask-draft-v1",source_digest:packet.source_digest,pixel_sha256:packet.pixel_sha256,
    frame:packet.frame,voxel_to_patient_mm:packet.voxel_to_patient_mm,voxel_spacing_mm:packet.voxel_spacing_mm,volume_dimensions:packet.dimensions_xyz,
    root_voxels_by_tooth:Object.fromEntries(masks.filter(m=>m.tooth!=="bone").map(m=>[m.tooth,m.voxels])),bone_voxels:masks.find(m=>m.tooth==="bone")?.voxels||[],
    model_provenance:"user-seeded-local-intensity-draft",reviewed:false,roi_boundary_regions:masks.filter(m=>m.touches_roi_boundary).map(m=>m.tooth)},"cbct-draft-masks.json");
});
