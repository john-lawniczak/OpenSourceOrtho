export const comparisonTemplate = `
  <div class="comparison-toolbar" role="group" aria-label="Scan history controls">
    <button type="button" data-comparison-arch="upper" aria-pressed="true">Upper teeth</button>
    <button type="button" data-comparison-arch="lower" aria-pressed="false">Lower teeth</button>
    <button type="button" data-comparison-view="occlusal">Biting surface</button>
    <button type="button" data-comparison-view="front">Front</button>
    <button type="button" data-comparison-view="left">Left side</button>
    <button type="button" data-comparison-view="right">Right side</button>
    <button type="button" id="comparisonZoomIn" aria-label="Zoom in on observed scans">+</button>
    <button type="button" id="comparisonZoomOut" aria-label="Zoom out of observed scans">−</button>
    <button type="button" id="comparisonReset">Reset view</button>
  </div>
  <div class="comparison-stage">
    <div id="comparisonCanvas" class="comparison-canvas"></div>
    <div class="comparison-visit" id="comparisonVisit" aria-live="polite">Week 1</div>
    <div id="comparisonMissing" class="comparison-missing" hidden>
      <strong id="comparisonMissingTitle"></strong>
      <p>Only weeks 1 and 7 have scans. Tooth positions for this week are unavailable.</p>
      <p>Accurate weekly motion needs additional observations. Estimates need the validated tooth map and registration data.</p>
    </div>
  </div>
  <nav class="comparison-timeline" aria-label="Reported scan weeks">
    <div class="comparison-week-navigation">
      <button id="comparisonPrevious" type="button" disabled>← Previous week</button>
      <output id="comparisonWeekLabel" aria-live="polite">Week 1 of 7</output>
      <button id="comparisonNext" type="button" disabled>Next week →</button>
    </div>
    <div class="comparison-weeks">
      ${Array.from({ length: 7 }, (_, i) => `<button type="button" data-comparison-week="${i + 1}" disabled
        aria-label="Week ${i + 1}, ${i === 0 || i === 6 ? "observed scan" : "no scan"}">
        Week ${i + 1}<small>${i === 0 || i === 6 ? "Observed" : "No scan"}</small></button>`).join("")}
    </div>
  </nav>
  <p id="comparisonHelp" class="comparison-help">Drag to rotate; scroll or pinch to zoom.
    Double-click a crown to focus. The camera stays in place when changing weeks.</p>
  <p id="comparisonStatus" role="status" aria-live="polite">Loading original scan pair…</p>
  <button id="comparisonRetry" type="button" hidden>Retry scan loading</button>
  <details class="comparison-provenance"><summary>Scan dates and accuracy</summary>
    <p id="comparisonValidation">Loading the scan validation record…</p>
    <p>The earlier pair is labeled week 1 / baseline by the contributor and was recorded on June 5, 2026 (pretreatment).
      The September 17, 2026 scan is labeled week 7. These reported labels are not elapsed calendar weeks:
      the scans are 104 days apart, and the progress scan is 30 days after the recorded treatment start.</p>
    <p>The viewer uses display orientation and independent centering. The validated registration transform
      and tooth map have not been linked to this viewer. Progress scale is unverified; no per-tooth or
      millimeter displacement is calculated. Differences can include scan coverage and acquisition artifacts.</p>
    <p>No intermediate tooth positions are generated. The later personal scans of chipped stone models are excluded.
      Hypothetical edits belong to the separate Simulated planning demo.</p>
  </details>`;
