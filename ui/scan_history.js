// Reported week labels, not elapsed calendar time or an observed weekly schedule.
export function historyFrame(week, pair, motion = null, endpointEstimate = false) {
  if (!Number.isInteger(week) || week < 1 || week > 7) throw new Error("Choose a week from 1 to 7.");
  const endpoint = week === 1 ? 0 : week === 7 ? 1 : null;
  const estimated = Boolean(motion) && (endpoint === null || (week === 7 && endpointEstimate));
  return { week, index: estimated ? 2 : endpoint, fraction: (week - 1) / 6,
    kind: estimated ? "estimated" : endpoint === null ? "unavailable" : "observed",
    scan: endpoint === null ? null : pair[endpoint] };
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
