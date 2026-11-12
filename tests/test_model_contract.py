import hashlib
import json
import pytest
np = pytest.importorskip('numpy')
from orthoplan.segmentation.model_contract import FEATURES, read_contract, run_contract  # noqa: E402


def fixture(tmp_path):
    onnx = pytest.importorskip('onnx')
    from onnx import helper, TensorProto, numpy_helper
    weights = np.zeros((15, 3), dtype=np.float32)
    weights[0] = [0, -1, 1]
    graph = helper.make_graph([helper.make_node('MatMul', ['features', 'weights'], ['logits'])], 'synthetic-contract-fixture',
                             [helper.make_tensor_value_info('features', TensorProto.FLOAT, [1, 'faces', 15])],
                             [helper.make_tensor_value_info('logits', TensorProto.FLOAT, [1, 'faces', 3])],
                             [numpy_helper.from_array(weights, 'weights')])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid('', 17)], ir_version=9)
    path = tmp_path/'fixture.onnx'
    onnx.save(model, path)
    contract = dict(schema='ortho-face-model-v1', features=FEATURES, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    arches=['maxillary'], input_layout='NFC', output_layout='NFL', input_name='features', output_name='logits',
                    class_to_fdi={'maxillary':['0','11','21']}, provenance='Synthetic linear classifier for runtime contract testing', license='Apache-2.0')
    sidecar = tmp_path/'fixture.onnx.json'
    sidecar.write_text(json.dumps(contract))
    return path, contract, sidecar


def test_actual_onnx_runtime_uses_explicit_layout_and_fdi_classes(tmp_path):
    pytest.importorskip('onnxruntime')
    path, contract, sidecar = fixture(tmp_path)
    points = [(-1,0,0),(-1,1,0),(-1,0,1),(1,0,0),(1,1,0),(1,0,1)]
    assert run_contract(points, 'maxillary', path) == [11,21]
    contract['output_layout'] = 'NLF'
    sidecar.write_text(json.dumps(contract))
    with pytest.raises(ValueError, match='shape'):
        run_contract(points, 'maxillary', path)
    contract['sha256'] = '0'*64
    sidecar.write_text(json.dumps(contract))
    with pytest.raises(ValueError, match='hash'):
        read_contract(path, 'maxillary')
