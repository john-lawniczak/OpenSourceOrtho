import * as THREE from "./vendor/three.module.js";

// A separate, depth-tested overlay makes selection independent of label colors
// and lighting. It references source positions without changing their order.
export function createRegionSelection(host, scene, geometry, camera) {
  const surface = new THREE.BufferGeometry();
  surface.setAttribute("position", geometry.attributes.position);
  const indexBuffer = new THREE.BufferAttribute(new Uint32Array(geometry.attributes.position.count), 1);
  surface.setIndex(indexBuffer); surface.setDrawRange(0, 0);
  const material = new THREE.MeshBasicMaterial({
    color: 0xffb000, side: THREE.DoubleSide, polygonOffset: true,
    polygonOffsetFactor: -2, polygonOffsetUnits: -2, transparent: true, opacity: 0.55,
    depthWrite: false,
  });
  const overlay = new THREE.Mesh(surface, material);
  overlay.frustumCulled = false;
  overlay.visible = false; overlay.renderOrder = 1; scene.add(overlay);
  const marker = document.createElement("div");
  marker.id = "reviewSelectionMarker"; marker.className = "review-selection-marker";
  marker.hidden = true; host.append(marker);
  const bounds = new THREE.Box3(), point = new THREE.Vector3(), center = new THREE.Vector3();
  let showMarker = true;
  return {
    setMarkerVisible(visible) { showMarker = visible; },
    update(labels, selected) {
      bounds.makeEmpty();
      let count = 0;
      labels.forEach((id, face) => {
        if (!selected || id !== selected) return;
        for (let corner = 0; corner < 3; corner++) {
          const index = face * 3 + corner;
          indexBuffer.array[count++] = index;
          bounds.expandByPoint(point.fromBufferAttribute(geometry.attributes.position, index));
        }
      });
      indexBuffer.needsUpdate = true; surface.setDrawRange(0, count);
      overlay.visible = count > 0;
      marker.textContent = `Label ${selected}`;
      marker.dataset.selectedTooth = String(selected);
      if (overlay.visible) bounds.getCenter(center);
    },
    positionMarker() {
      point.copy(center).project(camera);
      const inView = showMarker && overlay.visible && point.z >= -1 && point.z <= 1
        && Math.abs(point.x) <= 1 && Math.abs(point.y) <= 1;
      marker.hidden = !inView;
      if (inView) {
        marker.style.left = `${(point.x + 1) * host.clientWidth / 2}px`;
        marker.style.top = `${(1 - point.y) * host.clientHeight / 2}px`;
      }
    },
    focusBounds() {
      if (bounds.isEmpty()) return null;
      // Include surrounding surface so locating a label retains some context.
      return bounds.clone().expandByScalar(bounds.getSize(point).length() * 0.3);
    },
    dispose() { scene.remove(overlay); surface.dispose(); material.dispose(); marker.remove(); },
  };
}
