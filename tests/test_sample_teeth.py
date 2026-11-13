"""Painted sample regions preserve source faces and never imply review or scale."""
import base64
import pytest

from orthoplan.datasets import SAMPLE_CASE_DIR
from orthoplan.io.mesh_import import read_mesh_geometry
from orthoplan.mesh_workspace import resolve_mesh_path
from orthoplan.sample_teeth import sample_annotation, sample_teeth_payload
from orthoplan.region_corrections import baseline_source


def test_saved_week_seven_regions_export_exact_painted_triangles(tmp_path):
    workspace = tmp_path / 'meshes'
    result = sample_teeth_payload({'visit': 'progress-01'}, workspace=workspace, root=tmp_path/'labels')
    assert result['ok'], result
    assert len(result['teeth']) == 28
    assert all(not link['reviewed'] for link in result['plan_fragment']['tooth_meshes'])
    assert all(scan['asset']['units'] == 'unverified' for scan in result['scan_sources'])
    for arch in ['upper', 'lower']:
        record, origin = sample_annotation(arch, 'progress-01', root=tmp_path/'labels')
        assert origin == 'private-archive'
        source = baseline_source(arch, 'progress-01')
        _, vertices = read_mesh_geometry(SAMPLE_CASE_DIR / source['filename'])
        labels = base64.b64decode(record['labels_base64'])
        for tooth in result['teeth']:
            if tooth['arch'] != ('maxillary' if arch == 'upper' else 'mandibular'):
                continue
            expected = [v for face, label in enumerate(labels) if label == int(tooth['tooth']) for v in vertices[face*3:face*3+3]]
            _, actual = read_mesh_geometry(resolve_mesh_path(tooth['mesh_asset_id'], workspace=workspace))
            assert actual == expected


@pytest.mark.parametrize('visit', ['../private', 'progress-02', '', None])
def test_unknown_sample_visits_fail_closed(visit, tmp_path):
    result = sample_teeth_payload({'visit': visit}, workspace=tmp_path/'meshes', root=tmp_path/'labels')
    assert not result['ok']
    assert not (tmp_path/'meshes').exists()


def test_walkthrough_override_is_explicit_and_private(tmp_path, monkeypatch):
    import orthoplan.sample_teeth as module
    monkeypatch.setattr(module, 'SAMPLE_CASE_DIR', tmp_path)
    media = tmp_path/'private/media'
    media.mkdir(parents=True)
    video = media/'workflow-demo.webm'
    assert module.sample_walkthrough_path('/workflow-demo.webm') is None
    video.write_bytes(b'private recording')
    assert module.sample_walkthrough_path('/workflow-demo.webm') == video
    for path in ['/private/media/workflow-demo.webm', '/../../workflow-demo.webm', '/secret.json']:
        assert module.sample_walkthrough_path(path) is None
