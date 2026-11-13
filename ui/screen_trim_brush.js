import * as THREE from "./vendor/three.module.js";

// Pick visible face IDs in a screen circle. Depth testing prevents the eraser
// from selecting the back of the arch through a foreground surface.
export function createScreenTrimBrush(renderer, host, camera, geometry, targetPoint) {
  const circle=document.createElement("div"); circle.className="screen-trim-brush";
  circle.style.cssText="position:absolute;pointer-events:none;border:2px solid #ffbf47;border-radius:50%;box-sizing:border-box;z-index:6;display:none";
  host.append(circle);
  // Orbit/paint-only viewers never need the face-ID buffer or render target.
  let pickGeometry,material,scene,target;
  function initialize() {
    if(target) return;
    pickGeometry=new THREE.BufferGeometry(); pickGeometry.setAttribute("position",geometry.attributes.position);
    const ids=new Float32Array(geometry.attributes.position.count);
    for(let i=0;i<ids.length;i++) ids[i]=Math.floor(i/3)+1;
    pickGeometry.setAttribute("faceId",new THREE.BufferAttribute(ids,1));
    material=new THREE.ShaderMaterial({side:THREE.DoubleSide,
      vertexShader:"attribute float faceId; varying float id; void main(){ id=faceId; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
      fragmentShader:"precision highp float; varying float id; void main(){ float n=floor(id+0.5); gl_FragColor=vec4(floor(n/65536.0),mod(floor(n/256.0),256.0),mod(n,256.0),255.0)/255.0; }"});
    scene=new THREE.Scene(); scene.add(new THREE.Mesh(pickGeometry,material));
    target=new THREE.WebGLRenderTarget(1,1,{minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter});
  }
  let pointer=null,radius=0;
  function show(settings,event) {
    if(event) { const rect=renderer.domElement.getBoundingClientRect(); pointer={x:event.clientX-rect.left,y:event.clientY-rect.top}; }
    if(!pointer||!["trim","untrim"].includes(settings.mode)) { circle.style.display="none"; return; }
    const distance=camera.position.distanceTo(targetPoint());
    radius=Math.max(6,Math.min(180,settings.radius*host.clientHeight/(2*distance*Math.tan(THREE.MathUtils.degToRad(camera.fov/2)))));
    Object.assign(circle.style,{display:"block",left:`${pointer.x-radius}px`,top:`${pointer.y-radius}px`,width:`${radius*2}px`,height:`${radius*2}px`});
  }
  function select() {
    if(!pointer) return [];
    initialize();
    const size=renderer.getDrawingBufferSize(new THREE.Vector2()),scale=size.x/host.clientWidth;
    if(target.width!==size.x||target.height!==size.y) target.setSize(size.x,size.y);
    const cx=pointer.x*scale,cy=size.y-pointer.y*scale,r=radius*scale;
    const x=Math.max(0,Math.floor(cx-r)),y=Math.max(0,Math.floor(cy-r));
    const w=Math.max(0,Math.min(size.x,Math.ceil(cx+r))-x),h=Math.max(0,Math.min(size.y,Math.ceil(cy+r))-y);
    if(!w||!h) return [];
    const oldTarget=renderer.getRenderTarget(),color=renderer.getClearColor(new THREE.Color()),alpha=renderer.getClearAlpha();
    const pixels=new Uint8Array(w*h*4),faces=new Set();
    try {
      renderer.setRenderTarget(target); renderer.setClearColor(0,0); renderer.clear(); renderer.render(scene,camera);
      renderer.readRenderTargetPixels(target,x,y,w,h,pixels);
    } finally { renderer.setRenderTarget(oldTarget); renderer.setClearColor(color,alpha); }
    for(let row=0;row<h;row++) for(let col=0;col<w;col++) {
      if((x+col+.5-cx)**2+(y+row+.5-cy)**2>r*r) continue;
      const i=(row*w+col)*4,id=pixels[i]*65536+pixels[i+1]*256+pixels[i+2];
      if(id>0) faces.add(id-1);
    }
    return [...faces];
  }
  return {show,select,hide(){pointer=null;circle.style.display="none";},dispose(){circle.remove();target?.dispose();pickGeometry?.dispose();material?.dispose();}};
}
