import bpy
import json
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 3:
        raise SystemExit("usage: blender --background --python diagnose_collision_locations.py -- shell.blend frame_dir report.json")
    return os.path.abspath(args[0]), os.path.abspath(args[1]), os.path.abspath(args[2])


def load_stl(path, name):
    bpy.ops.wm.stl_import(filepath=path, global_scale=1.0, use_scene_unit=False)
    obj = bpy.context.object
    obj.name = name
    return obj


def polygon_points(obj, polygon_index):
    polygon = obj.data.polygons[polygon_index]
    return [obj.matrix_world @ obj.data.vertices[index].co for index in polygon.vertices]


def points_report(points):
    if not points:
        return None
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    average = sum(points, Vector()) / len(points)
    return {
        "min_mm": [round(float(value), 3) for value in minimum],
        "max_mm": [round(float(value), 3) for value in maximum],
        "average_mm": [round(float(value), 3) for value in average],
    }


blend_path, frame_dir, report_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)
pairs = [
    ("05_BodyFrontShell", "05_electronics_deck.stl"),
    ("05_BodyFrontShell", "06_standoff_set.stl"),
    ("07_HeadFrontShell", "13_mouth_bracket.stl"),
    ("05_BodyFrontShell", "35_HCSR04Placeholder.stl"),
]
depsgraph = bpy.context.evaluated_depsgraph_get()
report = []
for index, (shell_name, frame_filename) in enumerate(pairs):
    shell = bpy.data.objects[shell_name]
    source_folder = "preview_meshes_v0.3" if "Placeholder" in frame_filename else "stl"
    frame = load_stl(os.path.join(frame_dir, source_folder, frame_filename), f"DiagnosticFrame{index}")
    overlaps = BVHTree.FromObject(shell, depsgraph).overlap(BVHTree.FromObject(frame, depsgraph))
    shell_points = []
    frame_points = []
    for shell_polygon, frame_polygon in overlaps:
        shell_points.extend(polygon_points(shell, shell_polygon))
        frame_points.extend(polygon_points(frame, frame_polygon))
    report.append(
        {
            "shell": shell_name,
            "frame": frame_filename,
            "triangle_pair_count": len(overlaps),
            "shell_overlap_region": points_report(shell_points),
            "frame_overlap_region": points_report(frame_points),
        }
    )

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
