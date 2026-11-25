"""Compare each cast scan to its same-day dental arch, retaining raw geometry."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

from tools.cast_registration import register, sample_surface, surface_distances, summarize, transform, trimmed_icp
from tools.compare_canonical_progress import read_triangles
from orthoplan.evaluation.capture_review import review_manifest
from orthoplan.model.dataset import read_manifest


def compare_repeats(bundle, manifest, records):
    repeat = []
    fitted = {item["capture_id"]: item for item in records}
    for first, second in [("upper-1-c1", "upper-1-c2"), ("upper-1-c1", "upper-1-c3")]:
        meshes = [read_triangles(bundle / f"{name}.stl", next(s["sha256"] for s in manifest["captures"] if s["capture_id"] == name)) for name in (first, second)]
        av, bv = [np.unique(t.reshape(-1, 3), axis=0) for t in meshes]
        distance = cKDTree(bv).query(av)[0]
        initial = np.array(fitted[second]["dental_to_cast_rigid_transform"]) @ np.array(fitted[first]["cast_to_dental_rigid_transform"])
        matrix, _ = trimmed_icp(sample_surface(meshes[0], 8000), sample_surface(meshes[1], 24000), initial, 100)
        aligned = surface_distances(transform(sample_surface(meshes[0], 16000, 2110), matrix), meshes[1])
        repeat.append({"source": first, "target": second,
                       "original_frame_note": "Nearest-vertex comparison before fitting; pose differences are not shape error.",
                       "exact_vertex_fraction": float(np.mean(distance == 0)),
                       "original_frame_distances": summarize(distance),
                       "source_to_target_rigid_transform": matrix.tolist(),
                       "aligned_source_surface_to_target": summarize(aligned),
                       "method": "Rigid 80%-trimmed ICP seeded by dental-reference fits; separate held-out samples against target triangles. No scaling."})
    return repeat


def compare(bundle):
    manifest = json.loads((bundle / "source-metadata.json").read_text())
    case = bundle.parents[2]
    dental_manifest = json.loads((case / "visits/progress-03/manifest.json").read_text())
    refs = {("upper" if scan["arch"] == "maxillary" else "lower"): scan for scan in dental_manifest["scans"]}
    triangles = {arch: read_triangles(case / "visits/progress-03" / scan["filename"], scan["sha256"])
                 for arch, scan in refs.items()}
    records = []
    fig, axes = plt.subplots(6, 3, figsize=(16, 25), facecolor="white")
    for row, scan in enumerate(manifest["captures"]):
        cast = read_triangles(bundle / scan["filename"], scan["sha256"])
        reference = triangles[scan["arch"]]
        dental_to_cast, fit_error = register(reference, cast)
        cast_to_dental = np.linalg.inv(dental_to_cast)
        samples = sample_surface(reference, 16000, seed=2101)
        cast_samples = sample_surface(cast, 16000, seed=2102)
        distances = surface_distances(transform(samples, dental_to_cast), cast)
        reverse = surface_distances(transform(cast_samples, cast_to_dental), reference)
        record = {"capture_id": scan["capture_id"], "source_sha256": scan["sha256"],
                  "reference_sha256": refs[scan["arch"]]["sha256"],
                  "dental_to_cast_rigid_transform": dental_to_cast.tolist(),
                  "cast_to_dental_rigid_transform": cast_to_dental.tolist(),
                  "trimmed_fit_mean_squared_point_distance": fit_error,
                  "dental_surface_to_cast": summarize(distances),
                  "cast_surface_to_dental_including_cast_walls": summarize(reverse),
                  "status": "exploratory rigid surface alignment; not an anatomical validation"}
        if scan.get("intact_arch_reference") is False:
            record["interpretation_caveat"] = "Two-piece cast held together with clay; relative fragment alignment unverified. Distances describe this assembly, not intact-arch accuracy or scanner performance."
        records.append(record)
        print(json.dumps(record), flush=True)
        aligned = transform(cast_samples, cast_to_dental)
        for col, plane in enumerate([(0, 1), (0, 2), (1, 2)]):
            ax = axes[row, col]
            ax.scatter(aligned[::3, plane[0]], aligned[::3, plane[1]], s=.3, c="#94a3b8", alpha=.25)
            colors = ax.scatter(samples[::2, plane[0]], samples[::2, plane[1]], s=1.2,
                                c=distances[::2], cmap="viridis", vmin=0, vmax=2)
            ax.set_aspect("equal")
            suffix = "\nreassembled with clay" if scan.get("intact_arch_reference") is False else ""
            ax.set_title(f'{scan["capture_id"]} | {"XYZ"[plane[0]]}{"XYZ"[plane[1]]}{suffix}')
            ax.set_axis_off()
        fig.colorbar(colors, ax=list(axes[row]), shrink=.55, label="Dental-to-cast distance (source units)")
    fig.suptitle("Week 21 | same-day dental surface vs personal casts | exploratory rigid fit", fontsize=17)
    fig.text(.5, .01, "Colored points: dental reference; gray: aligned cast. Color capped at 2 source units.\n"
             "No scaling/deformation. Cast walls and dental soft-tissue margins differ; distances are not tooth-level accuracy.", ha="center")
    fig.subplots_adjust(top=.96, bottom=.05, hspace=.15, right=.78)
    fig.savefig(bundle / "dental-comparison.png", dpi=110)
    plt.close(fig)
    repeat = compare_repeats(bundle, manifest, records)
    report = {"schema": "opensource-ortho-personal-cast-comparison-v1", "units": "unverified source units",
              "acquisition_review": review_manifest(read_manifest(bundle / "manifest.json")),
              "input_geometry_modified": False, "scans": records, "repeat_scan_checks": repeat,
              "method": "Deterministic area samples; 73 rigid initializations; 80%-trimmed nearest-point ICP; held-out 16000 dental samples measured against original cast triangles.",
              "limitations": ["Dental scan is a comparison reference, not independently measured ground truth.",
                              "No physical scale calibration, tooth segmentation, bite fit or nonrigid correction.",
                              "Lower C6 is a two-piece cast supported with clay; relative fragment alignment is unverified.",
                              "Whole-surface metrics include soft-tissue margins and cast walls; they do not isolate crown accuracy.",
                              "Distances conflate impression/casting/scanning differences and fitting error; these stages cannot be separated from these files alone."]}
    (bundle / "dental-comparison.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    compare(parser.parse_args().bundle.resolve())
