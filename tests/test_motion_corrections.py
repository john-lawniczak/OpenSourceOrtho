import base64
import pytest
np=pytest.importorskip("numpy")
from orthoplan.longitudinal.corrections import correction_segments  # noqa:E402


def test_corrected_boundaries_and_source_identity():
    triangles=np.random.default_rng(4).normal(size=(12,3,3))
    record=dict(schema="ortho-region-corrections-v1",source_sha256="abc",arch="upper",face_count=12,
                labels_base64=base64.b64encode(bytes([11]*6+[12]*6)).decode())
    segments=correction_segments(record,triangles,"abc","maxillary")
    assert [s.tooth_value for s in segments]==["11","12"]
    assert len(segments[0].triangles)==6
    with pytest.raises(ValueError,match="hash"):
        correction_segments(record,triangles,"wrong","maxillary")
