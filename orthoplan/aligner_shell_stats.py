from __future__ import annotations


def connected_components(faces: list[tuple[int, int, int]]) -> int:
    if not faces:
        return 0
    by_vertex: dict[int, list[int]] = {}
    for index, face in enumerate(faces):
        for vertex in face:
            by_vertex.setdefault(vertex, []).append(index)
    return _count_components(faces, by_vertex)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _count_components(faces: list[tuple[int, int, int]], by_vertex: dict[int, list[int]]) -> int:
    seen: set[int] = set()
    count = 0
    for start in range(len(faces)):
        if start in seen:
            continue
        count += 1
        _visit_component(start, faces, by_vertex, seen)
    return count


def _visit_component(
    start: int,
    faces: list[tuple[int, int, int]],
    by_vertex: dict[int, list[int]],
    seen: set[int],
) -> None:
    stack = [start]
    seen.add(start)
    while stack:
        current = stack.pop()
        for vertex in faces[current]:
            for neighbor in by_vertex[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
