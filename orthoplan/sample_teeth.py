"""Source-bound painted USER_ONE regions for exploratory selection, never auto-reviewed."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_URL_ROOT
from orthoplan.io.mesh_import import read_mesh_geometry
from orthoplan.region_corrections import baseline_source, load_baseline_corrections, validate_corrections
from orthoplan.segmentation.heuristic import ToothSegment
from orthoplan.segmentation.mesh_export import export_proposal_rows


class MissingPaintedSample(ValueError):
    """No labels exist for the requested visit; invalid labels are a separate error."""


def sample_annotation(arch: str, visit: str, *, root: Path | None = None) -> tuple[dict, str]:
    source = baseline_source(arch, visit)
    saved = load_baseline_corrections(arch, visit=visit, root=root)
    if not saved['ok']:
        raise ValueError('Saved labels are invalid; reload or repair the saved annotation.')
    if saved['saved']:
        return saved['corrections'], 'local-save'
    folder = SAMPLE_CASE_DIR / 'private/annotations'
    index_path = folder / 'index.json'
    entry = json.loads(index_path.read_text()).get('visits', {}).get(visit, {}).get(arch) if index_path.exists() else None
    if entry:
        path = folder / entry['path']
        if path.parent != folder or path.is_symlink():
            raise ValueError('Invalid annotation index path.')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Archived annotation hash mismatch.')
        record = json.loads(raw)
        origin = 'private-archive'
    elif visit == 'initial':
        context = json.loads((SAMPLE_CASE_DIR / 'treatment-context.json').read_text())
        record = json.loads((SAMPLE_CASE_DIR / context['baseline_annotations'][arch]).read_text())
        origin = 'bundled-draft'
    else:
        raise MissingPaintedSample('No saved week 7 labels are available for this arch. Paint and save them first.')
    validate_corrections(record, arch, source)
    return record, origin


def painted_segments(vertices, record):
    labels = base64.b64decode(record['labels_base64'], validate=True)
    if len(vertices) != len(labels) * 3:
        raise ValueError('Painted labels do not match the source triangle order.')
    grouped = {}
    for face, tooth in enumerate(labels):
        if tooth:
            grouped.setdefault(tooth, []).append(tuple(vertices[face * 3:face * 3 + 3]))
    parts = []
    for tooth, triangles in sorted(grouped.items()):
        if len(triangles) < 4:
            continue
        center = tuple(sum(v[axis] for triangle in triangles for v in triangle) / (3 * len(triangles)) for axis in range(3))
        parts.append(ToothSegment(str(tooth), triangles, center, 0.0))
    return parts


def sample_teeth_payload(payload: dict, *, workspace=None, root: Path | None = None) -> dict:
    try:
        visit = payload.get('visit', 'progress-01')
        try:
            records = {arch: sample_annotation(arch, visit, root=root) for arch in ['upper', 'lower']}
        except MissingPaintedSample:
            if visit != 'progress-01' or payload.get('allow_baseline_fallback') is not True:
                raise
            result = sample_teeth_payload({'visit': 'initial'}, workspace=workspace, root=root)
            if result['ok']:
                result['notice'] = 'Week 7 painting is unavailable here; showing the week 1 baseline draft.'
            return result
        sources, teeth, assets, links, annotations = [], [], [], [], []
        for arch, anatomical in [('upper', 'maxillary'), ('lower', 'mandibular')]:
            source = baseline_source(arch, visit)
            record, origin = records[arch]
            asset, vertices = read_mesh_geometry(SAMPLE_CASE_DIR / source['filename'])
            parts = painted_segments(vertices, record)
            proposed, meshes, tooth_links = export_proposal_rows(parts, arch=anatomical, workspace=workspace)
            for link in tooth_links:
                link.reviewed = False
                link.notes = 'Contributor-painted region; identity/boundary review is still required.'
            teeth.extend(t.model_dump(mode='json') for t in proposed)
            assets.extend({**m.model_dump(mode='json'), 'units': source['units']} for m in meshes)
            links.extend(link.model_dump(mode='json') for link in tooth_links)
            url = f"{SAMPLE_URL_ROOT}/{source['filename']}"
            metadata = asset.model_dump(mode='json')
            metadata.update(units=source['units'], reference=url.lstrip('/'))
            sources.append({'name': source['filename'], 'url': url, 'segmentReference': url, 'arch': anatomical,
                            'asset': metadata, 'displayArchStack': visit == 'progress-01'})
            annotations.append({'arch': arch, 'origin': origin, 'source_sha256': source['sha256'],
                                'labels_sha256': hashlib.sha256(base64.b64decode(record['labels_base64'])).hexdigest(),
                                'tooth_ids': [p.tooth_value for p in parts], 'reviewed': record['reviewed']})
        return {'ok': True, 'visit': visit, 'scan_sources': sources, 'teeth': teeth, 'annotations': annotations,
                'requires_review': True, 'plan_fragment': {'mesh_assets': assets, 'tooth_meshes': links}}
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        return {'ok': False, 'errors': [str(exc)]}


def sample_walkthrough_path(url_path: str) -> Path | None:
    if url_path not in {'/workflow-demo.webm', '/workflow-demo.vtt', '/workflow-poster.jpg'}:
        return None
    path = SAMPLE_CASE_DIR / 'private/media' / url_path.lstrip('/')
    return path if path.is_file() and not path.is_symlink() else None
