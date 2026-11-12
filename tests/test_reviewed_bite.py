import pytest
from orthoplan.occlusion.reviewed_bite import apply_reviewed_bite
from orthoplan.occlusion.registration import register_bite


def test_reviewed_bite_binds_both_sources_and_rejects_scale_or_reflection():
    hashes = {"upper": "a", "lower": "b"}
    record = dict(
        schema="ortho-bite-review-v1",
        source_hashes=hashes,
        accepted=True,
        reviewer="Reviewer",
        reference_description="Independent bite landmarks",
        lower_to_upper=[[1, 0, 0, 2], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
    )
    assert apply_reviewed_bite(record, hashes, [(0, 0, 0)]) == [(2, 0, 0)]
    for change in (
        {"accepted": "true"},
        {"source_hashes": {"upper": "other", "lower": "b"}},
        {"lower_to_upper": [[-1, 0, 0, 2], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
    ):
        with pytest.raises(ValueError):
            apply_reviewed_bite({**record, **change}, hashes, [(0, 0, 0)])


def test_explicit_frame_is_not_repositioned_to_first_contact():
    upper = [(0, 0, 10), (1, 0, 10), (0, 1, 10)]
    lower = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]
    reviewed = register_bite(upper, lower, preserve_frame=True)
    assert reviewed.lower_offset == (0, 0, 0)
    assert reviewed.occlusal_gap_mm == 10
    unavailable = register_bite(
        upper, [(100, 100, 0), (101, 100, 0), (100, 101, 0)], preserve_frame=True
    )
    assert unavailable.mode == "unavailable"
