import base64
import hashlib
import struct
import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from orthoplan.longitudinal.api import motion_payload  # noqa: E402
from orthoplan.mesh_workspace import register_scan_mesh  # noqa: E402


def binary_mesh(triangles):
    return (
        bytes(80)
        + struct.pack("<I", len(triangles))
        + b"".join(struct.pack("<12fH", 0, 0, 1, *triangle.flatten(), 0) for triangle in triangles)
    )


def test_two_visit_pipeline_uses_corrected_identity_and_reference(tmp_path):
    rng = np.random.default_rng(2)
    triangles = np.concatenate(
        [rng.normal(size=(80, 3, 3)), rng.normal(size=(80, 3, 3)) + [8, 0, 0]]
    )
    raw = binary_mesh(triangles)
    path = tmp_path / "scan.stl"
    path.write_bytes(raw)
    asset = register_scan_mesh(path, workspace=tmp_path / "registry")
    correction = dict(
        schema="ortho-region-corrections-v1",
        source_sha256=hashlib.sha256(raw).hexdigest(),
        arch="upper",
        face_count=160,
        labels_base64=base64.b64encode(bytes([11] * 80 + [12] * 80)).decode(),
    )
    payload = dict(
        arch="upper",
        units="mm",
        units_confirmed=True,
        scans=[dict(reference="/api/mesh/" + asset.id, filename="scan.stl")] * 2,
        corrections=[correction, correction],
        reference_teeth=["11"],
    )
    kwargs = dict(workspace=tmp_path / "registry", ui_dir=tmp_path)
    result = motion_payload(payload, **kwargs)
    assert result["ok"], result
    preview = result["preview"]
    from orthoplan.longitudinal.contact_detail import contact_payload
    contact = contact_payload({"scan": payload["scans"][0], "preview": preview,
                               "teeth": ["11", "12"], "fraction": .5}, **kwargs)
    assert contact["ok"] and contact["result"]["status"] == "complete"
    assert contact["result"]["distance"] > 0
    assert "User-selected reference" in preview["reference"]
    assert preview["units_confirmation"]["unit"] == "mm"
    assert len(base64.b64decode(preview["target_face_labels_base64"])) == 160
    for tooth in preview["teeth"]:
        assert tooth["status"].startswith("estimated")
        np.testing.assert_allclose(tooth["translation"], 0, atol=1e-9)
        assert tooth["reviewed"] is False
    payload["corrections"][0] = {**correction, "source_sha256": "wrong"}
    assert "hash" in motion_payload(payload, **kwargs)["errors"][0]


def test_motion_input_validation_rejects_unconfirmed_scale_and_paths(tmp_path):
    kwargs = dict(workspace=tmp_path, ui_dir=tmp_path)
    payload = dict(arch="upper", units="mm", scans=[{"reference": "/etc/passwd"}] * 2)
    assert "Confirm" in motion_payload(payload, **kwargs)["errors"][0]
    payload["units_confirmed"] = True
    assert "registered" in motion_payload(payload, **kwargs)["errors"][0]
