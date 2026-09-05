import bpy
import bmesh
import json
import os
import sys
from mathutils import Vector


TARGET_HEIGHT_MM = 330.0
TARGET_WIDTH_MM = 220.0
TARGET_DEPTH_MM = 200.0
WELD_DISTANCE_SOURCE = 0.000001
VOXEL_SIZE_SOURCE = 0.004


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python build_welded_outer_preview.py -- input.glb output_dir")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
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


def mesh_report(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    minimum, maximum = bounds(obj)
    report = {
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
        "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        "dimensions": [float(v) for v in maximum - minimum],
        "signed_volume": float(bm.calc_volume(signed=True)),
    }
    bm.free()
    return report


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


source_path, output_dir = cli_args()
os.makedirs(output_dir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)
source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
select_only(source)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

kept = []
removed_tail = []
for component in [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]:
    _, maximum = bounds(component)
    if maximum.y > 0.30:
        removed_tail.append(component)
        bpy.data.objects.remove(component, do_unlink=True)
    else:
        kept.append(component)

outer = join_meshes(kept, "NiulaiJoinedRaw")
bm = bmesh.new()
bm.from_mesh(outer.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_DISTANCE_SOURCE)
bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=WELD_DISTANCE_SOURCE * 0.1)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(outer.data)
bm.free()
outer.data.update()

# The weld collapses 4,751 tiled patches into one dominant body surface and a
# few triangle-sized scraps.  Keep only the dominant connected component.
select_only(outer)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
welded_components = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
welded_components.sort(key=lambda obj: len(obj.data.polygons), reverse=True)
outer = welded_components[0]
outer.name = "NiulaiWeldedMainSurface"
for scrap in welded_components[1:]:
    bpy.data.objects.remove(scrap, do_unlink=True)

bm = bmesh.new()
bm.from_mesh(outer.data)
boundary = [edge for edge in bm.edges if edge.is_boundary]
filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=0) if boundary else {"faces": []}
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
bm.to_mesh(outer.data)
bm.free()
outer.data.validate(clean_customdata=True)
outer.data.update()
welded_report = mesh_report(outer)
welded_report["filled_faces"] = len(filled.get("faces", []))

outer.data.remesh_voxel_size = VOXEL_SIZE_SOURCE
outer.data.remesh_voxel_adaptivity = 0.10
select_only(outer)
bpy.ops.object.voxel_remesh()
outer.name = "NiulaiClosedVoxelOuter"

smooth = outer.modifiers.new(name="GentleSurfaceSmooth", type="SMOOTH")
smooth.factor = 0.25
smooth.iterations = 2
select_only(outer)
bpy.ops.object.modifier_apply(modifier=smooth.name)

bm = bmesh.new()
bm.from_mesh(outer.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
bm.to_mesh(outer.data)
bm.free()
outer.data.update()

minimum, maximum = bounds(outer)
scale = TARGET_HEIGHT_MM / (maximum.z - minimum.z)
outer.scale = (scale, scale, scale)
select_only(outer)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minimum, maximum = bounds(outer)
outer.scale = (
    TARGET_WIDTH_MM / (maximum.x - minimum.x),
    TARGET_DEPTH_MM / (maximum.y - minimum.y),
    1.0,
)
select_only(outer)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minimum, maximum = bounds(outer)
outer.location += Vector((-(minimum.x + maximum.x) / 2.0, -(minimum.y + maximum.y) / 2.0, -minimum.z))
select_only(outer)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

for polygon in outer.data.polygons:
    polygon.use_smooth = True
outer.color = (0.95, 0.62, 0.08, 1.0)

report = {
    "source": source_path,
    "removed_tail_components": len(removed_tail),
    "weld_distance_source": WELD_DISTANCE_SOURCE,
    "voxel_size_source": VOXEL_SIZE_SOURCE,
    "welded_before_voxel": welded_report,
    "outer_after_voxel": mesh_report(outer),
}
with open(os.path.join(output_dir, "welded-outer-preview-report.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

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
bpy.ops.object.camera_add(location=(430.0, -560.0, 330.0))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = 430.0
look_at(camera, (0.0, 0.0, 180.0))
scene.camera = camera
scene.render.filepath = os.path.join(output_dir, "niulai-welded-outer-preview.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "niulai-welded-outer-preview.blend"))
print(json.dumps(report, ensure_ascii=False, indent=2))
