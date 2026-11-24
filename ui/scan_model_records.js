import { sampleAssetUrl } from "./sample-dataset.js";

const asset = name => sampleAssetUrl(`visits/progress-02/${name}`);

export const weekEighteenRecords = `
  <section id="comparisonWeek18Records" hidden aria-label="Week 18 personal model scans">
    <p class="comparison-help"><strong>Personal model-making and 3D-scanning experiment.</strong>
      USER_ONE made physical models and scanned them. The contributor reports chips
      in both original stone models; these are model defects, not actual tooth damage.
      Acquisition date, scale and bite alignment remain unverified.</p>
    <details class="viewer-diagnostics">
      <summary>Week 18 · personal model records &amp; STL downloads</summary>
      <ul>
        <li><a href="${asset("progress-02-upper.stl")}" download>Download week 18 original upper STL</a></li>
        <li><a href="${asset("progress-02-lower.stl")}" download>Download week 18 original lower STL</a></li>
        <li><a href="${asset("captures/upper-clean/progress-02-upper-clean.stl")}" download>Download week 18 cleaned upper STL</a> · triangle removal only</li>
        <li><a href="${asset("captures/fusion-h-4/2026-11-12_USER_ONE_lower_week-18_fusion-h-4.stl")}" download>Download week 18 Fusion H4 lower STL</a></li>
        <li><a href="${asset("captures/fusion-h-6/2026-11-12_USER_ONE_lower_week-18_fusion-h-6.stl")}" download>Download week 18 Fusion H6 lower STL</a></li>
      </ul>
      <p>These are variants from the same reported week, not separate progress visits.
        History normally displays the cleaned upper and H4 lower; the selected local
        H4 trim may be displayed when available. Downloads above retain the public source versions.</p>
      <p><a href="${asset("README.md")}" target="_blank" rel="noopener">Model-making and capture record</a> ·
        <a href="${asset("source-metadata.json")}" target="_blank" rel="noopener">Source metadata</a> ·
        <a href="${asset("quality-assessment.md")}" target="_blank" rel="noopener">Original-pair quality report</a> ·
        <a href="${asset("captures/quality-assessment.md")}" target="_blank" rel="noopener">H4/H6 comparison</a></p>
    </details>
  </section>`;
