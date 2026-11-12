export function proximitySummary(reports, week, timing) {
  if (!reports.length) return "Proximity hints unavailable for this fit.";
  const summaries = reports.map(({arch, simulation}) => {
    const pairs = simulation?.profiles?.[timing]?.proximity_by_week?.[week-1];
    if (!pairs) return `${arch}: unavailable`;
    const fresh = pairs.filter(p=>p.new_proximity).length;
    return `${arch}: ${pairs.length} nearby region pairs (${fresh} new since baseline), sampled threshold ${simulation.proximity_threshold.toFixed(3)} scan units`;
  });
  return `${summaries.join(" · ")}. Same-arch proximity hints only; sampling can miss contact or intersections. Absence does not establish clearance.`;
}
