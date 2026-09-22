"""Small voxel-geometry helpers for optional local CBCT proposal code."""

from __future__ import annotations

VoxelIndex = tuple[int, int, int]


def connected_components(voxels: list[VoxelIndex]) -> list[list[VoxelIndex]]:
    remaining = set(voxels)
    components: list[list[VoxelIndex]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = [seed]
        while stack:
            voxel = stack.pop()
            for neighbour in neighbours(voxel):
                if neighbour in remaining:
                    remaining.remove(neighbour)
                    stack.append(neighbour)
                    component.append(neighbour)
        components.append(component)
    return components


def neighbours(voxel: VoxelIndex) -> tuple[VoxelIndex, ...]:
    x, y, z = voxel
    return (
        (x - 1, y, z), (x + 1, y, z),
        (x, y - 1, z), (x, y + 1, z),
        (x, y, z - 1), (x, y, z + 1),
    )


def voxel_bounds(voxels: set[VoxelIndex]) -> tuple[VoxelIndex, VoxelIndex]:
    if not voxels:
        return (0, 0, 0), (0, 0, 0)
    return (
        (min(v[0] for v in voxels), min(v[1] for v in voxels), min(v[2] for v in voxels)),
        (max(v[0] for v in voxels), max(v[1] for v in voxels), max(v[2] for v in voxels)),
    )


def format_voxel(voxel: VoxelIndex) -> str:
    return ",".join(str(v) for v in voxel)


def touches_boundary(voxels: set[VoxelIndex], dimensions: tuple[int, int, int] | None) -> bool:
    if not dimensions or not voxels:
        return False
    max_index = tuple(max(0, value - 1) for value in dimensions)
    return any(any(coord in (0, max_index[i]) for i, coord in enumerate(voxel)) for voxel in voxels)


def boundary_voxel_count(voxels: set[VoxelIndex]) -> int:
    return sum(1 for voxel in voxels if any(neighbour not in voxels for neighbour in neighbours(voxel)))
