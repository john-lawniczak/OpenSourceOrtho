"""Face adjacency and seeded surface propagation, independent of STL face order."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra


def face_graph(triangles, allowed=None):
    mesh = np.asarray(triangles, dtype=float)
    if mesh.ndim != 3 or mesh.shape[1:] != (3, 3) or not np.isfinite(mesh).all():
        raise ValueError('Expected finite triangle geometry')
    _, welded = np.unique(mesh.reshape(-1, 3), axis=0, return_inverse=True)
    vertices = welded.reshape(-1, 3)
    edges = np.sort(np.concatenate([vertices[:, [0, 1]], vertices[:, [1, 2]], vertices[:, [2, 0]]]), axis=1)
    owners = np.tile(np.arange(len(mesh)), 3)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    edges, owners = edges[order], owners[order]
    equal = np.all(edges[1:] == edges[:-1], axis=1)
    # Only manifold shared edges connect faces; duplicate/degenerate edges do not.
    pairs = np.flatnonzero(equal & ~np.r_[False, equal[:-1]] & ~np.r_[equal[1:], False])
    a, b = owners[pairs], owners[pairs+1]
    valid = a != b
    if allowed is not None:
        valid &= np.asarray(allowed)[a] & np.asarray(allowed)[b]
    a, b = a[valid], b[valid]
    centers = mesh.mean(axis=1)
    normals = np.cross(mesh[:, 1]-mesh[:, 0], mesh[:, 2]-mesh[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    crease = 1 - np.abs(np.sum(normals[a]*normals[b], axis=1))
    cost = np.maximum(np.linalg.norm(centers[a]-centers[b], axis=1), 1e-9) * (1+8*crease)
    return coo_matrix((np.r_[cost, cost], (np.r_[a, b], np.r_[b, a])), shape=(len(mesh), len(mesh))).tocsr()


def propagate_seeds(triangles, seeds, allowed=None):
    """Return draft face labels; disconnected faces without seeds stay context (0)."""
    seeds = np.asarray(seeds, dtype=int)
    if len(seeds) != len(triangles) or np.any(seeds < 0):
        raise ValueError('Seeds must have one nonnegative label per face')
    indices = np.flatnonzero(seeds)
    if not len(indices):
        raise ValueError('At least one seed is required')
    allowed = np.ones(len(seeds), dtype=bool) if allowed is None else np.asarray(allowed, dtype=bool)
    if len(allowed) != len(seeds) or not allowed[indices].all():
        raise ValueError('Seeds must lie inside the selected surface')
    graph = face_graph(triangles, allowed)
    distances, _, origins = dijkstra(graph, directed=False, indices=indices, min_only=True, return_predecessors=True)
    result = np.zeros(len(seeds), dtype=int)
    assigned = np.isfinite(distances) & allowed
    result[assigned] = seeds[origins[assigned]]
    result[indices] = seeds[indices]
    return result


def repair_face_islands(triangles, labels):
    """Repair a one-face island only when all adjacent non-context neighbors agree."""
    labels = np.asarray(labels, dtype=int)
    if labels.shape != (len(triangles),):
        raise ValueError('Model returned a different number of labels than faces')
    graph = face_graph(triangles)
    result = labels.copy()
    for i in range(len(labels)):
        neighbors = graph.indices[graph.indptr[i]:graph.indptr[i+1]]
        values = labels[neighbors]
        if labels[i] and len(values) >= 2 and values[0] and np.all(values == values[0]):
            result[i] = values[0]
    return result.tolist()
