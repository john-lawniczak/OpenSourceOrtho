// Occlusal proximity client. Asks the local server (POST /api/occlusion) to
// register the loaded upper+lower scan pair into one bite frame and classify how
// close the crown surfaces are, then the 3D viewer paints the result red/amber/
// green. This is GEOMETRIC proximity (how close the registered surfaces are), never
// bite force or contact pressure, and never a diagnosis or occlusal assessment.

import { requestOcclusion, state } from "./state.js";
import { scaleConfirmed } from "./manual_edit.js";

// Build the /api/occlusion scan list from the loaded sources. Mirrors segment.js:
// only server-resolvable references work (uploaded files stay in the browser).
export function buildProximityScans(scanSources) {
  return scanSources.map((source) => ({
    reference: source.url || source.name,
    arch: source.arch,
  }));
}

// The overlay needs BOTH arches: occlusion is a relationship between them.
export function hasBothArches(scans) {
  const arches = new Set(scans.map((scan) => scan.arch));
  return arches.has("maxillary") && arches.has("mandibular");
}

// One-line summary of a returned registration, for the status strip.
export function proximitySummary(result) {
  const counts = result?.proximity?.counts || {};
  const reg = result?.registration || {};
  const total = (counts.contact || 0) + (counts.near || 0) + (counts.clearance || 0);
  const aligned = result?.proximity?.aligned_to_scan;
  const mode = reg.mode === "as-scanned" ? "using the scan's own bite" : `${reg.mode} alignment`;
  const note = aligned
    ? ""
    : " The arches were not pre-registered, so the overlay is hidden (an estimated bite would not line up with the scans).";
  return (
    `Bite proximity ready (${mode}): ${counts.contact || 0} touching, ${counts.near || 0} near, ` +
    `${counts.clearance || 0} clear of ${total} cells. Geometric closeness, not bite force.${note}`
  );
}

export async function requestProximity() {
  const prox = state.proximity;
  if (prox.busy) return;
  const scans = buildProximityScans(state.scanSources);
  if (!hasBothArches(scans)) {
    prox.map = null;
    prox.enabled = false;
    prox.status =
      "Load both an upper and a lower example scan first. Uploaded files stay in your " +
      "browser, so the local server cannot read them for occlusion.";
    return;
  }
  prox.busy = true;
  prox.status = "Registering the bite and mapping proximity on this machine...";
  try {
    const result = await requestOcclusion({
      scans,
      units_confirmed: scaleConfirmed(state.scanUnits),
    });
    if (result.ok === false) {
      prox.map = null;
      prox.enabled = false;
      prox.status = (result.errors || ["occlusion failed"]).join("; ");
      return;
    }
    prox.map = result.proximity;
    prox.registration = result.registration;
    prox.enabled = Boolean(result.proximity?.aligned_to_scan);
    prox.status = proximitySummary(result);
  } catch (error) {
    prox.map = null;
    prox.enabled = false;
    prox.status = error.message;
  } finally {
    prox.busy = false;
  }
}
