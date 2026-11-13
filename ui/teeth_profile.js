import { renderScanDates } from "./scan_dates_view.js";
import { el, state } from "./state.js";

export function renderProfile() {
  renderScanDates();
  const sample = state.sample.active;
  const scans = state.scanSources.length || state.files.length;
  el("teethProfileStatus").textContent = sample ? "Return to your own scans" : scans ? `${scans} scan${scans === 1 ? "" : "s"} · your workspace` : "";
  el("teethProfileStatus").hidden = !sample && !scans;
  el("teethProfile").setAttribute("aria-pressed", String(!sample && !["toothmap", "glossary", "photos", "notes"].includes(state.activeStep)));
  for (const id of ["simpleStlFile", "stlFile"]) el(id).disabled = sample;
  el("uploadHeading").textContent = sample ? "1 · Supplied STL scans" : "1 · Upload your scan files";
}
