// 3D scale-reference helpers. A loaded STL scan renders at TRUE scale in the
// viewer (only tooth movement is exaggerated, never the scan geometry), so a
// fixed-length labelled bar against the scan is an honest millimetre reference.
// Pure text/number logic here is unit-tested; the Three.js bar lives in viewer3d.

// Length of the on-scene scale bar, in scan units. When the scan units are
// confirmed millimetres this is exactly this many mm of real dentition.
export const SCALE_BAR_MM = 10;

export function scaleBarLabel() {
  return `${SCALE_BAR_MM} mm`;
}

// Status strip under the viewer toolbar. The scale reference only means millimetres
// when a scan is loaded AND its units are confirmed mm; otherwise it tells the user
// what to do rather than drawing a bar that cannot be trusted as a measurement.
export function formatScaleStatus({ enabled, hasScan, unitsConfirmed, extentMm } = {}) {
  if (!enabled) return "";
  if (!hasScan) return "Load a scan to show a true-scale reference.";
  if (!unitsConfirmed) {
    return "Confirm the scan units (mm) in Settings to show a true-scale reference.";
  }
  let status = `Scale: ${SCALE_BAR_MM} mm reference shown on the scan.`;
  if (extentMm && Number.isFinite(extentMm.x) && Number.isFinite(extentMm.y) && Number.isFinite(extentMm.z)) {
    const w = Math.round(extentMm.x);
    const h = Math.round(extentMm.y);
    const d = Math.round(extentMm.z);
    status += ` Loaded scan ≈ ${w} × ${h} × ${d} mm (W×H×D). Approximate, for review.`;
  }
  return status;
}
