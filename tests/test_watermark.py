from __future__ import annotations

from orthoplan.watermark import (
    CANARY_TOKEN,
    GEOMETRY_SIGNATURE_MAGNITUDE_MM,
    WATERMARK_SCHEMA,
    DataWatermark,
    contains_canary,
    content_bound_watermark,
    detect_geometry_signature,
    embed_geometry_signature,
    new_watermark,
    stamp_solid_name,
    watermark_block,
)


def test_new_watermark_carries_canary_and_notice() -> None:
    mark = new_watermark()
    assert mark.canary == CANARY_TOKEN
    assert "DATA_LICENSE.md" in mark.notice
    assert mark.watermark_id


def test_new_watermark_ids_are_unique() -> None:
    a, b = new_watermark(), new_watermark()
    assert a.watermark_id != b.watermark_id


def test_new_watermark_binds_content_hash_when_given() -> None:
    mark = new_watermark(content_sha256="a" * 64)
    assert mark.content_sha256 == "a" * 64


def test_watermark_block_is_json_safe_with_schema_alias() -> None:
    mark = new_watermark()
    block = watermark_block(mark)
    assert block["schema"] == WATERMARK_SCHEMA
    assert block["canary"] == CANARY_TOKEN
    assert block["watermark_id"] == mark.watermark_id
    # created_at must have round-tripped to a JSON-serializable string.
    assert isinstance(block["created_at"], str)


def test_watermark_round_trips_through_model_validate() -> None:
    mark = new_watermark(content_sha256="b" * 64)
    block = watermark_block(mark)
    restored = DataWatermark.model_validate(block)
    assert restored.watermark_id == mark.watermark_id
    assert restored.content_sha256 == "b" * 64


def test_stamp_solid_name_embeds_id_and_canary() -> None:
    mark = new_watermark()
    stamped = stamp_solid_name("plan_stage_00", mark)
    assert stamped.startswith("plan_stage_00__oso-wm:")
    assert mark.watermark_id in stamped
    assert CANARY_TOKEN in stamped


def test_content_bound_watermark_is_deterministic_for_same_seed() -> None:
    a = content_bound_watermark("plan-1:deadbeef")
    b = content_bound_watermark("plan-1:deadbeef")
    assert a.watermark_id == b.watermark_id
    assert a.created_at is None  # reproducible output carries no wall-clock time


def test_content_bound_watermark_differs_for_different_seed() -> None:
    a = content_bound_watermark("plan-1:deadbeef")
    b = content_bound_watermark("plan-1:cafef00d")
    assert a.watermark_id != b.watermark_id


def test_contains_canary_detects_exact_token_only() -> None:
    assert contains_canary(f"some model output containing {CANARY_TOKEN} verbatim")
    assert not contains_canary("ordinary text with no marker at all")
    assert not contains_canary(CANARY_TOKEN.lower())


_TRIANGLE = (
    (0.0, 0.0, 0.0),
    (10.0, 0.0, 0.0),
    (0.0, 10.0, 0.0),
)
_ADJACENT_TRIANGLE = (
    (10.0, 0.0, 0.0),
    (10.0, 10.0, 0.0),
    (0.0, 10.0, 0.0),
)


def test_embed_geometry_signature_nudges_vertices_imperceptibly() -> None:
    mark = new_watermark()
    signed = embed_geometry_signature([_TRIANGLE], mark)
    for original, moved in zip(_TRIANGLE, signed[0]):
        for a, b in zip(original, moved):
            assert 0 < abs(a - b) <= GEOMETRY_SIGNATURE_MAGNITUDE_MM


def test_embed_geometry_signature_keeps_shared_edges_watertight() -> None:
    # The shared edge (10,0,0)-(0,10,0) must stay bit-identical across both
    # triangles after signing, or the mesh would gain a seam.
    mark = new_watermark()
    signed = embed_geometry_signature([_TRIANGLE, _ADJACENT_TRIANGLE], mark)
    tri_a, tri_b = signed
    assert tri_a[1] == tri_b[0]  # (10,0,0) in both
    assert tri_a[2] == tri_b[2]  # (0,10,0) in both


def test_embed_geometry_signature_is_deterministic() -> None:
    mark = new_watermark()
    first = embed_geometry_signature([_TRIANGLE], mark)
    second = embed_geometry_signature([_TRIANGLE], mark)
    assert first == second


def test_detect_geometry_signature_confirms_matching_id() -> None:
    mark = new_watermark()
    signed = embed_geometry_signature([_TRIANGLE, _ADJACENT_TRIANGLE], mark)
    assert detect_geometry_signature(signed, mark.watermark_id) == 1.0


def test_detect_geometry_signature_rejects_wrong_id() -> None:
    mark = new_watermark()
    other = new_watermark()
    signed = embed_geometry_signature([_TRIANGLE, _ADJACENT_TRIANGLE], mark)
    assert detect_geometry_signature(signed, other.watermark_id) == 0.0


def test_detect_geometry_signature_on_unsigned_mesh_is_zero() -> None:
    mark = new_watermark()
    assert detect_geometry_signature([_TRIANGLE], mark.watermark_id) == 0.0


def _parse_ascii_vertex_triangles(text: str) -> list[tuple]:
    vertices = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("vertex"):
            _, x, y, z = stripped.split()
            vertices.append((float(x), float(y), float(z)))
    return [tuple(vertices[i : i + 3]) for i in range(0, len(vertices), 3)]


def test_solid_stl_hidden_geometry_signature_survives_text_round_trip() -> None:
    from orthoplan.print_stl import solid_stl

    mark = new_watermark()
    triangle = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0))
    text = solid_stl("part", [triangle], mark)

    triangles = _parse_ascii_vertex_triangles(text)
    # Strong match for the id that signed it, no match for an unrelated one.
    assert detect_geometry_signature(triangles, mark.watermark_id) == 1.0
    other = new_watermark()
    assert detect_geometry_signature(triangles, other.watermark_id) == 0.0
    # Confirms this is a genuinely separate, non-textual layer: the id string
    # itself never appears anywhere in the vertex/facet body of the file.
    vertex_lines = "\n".join(line for line in text.splitlines() if "vertex" in line)
    assert mark.watermark_id not in vertex_lines
