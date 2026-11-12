import pytest
np = pytest.importorskip('numpy')
pytest.importorskip('scipy')
from orthoplan.segmentation.topology import propagate_seeds, repair_face_islands  # noqa: E402


def strip():
    faces = []
    for x in range(8):
        a, b, c, d = [x, 0, 0], [x+1, 0, 0], [x, 1, 0], [x+1, 1, 0]
        faces.extend([[a, b, c], [b, d, c]])
    return np.array(faces, dtype=float)


def test_surface_propagation_is_independent_of_face_order_and_holds_disconnected_faces():
    mesh = strip()
    mesh = np.concatenate([mesh, mesh[:1]+[0, 0, 20]])
    seeds = np.zeros(len(mesh), dtype=int)
    seeds[0], seeds[15] = 11, 21
    labels = propagate_seeds(mesh, seeds)
    assert set(labels[:8]) == {11} and set(labels[8:16]) == {21}
    assert labels[-1] == 0
    order = np.random.default_rng(3).permutation(len(mesh))
    shuffled = propagate_seeds(mesh[order], seeds[order])
    np.testing.assert_array_equal(shuffled[np.argsort(order)], labels)


def test_island_repair_uses_neighbors_not_stl_runs():
    mesh = strip()
    labels = [11]*len(mesh)
    labels[7] = 21
    fixed = repair_face_islands(mesh, labels)
    assert fixed == [11]*len(mesh)
    order = np.random.default_rng(8).permutation(len(mesh))
    shuffled = repair_face_islands(mesh[order], np.array(labels)[order])
    np.testing.assert_array_equal(np.array(shuffled)[np.argsort(order)], fixed)
    with pytest.raises(ValueError, match='number'):
        repair_face_islands(mesh, [11])
