import bpy
import bmesh
import json
import os
import sys
from mathutils import Vector


TARGET_HEIGHT_MM = 330.0
TARGET_WIDTH_MM = 220.0
TARGET_DEPTH_MM = 200.0
WALL_MM = 1.8
BOTTOM_OPEN_Z_MM = 70.0
HEAD_MIN_Z_MM = 195.0
HEAD_HALF_WIDTH_MM = 95.0
HEAD_FRONT_MM = -110.0
HEAD_REAR_MM = 110.0
SEAM_Y_MM = 0.0
MOUTH_CLEARANCE_MM = 0.8
VOXEL_SIZE_SOURCE = 0.010
PRE_REMESH_DECIMATE_RATIO = 1.0
TAIL_TRIM_Y_SOURCE = 0.22


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit("usage: blender --background --python build_niulai_shell_v0_3.py -- input.glb output_dir")
    return os.path.abspath(args[0]), os.path.abspath(args[1])


def select_only(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier(obj, modifier):
    select_only(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def object_bounds(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    return minimum, maximum


def make_box(name, minimum, maximum):
    dimensions = Vector(maximum) - Vector(minimum)
    center = (Vector(minimum) + Vector(maximum)) / 2.0
    bpy.ops.mesh.primitive_cube_add(location=center)
    box = bpy.context.object
    box.name = name
    box.dimensions = dimensions
    select_only(box)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return box


def boolean_result(source, cutter, operation, name):
    result = source.copy()
    result.data = source.data.copy()
    bpy.context.collection.objects.link(result)
    result.name = name
    modifier = result.modifiers.new(name=f"{operation}_{cutter.name}", type="BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = cutter
    print(f"[stage] cutting {name}", flush=True)
    apply_modifier(result, modifier)
    print(f"[stage] cut complete {name}: {len(result.data.polygons)} polygons", flush=True)
    return result


def join_meshes(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = name
    return joined


def mesh_report(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    minimum, maximum = object_bounds(obj)
    report = {
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
        "non_manifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        "dimensions_mm": [round(float(v), 3) for v in maximum - minimum],
        "min_mm": [round(float(v), 3) for v in minimum],
        "max_mm": [round(float(v), 3) for v in maximum],
    }
    bm.free()
    return report


def export_stl(obj, path):
    select_only(obj)
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True, ascii_format=False)


def surface_region(source, name, predicate):
    """Copy selected outer-surface faces into a new open mesh patch."""
    vertex_map = {}
    vertices = []
    faces = []
    for polygon in source.data.polygons:
        if not predicate(polygon.center):
            continue
        face = []
        for source_index in polygon.vertices:
            if source_index not in vertex_map:
                vertex_map[source_index] = len(vertices)
                vertices.append(tuple(source.data.vertices[source_index].co))
            face.append(vertex_map[source_index])
        faces.append(face)
    if not faces:
        raise RuntimeError(f"Surface partition {name} selected no faces")
    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for material in source.data.materials:
        obj.data.materials.append(material)
    return obj


def make_hollow_region(source, name, predicate):
    obj = surface_region(source, name, predicate)
    modifier = obj.modifiers.new(name="Wall_1p8mm", type="SOLIDIFY")
    modifier.thickness = WALL_MM
    modifier.offset = -1.0
    modifier.use_rim = True
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    apply_modifier(obj, modifier)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.validate(clean_customdata=True)
    obj.data.update()
    print(f"[stage] hollow region complete {name}: {len(obj.data.polygons)} polygons", flush=True)
    return obj


source_path, output_dir = cli_args()
stl_dir = os.path.join(output_dir, "stl")
os.makedirs(stl_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.gltf(filepath=source_path)

source_objects = [obj for obj in scene.objects if obj.type == "MESH"]
if len(source_objects) != 1:
    raise RuntimeError(f"Expected one imported mesh, found {len(source_objects)}")

# Hunyuan generated thousands of disconnected surface patches and a very long
# tail. Trim the tail directly in source coordinates, then reduce the 1.5M
# triangles before voxel repair. This is intentionally a fast P0 print shell;
# the untouched source GLB remains available for a later fine-detail pass.
source = source_objects[0]
select_only(source)
source_vertex_count = len(source.data.vertices)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

all_components = [obj for obj in scene.objects if obj.type == "MESH"]
kept_components = []
removed_tail_components = 0
removed_tail_vertices = 0
for component in all_components:
    _, maximum = object_bounds(component)
    if maximum.y > 0.30:
        removed_tail_components += 1
        removed_tail_vertices += len(component.data.vertices)
        bpy.data.objects.remove(component, do_unlink=True)
    else:
        kept_components.append(component)

if not kept_components:
    raise RuntimeError("Tail component filter removed every component")
if removed_tail_vertices > source_vertex_count * 0.25:
    raise RuntimeError(
        f"Tail component safety gate failed: would remove {removed_tail_vertices}/{source_vertex_count} vertices"
    )

source = join_meshes(kept_components, "NiulaiRawWithoutTail")
select_only(source)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
print(
    f"[stage] tail removed: {removed_tail_components} components, {removed_tail_vertices} vertices",
    flush=True,
)

if PRE_REMESH_DECIMATE_RATIO < 0.999:
    decimate = source.modifiers.new(name="P0_PreRemeshDecimate", type="DECIMATE")
    decimate.decimate_type = "COLLAPSE"
    decimate.ratio = PRE_REMESH_DECIMATE_RATIO
    decimate.use_collapse_triangulate = True
    apply_modifier(source, decimate)
    print(f"[stage] pre-remesh decimated: {len(source.data.polygons)} polygons", flush=True)
else:
    print(f"[stage] pre-remesh decimation skipped: {len(source.data.polygons)} polygons", flush=True)

outer = source
outer.data.remesh_voxel_size = VOXEL_SIZE_SOURCE
outer.data.remesh_voxel_adaptivity = 0.15
select_only(outer)
bpy.ops.object.voxel_remesh()
outer.name = "NiulaiCleanOuter"
print(f"[stage] voxel repair complete: {len(outer.data.polygons)} polygons", flush=True)

smooth = outer.modifiers.new(name="P0_SurfaceSmooth", type="SMOOTH")
smooth.factor = 0.35
smooth.iterations = 2
apply_modifier(outer, smooth)
print(f"[stage] surface smoothing complete: {len(outer.data.polygons)} polygons", flush=True)

# Convert the arbitrary metre-scale generation into an explicit millimetre
# envelope compatible with the 220 x 180 x 360 mm mechanical baseline.
minimum, maximum = object_bounds(outer)
scale = TARGET_HEIGHT_MM / (maximum.z - minimum.z)
outer.scale = (scale, scale, scale)
select_only(outer)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minimum, maximum = object_bounds(outer)
outer.scale = (
    TARGET_WIDTH_MM / (maximum.x - minimum.x),
    TARGET_DEPTH_MM / (maximum.y - minimum.y),
    1.0,
)
select_only(outer)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
minimum, maximum = object_bounds(outer)
outer.location += Vector((-(minimum.x + maximum.x) / 2.0, -(minimum.y + maximum.y) / 2.0, -minimum.z))
select_only(outer)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

# Preserve a low-resolution copy of the repaired exterior as a reference.
outer_master = outer.copy()
outer_master.data = outer.data.copy()
bpy.context.collection.objects.link(outer_master)
outer_master.name = "00_CleanOuterReference"

def is_mouth(point):
    return abs(point.x) <= 52.0 and point.y <= -42.0 and 205.0 <= point.z <= 250.0


def is_head(point):
    return (
        abs(point.x) <= HEAD_HALF_WIDTH_MM
        and HEAD_FRONT_MM <= point.y <= HEAD_REAR_MM
        and point.z >= HEAD_MIN_Z_MM
    )


def part_predicate(part_name):
    def predicate(point):
        if point.z < BOTTOM_OPEN_Z_MM:
            return False
        mouth = is_mouth(point)
        head = is_head(point)
        if part_name == "mouth":
            return mouth
        if part_name == "head_front":
            return head and not mouth and point.y < SEAM_Y_MM
        if part_name == "head_rear":
            return head and not mouth and point.y >= SEAM_Y_MM
        if part_name == "body_front":
            return not head and point.y < SEAM_Y_MM
        if part_name == "body_rear":
            return not head and point.y >= SEAM_Y_MM
        raise ValueError(part_name)

    return predicate


# Split the repaired exterior by face location first, then solidify each open
# patch. This avoids Boolean self-intersection failures on AI-generated meshes
# and produces explicit service openings at every seam.
open_shell = make_hollow_region(
    outer_master,
    "02_OpenBottomShell",
    lambda point: point.z >= BOTTOM_OPEN_Z_MM,
)
parts = {
    "05_body_front_shell": make_hollow_region(
        outer_master, "05_BodyFrontShell", part_predicate("body_front")
    ),
    "06_body_rear_shell": make_hollow_region(
        outer_master, "06_BodyRearShell", part_predicate("body_rear")
    ),
    "07_head_front_shell": make_hollow_region(
        outer_master, "07_HeadFrontShell", part_predicate("head_front")
    ),
    "08_head_rear_shell": make_hollow_region(
        outer_master, "08_HeadRearShell", part_predicate("head_rear")
    ),
    "09_mouth_shell": make_hollow_region(
        outer_master, "09_MouthShell", part_predicate("mouth")
    ),
}

# Give the removable muzzle a visible P0 assembly gap without changing its
# overall shape. The final hinge and servo link remain deliberately unfrozen.
parts["09_mouth_shell"].location.y -= MOUTH_CLEARANCE_MM
select_only(parts["09_mouth_shell"])
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

outer_min, outer_max = object_bounds(outer_master)
outer_dimensions = outer_max - outer_min
for name, obj in {"open_shell": open_shell, **parts}.items():
    part_min, part_max = object_bounds(obj)
    dimensions = part_max - part_min
    if dimensions.x > outer_dimensions.x + 5.0 or dimensions.y > outer_dimensions.y + 5.0:
        raise RuntimeError(
            f"Envelope gate failed for {name}: expected within {tuple(outer_dimensions)}, got {tuple(dimensions)}"
        )

outer_master.hide_render = True
outer.hide_render = True
open_shell.hide_render = True

report = {
    "source": source_path,
    "removed_tail_components": removed_tail_components,
    "removed_tail_vertices": removed_tail_vertices,
    "pre_remesh_decimate_ratio": PRE_REMESH_DECIMATE_RATIO,
    "voxel_size_source": VOXEL_SIZE_SOURCE,
    "target_height_mm": TARGET_HEIGHT_MM,
    "target_width_mm": TARGET_WIDTH_MM,
    "target_depth_mm": TARGET_DEPTH_MM,
    "wall_mm": WALL_MM,
    "bottom_open_z_mm": BOTTOM_OPEN_Z_MM,
    "head_min_z_mm": HEAD_MIN_Z_MM,
    "outer_reference": mesh_report(outer_master),
    "shell_master": mesh_report(open_shell),
    "parts": {},
}

for filename, obj in parts.items():
    path = os.path.join(stl_dir, f"{filename}.stl")
    export_stl(obj, path)
    report["parts"][filename] = {**mesh_report(obj), "file": path}
    print(f"[stage] exported {filename}", flush=True)

select_only(outer_master)
scene.unit_settings.system = "METRIC"
scene.unit_settings.length_unit = "MILLIMETERS"
scene.unit_settings.scale_length = 0.001
bpy.ops.export_scene.gltf(
    filepath=os.path.join(output_dir, "niulai-clean-outer-reference-v0.3.glb"),
    export_format="GLB",
    use_selection=True,
)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "niulai-hollow-shell-v0.3.blend"))
with open(os.path.join(output_dir, "validation-report-v0.3.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

print(json.dumps(report, ensure_ascii=False, indent=2))
