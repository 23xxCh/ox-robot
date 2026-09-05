import bpy
import bmesh
import json
import os
import sys
from collections import deque
from math import cos, pi, sin
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
MOUTH_CENTER_X_MM = 0.0
MOUTH_CENTER_Z_MM = 231.5
MOUTH_RADIUS_X_MM = 48.0
MOUTH_RADIUS_Z_MM = 19.5
MOUTH_REAR_Y_MM = -42.0
MOUTH_SEAM_SEGMENTS = 16
BODY_HATCH_CENTER_X_MM = 0.0
BODY_HATCH_CENTER_Z_MM = 130.0
BODY_HATCH_RADIUS_X_MM = 60.0
BODY_HATCH_RADIUS_Z_MM = 52.0
BODY_HATCH_FRONT_Y_MM = 35.0
BODY_HATCH_SEAM_SEGMENTS = 20
ULTRASONIC_CENTER_Z_MM = 92.0
ULTRASONIC_CENTER_X_MM = 13.0
ULTRASONIC_RADIUS_MM = 10.5
# Put the HC-SR04 at the lower belly edge instead of damaging the character's
# face.  The bores continue into the body cavity so no inner membrane remains.
ULTRASONIC_REAR_Y_MM = -40.0
ULTRASONIC_SEAM_SEGMENTS = 14
VOXEL_SIZE_SOURCE = 0.004
POST_SOLIDIFY_VOXEL_MM = 0.6
PRE_REMESH_DECIMATE_RATIO = 1.0
TAIL_TRIM_Y_SOURCE = 0.22
WELD_DISTANCE_SOURCE = 0.000001


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


def remove_components_below_faces(obj, minimum_faces=100):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    unseen = set(bm.faces)
    remove_faces = []
    removed_components = 0
    while unseen:
        seed = unseen.pop()
        queue = deque([seed])
        component = []
        while queue:
            face = queue.popleft()
            component.append(face)
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in unseen:
                        unseen.remove(linked)
                        queue.append(linked)
        if len(component) < minimum_faces:
            remove_faces.extend(component)
            removed_components += 1
    if remove_faces:
        bmesh.ops.delete(bm, geom=remove_faces, context="FACES")
        orphan_verts = [vert for vert in bm.verts if not vert.link_faces]
        if orphan_verts:
            bmesh.ops.delete(bm, geom=orphan_verts, context="VERTS")
        bm.to_mesh(obj.data)
        obj.data.update()
    bm.free()
    return removed_components


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


def bisect(bm, plane_co, plane_no, keep_positive=None):
    kwargs = {
        "geom": list(bm.verts) + list(bm.edges) + list(bm.faces),
        "dist": 0.0001,
        "plane_co": plane_co,
        "plane_no": plane_no,
        "use_snap_center": False,
        "clear_inner": keep_positive is True,
        "clear_outer": keep_positive is False,
    }
    bmesh.ops.bisect_plane(bm, **kwargs)


def ellipse_seam_planes(center_x, center_z, radius_x, radius_z, segments):
    planes = []
    for index in range(segments):
        angle = 2.0 * pi * index / segments
        plane_co = (
            center_x + radius_x * cos(angle),
            0.0,
            center_z + radius_z * sin(angle),
        )
        plane_no = (
            cos(angle) / radius_x,
            0.0,
            sin(angle) / radius_z,
        )
        planes.append((plane_co, plane_no))
    return planes


MOUTH_SEAM_PLANES = ellipse_seam_planes(
    MOUTH_CENTER_X_MM,
    MOUTH_CENTER_Z_MM,
    MOUTH_RADIUS_X_MM,
    MOUTH_RADIUS_Z_MM,
    MOUTH_SEAM_SEGMENTS,
)
BODY_HATCH_SEAM_PLANES = ellipse_seam_planes(
    BODY_HATCH_CENTER_X_MM,
    BODY_HATCH_CENTER_Z_MM,
    BODY_HATCH_RADIUS_X_MM,
    BODY_HATCH_RADIUS_Z_MM,
    BODY_HATCH_SEAM_SEGMENTS,
)
ULTRASONIC_SEAM_PLANES = [
    ellipse_seam_planes(
        center_x,
        ULTRASONIC_CENTER_Z_MM,
        ULTRASONIC_RADIUS_MM,
        ULTRASONIC_RADIUS_MM,
        ULTRASONIC_SEAM_SEGMENTS,
    )
    for center_x in (-ULTRASONIC_CENTER_X_MM, ULTRASONIC_CENTER_X_MM)
]


def inside_mouth_panel(point):
    if point.y > MOUTH_REAR_Y_MM + 0.0001:
        return False
    for plane_co, plane_no in MOUTH_SEAM_PLANES:
        if (Vector(point) - Vector(plane_co)).dot(Vector(plane_no)) > 0.0001:
            return False
    return True


def inside_body_hatch(point):
    if point.y < BODY_HATCH_FRONT_Y_MM - 0.0001:
        return False
    for plane_co, plane_no in BODY_HATCH_SEAM_PLANES:
        if (Vector(point) - Vector(plane_co)).dot(Vector(plane_no)) > 0.0001:
            return False
    return True


def inside_ultrasonic_aperture(point):
    if point.y > ULTRASONIC_REAR_Y_MM + 0.0001:
        return False
    for circle_planes in ULTRASONIC_SEAM_PLANES:
        if all(
            (Vector(point) - Vector(plane_co)).dot(Vector(plane_no)) <= 0.0001
            for plane_co, plane_no in circle_planes
        ):
            return True
    return False


def inside_head_front_cutout(point):
    return inside_mouth_panel(point)


def inside_body_front_cutout(point):
    return inside_body_hatch(point) or inside_ultrasonic_aperture(point)


def surface_region_clipped(source, name, clips, split_planes=None, exclude=None):
    """Clip the repaired outer surface exactly so assembly seams are smooth."""
    mesh = source.data.copy()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for plane_co, plane_no, keep_positive in clips:
        bisect(bm, plane_co, plane_no, keep_positive=keep_positive)
    for plane_co, plane_no in split_planes or []:
        bisect(bm, plane_co, plane_no, keep_positive=None)
    if exclude is not None:
        removed_faces = [face for face in bm.faces if exclude(face.calc_center_median())]
        if removed_faces:
            bmesh.ops.delete(bm, geom=removed_faces, context="FACES")
        orphan_verts = [vert for vert in bm.verts if not vert.link_faces]
        if orphan_verts:
            bmesh.ops.delete(bm, geom=orphan_verts, context="VERTS")
    if not bm.faces:
        bm.free()
        raise RuntimeError(f"Surface partition {name} selected no faces")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.validate(clean_customdata=True)
    obj.data.update()
    return obj


def make_hollow_region(source, name, clips, split_planes=None, exclude=None):
    obj = surface_region_clipped(source, name, clips, split_planes, exclude)
    modifier = obj.modifiers.new(name="Wall_1p8mm", type="SOLIDIFY")
    modifier.thickness = WALL_MM
    # The welded exterior has normalized outward winding.  Grow the wall only
    # into the robot cavity so the visible movie-character surface stays fixed.
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

    # Dense voxel surfaces produce local offset self-intersections during
    # Solidify.  A 0.6 mm material-volume remesh repairs those intersections
    # while retaining a three-voxel nominal 1.8 mm wall.  The mouth-shell
    # experiment measured zero non-manifold edges and only ~5% volume change.
    obj.data.remesh_voxel_size = POST_SOLIDIFY_VOXEL_MM
    obj.data.remesh_voxel_adaptivity = 0.0
    select_only(obj)
    bpy.ops.object.voxel_remesh()
    removed_components = remove_components_below_faces(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    if bm.calc_volume(signed=True) < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print(
        f"[stage] hollow region repaired {name}: {len(obj.data.polygons)} polygons; "
        f"removed {removed_components} tiny components",
        flush=True,
    )
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

# Hunyuan exported the visually continuous skin as thousands of tiled patches
# with duplicated seam vertices.  Voxel-remeshing those open patches directly
# turns every patch boundary into a raised ring.  Weld coincident vertices
# first, then discard only triangle-sized disconnected scraps.
bm = bmesh.new()
bm.from_mesh(source.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=WELD_DISTANCE_SOURCE)
bmesh.ops.dissolve_degenerate(
    bm, edges=list(bm.edges), dist=WELD_DISTANCE_SOURCE * 0.1
)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(source.data)
bm.free()
source.data.validate(clean_customdata=True)
source.data.update()

select_only(source)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
welded_components = [obj for obj in scene.objects if obj.type == "MESH"]
welded_components.sort(key=lambda obj: len(obj.data.polygons), reverse=True)
source = welded_components[0]
source.name = "NiulaiWeldedMainSurface"
removed_weld_scraps = len(welded_components) - 1
for scrap in welded_components[1:]:
    bpy.data.objects.remove(scrap, do_unlink=True)

# Close the small residual generation gaps before the volume remesh.  The
# remesh is now operating on one solid character surface instead of 4,751
# independent open patches.
bm = bmesh.new()
bm.from_mesh(source.data)
boundary = [edge for edge in bm.edges if edge.is_boundary]
filled = bmesh.ops.holes_fill(bm, edges=boundary, sides=0) if boundary else {"faces": []}
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
source_repair_report = {
    "removed_weld_scraps": removed_weld_scraps,
    "filled_faces": len(filled.get("faces", [])),
    "boundary_edges_before_voxel": sum(1 for edge in bm.edges if edge.is_boundary),
    "non_manifold_edges_before_voxel": sum(1 for edge in bm.edges if not edge.is_manifold),
}
bm.to_mesh(source.data)
bm.free()
source.data.validate(clean_customdata=True)
source.data.update()
print(f"[stage] source seams welded: {source_repair_report}", flush=True)

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
outer.data.remesh_voxel_adaptivity = 0.10
select_only(outer)
bpy.ops.object.voxel_remesh()
outer.name = "NiulaiCleanOuter"
print(f"[stage] voxel repair complete: {len(outer.data.polygons)} polygons", flush=True)

smooth = outer.modifiers.new(name="P0_SurfaceSmooth", type="SMOOTH")
smooth.factor = 0.25
smooth.iterations = 2
apply_modifier(outer, smooth)
print(f"[stage] surface smoothing complete: {len(outer.data.polygons)} polygons", flush=True)

# Voxel remesh can leave tiny degenerates or locally inconsistent winding on
# a dense mesh.  Normalize the closed exterior before splitting it; otherwise
# inward solidify may push isolated patches outside the intended envelope.
bm = bmesh.new()
bm.from_mesh(outer.data)
bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.000001)
bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.000001)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
if bm.calc_volume(signed=True) < 0:
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
bm.to_mesh(outer.data)
bm.free()
outer.data.validate(clean_customdata=True)
outer.data.update()
print(f"[stage] exterior winding normalized: {len(outer.data.polygons)} polygons", flush=True)

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

# Split the repaired exterior by face location first, then solidify each open
# patch. Exact BMesh plane cuts keep the service seams straight and matching.
clip_above_bottom = ((0.0, 0.0, BOTTOM_OPEN_Z_MM), (0.0, 0.0, 1.0), True)
clip_below_head = ((0.0, 0.0, HEAD_MIN_Z_MM), (0.0, 0.0, 1.0), False)
clip_above_head = ((0.0, 0.0, HEAD_MIN_Z_MM), (0.0, 0.0, 1.0), True)
clip_front = ((0.0, SEAM_Y_MM, 0.0), (0.0, 1.0, 0.0), False)
clip_rear = ((0.0, SEAM_Y_MM, 0.0), (0.0, 1.0, 0.0), True)
clip_mouth_front = ((0.0, MOUTH_REAR_Y_MM, 0.0), (0.0, 1.0, 0.0), False)
split_ultrasonic_rear = (
    (0.0, ULTRASONIC_REAR_Y_MM, 0.0),
    (0.0, 1.0, 0.0),
)
clip_body_hatch_rear = (
    (0.0, BODY_HATCH_FRONT_Y_MM, 0.0),
    (0.0, 1.0, 0.0),
    True,
)

open_shell = make_hollow_region(
    outer_master,
    "02_OpenBottomShell",
    [clip_above_bottom],
)
parts = {
    "05_body_front_shell": make_hollow_region(
        outer_master,
        "05_BodyFrontShell",
        [clip_above_bottom, clip_below_head],
        split_planes=[
            (clip_body_hatch_rear[0], clip_body_hatch_rear[1]),
            *BODY_HATCH_SEAM_PLANES,
            split_ultrasonic_rear,
            *[
                plane
                for circle_planes in ULTRASONIC_SEAM_PLANES
                for plane in circle_planes
            ],
        ],
        exclude=inside_body_front_cutout,
    ),
    "06_body_rear_shell": make_hollow_region(
        outer_master,
        "06_BodyRearShell",
        [
            clip_above_bottom,
            clip_below_head,
            clip_body_hatch_rear,
            *[
                (plane_co, plane_no, False)
                for plane_co, plane_no in BODY_HATCH_SEAM_PLANES
            ],
        ],
    ),
    "07_head_front_shell": make_hollow_region(
        outer_master,
        "07_HeadFrontShell",
        [clip_above_head, clip_front],
        split_planes=[
            (clip_mouth_front[0], clip_mouth_front[1]),
            *MOUTH_SEAM_PLANES,
        ],
        exclude=inside_head_front_cutout,
    ),
    "08_head_rear_shell": make_hollow_region(
        outer_master,
        "08_HeadRearShell",
        [clip_above_head, clip_rear],
    ),
    "09_mouth_shell": make_hollow_region(
        outer_master,
        "09_MouthShell",
        [
            clip_mouth_front,
            *[(plane_co, plane_no, False) for plane_co, plane_no in MOUTH_SEAM_PLANES],
        ],
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
    "source_repair": source_repair_report,
    "weld_distance_source": WELD_DISTANCE_SOURCE,
    "pre_remesh_decimate_ratio": PRE_REMESH_DECIMATE_RATIO,
    "voxel_size_source": VOXEL_SIZE_SOURCE,
    "post_solidify_voxel_mm": POST_SOLIDIFY_VOXEL_MM,
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
    filepath=os.path.join(output_dir, "niulai-clean-outer-reference-v0.4.glb"),
    export_format="GLB",
    use_selection=True,
)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_dir, "niulai-hollow-shell-v0.4.blend"))
with open(os.path.join(output_dir, "validation-report-v0.4.json"), "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)

print(json.dumps(report, ensure_ascii=False, indent=2))
