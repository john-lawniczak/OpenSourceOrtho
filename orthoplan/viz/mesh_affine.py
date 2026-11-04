"""Expose the engine's exact scan-local affine transform to mesh renderers."""

from orthoplan.planning.biomechanics import apply_pose_to_vertex


def mesh_affine(pose, frame):
    origin = apply_pose_to_vertex((0, 0, 0), pose, frame)
    basis = [apply_pose_to_vertex(v, pose, frame) for v in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
    return [[*(basis[j][i] - origin[i] for j in range(3)), origin[i]] for i in range(3)]
