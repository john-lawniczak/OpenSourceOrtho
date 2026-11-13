import * as THREE from "./vendor/three.module.js";
import { SCALE_BAR_MM, scaleBarLabel } from "./scale.js";
import { makeTextSprite } from "./viewer_labels.js";
const SCALE_TICK_H = 1.2;

export function createViewerScaleBar(scene) {
  const scaleBar = new THREE.Group(); scene.add(scaleBar); scaleBar.visible = false;
  const MEASURE_MAT = new THREE.LineBasicMaterial({ color: 0x475569 });
  let scaleBarGeometry = null, scaleBarSprite = null;
  function clearScaleBar() {
    if (scaleBarGeometry) {
      scaleBarGeometry.dispose();
      scaleBarGeometry = null;
    }
    if (scaleBarSprite) {
      scaleBarSprite.material.map?.dispose();
      scaleBarSprite.material.dispose();
      scaleBarSprite = null;
    }
    scaleBar.clear();
    scaleBar.visible = false;
  }

  // Draw a labelled scale bar of SCALE_BAR_MM along the front-bottom edge of the
  // loaded scan. Only when a scan is loaded AND its units are confirmed mm - the
  // scan geometry is at true scale, so the bar is an honest millimetre reference.
  function update(box, show, unitsConfirmed) {
    clearScaleBar();
    if (!show || !unitsConfirmed) return false;
    if (!box) return false;
    const y = box.min.y + 0.4;
    const z = box.max.z + 3;
    const x0 = box.min.x;
    const xm = x0 + SCALE_BAR_MM / 2;
    const x1 = x0 + SCALE_BAR_MM;
    const points = [
      [x0, y, z], [x1, y, z], // main bar
      [x0, y, z], [x0, y + SCALE_TICK_H, z], // left tick
      [xm, y, z], [xm, y + SCALE_TICK_H * 0.6, z], // mid tick
      [x1, y, z], [x1, y + SCALE_TICK_H, z], // right tick
    ].map((p) => new THREE.Vector3(p[0], p[1], p[2]));
    scaleBarGeometry = new THREE.BufferGeometry().setFromPoints(points);
    scaleBar.add(new THREE.LineSegments(scaleBarGeometry, MEASURE_MAT));
    scaleBarSprite = makeTextSprite(scaleBarLabel());
    scaleBarSprite.scale.set(5, 1.25, 1);
    scaleBarSprite.position.set(xm, y + SCALE_TICK_H + 1.2, z);
    scaleBar.add(scaleBarSprite);
    scaleBar.visible = true;
    return true;
  }

  return { update, dispose() { clearScaleBar(); MEASURE_MAT.dispose(); scene.remove(scaleBar); } };
}
