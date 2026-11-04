"""Exact triangle-distance search with bounding-box pruning.

The hierarchy only rejects pairs whose box separation exceeds an already known
surface distance. Leaf tests use the existing intersection and distance routines;
no triangles are sampled or discarded.
"""
from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass
from typing import Callable

from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]
Box = tuple[Vec3, Vec3]


@dataclass(slots=True)
class Node:
    box: Box
    count: int
    items: tuple[int, ...] = ()
    left: Node | None = None
    right: Node | None = None


def _box(triangle: Triangle) -> Box:
    return (tuple(min(p[i] for p in triangle) for i in range(3)),
            tuple(max(p[i] for p in triangle) for i in range(3)))


def _tree(boxes: list[Box], indexes: list[int]) -> Node:
    bounds = (tuple(min(boxes[j][0][i] for j in indexes) for i in range(3)),
              tuple(max(boxes[j][1][i] for j in indexes) for i in range(3)))
    return Node(bounds, len(indexes), tuple(indexes))


def _split(node: Node, boxes: list[Box]) -> tuple[Node, Node]:
    if node.left is None:
        axis = max(range(3), key=lambda i: node.box[1][i] - node.box[0][i])
        indexes = sorted(node.items, key=lambda j: boxes[j][0][axis] + boxes[j][1][axis])
        midpoint = len(indexes) // 2
        node.left = _tree(boxes, indexes[:midpoint])
        node.right = _tree(boxes, indexes[midpoint:])
    return node.left, node.right


def _gap_squared(a: Box, b: Box) -> float:
    return sum(max(0.0, a[0][i] - b[1][i], b[0][i] - a[1][i]) ** 2 for i in range(3))


def minimum_triangle_distance(
    triangles_a: list[Triangle], triangles_b: list[Triangle], *,
    intersects: Callable[[Triangle, Triangle], bool],
    distance: Callable[[Triangle, Triangle], float],
) -> float:
    if not triangles_a or not triangles_b:
        return 0.0
    # Shared boundary vertices establish an exact zero without building trees.
    vertices = {point for triangle in triangles_a for point in triangle}
    if any(point in vertices for triangle in triangles_b for point in triangle):
        return 0.0
    boxes_a, boxes_b = [_box(t) for t in triangles_a], [_box(t) for t in triangles_b]
    root_a = _tree(boxes_a, list(range(len(boxes_a))))
    root_b = _tree(boxes_b, list(range(len(boxes_b))))
    best = math.dist(triangles_a[0][0], triangles_b[0][0])
    serial = itertools.count()
    queue = [(_gap_squared(root_a.box, root_b.box), next(serial), root_a, root_b)]
    while queue:
        lower, _, a, b = heapq.heappop(queue)
        if lower > best * best + 1e-12:
            continue
        if a.count <= 8 and b.count <= 8:
            for i in a.items:
                for j in b.items:
                    gap = _gap_squared(boxes_a[i], boxes_b[j])
                    if gap > best * best + 1e-12:
                        continue
                    if gap <= 1e-12 and intersects(triangles_a[i], triangles_b[j]):
                        return 0.0
                    best = min(best, distance(triangles_a[i], triangles_b[j]))
                    if best == 0:
                        return 0.0
            continue
        if a.count > 8 and (b.count <= 8 or a.count >= b.count):
            left, right = _split(a, boxes_a)
            pairs = ((left, b), (right, b))
        else:
            left, right = _split(b, boxes_b)
            pairs = ((a, left), (a, right))
        for first, second in pairs:
            if first is not None and second is not None:
                gap = _gap_squared(first.box, second.box)
                if gap <= best * best + 1e-12:
                    heapq.heappush(queue, (gap, next(serial), first, second))
    return best
