import bpy
import os
import sys
from mathutils import Vector


TARGET_HEIGHT_MM = 330.0
TARGET_WIDTH_MM = 220.0
TARGET_DEPTH_MM = 200.0


def cli_args():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(args) < 2:
        raise SystemExit(
            "usage: blender --background --python render_exterior_target_v0_4.py -- input.glb output.png"
        )
    return os.path.abspath(args[0]), os.path.abspath(args[1])


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


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


source_path, output_path = cli_args()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=source_path)

source = next(obj for obj in bpy.context.scene.objects if obj.type == "MESH")
select_only(source)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")

kept = []
for component in [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]:
    _, maximum = bounds(component)
    if maximum.y > 0.30:
        bpy.data.objects.remove(component, do_unlink=True)
    else:
        kept.append(component)

outer = join_meshes(kept, "NiulaiHighDetailExteriorTarget")
minimum, maximum = bounds(outer)
outer.location += Vector((-(minimum.x + maximum.x) / 2, -(minimum.y + maximum.y) / 2, -minimum.z))
select_only(outer)
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
minimum, maximum = bounds(outer)
dimensions = maximum - minimum
center = (minimum + maximum) / 2.0
radius = max(dimensions) * 0.78

for polygon in outer.data.polygons:
    polygon.use_smooth = True

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -1.0
if scene.world is None:
    scene.world = bpy.data.worlds.new("WarmStudioWorld")
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.025, 0.035, 0.055, 1.0)
background.inputs["Strength"].default_value = 0.08

# Neutral floor makes this read as a product target, not a mesh debugger.
bpy.ops.mesh.primitive_plane_add(size=max(dimensions) * 3.0, location=(0.0, 0.0, -0.003))
floor = bpy.context.object
floor_material = bpy.data.materials.new("StudioFloor")
floor_material.diffuse_color = (0.055, 0.065, 0.085, 1.0)
floor.data.materials.append(floor_material)

for location, energy, size, color in [
    ((-radius, -radius, center.z + radius), 430.0, radius * 1.8, (1.0, 0.78, 0.58)),
    ((radius, -radius * 0.4, center.z + radius * 0.25), 280.0, radius * 1.5, (0.58, 0.73, 1.0)),
]:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = color
    look_at(light, center)

bpy.ops.object.camera_add(location=(radius * 0.95, -radius * 2.35, center.z + radius * 0.2))
camera = bpy.context.object
camera.data.type = "ORTHO"
camera.data.ortho_scale = max(dimensions.x, dimensions.z) * 1.18
camera.data.lens = 58.0
look_at(camera, center)
scene.camera = camera
scene.render.filepath = output_path
bpy.ops.render.render(write_still=True)
print(f"Rendered high-detail exterior target to {output_path}")
