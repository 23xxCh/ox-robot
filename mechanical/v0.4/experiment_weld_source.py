import bpy
import bmesh
import json
import os
import sys
from collections import deque
from mathutils import Vector


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 3:
        raise SystemExit("usage: blender --background --python experiment_weld_source.py -- input.glb weld_distance output.json")
    return os.path.abspath(args[0]), float(args[1]), os.path.abspath(args[2])


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector(tuple(min(point[i] for point in points) for i in range(3)))
    maximum = Vector(tuple(max(point[i] for point in points) for i in range(3)))
    return minimum, maximum


def join_meshes(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = name
    return result


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


source_path, weld_distance, output_path = cli_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)
source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
select_only(source)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

components = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
kept = []
for component in components:
    _, maximum = bounds(component)
    if maximum.y > 0.30:
        bpy.data.objects.remove(component, do_unlink=True)
    else:
        kept.append(component)

joined = join_meshes(kept, "NiulaiWeldExperiment")
bm = bmesh.new()
bm.from_mesh(joined.data)
before = {
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
    "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
}
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=weld_distance)
bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=weld_distance * 0.1)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
sizes = component_face_counts(bm)
after = {
    "vertices": len(bm.verts),
    "edges": len(bm.edges),
    "faces": len(bm.faces),
    "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
    "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
    "connected_components": len(sizes),
    "largest_component_faces": sizes[:20],
    "components_under_100_faces": sum(1 for size in sizes if size < 100),
}
report = {
    "source": source_path,
    "weld_distance_source_units": weld_distance,
    "kept_components": len(kept),
    "before": before,
    "after": after,
}
with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
