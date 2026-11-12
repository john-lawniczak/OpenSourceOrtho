import * as THREE from "./vendor/three.module.js";

const basis = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const inverseBasis = basis.clone().invert();
const basisQuaternion = new THREE.Quaternion().setFromRotationMatrix(basis);
const inverseQuaternion = basisQuaternion.clone().invert();
const identity = new THREE.Quaternion();
const vector = values => new THREE.Vector3(...values).applyMatrix4(basis);

export function viewerRegistration(rows) {
  return basis.clone().multiply(new THREE.Matrix4().set(...rows.flat())).multiply(inverseBasis);
}

export function motionPose(tooth, fraction) {
  const t = Math.max(0, Math.min(1, fraction));
  const pivot = vector(tooth.pivot);
  const delta = vector(tooth.translation);
  const rotation = basisQuaternion.clone().multiply(new THREE.Quaternion(...tooth.quaternion_xyzw))
    .multiply(inverseQuaternion);
  return { position: pivot.addScaledVector(delta, t), quaternion: identity.clone().slerp(rotation, t) };
}

function regionGeometry(source, indices, pivot) {
  const points = new Float32Array(indices.length * 9), normals = new Float32Array(points.length);
  indices.forEach((face, i) => {
    for (let v = 0; v < 3; v++) {
      const index = face * 3 + v, offset = i * 9 + v * 3;
      points.set([source.attributes.position.getX(index) - pivot.x,
        source.attributes.position.getY(index) - pivot.y, source.attributes.position.getZ(index) - pivot.z], offset);
      normals.set([source.attributes.normal.getX(index), source.attributes.normal.getY(index),
        source.attributes.normal.getZ(index)], offset);
    }
  });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(points, 3));
  geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  geometry.computeBoundingSphere();
  return geometry;
}

export function createMotionSurfaces(source, preview, material) {
  const group = new THREE.Group(), teeth = [], byLabel = new Map([[0, []]]);
  preview.teeth.forEach(tooth => byLabel.set(tooth.face_label, []));
  preview.faceLabels.forEach((label, face) => byLabel.get(label).push(face));
  const context = new THREE.Mesh(regionGeometry(source, byLabel.get(0), new THREE.Vector3()), material);
  group.add(context);
  for (const tooth of preview.teeth) {
    const mesh = new THREE.Mesh(regionGeometry(source, byLabel.get(tooth.face_label), vector(tooth.pivot)), material.clone());
    mesh.userData.tooth = tooth.tooth;
    group.add(mesh);
    teeth.push({ tooth, mesh });
  }
  function setFraction(t) {
    for (const { tooth, mesh } of teeth) {
      const pose = motionPose(tooth, t);
      mesh.position.copy(pose.position);
      mesh.quaternion.copy(pose.quaternion);
      mesh.updateMatrixWorld();
    }
  }
  setFraction(0);
  return {
    group, setFraction,
    select(id) {
      for (const { tooth, mesh } of teeth) mesh.material.color.set(tooth.tooth === id ? 0x49c5b6 : material.color);
    },
    center(id) { return teeth.find(({ tooth }) => tooth.tooth === id)?.mesh.position.clone(); },
    dispose() {
      context.geometry.dispose();
      for (const { mesh } of teeth) { mesh.geometry.dispose(); mesh.material.dispose(); }
    },
  };
}
