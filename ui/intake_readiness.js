import { escapeHtml } from "./core.js";

// UI owns routes; the engine emits stable action identifiers, never DOM selectors.
export const READINESS_ACTIONS = {
  upload_scans: { step: "upload", target: "stlFile", label: "Open scan upload" },
  confirm_units: { step: "upload", target: "scanUnits", label: "Review scale and units" },
  label_arch: { step: "upload", target: "scanArch", label: "Review scan identity" },
  review_segmentation: { step: "review", target: "proposeSegment", label: "Open segmentation" },
  review_bite: { step: "availability", target: "availabilityGrid", label: "Review bite declaration" },
  attach_cbct: { step: "upload", target: "dicomFile", label: "Open CBCT intake" },
  review_registration: { step: "upload", target: "cbctRegistrationAccepted", label: "Review registration" },
  review_anatomy: { step: "upload", target: "cbctMaskFile", label: "Open anatomy workflow" },
  review_plan: { step: "review", target: "movementReadinessChecklist", label: "Review plan checks" },
  configure_export: { step: "settings", target: "printEnabled", label: "Open export settings" },
};

const LABELS = {
  present: "Recorded", missing: "Missing", needs_review: "Needs review", blocked: "Blocked",
  not_assessed: "Not assessed", no_stages: "No staged proposal", limited: "Limited checks",
  findings_to_review: "Findings to review", checks_completed: "Checks completed",
  prerequisites_met: "Prerequisites met",
};

function actionMarkup(action) {
  const route = READINESS_ACTIONS[action];
  if (!route) return "";
  return `<a href="#${route.target}" data-readiness-action="${escapeHtml(action)}">${route.label}</a>`;
}

export function intakeReadinessMarkup(report, { pending = false, open = false } = {}) {
  if (!report || pending) {
    return `<p class="intake-readiness">${pending ? "Updating record and workflow readiness…" :
      "Record and workflow readiness is unavailable until evaluation succeeds."}</p>`;
  }
  const consistency = report.plan_consistency;
  const artifacts = report.artifacts;
  return `<details id="intakeReadinessDetails" class="intake-readiness" ${open ? "open" : ""}>
    <summary>Record and workflow readiness</summary>
    <p>${escapeHtml(report.caveat)}</p>
    <p>Links open the corresponding Technician controls.</p>
    <h4>Record evidence</h4>
    <ul class="intake-records">${report.records.map((entry) => `<li>
      <strong>${escapeHtml(entry.label)} · ${escapeHtml(LABELS[entry.state] || "Not assessed")}</strong>
      <span>${escapeHtml(entry.scope === "root_bone" ? "Optional root/bone context" :
        entry.scope === "bite" ? "Bite context" : "Surface records")}</span>
      <p>${escapeHtml(entry.detail)}</p>${actionMarkup(entry.action)}
    </li>`).join("")}</ul>
    <h4>Plan consistency · ${escapeHtml(LABELS[consistency.status] || "Not assessed")}</h4>
    <p>${escapeHtml(consistency.detail)}</p>${actionMarkup("review_plan")}
    <h4>Artifact prerequisites · ${escapeHtml(LABELS[artifacts.status] || "Not assessed")}</h4>
    <p>${escapeHtml(artifacts.detail)} Geometry QA has not run in this evaluation.</p>
    <ul>${artifacts.blockers.map((blocker) => `<li>${escapeHtml(blocker)}</li>`).join("")}</ul>
    ${actionMarkup("configure_export")}
    <h4>Physical validation · Not assessed</h4>
    <p>This report does not establish physical fit, material performance, or authorization for use.</p>
  </details>`;
}

export function navigateReadinessAction(action, state, render, doc = document) {
  const route = READINESS_ACTIONS[action];
  if (!route) return false;
  state.userMode = "advanced";
  state.activeStep = route.step;
  render();
  const target = doc.getElementById(route.target);
  if (target) {
    target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
    target.scrollIntoView({ block: "center", behavior: "auto" });
  }
  return true;
}
