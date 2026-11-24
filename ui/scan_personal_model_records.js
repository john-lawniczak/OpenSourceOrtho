const endpoint = "/api/sample-personal-models";
const asset = name => `${endpoint}/assets/${encodeURIComponent(name)}`;

export const personalModelTemplate = `<details id="comparisonWeek21Casts" class="viewer-diagnostics" hidden>
  <summary>Week 21 · same-day personal casts &amp; dental comparison</summary>
  <p id="personalCastStatus" role="status"></p>
  <div id="personalCastContent"></div>
</details>`;

let loaded = false, pending = null;

function link(name, label, download = false) {
  const node = document.createElement("a");
  node.href = asset(name); node.textContent = label;
  if (download) node.download = name;
  else { node.target = "_blank"; node.rel = "noopener"; }
  return node;
}

function render(data, container) {
  container.replaceChildren();
  const note = document.createElement("p");
  note.textContent = `${data.date} · Four physical casts, six scans. Chips refer to the casts, not actual tooth damage. Lower C6 was broken into two parts and held together with clay; its fragment alignment is unverified. Original files are preserved; cast scans have no shared bite frame.`;
  container.append(note);
  for (const model of data.models) {
    const row = document.createElement("p"), title = document.createElement("strong");
    title.textContent = `${model.label}: ${Number(model.score).toFixed(2)}/10.00 `;
    row.append(title);
    for (const scan of data.captures.filter(item => item.model_id === model.model_id)) {
      row.append(link(scan.filename, `Download ${scan.capture_id}`, true), document.createTextNode(" · "));
    }
    container.append(row);
  }
  const limits = document.createElement("p");
  limits.textContent = "Scores are subjective research-data judgments, not anatomical accuracy. Comparison fits are rigid estimates with unverified scale; they do not change dental scans, bite coordinates, or motion estimates.";
  container.append(limits);
  for (const [name, label] of [["quality-assessment.md", "Cast assessment and scoring rubric"],
    ["cast-overview.png", "Inspect original cast views"], ["dental-comparison.png", "Inspect dental comparison"],
    ["dental-comparison.json", "Download measured comparison and transforms"], ["source-metadata.json", "Capture provenance"]]) {
    container.append(link(name, label), document.createTextNode(" · "));
  }
  const findings = document.createElement("ul");
  for (const item of data.findings) {
    const li = document.createElement("li"); li.textContent = item.message; findings.append(li);
  }
  container.append(findings);
}

export function showPersonalModelRecords(week) {
  const panel = document.getElementById("comparisonWeek21Casts");
  panel.hidden = week !== 21 || panel.dataset.available !== "true";
  if (week !== 21 || loaded || pending) return;
  pending = fetch(endpoint).then(async response => {
    if (!response.ok) throw new Error(`Companion records unavailable (HTTP ${response.status}).`);
    const data = await response.json();
    loaded = true; panel.dataset.available = String(Boolean(data.available));
    if (data.available) {
      render(data, document.getElementById("personalCastContent"));
      document.getElementById("personalCastStatus").textContent = "Public companion records attached to this week 21 visit; original STL downloads available below.";
    }
    panel.hidden = document.getElementById("sampleComparison").dataset.week !== "21" || !data.available;
  }).catch(() => { loaded = false; }).finally(() => { pending = null; });
}
