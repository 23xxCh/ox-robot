import bpy
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python render_outer_reference_v0_4.py -- input.blend output.png")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


blend_path, output_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)
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

outer = bpy.data.objects["00_CleanOuterReference"]
outer.hide_render = False
outer.color = (0.95, 0.62, 0.08, 1.0)
for polygon in outer.data.polygons:
    polygon.use_smooth = True
for obj in scene.objects:
    obj.hide_render = obj != outer

bpy.ops.object.camera_add(location=(430.0, -560.0, 330.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 430.0
look_at(camera, (0.0, 0.0, 180.0))
scene.camera = camera
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)
print(f"Rendered {output_path}")
