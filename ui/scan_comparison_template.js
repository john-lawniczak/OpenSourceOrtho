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
  <p id="comparisonEstimateNote" class="comparison-estimate-note" hidden></p>
  <div class="comparison-stage">
    <div id="comparisonCanvas" class="comparison-canvas"></div>
    <div class="comparison-visit" id="comparisonVisit" aria-live="polite">Week 1</div>
    <div id="comparisonMissing" class="comparison-missing" hidden>
      <strong id="comparisonMissingTitle"></strong>
      <p>The endpoint-based estimate could not be loaded. Weeks 1 and 7 still show their recorded surfaces.</p>
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
        aria-label="Week ${i + 1}, ${i === 0 || i === 6 ? "observed scan" : "simulated estimate"}">
        Week ${i + 1}<small>${i === 0 || i === 6 ? "Observed" : "Estimated"}</small></button>`).join("")}
    </div>
  </nav>
  <div class="comparison-motion-tools">
    <label>Tooth <select id="comparisonTooth" disabled><option value="">All teeth</option></select></label>
    <button id="comparisonFocusTooth" type="button" disabled>Focus selected tooth</button>
    <button id="comparisonEndpointFit" type="button" aria-pressed="false" hidden>Inspect estimated endpoint</button>
  </div>
  <p id="comparisonMatchDetail" class="comparison-help" aria-live="polite"></p>
  <button id="comparisonMotionRetry" type="button" hidden>Retry motion preview</button>
  <p id="comparisonHelp" class="comparison-help">Drag to rotate; scroll or pinch to zoom.
    Double-click a crown to focus. The camera stays in place when changing weeks.</p>
  <p id="comparisonStatus" role="status" aria-live="polite">Loading original scan pair…</p>
  <button id="comparisonRetry" type="button" hidden>Retry scan loading</button>
  <details class="comparison-provenance"><summary>Scan dates and accuracy</summary>
    <p id="comparisonValidation">Loading the scan validation record…</p>
    <p>The earlier pair is labeled week 1 / baseline by the contributor and was recorded on June 5, 2026 (pretreatment).
      The September 17, 2026 scan is labeled week 7. These reported labels are not elapsed calendar weeks:
      the scans are 104 days apart, and the progress scan is 30 days after the recorded treatment start.</p>
    <p>Motion is estimated from local tooth-segmentation drafts and rigid surface matching between the scans.
      Week 7 is fitted to week 1 using a whole-arch reference; this can remove global arch movement.
      Each draft region then receives an endpoint translation and rotation. Weeks 2–6 distribute those
      changes uniformly across the six labeled intervals; the real timing and path are unknown.</p>
    <p>Draft FDI labels and crown boundaries need review and may include gum. Remaining surface context stays fixed.
      Surface residuals describe geometric fit, not certainty about tooth identity. Weak fits remain labeled;
      unmatched or numerically unusable regions are held in place. The strict production segmentation gate
      does not block this exploratory simulation. Progress scale is unverified; displayed distances are scan units.</p>
    <p>Use “Inspect estimated endpoint” at week 7 to compare the fitted baseline regions with the recorded scan.
      Scan coverage, attachments, and soft-tissue changes will not be reproduced by rigid tooth motion.
      The later personal scans of chipped stone models are excluded. The separate planning demo uses hypothetical targets.</p>
  </details>`;
