// Section 2 owns this preference. Other steps may need the tooth workspace
// without changing which overview the user returns to.
export function sampleViewForStep(sample, mode, step) {
  if (mode === "simple" && ["details", "review", "preview", "print"].includes(step)) return "simulation";
  return sample.view || "observed";
}
