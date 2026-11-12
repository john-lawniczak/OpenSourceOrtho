# Timing assumptions and proximity hints

Every simulated pose remains a rigid transformation of a baseline draft tooth
region. Timing changes the fraction of its fitted endpoint translation and
shortest-arc rotation, preserving the same endpoints:

- Uniform: equal progression per week slot.
- Slow start and finish: smoothstep progression, slower near either endpoint.
- Delayed start: hold through the first interval, then uniform progression.

These are alternative assumptions, not a model fitted to missing weekly scans.
The original week 1 and week 7 surfaces remain the observed endpoint views.
Timing selection never changes segmentation, correspondence, or endpoint fitting.

Each artifact also evaluates sampled within-arch surface proximity at every
profile's weekly poses. It records pairs within the declared threshold and flags
pairs newly near relative to baseline. The default threshold is 0.3% of the arch
span in source units, not a clinical tolerance. At most 256 vertices per region
are sampled. This can miss contacts and intersections; no hint means no clearance
claim. Draft boundaries may also produce false hints. The two simultaneous arch
viewports are not a bite registration, so no inter-arch contact claim is made.

Known-geometry tests cover monotone timing, exact endpoints, rigid shape
preservation, stationary regions, and newly approaching surface samples. These
tests verify implementation behavior, not patient-specific accuracy.
