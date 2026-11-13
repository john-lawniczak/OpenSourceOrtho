const sub = (a,b) => a.map((v,i) => v-b[i]);
const dot = (a,b) => a.reduce((s,v,i) => s+v*b[i],0);
const cross = (a,b) => [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
function segmentHit(p,q,t,epsilon) {
  const d=sub(q,p), e1=sub(t[1],t[0]), e2=sub(t[2],t[0]), h=cross(d,e2), det=dot(e1,h);
  if (Math.abs(det)<epsilon**3) return false;
  const s=sub(p,t[0]), u=dot(s,h)/det, r=cross(s,e1), v=dot(d,r)/det, time=dot(e2,r)/det;
  // Only interior hits: the expected shared boundary is allowed.
  return u>1e-7 && v>1e-7 && u+v<1-1e-7 && time>1e-7 && time<1-1e-7;
}
const orient = (a,b,c) => (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
function inside(p,t,eps) {
  const values=t.map((a,i) => orient(a,t[(i+1)%3],p));
  return values.every(v=>v>eps) || values.every(v=>v< -eps);
}
function intersect(a,b,eps) {
  for(let i=0;i<3;i++) if(segmentHit(a[i],a[(i+1)%3],b,eps)||segmentHit(b[i],b[(i+1)%3],a,eps)) return true;
  const normal=cross(sub(a[1],a[0]),sub(a[2],a[0])), len=Math.hypot(...normal);
  if(!len || b.some(p=>Math.abs(dot(sub(p,a[0]),normal))>eps*len)) return false;
  const axis=normal.map(Math.abs).indexOf(Math.max(...normal.map(Math.abs)));
  const aa=a.map(p=>p.filter((_,i)=>i!==axis)), bb=b.map(p=>p.filter((_,i)=>i!==axis));
  const center=t=>[0,1].map(i=>t.reduce((n,p)=>n+p[i],0)/3);
  if(inside(center(aa),bb,eps**2)||inside(center(bb),aa,eps**2)||aa.some(p=>inside(p,bb,eps**2))||bb.some(p=>inside(p,aa,eps**2))) return true;
  for(let i=0;i<3;i++) for(let j=0;j<3;j++) {
    const p=aa[i],q=aa[(i+1)%3],r=bb[j],s=bb[(j+1)%3];
    if(orient(p,q,r)*orient(p,q,s)< -(eps**4) && orient(r,s,p)*orient(r,s,q)< -(eps**4)) return true;
  }
  return false;
}
export function patchIntersectsSurface(patch, positions, diameter) {
  const low=[Infinity,Infinity,Infinity], high=[-Infinity,-Infinity,-Infinity], eps=diameter*1e-6;
  patch.forEach((v,i)=> { low[i%3]=Math.min(low[i%3],v); high[i%3]=Math.max(high[i%3],v); });
  const triangles=[];
  for(let i=0;i<patch.length;i+=9) triangles.push([0,3,6].map(j=>patch.slice(i+j,i+j+3)));
  for(let i=0;i<positions.length;i+=9) {
    let outside=false;
    for(let a=0;a<3;a++) if(Math.max(positions[i+a],positions[i+3+a],positions[i+6+a])<low[a]-eps || Math.min(positions[i+a],positions[i+3+a],positions[i+6+a])>high[a]+eps) { outside=true; break; }
    if(outside) continue;
    const tri=[0,3,6].map(j=>Array.from(positions.subarray(i+j,i+j+3)));
    if(triangles.some(p=>intersect(p,tri,eps))) return true;
  }
  return false;
}
