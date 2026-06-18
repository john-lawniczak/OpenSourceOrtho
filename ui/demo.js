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

// The two STL scans the Sample Test Case loads as its "already uploaded" records.
// These are the exact models rendered in the sample's 3D preview.
export const canonicalScanSources = [
  {
    name: "sample-test-case-upper.stl",
    url: "./example-scans/canonical-orthocad-001/sample-test-case-upper.stl",
    segmentReference: "./example-scans/canonical-orthocad-001/sample-test-case-upper.stl",
    arch: "maxillary",
    asset: {
      id: "76daf4068ec39fa2",
      format: "stl-binary",
      provenance: "patient-derived",
      units: "mm",
      vertex_count: 990927,
      face_count: 330309,
      bounds: {
        min_xyz: [-30.415630340576172, -50.040771484375, -1.499996542930603],
        max_xyz: [32.407981872558594, 3.999868392944336, 15.583396911621094],
      },
      sha256: "76daf4068ec39fa2685607adc4ef50b254d275fb28d7a311af0f1dc9705e7166",
      reference: "example-scans/canonical-orthocad-001/sample-test-case-upper.stl",
    },
  },
  {
    name: "sample-test-case-lower.stl",
    url: "./example-scans/canonical-orthocad-001/sample-test-case-lower.stl",
    segmentReference: "./example-scans/canonical-orthocad-001/sample-test-case-lower.stl",
    arch: "mandibular",
    asset: {
      id: "5e4b629904c481bf",
      format: "stl-binary",
      provenance: "patient-derived",
      units: "mm",
      vertex_count: 860403,
      face_count: 286801,
      bounds: {
        min_xyz: [-31.994709014892578, -49.88878631591797, -15.29747200012207],
        max_xyz: [32.569801330566406, 0.7881450653076172, 3.537170886993408],
      },
      sha256: "5e4b629904c481bf914393b4935f324599d74031c78c92f2ad2e36e637243a72",
      reference: "example-scans/canonical-orthocad-001/sample-test-case-lower.stl",
    },
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
