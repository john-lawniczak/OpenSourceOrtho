export const comparisonTemplate = `
  <header class="comparison-heading">
    <div><p class="comparison-eyebrow">USER_ONE · observed scan history</p>
    <h3>Look closely at what changed</h3></div>
    <label>Arch <select id="comparisonArch"><option value="upper">Upper</option><option value="lower">Lower</option></select></label>
  </header>
  <p>Two original scans, one camera. Reveal either visit while keeping the same close-up.</p>
  <p class="comparison-limitation"><strong>Visual comparison, not measured tooth movement.</strong>
    Display orientation and centering only; cross-visit alignment and week 7 scale are unverified.
    Tooth identities have not been matched across visits.</p>
  <div class="comparison-toolbar" role="group" aria-label="Comparison camera">
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
    <div class="comparison-visit comparison-before" id="comparisonBefore">Pretreatment baseline</div>
    <div class="comparison-visit comparison-after" id="comparisonAfter">Reported week 7</div>
    <div id="comparisonDivider" class="comparison-divider" hidden aria-hidden="true"><span>↔</span></div>
  </div>
  <div class="comparison-reveal">
    <div class="comparison-endpoints">
      <button id="comparisonBaseline" type="button">Baseline only</button>
      <button id="comparisonSplit" type="button">Split view</button>
      <button id="comparisonWeek7" type="button">Week 7 only</button>
    </div>
    <label for="comparisonReveal">Reveal week 7 <output id="comparisonPercent">0%</output></label>
    <input id="comparisonReveal" type="range" min="0" max="100" step="0.1" value="0" disabled
      aria-label="Reveal week 7 scan" aria-describedby="comparisonHelp" />
  </div>
  <p id="comparisonHelp" class="comparison-help">Drag the slider or divider to reveal the other scan.
    Drag the model to rotate; scroll or pinch to zoom. Double-click a crown to focus that region.
    Use the endpoint buttons to alternate visits without moving the camera.</p>
  <p id="comparisonStatus" role="status" aria-live="polite">Loading original scan pair…</p>
  <button id="comparisonRetry" type="button" hidden>Retry scan loading</button>
  <details class="comparison-provenance"><summary>About these visits</summary>
    <p>The baseline is a pretreatment scan from June 5, 2026, not a confirmed week 1 scan.
      The progress scan is from September 17, 2026, reported as week 7.
      There are 104 days between the scans and 30 days from the recorded treatment start to the progress scan.
      The week label is not elapsed calendar time.</p>
    <p>Only two observed visits are available here. The slider reveals the recorded surfaces;
      intermediate positions are not inferred tooth positions or additional weeks. No movement is exaggerated.
      Differences can include scan coverage, orientation, attachments, and acquisition artifacts.
      The later chipped-stone test scans are excluded.</p>
    <p>Hypothetical tooth edits and Plan AI belong to the separate Simulated planning demo.</p>
  </details>`;
