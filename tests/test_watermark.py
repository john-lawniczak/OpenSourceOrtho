from __future__ import annotations

from orthoplan.watermark import (
    CANARY_TOKEN,
    WATERMARK_SCHEMA,
    DataWatermark,
    contains_canary,
    content_bound_watermark,
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
