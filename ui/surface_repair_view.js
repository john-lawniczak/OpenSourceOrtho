import * as THREE from "./vendor/three.module.js";

export function createRepairView(scene, geometry, scan) {
  const material=new THREE.MeshBasicMaterial({color:0xf4bd50,side:THREE.DoubleSide,transparent:true,opacity:.75,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-4});
  const surface=new THREE.Mesh(new THREE.BufferGeometry(),material);
  const outline=new THREE.LineLoop(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color:0xf4bd50,depthTest:false}));
  surface.renderOrder=8; outline.renderOrder=9; scene.add(surface,outline);
  const center=geometry.userData.sourceCenter;
  function transform(data) {
    const out=[];
    for(let i=0;i<data.length;i+=3) out.push(data[i]*scan.rotation[0]-center.x,data[i+2]*scan.rotation[2]-center.y,-data[i+1]*scan.rotation[1]-center.z);
    return out;
  }
  return {
    show(hole,preview=false) {
      for(const object of [surface,outline]) { object.geometry.dispose(); object.geometry=new THREE.BufferGeometry(); object.visible=Boolean(hole); }
      if(!hole) return null;
      outline.geometry.setAttribute("position",new THREE.Float32BufferAttribute(transform(hole.points.flat()),3));
      outline.geometry.computeBoundingBox();
      surface.visible=Boolean(preview && hole.triangles);
      if(surface.visible) surface.geometry.setAttribute("position",new THREE.Float32BufferAttribute(transform(hole.triangles),3));
      return outline.geometry.boundingBox.clone();
    },
    dispose() { for(const o of [surface,outline]) { scene.remove(o); o.geometry.dispose(); o.material.dispose(); } },
  };
}
