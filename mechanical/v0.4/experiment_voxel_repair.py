import bpy
import bmesh
import json
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit(
            "usage: blender --background --python experiment_voxel_repair.py -- input.blend output.json"
        )
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def report(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bounds = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[i] for point in bounds) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in bounds) for i in range(3)))
    result = {
        "vertices": len(obj.data.vertices),
        "polygons": len(obj.data.polygons),
        "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
        "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        "volume_mm3": round(abs(float(bm.calc_volume(signed=True))), 3),
        "dimensions_mm": [round(float(value), 3) for value in maximum - minimum],
    }
    bm.free()
    return result


blend_path, output_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)
source = bpy.data.objects["09_MouthShell"]
results = {"source": report(source), "tests": {}}

for voxel_size in (0.4, 0.6, 0.8):
    candidate = source.copy()
    candidate.data = source.data.copy()
    bpy.context.collection.objects.link(candidate)
    candidate.name = f"MouthRepair_{str(voxel_size).replace('.', 'p')}"
    candidate.data.remesh_voxel_size = voxel_size
    candidate.data.remesh_voxel_adaptivity = 0.0
    select_only(candidate)
    bpy.ops.object.voxel_remesh()
    results["tests"][str(voxel_size)] = report(candidate)
    bpy.data.objects.remove(candidate, do_unlink=True)

with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(results, handle, ensure_ascii=False, indent=2)
print(json.dumps(results, ensure_ascii=False, indent=2))
