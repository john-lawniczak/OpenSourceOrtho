export const demoInitialOffsets = {
  13: { x: 0.35, y: -0.18, z: 0 },
  12: { x: 0.55, y: 0.28, z: 0 },
  11: { x: -0.42, y: -0.32, z: 0 },
  21: { x: 0.44, y: 0.30, z: 0 },
  22: { x: -0.52, y: -0.26, z: 0 },
  23: { x: -0.32, y: 0.16, z: 0 },
  43: { x: 0.30, y: 0.14, z: 0 },
  42: { x: 0.48, y: -0.22, z: 0 },
  41: { x: -0.36, y: 0.26, z: 0 },
  31: { x: 0.38, y: -0.28, z: 0 },
  32: { x: -0.46, y: 0.24, z: 0 },
  33: { x: -0.28, y: -0.12, z: 0 },
};

export const canonicalScanSources = [
  {
    name: "308806025_shell_occlusion_u.stl",
    url: "./example-scans/canonical-orthocad-001/308806025_shell_occlusion_u.stl",
    arch: "maxillary",
  },
  {
    name: "308806025_shell_occlusion_l.stl",
    url: "./example-scans/canonical-orthocad-001/308806025_shell_occlusion_l.stl",
    arch: "mandibular",
  },
];

export function syntheticCrowdingRows(stageCount = 12, options = {}) {
  const rows = [];
  const movementStages = options.includeBaseline ? Math.max(1, stageCount - 1) : stageCount;
  for (let stage = 0; stage < stageCount; stage += 1) {
    for (const [tooth, offset] of Object.entries(demoInitialOffsets)) {
      const isBaseline = options.includeBaseline && stage === 0;
      rows.push({
        stage,
        tooth,
        x: isBaseline ? 0 : round(-offset.x / movementStages),
        y: isBaseline ? 0 : round(-offset.y / movementStages),
        z: 0,
        tip: 0,
        torque: 0,
        rotation: 0,
      });
    }
  }
  return rows;
}

function round(value) {
  return Math.round(value * 1000) / 1000;
}
