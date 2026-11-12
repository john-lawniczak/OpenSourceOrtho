import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { parseStlGeometry } from "./stl.js";
export function createBiteViewer(host) {
  const renderer=new THREE.WebGLRenderer({antialias:true});host.replaceChildren(renderer.domElement);
  const scene=new THREE.Scene();scene.background=new THREE.Color(0x172830);
  scene.add(new THREE.HemisphereLight(0xffffff,0x667788,3));
  const camera=new THREE.PerspectiveCamera(35,1,.1,5000);camera.up.set(0,0,1);
  const controls=new OrbitControls(camera,renderer.domElement);let meshes=[];
  const render=()=>renderer.render(scene,camera);controls.addEventListener("change",render);
  function resize(){renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();render();}
  const observer=new ResizeObserver(resize);observer.observe(host);
  return {setPair(pair,matrix=null){
    for(const mesh of meshes){scene.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();}
    meshes=pair.map((scan,i)=>{
      const geometry=parseStlGeometry(scan.bytes);
      if(i && matrix)geometry.applyMatrix4(new THREE.Matrix4().set(...matrix.flat()));
      const mesh=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color:i?0x64bfb3:0xe5dfce,side:THREE.DoubleSide}));scene.add(mesh);return mesh;
    });
    const box=new THREE.Box3();for(const mesh of meshes)box.union(new THREE.Box3().setFromObject(mesh));
    const center=box.getCenter(new THREE.Vector3()),span=Math.max(box.getSize(new THREE.Vector3()).length(),1);
    controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(0,-span*1.8,span*.25));controls.update();resize();
  },dispose(){observer.disconnect();controls.dispose();renderer.dispose();meshes.forEach(m=>{m.geometry.dispose();m.material.dispose();});}};
}
