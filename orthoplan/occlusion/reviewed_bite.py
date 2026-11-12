"""Import an explicit, scan-bound bite transform without inferring its review."""

import math


def apply_reviewed_bite(record, hashes, lower):
    if (
        record.get("schema") != "ortho-bite-review-v1"
        or record.get("source_hashes") != hashes
        or record.get("accepted") is not True
        or not isinstance(record.get("reviewer"), str)
        or not record["reviewer"].strip()
        or not record.get("reference_description")
    ):
        raise ValueError(
            "Bite review needs matching source hashes, reviewer, reference description and explicit acceptance"
        )
    matrix = record.get("lower_to_upper")
    if (
        not isinstance(matrix, list)
        or len(matrix) != 4
        or any(not isinstance(row, list) or len(row) != 4 for row in matrix)
        or not all(isinstance(x, (int, float)) and math.isfinite(x) for row in matrix for x in row)
        or matrix[3] != [0, 0, 0, 1]
    ):
        raise ValueError("Bite transform must be a finite homogeneous matrix")
    for i in range(3):
        for j in range(3):
            if abs(sum(matrix[i][k] * matrix[j][k] for k in range(3)) - (i == j)) > 1e-6:
                raise ValueError("Bite transform must preserve lengths")
    a, b, c = matrix[:3]
    determinant = (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )
    if abs(determinant - 1) > 1e-6:
        raise ValueError("Bite transform cannot reflect anatomy")
    return [
        tuple(sum(matrix[i][j] * point[j] for j in range(3)) + matrix[i][3] for i in range(3))
        for point in lower
    ]
