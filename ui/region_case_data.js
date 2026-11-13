import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";

export async function loadBaselineCaseData(arch, visit = "initial") {
  const response = await fetch(sampleAssetUrl("treatment-context.json"), { cache: "no-store" });
  if (!response.ok) throw new Error("Could not load USER_ONE tooth inventory.");
  const record = await response.json();
  if (record.specimen_id !== sampleDataset.specimenId) throw new Error("Tooth inventory belongs to another case.");
  const absentTeeth = (record.dentition?.absent_fdi || []).map(Number);
  const path = visit === "initial" ? record.baseline_annotations?.[arch] : null;
  if (!path) return { absentTeeth, corrections: null };
  const labels = await fetch(sampleAssetUrl(path), { cache: "no-store" });
  if (!labels.ok) throw new Error("Could not load the published baseline annotation.");
  return { absentTeeth, corrections: await labels.json() };
}
