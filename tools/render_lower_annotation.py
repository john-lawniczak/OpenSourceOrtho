"""Render the lower-only draft in Above and front views for boundary review."""
import colorsys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402
import numpy as np  # noqa: E402

from correct_user_one_lower_labels import CASE, generate  # noqa: E402


def render_lower(triangles, labels, destination):
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
    palette = {0: [.6, .65, .68]}
    for label in np.unique(labels):
        if label:
            palette[int(label)] = colorsys.hls_to_rgb((int(label) * .6180339) % 1, .55, .65)
    colors = np.asarray([palette[int(label)] for label in labels])
    colors *= (.45 + .55 * np.abs(normals @ np.array([.1, .3, .95])))[:, None]
    fig = plt.figure(figsize=(18, 9))
    for i, (elev, azim) in enumerate([(90, -90), (16, -90)], 1):
        ax = fig.add_subplot(1, 2, i, projection="3d")
        ax.add_collection3d(Poly3DCollection(triangles, facecolors=colors, edgecolors="none"))
        ax.set(xlim=(-33, 33), ylim=(-51, 2), zlim=(-16, 5))
        ax.set_box_aspect((66, 53, 21))
        ax.view_init(elev=elev, azim=azim)
        for label in sorted(set(labels) - {0}):
            point = np.median(triangles[labels == label].mean(axis=1), axis=0)
            ax.text(*point, str(label), color="black", bbox={"facecolor": "white", "alpha": .85})
        if i == 1:
            ax.plot([.025, .025], [-49, -41], [4, 4], color="black", linestyle="--", linewidth=1)
        ax.set_title("Above: right 4x | left 3x; dashed = 41/31 midline" if i == 1 else "Front: 14 connected draft crown regions")
        ax.set_axis_off()
    fig.suptitle("initial-lower.stl only · gray = context / uncertain boundary · geometry unchanged")
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(Path(destination), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    mesh, labels, _ = generate()
    render_lower(mesh, labels, CASE / "annotations/initial-lower-segmentation-views.png")
