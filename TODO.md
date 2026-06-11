# TODO

## Browser planning roadmap

Goal: make the main browser workspace accept STL and CBCT/DICOM records in a
phased, safety-bound way. A "full plan" means reproducible staged geometry plus
clearly labeled findings and data limitations. It must never mean diagnosis,
clinical approval, treatment clearance, or authorization for physical use.

### Phase 1: Durable browser intake and case storage

- [x] Add real browser-to-engine upload for STL bytes instead of browser-memory
  metadata only.
- [x] Register uploaded STL files automatically into the local mesh workspace.
- [x] Add CBCT/DICOM upload as local-only case records, storing volume references
  and redacted metadata rather than volume bytes in plan JSON.
- [x] Add photo/X-ray/notes attachment records as enhanced-review context.
- [x] Persist cases with scan provenance, modality, units, arch, file IDs, and
  engine version.
- [x] Make UI copy distinguish STL-only, enhanced-records, and CBCT-attached
  cases from root/bone-aware review.
- [x] Add PHI/path redaction tests for all uploaded record types.

### Phase 2: Excellent STL surface planning

- [ ] Make scale/unit confirmation a required gate before millimeter movement
  checks run.
- [ ] Run auto-segmentation from uploaded whole-arch STL files through
  `/api/segment`.
- [ ] Build a segmentation review UI for tooth labels, missing teeth, rejected
  fragments, and reviewer corrections.
- [ ] Persist segmentation proposals, edits, and applied per-tooth mesh links per
  case/version.
- [ ] Render real segmented per-tooth STL fragments in the browser viewer.
- [ ] Generate movement from segmented crown geometry where available.
- [ ] Run crown collision, spacing, IPR, attachment, and movement-cap checks from
  the same engine data used by the viewer.
- [ ] Export STL-surface reports that clearly list unresolved data gaps for roots,
  bone, periodontal status, occlusion, and CBCT anatomy.

### Phase 3: Real per-tooth print/export

- [ ] Transform actual per-tooth mesh vertices for stage exports when reviewed
  segmentation exists.
- [ ] Keep schematic/proxy export only as a labeled fallback.
- [ ] Include hashes for original scans, segmentation fragments, stage frames,
  findings, and generated artifacts.
- [ ] Label every export with review tier: STL-only, enhanced-records, or
  CBCT-registered/root-bone-aware when that exists.
- [ ] Add print-package tests that prove exports use real mesh geometry when
  available and fail closed when geometry is missing.

### Phase 4: CBCT/DICOM ingestion and viewer

- [ ] Add optional `dicom` extra using `pydicom` or a similarly reviewed local
  dependency.
- [ ] Parse DICOM metadata locally: study date, modality, voxel spacing,
  dimensions, orientation, and redacted provenance.
- [ ] Add local volume registration/storage contract; never serialize volume
  bytes into plan JSON.
- [ ] Add axial/coronal/sagittal slice viewer in the browser, or a clean handoff
  path to a trusted local viewer such as 3D Slicer.
- [ ] Show CBCT status in the case UI: attached, viewed, registered,
  anatomy-reviewed, or unavailable.
- [ ] Keep CBCT attachment from changing movement generation until registration
  and reviewed anatomy contracts exist.

### Phase 5: STL-to-CBCT registration

- [ ] Add `RegistrationTransform` model with source STL asset, target CBCT
  record, transform matrix, method, operator/model provenance, quality score, and
  notes.
- [ ] Support imported/manual registration transforms before automatic
  registration.
- [ ] Add registration quality metrics and browser visualization overlays.
- [ ] Add automatic registration experiments behind optional Open3D/VTK-style
  dependencies.
- [ ] Prevent CBCT-derived checks from running unless registration quality is
  present and accepted.
- [ ] Add synthetic and fixture-based registration validation tests.

### Phase 6: Reviewed CBCT-derived anatomy

- [ ] Add models for root meshes or root centerlines per tooth.
- [ ] Add models for trusted tooth axes derived from reviewed crown/root anatomy.
- [ ] Add alveolar bone surface or boundary-volume records.
- [ ] Track source record, registration transform, model/operator provenance,
  confidence, and review/correction status for every derived object.
- [ ] Build browser review UI for accepting, correcting, or rejecting derived
  anatomy.
- [ ] Fail closed when anatomy is missing, uncertain, out of field, or
  unreviewed.

### Phase 7: Root/bone-aware review checks

- [ ] Add deterministic root proximity and inter-root collision warnings.
- [ ] Add cortical boundary proximity warnings.
- [ ] Add root/bone context for tip, torque, intrusion, extrusion, and expansion.
- [ ] Add "cannot assess" findings when registration, segmentation, or anatomy
  review quality is insufficient.
- [ ] Keep verdict vocabulary limited to `CONSISTENT`, `ISSUES`, and
  `NOT_APPLICABLE`.
- [ ] Add root/bone-aware tests with known fixture geometry and expected findings.

### Phase 8: Browser/mobile handoff

- [ ] Export browser-generated case review JSON that mobile can import as an
  opaque stored review.
- [ ] Add case handoff link/QR/deep-link for opening the same local/hosted case
  on a device.
- [ ] Make mobile imports show review tier, unresolved data gaps, and whether the
  source plan can only be edited in the browser/full engine.
