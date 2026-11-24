"""Compare original weeks 1, 7 and 21 without changing geometry.

Run from the repository root with .venv/bin/python and NumPy/Matplotlib.
Exact-coordinate topology reuses the existing inventory implementation.
"""

import importlib.util
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

BUNDLE = Path(__file__).resolve().parent
CASE = BUNDLE.parents[1]
ROOT = CASE.parents[1]
sys.path.insert(0, str(ROOT))
from tools import check_sample_topology as topology  # noqa: E402
from tools.compare_canonical_progress import read_triangles  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'visit_views', CASE/'visits/progress-02/evaluate_meshes.py')
views = importlib.util.module_from_spec(spec)
spec.loader.exec_module(views)


def inputs():
    baseline = json.loads((CASE/'manifest.json').read_text())['scans']
    latest = json.loads((BUNDLE/'manifest.json').read_text())['scans']
    for week, folder, scans in [(1, CASE, baseline[:2]), (7, CASE, baseline[2:]),
                                (21, BUNDLE, latest)]:
        for scan in scans:
            yield week, folder, scan


def measure(week, folder, scan):
    topology.CASE = folder
    record = topology.inspect(scan)
    t = read_triangles(folder/scan['filename'], scan['sha256'])
    areas = np.linalg.norm(np.cross(t[:, 1]-t[:, 0], t[:, 2]-t[:, 0]), axis=1)/2
    lengths = np.linalg.norm(t[:, [1, 2, 0]]-t, axis=2)
    record.update(reported_week=week, arch=scan['arch'], units=scan['units'],
        extent_source_units=np.ptp(t.reshape(-1, 3), axis=0).tolist(),
        surface_area_source_units_squared=float(areas.sum()),
        triangle_area_percentiles=dict(zip(['p05','p50','p95'], np.percentile(areas,[5,50,95]).tolist())),
        edge_length_percentiles=dict(zip(['p05','p50','p95'], np.percentile(lengths,[5,50,95]).tolist())),
        source_file=str((folder/scan['filename']).relative_to(CASE)))
    return record, t


def main():
    records = []
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), facecolor='white')
    latest = []
    for week, folder, scan in inputs():
        record, t = measure(week, folder, scan)
        records.append(record)
        row = 0 if scan['arch']=='maxillary' else 1
        col = [1,7,21].index(week)
        signs = [-1,1,-1] if row==0 and week!=7 else [1,1,1]
        views.draw_view(axes[row,col], t, [0,1,2], signs,
                        f"Week {week} | {'upper' if row==0 else 'lower'}")
        if week==21:
            latest.append((scan,t))
        print(json.dumps(record), flush=True)
    fig.suptitle('USER_ONE | original scan surfaces | weeks 1, 7 and 21', fontsize=17)
    fig.text(.5,.025,'All triangles rendered; each panel fitted independently. Camera rotations only.\n'
             'No anatomical registration, geometry repair or scale validation.',ha='center')
    fig.subplots_adjust(top=.91,bottom=.09,wspace=.03,hspace=.12)
    fig.savefig(BUNDLE/'comparison-views.png',dpi=120)
    plt.close(fig)
    fig, axes=plt.subplots(2,3,figsize=(15,10),facecolor='white')
    cameras=[([0,1,2],[1,1,1],'+Z'),([0,1,2],[-1,1,-1],'-Z'),
             ([0,2,1],[1,-1,1],'+Y')]
    for row,(scan,t) in enumerate(latest):
        for ax,(permutation,signs,direction) in zip(axes[row],cameras):
            views.draw_view(ax,t,permutation,signs,f"Week 21 {scan['arch']} | {direction}")
    fig.suptitle('Week 21 | three views per original arch',fontsize=17)
    fig.subplots_adjust(top=.92,bottom=.04,wspace=.03,hspace=.12)
    fig.savefig(BUNDLE/'week-21-views.png',dpi=120)
    plt.close(fig)
    report={'schema':'opensource-ortho-scan-topology-comparison-v1',
        'specimen_id':CASE.name,'generator':'evaluate_comparison.py',
        'method':'Exact-coordinate vertex deduplication, undirected edge incidence and vertex connectivity; float64 areas; all source triangles.',
        'input_geometry_modified':False,'scans':records,
        'dependencies':{'numpy':np.__version__,'matplotlib':matplotlib.__version__},
        'not_assessed':['self intersections','vertex manifoldness','winding consistency',
            'scanner accuracy','verified anatomical completeness','physical scale',
            'bite accuracy','cross-visit registration','tooth movement'],
        'interpretation':'Open shell margins are expected; boundary counts and triangle density are not accuracy measures.'}
    (BUNDLE/'mesh-quality-comparison.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
