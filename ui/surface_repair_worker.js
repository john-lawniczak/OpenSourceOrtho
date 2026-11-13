import { findSurfaceHoles } from "./surface_holes.js";
self.onmessage = ({ data }) => {
  try { self.postMessage({ result: findSurfaceHoles(data.positions, data.maxDiameter) }); }
  catch (error) { self.postMessage({ error: error.message }); }
};
