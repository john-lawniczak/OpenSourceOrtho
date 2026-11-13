export const comparisonTemplate = `
  <div class="comparison-toolbar" role="group" aria-label="Scan history controls">
    <button type="button" data-comparison-arch="both" aria-pressed="true">Both arches</button>
    <button type="button" data-comparison-arch="upper" aria-pressed="false">Upper teeth</button>
    <button type="button" data-comparison-arch="lower" aria-pressed="false">Lower teeth</button>
    <button type="button" data-comparison-view="occlusal">Biting surface</button>
    <button type="button" data-comparison-view="front">Front</button>
    <button type="button" data-comparison-view="left">Left side</button>
    <button type="button" data-comparison-view="right">Right side</button>
    <button type="button" id="comparisonReset">Reset view</button>
  </div>
  <p id="comparisonEstimateNote" class="comparison-estimate-note" hidden></p>
  <div class="comparison-stage">
    <div id="comparisonCanvas" class="comparison-canvas"></div>
    <div class="comparison-zoom" role="group" aria-label="Zoom both visible arches">
    <button type="button" id="comparisonZoomIn" aria-label="Zoom in on observed scans">+</button>
    <button type="button" id="comparisonZoomOut" aria-label="Zoom out of observed scans">−</button>
    </div>
    <div class="comparison-visit" id="comparisonVisit" aria-live="polite">Week 1</div>
    <div id="comparisonMissing" class="comparison-missing" hidden>
      <strong id="comparisonMissingTitle"></strong>
      <p>The endpoint-based estimate could not be loaded. Weeks 1, 7 and 18 have recorded scans. Weeks 8–17 need a new endpoint fit; no week 1–7 motion is extrapolated.</p>
    </div>
  </div>
  <nav class="comparison-timeline" aria-label="Reported scan weeks">
    <div class="comparison-week-navigation">
      <button id="comparisonPrevious" type="button" disabled>← Previous week</button>
      <output id="comparisonWeekLabel" aria-live="polite">Week 1 of 18</output>
      <button id="comparisonNext" type="button" disabled>Next week →</button>
    </div>
    <div class="comparison-highlight-controls" role="group" aria-label="Week highlighting">
      <span>Highlight weeks</span>
      <label class="scan-highlight-toggle"><input id="highlightScanWeeks" type="checkbox" role="switch" checked> Recorded scans <span class="week-color recorded" aria-hidden="true"></span></label>
      <label class="scan-highlight-toggle"><input id="highlightEstimatedWeeks" type="checkbox" role="switch" checked> Estimated weeks <span class="week-color estimated" aria-hidden="true"></span></label>
    </div>
    <div class="comparison-weeks">
      ${Array.from({ length: 18 }, (_, i) => `<button type="button" data-comparison-week="${i + 1}" data-scan-kind="${[0, 6, 17].includes(i) ? "observed" : i < 7 ? "estimated" : "unavailable"}" disabled
        aria-label="Week ${i + 1}, ${[0, 6, 17].includes(i) ? "observed scan" : i < 7 ? "simulated estimate" : "not fitted"}">
        Week ${i + 1}<small>${[0, 6, 17].includes(i) ? "Observed" : i < 7 ? "Estimated" : "Not fitted"}</small></button>`).join("")}
    </div>
  </nav>
  <div class="comparison-motion-tools">
    <a href="./progress.html" id="openScanPair">Compare two scans</a>
      <a href="./region-review.html?baseline=upper" target="_blank" rel="noopener">Paint USER_ONE upper baseline</a>
      <a href="./region-review.html?baseline=lower" target="_blank" rel="noopener">Paint USER_ONE lower baseline</a>
      <a href="./region-review.html?baseline=upper&amp;visit=progress-01" target="_blank" rel="noopener">Paint USER_ONE week 7 upper</a>
      <a href="./region-review.html?baseline=lower&amp;visit=progress-01" target="_blank" rel="noopener">Paint USER_ONE week 7 lower</a>
      <a href="./region-review.html?baseline=upper&amp;visit=progress-02&amp;capture=upper-clean" target="_blank" rel="noopener">Paint USER_ONE week 18 upper</a>
      <a href="./region-review.html?baseline=lower&amp;visit=progress-02&amp;capture=fusion-h-4" target="_blank" rel="noopener">Paint USER_ONE week 18 lower</a>
    <label>Timing assumption <select id="comparisonTiming"><option value="uniform">Uniform motion</option><option value="smooth">Slow start and finish</option><option value="delayed">Delayed start</option></select></label>
    <label>Tooth <select id="comparisonTooth" disabled><option value="">All teeth</option></select></label>
    <button id="comparisonFocusTooth" type="button" disabled>Focus selected tooth</button>
    <button id="comparisonEndpointFit" type="button" aria-pressed="false" hidden>Inspect estimated endpoint</button>
  </div>
  <p class="comparison-help">Compare two scans opens a separate tool for uploading two visits and estimating positions between them. Return here to continue this sample.</p>
  <details><summary>Proximity hints</summary><p id="comparisonProximity" class="comparison-help"></p></details>
  <p id="comparisonMatchDetail" class="comparison-help" aria-live="polite"></p>
  <button id="comparisonMotionRetry" type="button" hidden>Retry motion preview</button>
  <p id="comparisonHelp" class="comparison-help">Drag to rotate; scroll or pinch to zoom.
    Double-click a crown to focus. The camera stays in place when changing weeks.</p>
  <p id="comparisonStatus" role="status" aria-live="polite">Loading original scan pair…</p>
  <button id="comparisonRetry" type="button" hidden>Retry scan loading</button>
`;
