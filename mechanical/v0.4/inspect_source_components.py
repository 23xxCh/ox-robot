import bpy
import json
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python inspect_source_components.py -- input.glb output_dir")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def combined_bounds(objects):
    minima, maxima = zip(*(bounds(obj) for obj in objects))
    return (
        Vector(tuple(min(point[i] for point in minima) for i in range(3))),
        Vector(tuple(max(point[i] for point in maxima) for i in range(3))),
    )


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


source_path, output_dir = cli_args()
os.makedirs(output_dir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)
source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
select_only(source)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

components = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
trimmed = []
tail = []
for component in components:
    _, maximum = bounds(component)
    (tail if maximum.y > 0.30 else trimmed).append(component)
trimmed.sort(key=lambda obj: len(obj.data.polygons), reverse=True)

minimum, maximum = combined_bounds(trimmed)
center = (minimum + maximum) / 2.0
dimensions = maximum - minimum
radius = max(dimensions) * 0.78

report = {
    "component_count": len(components),
    "trimmed_component_count": len(trimmed),
    "tail_component_count": len(tail),
    "total_faces": sum(len(obj.data.polygons) for obj in components),
    "trimmed_faces": sum(len(obj.data.polygons) for obj in trimmed),
    "top_components": [],
}
for rank, obj in enumerate(trimmed[:100], start=1):
    obj_min, obj_max = bounds(obj)
    materials = sorted(
        {
            obj.data.materials[poly.material_index].name
            for poly in obj.data.polygons
            if poly.material_index < len(obj.data.materials) and obj.data.materials[poly.material_index]
        }
    )
    report["top_components"].append(
        {
            "rank": rank,
            "name": obj.name,
            "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons),
            "min": [float(v) for v in obj_min],
            "max": [float(v) for v in obj_max],
            "dimensions": [float(v) for v in obj_max - obj_min],
            "materials": materials,
        }
    )

with open(os.path.join(output_dir, "source-component-report.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 900
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "rim.sl"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = False
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.92, 0.92, 0.92)
for obj in components:
    obj.color = (0.95, 0.62, 0.08, 1.0)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

bpy.ops.object.camera_add(location=(radius * 0.95, -radius * 2.35, center.z + radius * 0.2))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = max(dimensions.x, dimensions.z) * 1.18
look_at(camera, center)
scene.camera = camera

for keep_count in (1, 5, 20, 100, len(trimmed)):
    allowed = set(trimmed[:keep_count])
    for obj in components:
        obj.hide_render = obj not in allowed
    scene.render.filepath = os.path.join(output_dir, f"source-top-{keep_count:04d}-components.png")
    bpy.ops.render.render(write_still=True)

print(json.dumps(report, ensure_ascii=False, indent=2))
