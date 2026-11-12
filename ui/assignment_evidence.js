// Assignment costs describe competing geometric hypotheses, not anatomical confidence.
export function assignmentEvidenceText(tooth) {
  const evidence = tooth?.assignment_evidence;
  if (!evidence) return "";
  if (evidence.status?.startsWith("unmatched-")) return "No independent one-to-one region match; projected motion needs identity review.";
  if (!evidence.ambiguous) return "";
  const candidates = (evidence.candidates || []).map(c => String(c.target_tooth)).filter(id => /^[1-4][1-8]$/.test(id));
  const margin = evidence.alternative_cost_increase;
  return `Ambiguous endpoint identity: a competing assignment has nearly the same geometric cost${Number.isFinite(margin) ? ` (difference ${margin.toFixed(3)})` : ""}. Candidate regions: ${candidates.join(", ") || "unavailable"}. Review the endpoint mapping; this is not an identity probability.`;
}
