import { ShapeUtils, Vector2 } from "./vendor/three.module.js";
import { localFillFit } from "./surface_fill_fit.js";
import { patchIntersectsSurface } from "./surface_patch_intersection.js";

const edge=(a,b)=>a<b?`${a}:${b}`:`${b}:${a}`;
const orient=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
function simplePolygon(points) {
  for(let i=0;i<points.length;i++) for(let j=i+1;j<points.length;j++) {
    const ni=(i+1)%points.length,nj=(j+1)%points.length;
    if(ni===j||nj===i) continue;
    const a=points[i],b=points[ni],c=points[j],d=points[nj];
    if(orient(a,b,c)*orient(a,b,d)<=0 && orient(c,d,a)*orient(c,d,b)<=0 &&
      Math.max(Math.min(a[0],b[0]),Math.min(c[0],d[0]))<=Math.min(Math.max(a[0],b[0]),Math.max(c[0],d[0])) &&
      Math.max(Math.min(a[1],b[1]),Math.min(c[1],d[1]))<=Math.min(Math.max(a[1],b[1]),Math.max(c[1],d[1]))) return false;
  }
  return true;
}

export function estimateHoleFill(hole, positions, maxDiameter=6, strength=1) {
  if(!hole || hole.outer || !hole.support?.length) throw new Error("Select an interior opening with surrounding surface support. Outer edges stay open.");
  if(!Number.isFinite(strength)||strength<0||strength>1) throw new Error("Choose surface following between 0 and 100 percent.");
  const points=hole.points;
  if(points.length<3||points.length>256) throw new Error("Estimate openings with 3–256 rim vertices.");
  const diameter=Math.hypot(...[0,1,2].map(a=>Math.max(...points.map(p=>p[a]))-Math.min(...points.map(p=>p[a]))));
  if(!Number.isFinite(maxDiameter)||!(diameter>0)||diameter>maxDiameter) throw new Error("Opening exceeds the size limit. Increase Maximum opening span and find openings again.");
  const fit=localFillFit(points,hole.support,diameter),vertices=fit.rim.map(p=>p.slice());
  if(!simplePolygon(vertices)) throw new Error("Opening overlaps itself in projection; a local fill would be ambiguous.");
  const faces=ShapeUtils.triangulateShape(vertices.map(p=>new Vector2(p[0],p[1])),[]);
  const edges=new Map();
  faces.forEach(f=>f.forEach((a,i)=> { const key=edge(a,f[(i+1)%3]); edges.set(key,(edges.get(key)||0)+1); }));
  const boundary=new Set(points.map((_,i)=>edge(i,(i+1)%points.length)));
  if(faces.length!==points.length-2 || [...boundary].some(k=>edges.get(k)!==1) || [...edges].some(([k,n])=>n!==(boundary.has(k)?1:2))) throw new Error("Cannot triangulate the complete rim without losing boundary edges.");
  const raw=points.map(p=>p.slice()),midpoints=new Map(),refined=[];
  function add(indices) {
    const p=[0,1,2].map(a=>indices.reduce((s,i)=>s+vertices[i][a],0)/indices.length);
    p[2]+=strength*(fit.estimate(p[0],p[1])-p[2]);
    const index=vertices.length; vertices.push(p); raw.push(fit.unproject(p)); return index;
  }
  for(const f of faces) {
    // Split internal edges identically on both sides, retaining every rim edge.
    if(orient(vertices[f[0]],vertices[f[1]],vertices[f[2]])<0) f.reverse();
    const perimeter=[];
    f.forEach((a,i)=> {
      const b=f[(i+1)%3],key=edge(a,b); perimeter.push(a);
      if(!boundary.has(key)) { if(!midpoints.has(key)) midpoints.set(key,add([a,b])); perimeter.push(midpoints.get(key)); }
    });
    const center=add(f);
    perimeter.forEach((a,i)=>refined.push([perimeter[(i+1)%perimeter.length],a,center]));
  }
  const triangles=refined.flatMap(f=>f.flatMap(i=>raw[i]));
  if(triangles.length/9>4096) throw new Error("Fill exceeds the bounded surface budget.");
  // Check the final STL-precision proposal, not a higher-precision surrogate.
  const rounded=Array.from(new Float32Array(triangles));
  if(patchIntersectsSurface(rounded,positions,diameter)) throw new Error("Estimated fill would intersect an existing surface. Reduce surface following or leave the opening unfilled.");
  return {...hole,reason:null,triangles:rounded,diameter,method:"adjacent-quadratic-rim-fill",strength,fitRms:fit.rms};
}
