import { renderCaptureReview } from "./scan_capture_review.js";

export const impressionTemplate = `<details id="comparisonWeek21Impression" class="viewer-diagnostics" hidden>
  <summary>Week 21 · negative-impression scans</summary>
  <div id="impressionContent"></div>
</details>`;

export function renderImpressionRecords(data, assetLink) {
  const panel = document.getElementById("comparisonWeek21Impression");
  panel.dataset.available = String(Boolean(data?.length));
  const container = document.getElementById("impressionContent");
  container.replaceChildren();
  for (const [index, record] of (data || []).entries()) {
    const section = document.createElement("section");
    section.dataset.impressionLabel = record.label;
    renderRecord(record, section, assetLink, index);
    container.append(section);
  }
}

function renderRecord(data, container, assetLink, index) {
  const title = document.createElement("p");
  title.textContent = `${data.label}: ${Number(data.score).toFixed(2)}/10.00 · ${data.score_scope}`;
  const timing = document.createElement("p");
  timing.textContent = `Attached to reported week 21. Impression taken: ${data.impression_date || "not confirmed"}. Digitized: ${data.capture_date || "not confirmed"}. Negative impression; not an additional tooth-motion observation.`;
  container.append(title, timing);
  for (const scan of data.captures) {
    container.append(assetLink(`${data.asset_prefix}${scan.filename}`, `Download ${data.label} STL`, true));
  }
  for (const photo of data.photos || []) {
    const row = document.createElement("p");
    const description = photo.same_condition_as_scan
      ? ` · Same condition as scan, confirmed ${photo.confirmed_on}.`
      : " · Physical specimen photograph.";
    row.append(assetLink(`${data.asset_prefix}${photo.filename}`, photo.label),
      document.createTextNode(description));
    container.append(row);
  }
  const list = document.createElement("ul");
  for (const finding of data.findings) {
    const item = document.createElement("li"); item.textContent = finding.message; list.append(item);
  }
  container.append(list);
  for (const [name, label] of [["scan-overview.png", "Six scan views"],
    ["boundary-detail.png", "Open-edge detail"], ["quality-assessment.md", "Assessment and rescan guidance"],
    ["manifest.json", "Typed provenance"], ["mesh-inventory.json", "Measured topology"]]) {
    container.append(assetLink(`${data.asset_prefix}${name}`, label), document.createTextNode(" · "));
  }
  renderCaptureReview(data.acquisition_review, container, `impressionCaptureReview-${index}`);
}

export function showImpressionRecords(week) {
  const panel = document.getElementById("comparisonWeek21Impression");
  panel.hidden = week !== 21 || panel.dataset.available !== "true";
}
