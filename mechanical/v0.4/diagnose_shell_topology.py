import bpy
import bmesh
import json
import os
import sys
from collections import deque


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python diagnose_shell_topology.py -- input.blend report.json")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def component_face_counts(bm):
    unseen = set(bm.faces)
    sizes = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        size = 0
        while queue:
            face = queue.popleft()
            size += 1
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in unseen:
                        unseen.remove(linked)
                        queue.append(linked)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def inspect(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    sizes = component_face_counts(bm)
    result = {
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
        "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
        "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        "connected_components": len(sizes),
        "largest_component_faces": sizes[:10],
        "components_under_100_faces": sum(1 for size in sizes if size < 100),
        "signed_volume": float(bm.calc_volume(signed=True)),
    }
    bm.free()
    return result


blend_path, report_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)

names = [
    "00_CleanOuterReference",
    "02_OpenBottomShell",
    "05_BodyFrontShell",
    "06_BodyRearShell",
    "07_HeadFrontShell",
    "08_HeadRearShell",
    "09_MouthShell",
]
report = {name: inspect(bpy.data.objects[name]) for name in names}

with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

print(json.dumps(report, ensure_ascii=False, indent=2))
