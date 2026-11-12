import * as THREE from "./vendor/three.module.js";

export function createFragmentView(scene, geometry) {
  const positions = geometry.attributes.position.array;
  const surface = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({
    color: 0xff36b0, side: THREE.DoubleSide, depthWrite: false, toneMapped: false, transparent: true,
    polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3,
  }));
  const markers = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({
    color: 0xff36b0, size: 6, sizeAttenuation: false, depthTest: false, depthWrite: false, toneMapped: false, transparent: true,
  }));
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.84, 1, 48), new THREE.MeshBasicMaterial({
    color: 0xffffff, depthTest: false, depthWrite: false, side: THREE.DoubleSide, toneMapped: false, transparent: true,
  }));
  let hasFocus = false;
  ring.visible = false; ring.renderOrder = 7;
  surface.renderOrder = 5; markers.renderOrder = 6;
  surface.frustumCulled = markers.frustumCulled = false;
  scene.add(surface, markers, ring);
  function bounds(group) {
    const box = new THREE.Box3(), normal = new THREE.Vector3();
    for (const face of group.faces) {
      for (let vertex = 0; vertex < 3; vertex++) box.expandByPoint(new THREE.Vector3().fromArray(positions, face * 9 + vertex * 3));
      normal.add(new THREE.Vector3().fromArray(geometry.attributes.normal.array, face * 9));
    }
    return { box, normal: normal.normalize() };
  }
  return {
    update(groups) {
      if (!groups.length) { hasFocus = false; ring.visible = false; }
      const triangles = [], points = [];
      for (const group of groups) {
        for (const face of group.faces) triangles.push(...positions.subarray(face * 9, face * 9 + 9));
        points.push(...bounds(group).box.getCenter(new THREE.Vector3()).toArray());
      }
      for (const [object, data] of [[surface, triangles], [markers, points]]) {
        object.geometry.dispose(); object.geometry = new THREE.BufferGeometry();
        object.geometry.setAttribute("position", new THREE.Float32BufferAttribute(data, 3));
      }
    },
    visible(value) { surface.visible = markers.visible = value; ring.visible = value && hasFocus; },
    focus(group) { ring.position.copy(bounds(group).box.getCenter(new THREE.Vector3())); hasFocus = true; ring.visible = true; },
    positionMarker(camera, height) {
      if (!ring.visible) return;
      ring.quaternion.copy(camera.quaternion);
      const distance = camera.position.distanceTo(ring.position);
      ring.scale.setScalar(distance * Math.tan(camera.fov * Math.PI / 360) * 28 / Math.max(height, 1));
    },
    bounds,
    dispose() { for (const object of [surface, markers, ring]) { scene.remove(object); object.geometry.dispose(); object.material.dispose(); } },
  };
}
