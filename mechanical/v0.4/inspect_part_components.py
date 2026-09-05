import bpy
import bmesh
import json
import os
import sys
from collections import deque


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python inspect_part_components.py -- input.blend report.json")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def components(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.faces)
    result = []
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        faces = []
        verts = set()
        while queue:
            face = queue.popleft()
            faces.append(face)
            verts.update(face.verts)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in unseen:
                        unseen.remove(linked)
                        queue.append(linked)
        minimum = [min(vertex.co[i] for vertex in verts) for i in range(3)]
        maximum = [max(vertex.co[i] for vertex in verts) for i in range(3)]
        result.append(
            {
                "faces": len(faces),
                "vertices": len(verts),
                "min_mm": [round(float(value), 3) for value in minimum],
                "max_mm": [round(float(value), 3) for value in maximum],
            }
        )
    bm.free()
    return sorted(result, key=lambda item: item["faces"], reverse=True)


blend_path, report_path = cli_args()
bpy.ops.wm.open_mainfile(filepath=blend_path)
names = [
    "05_BodyFrontShell",
    "06_BodyRearShell",
    "07_HeadFrontShell",
    "08_HeadRearShell",
    "09_MouthShell",
]
report = {name: components(bpy.data.objects[name]) for name in names}
with open(report_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
