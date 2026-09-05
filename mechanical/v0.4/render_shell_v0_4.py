import bpy
import json
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python render_shell_v0_4.py -- input.blend output_dir")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


blend_path, output_dir = cli_args()
os.makedirs(output_dir, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "rim.sl"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = False
scene.display.shading.cavity_type = "WORLD"
scene.display.shading.curvature_ridge_factor = 1.8
scene.display.shading.curvature_valley_factor = 1.3
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.92, 0.92, 0.92)

parts = {
    "body_front": bpy.data.objects["05_BodyFrontShell"],
    "body_rear": bpy.data.objects["06_BodyRearShell"],
    "head_front": bpy.data.objects["07_HeadFrontShell"],
    "head_rear": bpy.data.objects["08_HeadRearShell"],
    "mouth": bpy.data.objects["09_MouthShell"],
}

# Show the actual HC-SR04 package in the assembled product view so the two
# character nostrils read as sensor faces, not as empty black apertures.
mechanical_dir = os.path.dirname(os.path.dirname(blend_path))
preview_dir = os.path.join(mechanical_dir, "v0.3", "preview_meshes_v0.3")
with open(os.path.join(preview_dir, "manifest.json"), encoding="utf-8") as handle:
    preview_manifest = json.load(handle)
hcsr_filename = next(item["file"] for item in preview_manifest if item["name"] == "HCSR04Placeholder")
hcsr_path = os.path.join(preview_dir, hcsr_filename)
bpy.ops.wm.stl_import(filepath=hcsr_path, global_scale=1.0, use_scene_unit=False)
hcsr = bpy.context.object
hcsr.name = "HCSR04_AssembledPreview"
hcsr.color = (0.18, 0.20, 0.22, 1.0)
for polygon in hcsr.data.polygons:
    polygon.use_smooth = True

bezel_path = os.path.join(mechanical_dir, "v0.3", "stl", "16_ultrasonic_bezel.stl")
bpy.ops.wm.stl_import(filepath=bezel_path, global_scale=1.0, use_scene_unit=False)
bezel = bpy.context.object
bezel.name = "UltrasonicBezel_AssembledPreview"
bezel.color = (0.08, 0.09, 0.10, 1.0)
for polygon in bezel.data.polygons:
    polygon.use_smooth = True

for obj in parts.values():
    for polygon in obj.data.polygons:
        polygon.use_smooth = True

for obj in scene.objects:
    obj.hide_render = obj not in [*parts.values(), hcsr, bezel]

parts["body_front"].color = (0.95, 0.55, 0.05, 1.0)
parts["body_rear"].color = (0.98, 0.74, 0.08, 1.0)
parts["head_front"].color = (0.95, 0.55, 0.05, 1.0)
parts["head_rear"].color = (0.98, 0.74, 0.08, 1.0)
parts["mouth"].color = (0.72, 0.34, 0.55, 1.0)

bpy.ops.object.camera_add(location=(430.0, -560.0, 330.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 430.0
look_at(camera, (0.0, 0.0, 180.0))
scene.camera = camera

assembled_transforms = {name: (obj.location.copy(), obj.rotation_euler.copy()) for name, obj in parts.items()}
scene.render.filepath = os.path.join(output_dir, "niulai-shell-assembled-v0.4.png")
bpy.ops.render.render(write_still=True)

hcsr.hide_render = True
bezel.hide_render = True

offsets = {
    "body_front": Vector((-125.0, -15.0, 0.0)),
    "body_rear": Vector((125.0, 15.0, 0.0)),
    "head_front": Vector((-125.0, -15.0, 75.0)),
    "head_rear": Vector((125.0, 15.0, 75.0)),
    "mouth": Vector((-225.0, -30.0, 75.0)),
}
for name, obj in parts.items():
    obj.location = assembled_transforms[name][0] + offsets[name]

camera.data.ortho_scale = 590.0
camera.location = (560.0, -720.0, 400.0)
look_at(camera, (0.0, 0.0, 210.0))
scene.render.filepath = os.path.join(output_dir, "niulai-shell-exploded-v0.4.png")
bpy.ops.render.render(write_still=True)

print(f"Rendered assembly and exploded shell views to {output_dir}")
