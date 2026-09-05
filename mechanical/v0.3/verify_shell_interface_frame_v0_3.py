import bpy
import json
import os
import sys
from mathutils.bvhtree import BVHTree


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 3:
        raise SystemExit(
            "usage: blender --background --python verify_shell_interface_frame_v0_3.py -- shell.blend v0.3_dir report.json"
        )
    return os.path.abspath(args[0]), os.path.abspath(args[1]), os.path.abspath(args[2])


def load_stl(path, name):
    bpy.ops.wm.stl_import(filepath=path, global_scale=1.0, use_scene_unit=False)
    obj = bpy.context.object
    obj.name = name
    return obj


def bvh(obj, depsgraph):
    return BVHTree.FromObject(obj, depsgraph, epsilon=0.0)


blend_path, frame_dir, report_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)

shells = {
    "body_front": bpy.data.objects["05_BodyFrontShell"],
    "body_rear": bpy.data.objects["06_BodyRearShell"],
    "head_front": bpy.data.objects["07_HeadFrontShell"],
    "head_rear": bpy.data.objects["08_HeadRearShell"],
    "mouth": bpy.data.objects["09_MouthShell"],
}

frame_files = [
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
    "17_body_mount_pads.stl",
]
frame = {
    filename[:-4]: load_stl(os.path.join(frame_dir, "stl", filename), f"Frame_{filename[:-4]}")
    for filename in frame_files
}
hardware_names = [
    "TTMotorLeft",
    "TTMotorRight",
    "WheelLeft",
    "WheelRight",
    "CasterBall",
    "Battery2S",
    "ServoPan",
    "ServoTilt",
    "ServoMouth",
    "ESP32Placeholder",
    "DRV8833Placeholder",
    "PowerPlaceholder",
    "RadarPlaceholder",
    "OLEDPlaceholder",
    "HCSR04Placeholder",
]
preview_dir = os.path.join(frame_dir, "preview_meshes_v0.3")
with open(os.path.join(preview_dir, "manifest.json"), encoding="utf-8") as handle:
    preview_manifest = json.load(handle)
preview_files = {item["name"]: item["file"] for item in preview_manifest}
missing_hardware = [name for name in hardware_names if name not in preview_files]
if missing_hardware:
    raise RuntimeError(f"preview manifest is missing hardware: {missing_hardware}")
for name in hardware_names:
    frame[name] = load_stl(
        os.path.join(preview_dir, preview_files[name]),
        f"Reference_{name}",
    )

# Every current hardware placeholder must be clear of the cosmetic shell. The
# HC-SR04 already has finished lower-belly apertures; radar and OLED remain
# fully behind their respective skins, so no provisional intersections remain.
planned_apertures = set()

depsgraph = bpy.context.evaluated_depsgraph_get()
shell_bvhs = {name: bvh(obj, depsgraph) for name, obj in shells.items()}
frame_bvhs = {name: bvh(obj, depsgraph) for name, obj in frame.items()}

blocking_collisions = []
planned_aperture_intersections = []
for shell_name, shell_tree in shell_bvhs.items():
    for frame_name, frame_tree in frame_bvhs.items():
        overlaps = shell_tree.overlap(frame_tree)
        if overlaps:
            item = {
                "shell": shell_name,
                "frame": frame_name,
                "triangle_pair_count": len(overlaps),
            }
            if (shell_name, frame_name) in planned_apertures:
                planned_aperture_intersections.append(item)
            else:
                blocking_collisions.append(item)

part_dimensions = {}
for name, obj in shells.items():
    part_dimensions[name] = [round(float(value), 3) for value in obj.dimensions]

report = {
    "shell_blend": blend_path,
    "frame_version": "v0.3-shell-interface",
    "part_dimensions_mm": part_dimensions,
    "printer_volume_mm": [330.0, 320.0, 325.0],
    "all_parts_fit_printer_when_oriented": all(
        all(part_edge <= printer_edge for part_edge, printer_edge in zip(sorted(dimensions), [320.0, 325.0, 330.0]))
        for dimensions in part_dimensions.values()
    ),
    "blocking_collision_pair_count": len(blocking_collisions),
    "blocking_collisions": sorted(blocking_collisions, key=lambda item: item["triangle_pair_count"], reverse=True),
    "planned_aperture_intersection_count": len(planned_aperture_intersections),
    "planned_aperture_intersections": sorted(
        planned_aperture_intersections,
        key=lambda item: item["triangle_pair_count"],
        reverse=True,
    ),
    "status": (
        "PROVISIONAL_NEEDS_INTERFACE_WORK"
        if blocking_collisions
        else (
            "STRUCTURE_CLEAR_APERTURES_PENDING"
            if planned_aperture_intersections
            else "STRUCTURE_AND_APERTURES_CLEAR"
        )
    ),
}

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
