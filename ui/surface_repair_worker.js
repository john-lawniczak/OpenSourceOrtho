import { findSurfaceHoles } from "./surface_holes.js";
import { estimateHoleFill } from "./surface_estimate.js";
self.onmessage = ({ data }) => {
  try { self.postMessage({ result: data.action==="estimate" ? estimateHoleFill(data.hole,data.positions,data.maxDiameter,data.strength) : findSurfaceHoles(data.positions, data.maxDiameter) }); }
  catch (error) { self.postMessage({ error: error.message }); }
};
