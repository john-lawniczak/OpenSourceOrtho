"""Cross-language check: engine scan points and actual viewer matrix agree."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from orthoplan.model import ToothId
from orthoplan.planning.biomechanics import apply_pose_to_vertex
from orthoplan.planning.transforms import ToothPose
from orthoplan.viz.mesh_affine import mesh_affine


@pytest.mark.parametrize("trusted", [False, True])
def test_rendered_reference_vertices_match_engine(trusted):
    pose = ToothPose(
        tooth=ToothId(value="11"),
        translate_x_mm=0.2,
        translate_y_mm=0.3,
        translate_z_mm=0.1,
        rotate_tip_deg=12,
        rotate_torque_deg=-7,
        rotate_rotation_deg=23,
    )
    frame = (
        SimpleNamespace(axis=SimpleNamespace(direction=(0, 0, 1)), center_of_resistance=(2, 3, 4))
        if trusted
        else None
    )
    points = [(3, 3, 4), (2, 4, 4), (2, 3, 5), (-8, 10, 2)]
    payload = dict(
        affine=mesh_affine(pose, frame), pose=pose.model_dump(mode="json"), points=points
    )
    script = """import { orientedMeshMatrix } from './ui/mesh_affine.js';
      let raw=''; for await (const chunk of process.stdin) raw+=chunk;
      const {affine,pose,points}=JSON.parse(raw), m=orientedMeshMatrix(affine,pose);
      console.log(JSON.stringify(points.map(([x,y,z])=>{
        const v=[x,z,-y,1]; return [0,1,2].map(r=>v.reduce((s,c,j)=>s+c*m[r*4+j],0));
      })));"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    for vertex, rendered in zip(points, json.loads(result.stdout)):
        x, y, z = apply_pose_to_vertex(vertex, pose, frame)
        assert rendered == pytest.approx([x, z, -y], abs=1e-9)


def test_root_rotation_has_independent_known_reference():
    pose = ToothPose(tooth=ToothId(value="11"), rotate_rotation_deg=90, translate_x_mm=0.2)
    frame = SimpleNamespace(
        axis=SimpleNamespace(direction=(0, 0, 1)), center_of_resistance=(2, 3, 4)
    )
    matrix = mesh_affine(pose, frame)
    vertex = [3, 3, 4, 1]
    assert [sum(c * v for c, v in zip(row, vertex)) for row in matrix] == pytest.approx([2.2, 4, 4])
