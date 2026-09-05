import bpy
import json
import os
import sys
from mathutils import Vector


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return minimum, maximum


args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
if len(args) < 2:
    raise SystemExit("usage: blender --background --python inspect_glb_components.py -- input.glb output.json")

source_path = os.path.abspath(args[0])
output_path = os.path.abspath(args[1])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)
objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if len(objects) != 1:
    raise RuntimeError(f"expected one mesh object, found {len(objects)}")

source = objects[0]
bpy.context.view_layer.objects.active = source
source.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

components = []
for obj in [item for item in bpy.context.scene.objects if item.type == "MESH"]:
    minimum, maximum = bounds(obj)
    components.append(
        {
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "polygons": len(obj.data.polygons),
            "min": [float(v) for v in minimum],
            "max": [float(v) for v in maximum],
            "dimensions": [float(v) for v in maximum - minimum],
            "center": [float(v) for v in (minimum + maximum) / 2.0],
        }
    )

components.sort(key=lambda item: item["polygons"], reverse=True)
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump({"component_count": len(components), "components": components}, handle, ensure_ascii=False, indent=2)
print(json.dumps({"component_count": len(components), "components": components[:30]}, ensure_ascii=False, indent=2))
