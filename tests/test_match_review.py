import pytest
np = pytest.importorskip('numpy')
pytest.importorskip('scipy')
from orthoplan.longitudinal.match_review import apply_match_overrides, reversible_fit_evidence  # noqa: E402
from orthoplan.longitudinal.rigid import fit_endpoint, transform  # noqa: E402


def test_overrides_allow_swaps_and_holds_but_reject_duplicate_or_partial_identity():
    regions = [dict(tooth=str(t), faces=np.arange(i*10,(i+1)*10), points=np.zeros((10,3)), confidence=.5) for i,t in enumerate([11,12])]
    swapped = apply_match_overrides(regions, regions, [], {'11':'12','12':'11'})
    assert [r['tooth'] for r in swapped] == ['12','11']
    assert swapped[0]['faces'] == list(range(10,20))
    assert apply_match_overrides(regions, regions, [], {'11':None,'12':'11'})[0] is None
    for mapping in ({'11':'12','12':'12'}, {'11':'12'}, {'11':'99','12':None}):
        with pytest.raises(ValueError):
            apply_match_overrides(regions, regions, [], mapping)


def test_reversible_fit_evidence_recovers_known_motion():
    source=np.random.default_rng(4).normal(size=(600,3))
    matrix=np.eye(4)
    matrix[:3,3]=[.1,.04,-.03]
    target=transform(source,matrix)
    fitted,_=fit_endpoint(source,target)
    evidence=reversible_fit_evidence(source,target,fitted)
    assert evidence['round_trip_shift']<1e-8
    assert evidence['sampling_shift']<1e-8
    assert evidence['round_trip_rotation_deg']<1e-6
