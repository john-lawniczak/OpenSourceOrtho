"""Deterministic exploratory rigid fitting; no scaling, deformation, or repairs."""
import itertools

import numpy as np
from scipy.spatial import cKDTree
import open3d as o3d


def sample_surface(triangles, count=12000, seed=21):
    rng = np.random.default_rng(seed)
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                    triangles[:, 2] - triangles[:, 0]), axis=1)
    chosen = triangles[rng.choice(len(triangles), count, p=areas / areas.sum())]
    u, v = rng.random((2, count))
    u = np.sqrt(u)
    return (1 - u[:, None]) * chosen[:, 0] + (u * (1-v))[:, None] * chosen[:, 1] + (u*v)[:, None] * chosen[:, 2]


def transform(points, matrix):
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def rigid_fit(a, b):
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    u, _, vt = np.linalg.svd((a-ca).T @ (b-cb))
    rotation = vt.T @ np.diag([1, 1, np.linalg.det(vt.T @ u.T)]) @ u.T
    result = np.eye(4)
    result[:3, :3], result[:3, 3] = rotation, cb - rotation @ ca
    return result


def trimmed_icp(source, target, initial, iterations=60):
    tree = cKDTree(target)
    matrix = initial.copy()
    old_error = np.inf
    keep = int(len(source) * .8)
    for _ in range(iterations):
        points = transform(source, matrix)
        distance, nearest = tree.query(points)
        ids = np.argpartition(distance, keep)[:keep]
        step = rigid_fit(points[ids], target[nearest[ids]])
        matrix = step @ matrix
        error = np.mean(distance[ids] ** 2)
        if abs(old_error-error) < 1e-8:
            break
        old_error = error
    distances = tree.query(transform(source, matrix))[0]
    return matrix, float(np.mean(np.sort(distances)[:keep] ** 2))


def candidate_frames(source, target):
    sc, tc = source.mean(axis=0), target.mean(axis=0)
    _, _, sa = np.linalg.svd(source-sc, full_matrices=False)
    _, _, ta = np.linalg.svd(target-tc, full_matrices=False)
    yield np.eye(4)
    for order in itertools.permutations(range(3)):
        for signs in itertools.product([-1, 1], repeat=3):
            rotation = ta.T @ np.diag(signs) @ np.eye(3)[list(order)] @ sa
            if np.linalg.det(rotation) < .99:
                continue
            for offset in [-8, 0, 8]:
                matrix = np.eye(4)
                matrix[:3, :3] = rotation
                matrix[:3, 3] = tc - rotation @ sc + offset * ta[2]
                yield matrix


def register(reference, cast):
    source, target = sample_surface(reference, 8000), sample_surface(cast, 24000)
    fits = [trimmed_icp(source[::4], target[::2], initial, 25)
            for initial in candidate_frames(source, target)]
    finalists = sorted(fits, key=lambda item: item[1])[:6]
    refined = [trimmed_icp(source, target, matrix, 100) for matrix, _ in finalists]
    matrix, error = min(refined, key=lambda item: item[1])
    return matrix, error


def surface_distances(points, triangles):
    vertices, faces = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    mesh = o3d.t.geometry.TriangleMesh(o3d.core.Tensor(vertices.astype(np.float32)),
                                     o3d.core.Tensor(faces.reshape(-1, 3).astype(np.uint32)))
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(mesh)
    return scene.compute_distance(o3d.core.Tensor(points.astype(np.float32))).numpy().astype(float)


def summarize(distances):
    return {"median": float(np.median(distances)), "p90": float(np.percentile(distances, 90)),
            "p95": float(np.percentile(distances, 95)), "maximum": float(distances.max()),
            "fraction_within_0_25": float(np.mean(distances <= .25)),
            "fraction_within_0_5": float(np.mean(distances <= .5)),
            "fraction_within_1": float(np.mean(distances <= 1))}
