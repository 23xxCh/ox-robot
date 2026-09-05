import bpy
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python render_shell_v0_3.py -- input.blend output_dir")
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
scene.display.shading.show_cavity = True
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

for obj in scene.objects:
    obj.hide_render = obj not in parts.values()

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
scene.render.filepath = os.path.join(output_dir, "niulai-shell-assembled-v0.3.png")
bpy.ops.render.render(write_still=True)

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
scene.render.filepath = os.path.join(output_dir, "niulai-shell-exploded-v0.3.png")
bpy.ops.render.render(write_still=True)

print(f"Rendered assembly and exploded shell views to {output_dir}")
