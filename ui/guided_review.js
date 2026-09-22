import { TARGET_STAGE, targetMagnitudeMm } from "./manual_edit.js";

function editedTargets(rows) {
  return (rows || [])
    .filter((row) => row.stage === TARGET_STAGE && rowMagnitude(row) > 0)
    .map((row) => ({
      tooth: String(row.tooth),
      magnitude: rowMagnitude(row),
    }))
    .sort((a, b) => b.magnitude - a.magnitude || a.tooth.localeCompare(b.tooth));
}

function rowMagnitude(row) {
  return targetMagnitudeMm({ x: row?.x || 0, y: row?.y || 0 });
}

export function guidedReviewDashboard(result, rows = []) {
  if (!result?.timeline) {
    return {
      verdict: "cannot-assess",
      label: "Cannot assess yet",
      summary: "Build your plan first.",
      cards: [],
      highlights: [],
    };
  }
  const warnings = (result.findings || []).filter(
    (finding) => !isAdvisorySeverity(finding.severity),
  );
  const edits = editedTargets(rows);
  const tier = result.review_tier || {};
  const print = result.print_export || {};
  const readiness = print.manufacturing_readiness || {};
  const rootAware = Boolean(tier.root_bone_aware);
  const scaleOk = result.scale_confirmed !== false;
  const printReady = Boolean(print.ready && readiness.verdict === "CONSISTENT");
  const verdict = !scaleOk ? "cannot-assess" : (warnings.length ? "needs-review" : "ready");

  return {
    verdict,
    label: {
      ready: "Plan checks reviewed",
      "needs-review": "Plan findings need review",
      "cannot-assess": "Movement checks unavailable",
    }[verdict],
    summary: dashboardSummary({ warnings, edits, rootAware, printReady, scaleOk }),
    cards: [
      editCard(edits),
      warningCard(warnings),
      rootBoneCard(tier, result.root_bone_review),
      printCard(print),
    ],
    highlights: overlayHighlights(warnings, tier),
  };
}

function isAdvisorySeverity(severity) {
  return severity === "info" || severity === "notice";
}

function dashboardSummary({ warnings, edits, rootAware, printReady, scaleOk }) {
  if (!scaleOk) return "Confirm scan units before trusting millimeter checks.";
  if (warnings.length) return `${warnings.length} deterministic warning(s) need plan review.`;
  if (!rootAware) {
    return "No deterministic warnings; review remains surface-only without trusted root/bone anatomy.";
  }
  if (!printReady) return "No deterministic warnings. Print readiness is reported separately below.";
  if (edits.length) return "Edits rebuilt with no deterministic warnings.";
  return "No deterministic warnings in the current review.";
}

function editCard(edits) {
  return {
    id: "edits",
    title: "Edit diff",
    status: edits.length ? "needs-review" : "ready",
    value: edits.length ? `${edits.length} tooth change(s)` : "No guided edits",
    detail: edits.slice(0, 4).map((edit) =>
      `Tooth ${edit.tooth}: ${edit.magnitude.toFixed(1)} mm`),
  };
}

function warningCard(warnings) {
  return {
    id: "warnings",
    title: "Warnings",
    status: warnings.length ? "needs-review" : "ready",
    value: warnings.length ? `${warnings.length} finding(s)` : "No findings",
    detail: warningGroupDetails(warnings),
  };
}

function warningGroupDetails(warnings) {
  const groups = new Map();
  for (const finding of warnings) {
    const text = `${finding.code || ""} ${finding.title || ""}`.toLowerCase();
    let label = "Other review findings";
    if (/contact|collision|spacing|ipr/.test(text)) label = "Crown contact / spacing";
    else if (/movement-cap|movement cap/.test(text)) label = "Movement caps";
    else if (/root|bone|cortical|apex/.test(text)) label = "Root / bone";
    groups.set(label, (groups.get(label) || 0) + 1);
  }
  return [...groups.entries()].map(([label, count]) => `${label}: ${count}`);
}

function rootBoneCard(tier, review) {
  const aware = Boolean(tier.root_bone_aware);
  return {
    id: "root-bone",
    title: "Root / bone",
    status: aware ? "ready" : "cannot-assess",
    value: aware ? "Trusted anatomy" : "Cannot assess",
    detail: [
      tier.label || "STL surface only",
      review?.verdict ? `Review: ${review.verdict}` : "",
    ].filter(Boolean),
  };
}

function printCard(print) {
  const readiness = print?.manufacturing_readiness || {};
  const verdict = readiness.verdict || "NOT_APPLICABLE";
  return {
    id: "print",
    title: "Print readiness",
    status: verdict === "CONSISTENT" && print?.ready
      ? "ready"
      : (verdict === "ISSUES" ? "needs-review" : "cannot-assess"),
    value: verdict,
    detail: [readiness.reason, ...(print?.blockers || []).slice(0, 2)].filter(Boolean),
  };
}

function overlayHighlights(warnings, tier) {
  const highlights = [];
  if (warnings.some((finding) => String(finding.code || "").includes("movement-cap"))) {
    highlights.push("Movement cap markers");
  }
  if (warnings.some((finding) => String(finding.code || "").includes("collision"))) {
    highlights.push("Collision/IPR highlights");
  }
  if (!tier?.root_bone_aware) highlights.push("Root/bone unavailable badge");
  return highlights;
}
