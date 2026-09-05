import bpy
import bmesh
import json
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not args:
        raise SystemExit("usage: blender --background --python inspect_niulai_glb.py -- input.glb output.json")
    output = args[1] if len(args) > 1 else "niulai-glb-inspection.json"
    return os.path.abspath(args[0]), os.path.abspath(output)


def world_bounds(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


source_path, output_path = cli_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
all_points = []
objects = []
depsgraph = bpy.context.evaluated_depsgraph_get()

for obj in mesh_objects:
    all_points.extend(world_bounds(obj))
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    boundary_edges = sum(1 for edge in bm.edges if edge.is_boundary)
    non_manifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    loose_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 0)
    volume = None
    if non_manifold_edges == 0:
        try:
            volume = abs(float(bm.calc_volume(signed=True)))
        except ValueError:
            volume = None
    objects.append(
        {
            "name": obj.name,
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "triangles": len(mesh.loop_triangles),
            "polygons": len(mesh.polygons),
            "boundary_edges": boundary_edges,
            "non_manifold_edges": non_manifold_edges,
            "loose_edges": loose_edges,
            "volume_scene_units_cubed": volume,
            "dimensions_scene_units": [float(v) for v in obj.dimensions],
            "scale": [float(v) for v in obj.scale],
            "materials": [slot.material.name if slot.material else None for slot in obj.material_slots],
        }
    )
    bm.free()
    evaluated.to_mesh_clear()

if all_points:
    minimum = Vector((min(point.x for point in all_points), min(point.y for point in all_points), min(point.z for point in all_points)))
    maximum = Vector((max(point.x for point in all_points), max(point.y for point in all_points), max(point.z for point in all_points)))
    dimensions = maximum - minimum
else:
    minimum = maximum = dimensions = Vector((0.0, 0.0, 0.0))

report = {
    "source": source_path,
    "source_bytes": os.path.getsize(source_path),
    "scene_unit_system": bpy.context.scene.unit_settings.system,
    "scene_length_unit": bpy.context.scene.unit_settings.length_unit,
    "mesh_object_count": len(mesh_objects),
    "bounds_scene_units": {
        "min": [float(v) for v in minimum],
        "max": [float(v) for v in maximum],
        "dimensions": [float(v) for v in dimensions],
    },
    "objects": objects,
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

print(json.dumps(report, ensure_ascii=False, indent=2))
