// Reported week labels, not elapsed calendar time or an observed weekly schedule.
export function historyFrame(week, pair, motion = null, endpointEstimate = false, timing = "uniform") {
  if (!Number.isInteger(week) || week < 1 || week > 7) throw new Error("Choose a week from 1 to 7.");
  const endpoint = week === 1 ? 0 : week === 7 ? 1 : null;
  const estimated = Boolean(motion) && (endpoint === null || (week === 7 && endpointEstimate));
  return { week, index: estimated ? 2 : endpoint, fraction: motion ? simulationFraction(week, motion.simulation, timing) : (week - 1) / 6,
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

export function simulationFraction(week, simulation, timing = "uniform") {
  const fractions = simulation?.profiles?.[timing]?.fractions;
  if (!fractions) {
    if (timing !== "uniform") throw new Error("Timing assumption unavailable for this fit.");
    return (week - 1) / 6;
  }
  if (fractions.length !== 7 || fractions[0] !== 0 || fractions[6] !== 1
      || fractions.some((v,i) => !Number.isFinite(v) || v < 0 || v > 1 || (i && v < fractions[i-1]))) {
    throw new Error("Invalid simulation timing.");
  }
  return fractions[week-1];
}
