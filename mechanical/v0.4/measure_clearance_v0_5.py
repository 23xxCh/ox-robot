import bpy
import json
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 3:
        raise SystemExit("usage: blender --background --python measure_clearance_v0_5.py -- shell.blend preview_dir report.json [trial_head_z_mm] [trial_head_x_scale]")
    return (
        os.path.abspath(args[0]),
        os.path.abspath(args[1]),
        os.path.abspath(args[2]),
        float(args[3]) if len(args) > 3 else 0.0,
        float(args[4]) if len(args) > 4 else 1.0,
    )


def load_stl(path, name):
    bpy.ops.wm.stl_import(filepath=path, global_scale=1.0, use_scene_unit=False)
    obj = bpy.context.object
    obj.name = name
    return obj


def world_bvh(obj):
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False)


def sample_points(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    points.extend(
        obj.matrix_world @ polygon.center
        for polygon in obj.data.polygons
    )
    return points


def bounds(objects):
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    minimum = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
    maximum = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
    return {
        "min_mm": [round(float(value), 3) for value in minimum],
        "max_mm": [round(float(value), 3) for value in maximum],
        "dimensions_mm": [round(float(maximum[i] - minimum[i]), 3) for i in range(3)],
    }


blend_path, preview_dir, report_path, trial_head_z_mm, trial_head_x_scale = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)

shell_names = [
    "05_BodyFrontShell",
    "06_BodyRearShell",
    "07_HeadFrontShell",
    "08_HeadRearShell",
    "09_MouthShell",
]
shells = {name: bpy.data.objects[name] for name in shell_names}
shell_trees = {name: world_bvh(obj) for name, obj in shells.items()}

with open(os.path.join(preview_dir, "manifest.json"), encoding="utf-8") as handle:
    manifest = json.load(handle)

# Minimum clearance gates are deliberately larger than nominal FDM tolerance.
# They reserve room for wires, tilted servo horns and imperfect source meshes.
profiles = {
    # The body collar intentionally sits close to the shell so epoxy can bridge
    # the remaining gap.  1.5 mm is the anti-rub / adhesive minimum, distinct
    # from component and motion clearances.
    "BodyMountPads": ("interface", 1.5),
    "BatteryTray": ("static", 5.0),
    "ElectronicsDeck": ("static", 5.0),
    "StandoffSet": ("structural", 3.0),
    "NeckColumnLeft": ("structural", 3.0),
    "NeckColumnRight": ("structural", 3.0),
    "NeckCrossbeam": ("structural", 3.0),
    "PanPlatform": ("moving", 8.0),
    "TiltBracket": ("moving", 8.0),
    "MouthBracket": ("moving", 8.0),
    "Battery2S": ("static", 5.0),
    "ServoPan": ("moving", 8.0),
    "ServoTilt": ("moving", 8.0),
    "ServoMouth": ("moving", 8.0),
    "ESP32Placeholder": ("static", 5.0),
    "DRV8833Placeholder": ("static", 5.0),
    "PowerPlaceholder": ("static", 5.0),
    "RadarPlaceholder": ("static", 5.0),
    "OLEDPlaceholder": ("static", 5.0),
}
head_moving_group = {
    "NeckCrossbeam",
    "PanPlatform",
    "TiltBracket",
    "MouthBracket",
    "ServoPan",
    "ServoTilt",
    "ServoMouth",
}
head_printed_group = {
    "NeckCrossbeam",
    "PanPlatform",
    "TiltBracket",
    "MouthBracket",
}

entries = {item["name"]: item for item in manifest}
missing = sorted(set(profiles) - set(entries))
if missing:
    raise RuntimeError(f"preview manifest is missing clearance targets: {missing}")

objects = {}
clearances = []
for name, (kind, target_mm) in profiles.items():
    obj = load_stl(os.path.join(preview_dir, entries[name]["file"]), f"Clearance_{name}")
    if name in head_moving_group:
        obj.location.z += trial_head_z_mm
        if name in head_printed_group:
            obj.scale.x = trial_head_x_scale
        bpy.context.view_layer.update()
    objects[name] = obj
    best_distance = float("inf")
    best_shell = None
    best_frame_point = None
    best_shell_point = None
    for point in sample_points(obj):
        for shell_name, tree in shell_trees.items():
            nearest = tree.find_nearest(point)
            if nearest is not None and nearest[3] < best_distance:
                best_distance = float(nearest[3])
                best_shell = shell_name
                best_frame_point = point.copy()
                best_shell_point = nearest[0].copy()
    clearance_mm = round(best_distance, 3)
    clearances.append(
        {
            "name": name,
            "kind": kind,
            "target_mm": target_mm,
            "measured_min_clearance_mm": clearance_mm,
            "nearest_shell": best_shell,
            "nearest_frame_point_mm": [round(float(value), 3) for value in best_frame_point],
            "nearest_shell_point_mm": [round(float(value), 3) for value in best_shell_point],
            "margin_to_target_mm": round(clearance_mm - target_mm, 3),
            "status": "PASS" if clearance_mm >= target_mm else "FAIL",
        }
    )

shell_bounds = bounds(shells.values())
internal_bounds = bounds(objects.values())
failed = [item for item in clearances if item["status"] == "FAIL"]
report = {
    "shell_assembled_bounds": shell_bounds,
    "critical_internal_bounds": internal_bounds,
    "clearance_gate": {
        "shell_interface_mm": 1.5,
        "static_mm": 5.0,
        "moving_mm": 8.0,
        "structural_mm": 3.0,
    },
    "trial_head_z_mm": trial_head_z_mm,
    "trial_head_x_scale": trial_head_x_scale,
    "failed_count": len(failed),
    "failed_names": [item["name"] for item in failed],
    "parts": sorted(clearances, key=lambda item: item["measured_min_clearance_mm"]),
}
with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
