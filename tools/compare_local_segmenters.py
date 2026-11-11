"""Compare installed local candidates against the SAME independently labeled cases."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.segmentation.auto import HybridArchSegmenter, load_local_segmenter  # noqa: E402
from orthoplan.segmentation.surface_graph import SurfaceGraphSegmenter  # noqa: E402
from orthoplan.validation.segmentation_real_report import labelled_real_scan_report  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    candidates = [HybridArchSegmenter(), SurfaceGraphSegmenter(), load_local_segmenter()]
    reports = {}
    for model in candidates:
        if model.name not in reports:
            report = labelled_real_scan_report(manifest_path=args.manifest, candidate_segmenter=model)
            reports[model.name] = report.model_dump(mode='json')
            reports[model.name]['passed'] = report.passed
    args.output.write_text(json.dumps({'candidates': reports, 'selection': 'No automatic promotion'}, indent=2)+'\n')


if __name__ == '__main__':
    main()
