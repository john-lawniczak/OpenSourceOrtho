import * as THREE from "./vendor/three.module.js";

const basis = (x,y) => [1,x,y,x*x,x*y,y*y];
function solve(matrix, rhs) {
  const a=matrix.map((row,i)=>[...row,rhs[i]]);
  for(let i=0;i<6;i++) {
    let best=i; for(let j=i+1;j<6;j++) if(Math.abs(a[j][i])>Math.abs(a[best][i])) best=j;
    [a[i],a[best]]=[a[best],a[i]];
    if(Math.abs(a[i][i])<1e-10) throw new Error("Surrounding surface does not constrain a stable fill.");
    const pivot=a[i][i]; for(let k=i;k<=6;k++) a[i][k]/=pivot;
    for(let j=0;j<6;j++) if(j!==i) { const f=a[j][i]; for(let k=i;k<=6;k++) a[j][k]-=f*a[i][k]; }
  }
  return a.map(row=>row[6]);
}

// Fit only topologically adjacent support, never a ray hit on the back wall.
export function localFillFit(points, support, diameter) {
  const center=new THREE.Vector3(); points.forEach(p=>center.add(new THREE.Vector3(...p))); center.divideScalar(points.length);
  const vectors=points.map(p=>new THREE.Vector3(...p).sub(center)),normal=new THREE.Vector3();
  vectors.forEach((p,i)=>normal.add(p.clone().cross(vectors[(i+1)%vectors.length])));
  if(normal.length()<diameter*diameter*1e-8) throw new Error("Opening has no stable projection plane.");
  normal.normalize();
  const u=vectors.reduce((a,b)=>a.lengthSq()>b.lengthSq()?a:b).clone();
  u.addScaledVector(normal,-u.dot(normal)).normalize();
  const v=normal.clone().cross(u);
  const project=p=> { const d=new THREE.Vector3(...p).sub(center).divideScalar(diameter); return [d.dot(u),d.dot(v),d.dot(normal)]; };
  const rim=points.map(project), nearby=support.map(project);
  if(rim.some(p=>Math.abs(p[2])>.35)) throw new Error("Opening folds too far around the surface to estimate a single fill.");
  const samples=[...rim,...nearby.filter(p=>Math.hypot(p[0],p[1])<1.5 && Math.abs(p[2])<.6)];
  if(samples.length<8) throw new Error("Not enough surrounding surface samples to estimate curvature.");
  const matrix=Array.from({length:6},()=>Array(6).fill(0)), rhs=Array(6).fill(0);
  samples.forEach(([x,y,z],i)=> {
    const b=basis(x,y),w=i<rim.length?4:1;
    b.forEach((a,j)=> { rhs[j]+=w*a*z; b.forEach((c,k)=>matrix[j][k]+=w*a*c); });
  });
  for(let i=0;i<6;i++) matrix[i][i]+=1e-8;
  const coefficients=solve(matrix,rhs), height=(x,y)=>basis(x,y).reduce((s,a,i)=>s+a*coefficients[i],0);
  const rms=Math.sqrt(samples.reduce((s,p)=>s+(height(p[0],p[1])-p[2])**2,0)/samples.length);
  if(rms>.05) throw new Error("Nearby surface is too irregular for a stable curved estimate.");
  const low=Math.min(...samples.map(p=>p[2]))-.1,high=Math.max(...samples.map(p=>p[2]))+.1;
  function estimate(x,y) {
    let weights=0,residual=0;
    for(const p of rim) {
      const d=(x-p[0])**2+(y-p[1])**2;
      if(d<1e-18) return p[2];
      const w=1/(d*d); weights+=w; residual+=w*(p[2]-height(p[0],p[1]));
    }
    const z=height(x,y)+residual/weights;
    if(!Number.isFinite(z)||z<low||z>high) throw new Error("Estimated fill would extend too far beyond its surrounding surface.");
    return z;
  }
  const unproject=p=>center.clone().addScaledVector(u,p[0]*diameter).addScaledVector(v,p[1]*diameter).addScaledVector(normal,p[2]*diameter).toArray();
  return {rim,estimate,unproject,rms:rms*diameter};
}
