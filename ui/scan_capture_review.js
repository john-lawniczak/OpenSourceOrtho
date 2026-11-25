/** Display declared capture provenance separately from geometric measurements. */
export function renderCaptureReview(review, container, id = "personalCaptureReview") {
  if (!review) return;
  const panel = document.createElement("details");
  panel.id = id;
  const heading = document.createElement("summary");
  heading.textContent = "Capture provenance and comparison limits";
  panel.append(heading);
  for (const record of review.records) {
    const item = document.createElement("details"), label = document.createElement("summary");
    item.dataset.captureFile = record.filename;
    label.textContent = `${record.filename} · ${record.interpretation}`;
    item.append(label);
    const scope = document.createElement("p");
    scope.textContent = record.intact_arch_reference === "excluded"
      ? "Not an intact-arch reference. Exploratory inspection remains available."
      : "Reference status is not established. Exploratory inspection remains available.";
    item.append(scope);
    const list = document.createElement("ul");
    for (const finding of record.findings) {
      const entry = document.createElement("li");
      entry.textContent = finding.message; list.append(entry);
    }
    item.append(list); panel.append(item);
  }
  for (const group of review.repeat_groups) {
    const row = document.createElement("p");
    row.textContent = `${group.physical_object_id}: ${group.capture_count} captures of one object; ${group.distinct_file_count} distinct files. Independent repeatability is not established by file count.`;
    panel.append(row);
  }
  container.append(panel);
}
