import bpy
import os
import sys
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 3:
        raise SystemExit(
            "usage: blender --background --python render_shell_with_frame_v0_3.py -- shell.blend v0.3_dir output.png"
        )
    return os.path.abspath(args[0]), os.path.abspath(args[1]), os.path.abspath(args[2])


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


blend_path, frame_dir, output_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

shell_names = {
    "05_BodyFrontShell",
    "06_BodyRearShell",
    "07_HeadFrontShell",
    "08_HeadRearShell",
    "09_MouthShell",
}
for obj in scene.objects:
    obj.hide_render = obj.name not in shell_names

# Hide the two front covers to expose the actual installation path. Keep the
# rear covers and mouth in place as a cutaway assembly.
bpy.data.objects["05_BodyFrontShell"].hide_render = True
bpy.data.objects["07_HeadFrontShell"].hide_render = True
bpy.data.objects["06_BodyRearShell"].color = (0.98, 0.70, 0.08, 1.0)
bpy.data.objects["08_HeadRearShell"].color = (0.98, 0.70, 0.08, 1.0)
bpy.data.objects["09_MouthShell"].color = (0.72, 0.34, 0.55, 1.0)

structure_files = [
    "01_chassis_base.stl",
    "02_motor_mount_left.stl",
    "03_motor_mount_right.stl",
    "04_battery_tray.stl",
    "05_electronics_deck.stl",
    "06_standoff_set.stl",
    "07_neck_column_left.stl",
    "08_neck_column_right.stl",
    "09_neck_crossbeam.stl",
    "10_pan_platform.stl",
    "11_tilt_bracket.stl",
    "12_head_interface_plate.stl",
    "13_mouth_bracket.stl",
    "14_front_anti_tip_skid.stl",
    "15_rear_caster_bracket.stl",
]

for filename in structure_files:
    bpy.ops.wm.stl_import(
        filepath=os.path.join(frame_dir, "stl", filename),
        global_scale=1.0,
        use_scene_unit=False,
    )
    obj = bpy.context.object
    obj.name = f"Frame_{filename[:-4]}"
    obj.color = (0.18, 0.35, 0.62, 1.0)
    obj.hide_render = False

for filename, color in [
    ("03_HardwarePlaceholders.stl", (0.25, 0.25, 0.28, 1.0)),
    ("04_ReservedInterfaces.stl", (0.80, 0.18, 0.10, 1.0)),
]:
    bpy.ops.wm.stl_import(
        filepath=os.path.join(frame_dir, "preview_meshes_v0.3", filename),
        global_scale=1.0,
        use_scene_unit=False,
    )
    obj = bpy.context.object
    obj.name = f"Reference_{filename[:-4]}"
    obj.color = color
    obj.hide_render = False

scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 1200
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "rim.sl"
scene.display.shading.color_type = "OBJECT"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "WORLD"
scene.display.shading.curvature_ridge_factor = 1.7
scene.display.shading.curvature_valley_factor = 1.2
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.94, 0.94, 0.94)

bpy.ops.object.camera_add(location=(470.0, -600.0, 350.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 430.0
look_at(camera, (0.0, 0.0, 175.0))
scene.camera = camera
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)

print(f"Rendered cutaway frame inspection to {output_path}")
