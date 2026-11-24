import { sampleAssetUrl } from "./sample-dataset.js";
import { weekTwentyOneFolder as folder } from "./scan_week_twenty_one.js";

const asset = name => sampleAssetUrl(`${folder}/${name}`);

export const weekTwentyOneRecords = `
  <details id="comparisonWeek21Records" class="viewer-diagnostics" hidden>
    <summary>Week 21 · scan images, source record &amp; downloads</summary>
    <p>November 23, 2026 · iTero Element 5D · Study Model / iRecord.
      Original whole-arch scans in their exported occlusion coordinates.
      Scale and bite accuracy remain unverified.</p>
    <p><a href="${asset("progress-03-upper.stl")}" download>Download week 21 upper STL</a> ·
      <a href="${asset("progress-03-lower.stl")}" download>Download week 21 lower STL</a> ·
      <a href="${asset("source-metadata.json")}" target="_blank" rel="noopener">Redacted PDF and export information</a> ·
      <a href="${asset("quality-assessment.md")}" target="_blank" rel="noopener">Quality comparison</a></p>
    <p>Source-rendered views, not clinical photographs. Identifying paperwork is excluded.
      Week 21 has no fitted tooth-motion estimates yet.</p>
    <div class="comparison-record-images">
      ${[["progress-03.jpg", "All views"], ["progress-03-front.jpg", "Front"],
        ["progress-03-upper.jpg", "Upper"], ["progress-03-lower.jpg", "Lower"],
        ["progress-03-patientleft.jpg", "Patient left"], ["progress-03-patientright.jpg", "Patient right"]]
        .map(([name, label]) => `<a href="${asset(`media/${name}`)}" target="_blank" rel="noopener"><img loading="lazy" src="${asset(`media/${name}`)}" alt="Week 21 source scan rendering: ${label}"><span>${label}</span></a>`).join("")}
    </div>
  </details>`;

export function laterVisitDetail(week, surfaces) {
  return week === 21
    ? "Week 21 observed intraoral scans · file integrity verified. Exported upper/lower relationship preserved; bite accuracy, scale and cross-visit alignment unverified."
    : `Week 18 observed surfaces: ${surfaces} · personal model-making and 3D-scanning experiment · file integrity verified. Model chips are reported; scale and cross-visit alignment are unverified. Approximate display placement, not a measured bite.`;
}
