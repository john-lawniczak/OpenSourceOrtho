import { el, state } from "./state.js";

export function renderProfile() {
  const sample = state.sample.active;
  const scans = state.scanSources.length || state.files.length;
  el("teethProfileStatus").textContent = sample ? "Return to your own scans" : scans ? `${scans} scan${scans === 1 ? "" : "s"} · your workspace` : "Start with your scan";
  for (const id of ["simpleStlFile", "stlFile"]) el(id).disabled = sample;
  el("uploadHeading").textContent = sample ? "1 · Supplied STL scans" : "1 · Upload your scan files";
  el("uploadIntroduction").textContent = sample
    ? "Upper and lower STL files are already loaded. Select a tooth in step 2, or return to Your Teeth Profile to upload your own scans."
    : "Add upper or lower 3D scans. Common mesh and point-cloud formats are supported.";
}
