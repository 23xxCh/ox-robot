import bpy
import math
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python render_glb_turnaround.py -- input.glb output_dir")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def look_at(camera, point):
    camera.rotation_euler = (Vector(point) - camera.location).to_track_quat("-Z", "Y").to_euler()


source_path, output_dir = cli_args()
os.makedirs(output_dir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)

mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
for obj in mesh_objects:
    obj.select_set(True)

minimum = Vector((1e9, 1e9, 1e9))
maximum = Vector((-1e9, -1e9, -1e9))
for obj in mesh_objects:
    for corner in obj.bound_box:
        point = obj.matrix_world @ Vector(corner)
        minimum.x = min(minimum.x, point.x)
        minimum.y = min(minimum.y, point.y)
        minimum.z = min(minimum.z, point.z)
        maximum.x = max(maximum.x, point.x)
        maximum.y = max(maximum.y, point.y)
        maximum.z = max(maximum.z, point.z)

center = (minimum + maximum) / 2.0
dimensions = maximum - minimum
radius = max(dimensions) * 0.78

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 768
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("InspectionWorld")
scene.world.color = (0.055, 0.055, 0.055)

bpy.ops.object.light_add(type="AREA", location=(center.x - radius, center.y - radius, center.z + radius))
key = bpy.context.object
key.data.energy = 1100
key.data.shape = "DISK"
key.data.size = radius * 1.8
look_at(key, center)

bpy.ops.object.light_add(type="AREA", location=(center.x + radius, center.y + radius, center.z + radius * 0.4))
fill = bpy.context.object
fill.data.energy = 800
fill.data.size = radius * 1.5
look_at(fill, center)

bpy.ops.object.camera_add(location=(center.x, center.y - radius * 2.4, center.z))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = max(dimensions.x, dimensions.z) * 1.18
scene.camera = camera

views = {
    "front": (center.x, minimum.y - radius * 2.4, center.z),
    "left": (minimum.x - radius * 2.4, center.y, center.z),
    "back": (center.x, maximum.y + radius * 2.4, center.z),
    "right": (maximum.x + radius * 2.4, center.y, center.z),
}

for name, position in views.items():
    camera.location = position
    camera.data.ortho_scale = max(dimensions.x if name in {"front", "back"} else dimensions.y, dimensions.z) * 1.18
    look_at(camera, center)
    scene.render.filepath = os.path.join(output_dir, f"glb-{name}.png")
    bpy.ops.render.render(write_still=True)

print(f"Rendered {len(views)} views to {output_dir}")
