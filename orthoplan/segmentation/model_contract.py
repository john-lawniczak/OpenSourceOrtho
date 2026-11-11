"""An ONNX file is not enough: verify its declared feature, class and tensor contract."""
import hashlib
import json
from pathlib import Path

FEATURES = 'raw-vertices-normal-centered-centroid-15-v1'


def read_contract(weights, arch):
    path = Path(str(weights)+'.json')
    if not path.is_file():
        raise ValueError('Learned model requires a .onnx.json contract sidecar')
    contract = json.loads(path.read_text())
    if contract.get('schema') != 'ortho-face-model-v1' or contract.get('features') != FEATURES:
        raise ValueError('Unsupported model feature contract')
    if contract.get('sha256') != hashlib.sha256(Path(weights).read_bytes()).hexdigest():
        raise ValueError('Model hash does not match its contract')
    if arch not in contract.get('arches', []):
        raise ValueError('Model does not declare support for this arch')
    if contract.get('input_layout') not in ['NFC', 'NCF'] or contract.get('output_layout') not in ['NFL', 'NLF']:
        raise ValueError('Declare model input and output tensor layout')
    classes = contract.get('class_to_fdi', {}).get(arch)
    allowed = {str(q*10+n) for q in ([1, 2] if arch == 'maxillary' else [3, 4]) for n in range(1, 9)}
    if not isinstance(classes, list) or not classes or classes[0] != '0' or len(set(classes)) != len(classes) or not set(classes[1:]) <= allowed:
        raise ValueError('Declare unique FDI class mapping with context class 0')
    if not contract.get('provenance') or not contract.get('license'):
        raise ValueError('Record model provenance and license')
    return contract


def run_contract(vertices, arch, weights):
    import numpy as np
    import onnxruntime as ort
    ort.disable_telemetry_events()
    from orthoplan.segmentation.learned import _facets, _tri_centroid, build_cell_features
    contract = read_contract(weights, arch)
    facets = _facets(vertices)
    features = np.asarray(build_cell_features(facets, [_tri_centroid(f) for f in facets]), dtype=np.float32)
    if not np.isfinite(features).all():
        raise ValueError('Non-finite model features')
    inputs = features[None] if contract['input_layout'] == 'NFC' else features.T[None]
    session = ort.InferenceSession(str(weights), providers=['CPUExecutionProvider'])
    if len(session.get_inputs()) != 1 or session.get_inputs()[0].name != contract.get('input_name'):
        raise ValueError('Model input names differ from contract')
    output = session.run([contract['output_name']], {contract['input_name']: inputs})[0]
    if contract['output_layout'] == 'NLF':
        output = np.transpose(output, (0, 2, 1))
    classes = contract['class_to_fdi'][arch]
    if output.shape != (1, len(facets), len(classes)) or not np.isfinite(output).all():
        raise ValueError('Model output shape or values differ from contract')
    return [int(classes[i]) for i in output[0].argmax(axis=1)]
