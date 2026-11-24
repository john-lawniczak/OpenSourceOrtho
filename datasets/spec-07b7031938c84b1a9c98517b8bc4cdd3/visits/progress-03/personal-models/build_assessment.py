"""Rebuild the reviewed editorial assessment and explicit local download inventory."""
import hashlib
import json
from pathlib import Path

from orthoplan.evaluation.finding import Finding, lint_finding

BUNDLE = Path(__file__).resolve().parent
MODELS = [
    ("upper-model-1", "Upper Model 1", [1.75, 3.00, 2.00, .50], "upper-1-c3",
     "Best upper cast in this set. C1/C2 retain recognizable crown surfaces; C3 adds coverage. Boundary losses and unverified scale remain. Three files represent one physical cast, not three independent cast specimens."),
    ("upper-model-2", "Upper Model 2", [1.75, 2.00, 1.75, .50], "upper-2-c4",
     "Much of the retained surface aligns closely, but anterior local losses are visible and the contributor labels this cast more chipped. Its low median distance does not capture the importance of missing local detail."),
    ("lower-model-1", "Lower Model 1", [1.75, 3.25, 2.00, .50], "lower-1-c5",
     "Strongest overall reference agreement of this set, with most sampled dental surface nearby after rigid fitting. Local mismatch patches remain; casting walls account for some reverse-direction differences."),
    ("lower-model-2", "Lower Model 2", [1.75, 1.75, 1.25, .50], "lower-2-c6",
     "Contributor confirms the cast broke into two pieces and was held together with clay during scanning. The score is retained only as a research-usability rating of this assembled specimen. Its fragment positions are unverified; the larger mismatch cannot establish intact-arch accuracy or scanner performance. Reassembly, damage, casting and scan/fitting effects are confounded."),
]


def advisory(title, message):
    return lint_finding(Finding(severity="notice", category="data_gap", provenance="MODEL",
                                title=title, message=message)).model_dump(mode="json")


def main():
    manifest = json.loads((BUNDLE / "source-metadata.json").read_text())
    comparisons = json.loads((BUNDLE / "dental-comparison.json").read_text())
    models, findings = [], []
    for identity, label, parts, preferred, note in MODELS:
        score = sum(parts)
        models.append(dict(model_id=identity, label=label, score=score,
                           rubric_points=parts, preferred_inspection_capture=preferred))
        findings.append(advisory(label, f"{label}: {score:.2f}/10.00 for cast-scan research usability. {note}"))
    findings += [
        advisory("Score interpretation", "The four physical casts average 6.50/10.00 with equal weight per cast. Scores are quarter-point editorial judgments displayed to two decimals, not measured anatomical accuracy or a rating of contributor skill. No new dental-scan score is assigned; the earlier 8.50 visit score used a different rubric."),
        advisory("Repeat-capture evidence", "The contributor confirms C1, C2 and C3 are separate scans of Upper Model 1. Nevertheless, C1 and C2 share 97.79% of exact vertex positions and identical face counts/bounds. Retain that provenance, but treat their exported surfaces as highly correlated. They do not supply independent repeatability evidence. C1 versus C3 has a fitted median surface difference of about 0.037 source units, with local outliers; this is same-cast consistency, not accuracy."),
        advisory("Comparison limits", "Reference-to-cast medians are about 0.16 for Upper Model 1, 0.15 for Upper Model 2, 0.10 for Lower Model 1 and 0.53 for Lower Model 2, in unverified source units. Whole-surface distances include soft-tissue boundaries and local missing surfaces. The dental scan is a useful comparison reference, not independently measured ground truth; rigid fitting can absorb pose differences but not prove anatomical fidelity."),
        advisory("C6 fracture clarification", "Lower C6 is a two-piece cast supported with clay, per contributor clarification. Its original bytes and computed distances are preserved, but those distances describe an assembled specimen. A new scan of the same assembly cannot recover the original relative fragment positions or missing surfaces. Do not use C6 as an intact lower-arch reference."),
        advisory("Research value", "Same-day dental and cast scans reduce timing differences when studying the home acquisition workflow. Two physical casts per arch expose between-cast variability, while repeat captures of one cast help assess scanning/export consistency. Damaged models provide examples for detecting incomplete surfaces and reporting uncertainty. This is one contributor and four casts; it does not establish general performance or isolate each source of error."),
    ]
    captures = [{key: row[key] for key in ["capture_id", "model_id", "arch", "filename", "sha256"]}
                for row in manifest["captures"]]
    summary = {"schema": "opensource-ortho-personal-cast-summary-v1", "date": manifest["acquisition_date"],
               "reported_week": 21, "models": models, "captures": captures,
               "rubric": [{"category": name, "maximum": maximum} for name, maximum in [
                   ("File integrity/basic topology", 2), ("Visible coverage/cast preservation", 4),
                   ("Exploratory reference agreement", 3), ("Provenance and calibration", 1)]],
               "overall_score": 6.5, "score_scope": "subjective cast-scan research usability; not anatomical accuracy",
               "findings": findings, "gate": "All interpretations passed lint_finding; language check only."}
    (BUNDLE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    lines = ["# USER_ONE — week 21 personal cast assessment", "",
             "Four physical casts, six original STL exports, reported same-day acquisition on 2026-11-23. Contributor-authorized public companion records for progress-03.", "",
             "| Physical cast | Score / 10.00 | Preferred inspection file |", "| --- | ---: | --- |"]
    lines += [f'| {row["label"]} | {row["score"]:.2f} | {row["preferred_inspection_capture"]}.stl |' for row in models]
    lines += ["", "Equal-weight mean across four casts: **6.50/10.00**. Upper Model 1 is counted once despite its three scans.", "",
              "Rubric: file integrity/basic topology 2 points; visible coverage/cast preservation 4; exploratory reference agreement 3; provenance/calibration 1. The component scores appear in summary.json. Chips and missing local surfaces matter more than triangle count. Scores are subjective, not clinical evaluations or hundredth-point measurements.", "",
              "## Same-day reference comparison", "",
              "| Scan | Dental→cast median | Dental→cast p95 | Dental samples within 0.5 source units |", "| --- | ---: | ---: | ---: |"]
    for record in comparisons["scans"]:
        q = record["dental_surface_to_cast"]
        lines.append(f'| {record["capture_id"]} | {q["median"]:.3f} | {q["p95"]:.3f} | {q["fraction_within_0_5"]:.1%} |')
    lines += ["", "All distances use **unverified source units**, not calibrated millimeters. Registration is rigid only: no scaling, deformation, repairs or hole filling. All 16,000 held-out dental samples are included in the reported distances, including samples excluded from the 80%-trimmed fitting step. Crown-only segmentation was not performed. Boundary/soft-tissue differences can dominate the tails; a low median cannot rule out important local damage.", "",
              "## Reviewed advisory interpretations", ""]
    lines += [f'**{f["title"]}.** {f["message"]}\n' for f in findings]
    lines += ["## Record and reproduction", "",
              "- Original scan bytes are preserved and SHA-256 verified in manifest.json.\n- mesh-inventory.json records finite coordinates, connected components and topology. Each file is connected, has no duplicate triangles, and has 2–6 zero-area triangles/non-manifold edge incidences. Open edges include intentional scan margins.\n- cast-overview.png shows all source triangles in three independent views.\n- dental-comparison.json contains both transform directions, reference/source hashes, full distributions and repeat-capture checks. dental-comparison.png shows dental-to-cast distance colors.\n- Upper Model 2 is explicitly labeled more chipped by the source folder; other exact chip locations/timing remain unconfirmed. The contributor reports difficulty making intact models despite experience. Damage describes the physical casts, not the actual teeth.\n- The dental upper/lower bite relationship is unchanged. Casts have no measured shared bite frame and are not used as treatment-motion observations.", "",
              "From repository root, with NumPy/SciPy/Open3D/Matplotlib installed:", "", "```sh",
              "export MPLCONFIGDIR=/private/tmp/ortho-matplotlib",
              "PYTHONPATH=. .venv/bin/python tools/inspect_personal_casts.py " + str(BUNDLE.relative_to(BUNDLE.parents[4])),
              "OMP_NUM_THREADS=2 PYTHONPATH=. .venv/bin/python tools/compare_personal_casts.py " + str(BUNDLE.relative_to(BUNDLE.parents[4])),
              "PYTHONPATH=. .venv/bin/python " + str((BUNDLE / "build_assessment.py").relative_to(BUNDLE.parents[4])), "```", ""]
    report = "\n".join(lines)
    advisory("Complete report language check", report)
    (BUNDLE / "quality-assessment.md").write_text(report)
    names = [row["filename"] for row in captures] + ["manifest.json", "source-metadata.json", "summary.json", "mesh-inventory.json",
             "cast-overview.png", "dental-comparison.json", "dental-comparison.png", "quality-assessment.md"]
    index = {"specimen_id": manifest["specimen_id"], "progress_record_id": "progress-03",
             "publication_scope": "Public companion downloads; individual publication scope in case consent.json",
             "assets": {name: hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest() for name in names}}
    (BUNDLE / "record-assets.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
