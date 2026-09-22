import { escapeHtml } from "./core.js";

function verdictClass(verdict) {
  if (verdict === "CONSISTENT") return "qa-ok";
  if (verdict === "ISSUES") return "qa-issue";
  return "qa-na";
}

function readinessMarkup(readiness) {
  if (!readiness?.verdict) return "";
  const reason = readiness.reason ? ` — ${escapeHtml(readiness.reason)}` : "";
  return `<p class="print-qa-readiness ${verdictClass(readiness.verdict)}">`
    + `<strong>Manufacturing readiness: ${escapeHtml(readiness.verdict)}</strong>${reason}</p>`;
}

function shellQaMarkup(findings) {
  if (!Array.isArray(findings) || findings.length === 0) return "";
  const items = findings
    .map((finding) => `<li class="${verdictClass(finding.verdict)}">`
      + `${escapeHtml(finding.verdict)}: ${escapeHtml(finding.message)}</li>`)
    .join("");
  return `<ul class="print-qa-findings">${items}</ul>`;
}

function tolerancesMarkup(tolerances) {
  if (!tolerances) return "";
  const fmt = (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "—");
  return `<p class="print-qa-tolerances">Printer compensation: `
    + `XY ${fmt(tolerances.xy_compensation_mm)} mm, Z ${fmt(tolerances.z_compensation_mm)} mm · `
    + `min feature ${fmt(tolerances.minimum_printable_feature_mm)} mm.</p>`;
}

export function printExportMarkup(status) {
  if (!status) return "";
  const blockers = status.blockers?.length
    ? `<ul>${status.blockers.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : "<p>Print package inputs are complete for export.</p>";
  const artifacts = status.artifacts?.length
    ? `<p>${escapeHtml(status.artifacts.map((item) => item.filename).join(", "))}</p>`
    : "";
  return `
    <p><strong>${status.ready ? "Inputs complete" : "Inputs incomplete"}</strong></p>
    ${blockers}
    ${readinessMarkup(status.manufacturing_readiness)}
    ${shellQaMarkup(status.shell_qa_findings)}
    ${tolerancesMarkup(status.printer_tolerances)}
    ${artifacts}
    <p>${escapeHtml(status.model_material)}</p>
    <p>${escapeHtml(status.thermoforming_material)}</p>
    <p>${escapeHtml(status.caveat)}</p>
  `;
}

export function renderPrintExport(host, status) {
  host.innerHTML = printExportMarkup(status);
}
