// Reported week labels, not a calendar-time or treatment-motion model.
// Missing observations must never reuse an endpoint or a synthetic planning pose.
export function historyFrame(week, pair) {
  if (!Number.isInteger(week) || week < 1 || week > 7) throw new Error("Choose a week from 1 to 7.");
  const index = week === 1 ? 0 : week === 7 ? 1 : null;
  return { week, index, scan: index === null ? null : pair[index] };
}

// Roll the upper view so the upper crowns point down in front/side views.
// This changes the camera only; source geometry and inter-visit distances stay intact.
export function historyCamera(arch, view = "front") {
  const position = {
    occlusal: [0, 180, 0], front: [0, 25, 180], left: [-180, 25, 0], right: [180, 25, 0],
  }[view] || [0, 25, 180];
  const up = view === "occlusal" ? [0, 0, arch === "upper" ? 1 : -1]
    : [0, arch === "upper" ? -1 : 1, 0];
  return { position, up };
}
