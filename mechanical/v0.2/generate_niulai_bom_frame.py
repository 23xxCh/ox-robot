from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
STL_DIR = ROOT / "stl"
FCSTD_PATH = ROOT / "niulai-bom-compatible-frame-v0.2.FCStd"
ASSEMBLY_STEP_PATH = ROOT / "niulai-bom-compatible-frame-assembly-v0.2.step"
PRINT_STEP_PATH = ROOT / "niulai-bom-compatible-frame-print-parts-v0.2.step"
REPORT_PATH = ROOT / "validation-report-v0.2.json"


P = {
    "envelope_w": 220.0,
    "envelope_d": 180.0,
    "envelope_h": 360.0,
    "printer_x": 330.0,
    "printer_y": 320.0,
    "printer_z": 325.0,
    "chassis_w": 180.0,
    "chassis_d": 140.0,
    "chassis_t": 4.0,
    "chassis_z": 42.0,
    # BOM row 51 only identifies a generic yellow TT motor.  Use a conservative
    # envelope and a clamp/strap mount instead of supplier-specific screw holes.
    "tt_length": 70.0,
    "tt_width": 23.0,
    "tt_height": 25.0,
    "wheel_radius": 32.5,
    "wheel_width": 13.0,
    # TowerPro's SG90 body dimensions.  A true positional servo in the same
    # micro-servo envelope can replace the BOM's continuous-rotation SG90.
    "sg90_length": 23.0,
    "sg90_width": 12.2,
    "sg90_height": 29.0,
    # Conservative adapter envelopes derived from the BOM photo and published
    # reference products.  Their mounts use slots or straps, not fixed PCB holes.
    "esp32_board_length": 66.0,
    "esp32_board_width": 32.0,
    "oled_module_width": 66.0,
    "oled_module_height": 44.0,
    "hcsr04_width": 48.0,
    "hcsr04_height": 23.0,
    "buck_envelope_length": 48.0,
    "buck_envelope_width": 28.0,
    "radar_envelope_width": 45.0,
    "radar_envelope_height": 35.0,
    "battery_envelope_length": 100.0,
    "battery_envelope_width": 60.0,
    "battery_envelope_height": 30.0,
    "shell_panel_t": 1.4,
    "clearance": 0.6,
    "m3_clearance": 3.4,
}


COLORS = {
    "print": (0.82, 0.68, 0.22),
    "motor": (0.95, 0.68, 0.08),
    "servo": (0.12, 0.30, 0.78),
    "wheel": (0.08, 0.08, 0.09),
    "battery": (0.14, 0.45, 0.20),
    "pcb": (0.10, 0.40, 0.32),
    "metal": (0.65, 0.68, 0.72),
    "warning": (0.92, 0.28, 0.10),
    "shell": (0.96, 0.72, 0.05),
}


def fused(*shapes: Part.Shape) -> Part.Shape:
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> Part.Shape:
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def cut_vertical_holes(shape: Part.Shape, points: list[tuple[float, float]], diameter: float, z0: float, height: float) -> Part.Shape:
    result = shape
    for x, y in points:
        hole = Part.makeCylinder(diameter / 2.0, height, App.Vector(x, y, z0))
        result = result.cut(hole)
    return result.removeSplitter()


def vertical_slot(
    center_x: float,
    center_y: float,
    length: float,
    width: float,
    z0: float,
    height: float,
    along_x: bool = True,
) -> Part.Shape:
    """Return a vertical capsule slot for adjustable PCB/strap mounting."""
    radius = width / 2.0
    straight = max(length - width, 0.01)
    if along_x:
        core = box(straight, width, height, center_x - straight / 2.0, center_y - radius, z0)
        end_a = Part.makeCylinder(radius, height, App.Vector(center_x - straight / 2.0, center_y, z0))
        end_b = Part.makeCylinder(radius, height, App.Vector(center_x + straight / 2.0, center_y, z0))
    else:
        core = box(width, straight, height, center_x - radius, center_y - straight / 2.0, z0)
        end_a = Part.makeCylinder(radius, height, App.Vector(center_x, center_y - straight / 2.0, z0))
        end_b = Part.makeCylinder(radius, height, App.Vector(center_x, center_y + straight / 2.0, z0))
    return fused(core, end_a, end_b)


def cut_vertical_slots(
    shape: Part.Shape,
    slots: list[tuple[float, float, float, float, bool]],
    z0: float,
    height: float,
) -> Part.Shape:
    result = shape
    for center_x, center_y, length, width, along_x in slots:
        result = result.cut(vertical_slot(center_x, center_y, length, width, z0, height, along_x))
    return result.removeSplitter()


def add_feature(
    doc: App.Document,
    group: App.DocumentObjectGroup,
    name: str,
    label: str,
    shape: Part.Shape,
    category: str,
    color: tuple[float, float, float],
    notes: str,
) -> App.DocumentObject:
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Category", "Niulai")
    obj.Category = category
    obj.addProperty("App::PropertyString", "Revision", "Niulai")
    obj.Revision = "v0.2"
    obj.addProperty("App::PropertyString", "Notes", "Niulai")
    obj.Notes = notes
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
    obj.addProperty("App::PropertyString", "DisplayColor", "Niulai")
    obj.DisplayColor = ",".join(f"{value:.3f}" for value in color)
    group.addObject(obj)
    return obj


def make_chassis() -> Part.Shape:
    z = P["chassis_z"]
    shape = box(P["chassis_w"], P["chassis_d"], P["chassis_t"], -90, -70, z)
    mounting_points = [
        (-78, -58), (78, -58), (-78, 58), (78, 58),
        (-58, -42), (58, -42), (-58, 42), (58, 42),
        (-72, -52), (72, -52),
    ]
    shape = cut_vertical_holes(shape, mounting_points, P["m3_clearance"], z - 1, P["chassis_t"] + 2)
    adjustable_slots = [
        (-66, -38, 34, 4.2, False), (-66, 18, 34, 4.2, False),
        (66, -38, 34, 4.2, False), (66, 18, 34, 4.2, False),
        (-34, -55, 28, 4.2, True), (34, -55, 28, 4.2, True),
        (-34, 55, 28, 4.2, True), (34, 55, 28, 4.2, True),
    ]
    return cut_vertical_slots(shape, adjustable_slots, z - 1, P["chassis_t"] + 2)


def make_motor_mount(side: str) -> Part.Shape:
    if side == "left":
        x0 = -90.0
        inner_x = -63.0
    else:
        x0 = 60.0
        inner_x = 60.0
    base = box(30, 76, 3, x0, -38, 20)
    inner_wall = box(3, 76, 31, inner_x, -38, 20)
    front_stop = box(30, 3, 25, x0, -38, 20)
    rear_stop = box(30, 3, 25, x0, 35, 20)
    mount = fused(base, inner_wall, front_stop, rear_stop)
    slots = [(-4, -27), (-4, 27)] if side == "left" else [(4, -27), (4, 27)]
    for x_offset, y in slots:
        x = inner_x + x_offset
        hole = Part.makeCylinder(1.7, 8, App.Vector(x, y, 37), App.Vector(1, 0, 0))
        mount = mount.cut(hole)
    strap_slots = [
        (x0 + 15, -21, 16, 3.2, True),
        (x0 + 15, 21, 16, 3.2, True),
    ]
    return cut_vertical_slots(mount, strap_slots, 19, 6)


def make_battery_tray() -> Part.Shape:
    base = box(106, 66, 3, -53, -33, 46)
    left = box(3, 66, 12, -53, -33, 49)
    right = box(3, 66, 12, 50, -33, 49)
    front = box(100, 3, 12, -50, -33, 49)
    rear = box(100, 3, 12, -50, 30, 49)
    tray = fused(base, left, right, front, rear)
    strap_slots = [
        (-34, -20, 18, 4.0, True), (34, -20, 18, 4.0, True),
        (-34, 20, 18, 4.0, True), (34, 20, 18, 4.0, True),
    ]
    return cut_vertical_slots(tray, strap_slots, 45, 6)


def make_electronics_deck() -> Part.Shape:
    deck = box(140, 96, 3, -70, -48, 84)
    points = [(-60, -38), (60, -38), (-60, 38), (60, 38)]
    deck = cut_vertical_holes(deck, points, P["m3_clearance"], 83, 5)
    module_slots = [
        (-36, -25, 44, 4.0, True), (18, -25, 44, 4.0, True),
        (-36, 0, 44, 4.0, True), (18, 0, 44, 4.0, True),
        (-36, 25, 44, 4.0, True), (18, 25, 44, 4.0, True),
        (57, 0, 58, 4.0, False),
    ]
    return cut_vertical_slots(deck, module_slots, 83, 5)


def make_standoffs() -> Part.Shape:
    shapes = []
    for x, y in [(-60, -38), (60, -38), (-60, 38), (60, 38)]:
        outer = Part.makeCylinder(4.0, 38.0, App.Vector(x, y, 46))
        inner = Part.makeCylinder(1.7, 38.0, App.Vector(x, y, 46))
        shapes.append(outer.cut(inner))
    return Part.makeCompound(shapes)


def make_neck_column(side: str) -> Part.Shape:
    x = -76.0 if side == "left" else 64.0
    column = box(12, 10, 146, x, -58, 46)
    foot = box(20, 24, 6, x - 4, -65, 46)
    brace = box(12, 30, 8, x, -48, 90)
    return fused(column, foot, brace)


def make_neck_crossbeam() -> Part.Shape:
    beam = box(152, 10, 8, -76, -58, 190)
    center_plate = box(54, 42, 4, -27, -64, 198)
    points = [(-18, -54), (18, -54), (-18, -32), (18, -32)]
    center_plate = cut_vertical_holes(center_plate, points, 2.4, 197, 6)
    return fused(beam, center_plate)


def make_pan_platform() -> Part.Shape:
    platform = box(90, 60, 4, -45, -75, 232)
    points = [(-36, -66), (36, -66), (-36, -24), (36, -24), (0, -45)]
    return cut_vertical_holes(platform, points, P["m3_clearance"], 231, 6)


def make_tilt_bracket() -> Part.Shape:
    left = box(4, 60, 58, -47, -75, 236)
    right = box(4, 60, 58, 43, -75, 236)
    rear = box(94, 4, 18, -47, -19, 236)
    left_axis = Part.makeCylinder(2.0, 8, App.Vector(-49, -46, 263), App.Vector(1, 0, 0))
    right_axis = Part.makeCylinder(2.0, 8, App.Vector(41, -46, 263), App.Vector(1, 0, 0))
    return fused(left, right, rear).cut(left_axis).cut(right_axis).removeSplitter()


def make_head_interface_plate() -> Part.Shape:
    plate = box(80, 50, 4, -40, -70, 274)
    points = [(-32, -62), (32, -62), (-32, -28), (32, -28)]
    return cut_vertical_holes(plate, points, P["m3_clearance"], 273, 6)


def make_mouth_bracket() -> Part.Shape:
    base = box(34, 18, 3, -17, -79, 238)
    left = box(3, 18, 34, -17, -79, 241)
    right = box(3, 18, 34, 14, -79, 241)
    rocker = box(64, 6, 3, -32, -86, 274)
    return Part.makeCompound([fused(base, left, right), rocker])


def make_front_skid() -> Part.Shape:
    foot = box(24, 10, 5, -12, -82, 2)
    upright = box(24, 5, 38, -12, -72, 7)
    return fused(foot, upright)


def make_caster_bracket() -> Part.Shape:
    top = box(42, 34, 4, -21, 38, 38)
    left = box(4, 24, 18, -21, 43, 20)
    right = box(4, 24, 18, 17, 43, 20)
    bracket = fused(top, left, right)
    slots = [(-12, 54, 16, 3.8, False), (12, 54, 16, 3.8, False)]
    return cut_vertical_slots(bracket, slots, 37, 6)


def make_rear_skid() -> Part.Shape:
    """Printable fallback when the organizer does not provide a caster."""
    mounting = box(40, 26, 4, -20, 42, 38)
    stem = box(14, 18, 25, -7, 47, 13)
    foot = box(24, 24, 5, -12, 44, 8)
    leading_bevel = Part.makeCylinder(12, 24, App.Vector(0, 44, 8), App.Vector(0, 1, 0))
    skid = fused(mounting, stem, foot, leading_bevel.common(box(24, 24, 8, -12, 44, 0)))
    slots = [(-11, 55, 14, 3.8, False), (11, 55, 14, 3.8, False)]
    return cut_vertical_slots(skid, slots, 37, 6)


def ellipse_wire(radius_x: float, radius_y: float, z: float) -> Part.Wire:
    edge = Part.Ellipse(App.Vector(0, 0, z), radius_x, radius_y).toShape()
    return Part.Wire([edge])


def make_torso_shell() -> Part.Shape:
    """Create a thin removable torso skin; the internal frame remains load-bearing."""
    sections = [
        (72.0, 48.0, 54.0),
        (94.0, 66.0, 88.0),
        (101.0, 72.0, 136.0),
        (78.0, 54.0, 194.0),
    ]
    wall = P["shell_panel_t"]
    outer = Part.makeLoft([ellipse_wire(rx, ry, z) for rx, ry, z in sections], True, False)
    inner_sections = [
        (rx - wall, ry - wall, z - 1.0 if index == 0 else z + 1.0 if index == len(sections) - 1 else z)
        for index, (rx, ry, z) in enumerate(sections)
    ]
    inner = Part.makeLoft([ellipse_wire(rx, ry, z) for rx, ry, z in inner_sections], True, False)
    return outer.cut(inner).removeSplitter()


def make_torso_panel(side: str) -> Part.Shape:
    shell = make_torso_shell()
    if side == "front":
        clip = box(230, 90, 170, -115, -90, 45)
    else:
        clip = box(230, 90, 170, -115, 0, 45)
    panel = shell.common(clip).removeSplitter()

    # Four seam tabs per panel accept M3 screws or zip ties.  These tabs are
    # intentionally generic so the cover can move after real component checks.
    tab_y = -2.5 if side == "front" else 0.0
    tabs = []
    for x, z in [(-64, 82), (64, 82), (-58, 160), (58, 160)]:
        tab = box(16, 5, 14, x - 8, tab_y, z - 7)
        hole = Part.makeCylinder(P["m3_clearance"] / 2.0, 8, App.Vector(x, tab_y - 1, z), App.Vector(0, 1, 0))
        tabs.append(tab.cut(hole))
    return fused(panel, *tabs)


def make_head_shell_envelope() -> Part.Shape:
    sections = [
        (48.0, 42.0, 276.0),
        (68.0, 56.0, 310.0),
        (58.0, 48.0, 348.0),
    ]
    return Part.makeLoft([ellipse_wire(rx, ry, z) for rx, ry, z in sections], True, False)


def make_tt_motor(side: str) -> Part.Shape:
    x0 = -88 if side == "left" else 65
    body = box(P["tt_width"], P["tt_length"], P["tt_height"], x0, -35, 19.5)
    if side == "left":
        axle = Part.makeCylinder(3, 18, App.Vector(-106, 0, 32), App.Vector(1, 0, 0))
    else:
        axle = Part.makeCylinder(3, 18, App.Vector(88, 0, 32), App.Vector(1, 0, 0))
    return fused(body, axle)


def make_wheel(side: str) -> Part.Shape:
    x = -103.5 if side == "left" else 90.5
    return Part.makeCylinder(P["wheel_radius"], P["wheel_width"], App.Vector(x, 0, 32), App.Vector(1, 0, 0))


def make_sg90(role: str) -> Part.Shape:
    if role == "pan":
        body = box(23, 12.2, 29, -11.5, -52, 202)
        flange = box(32, 12.2, 2, -16, -52, 218)
        horn = Part.makeCylinder(13, 2.0, App.Vector(0, -45.9, 231), App.Vector(0, 0, 1))
        return Part.makeCompound([body, flange, horn])
    if role == "tilt":
        body = box(12.2, 23, 29, -59.2, -58, 246)
        flange = box(2, 32, 29, -49, -62.5, 246)
        horn = Part.makeCylinder(13, 2.0, App.Vector(-47, -46.5, 263), App.Vector(1, 0, 0))
        return Part.makeCompound([body, flange, horn])
    body = box(23, 12.2, 29, -11.5, -76, 242)
    flange = box(32, 12.2, 2, -16, -76, 257)
    horn = Part.makeCylinder(10, 2.0, App.Vector(0, -69.9, 271), App.Vector(0, 0, 1))
    return Part.makeCompound([body, flange, horn])


def make_caster_ball() -> Part.Shape:
    return Part.makeSphere(12, App.Vector(0, 55, 12))


def make_battery_placeholder() -> Part.Shape:
    return box(
        P["battery_envelope_length"],
        P["battery_envelope_width"],
        P["battery_envelope_height"],
        -P["battery_envelope_length"] / 2.0,
        -P["battery_envelope_width"] / 2.0,
        49,
    )


def make_pcb_placeholder(dx: float, dy: float, x: float, y: float, dz: float = 8.0) -> Part.Shape:
    return box(dx, dy, dz, x, y, 87)


def make_vertical_module(dx: float, dz: float, x: float, y: float, z: float, depth: float = 8.0) -> Part.Shape:
    return box(dx, depth, dz, x, y, z)


def export_stl(obj: App.DocumentObject, filename: str) -> None:
    Mesh.export([obj], str(STL_DIR / filename))


def bbox_dict(shape: Part.Shape) -> dict[str, float]:
    bb = shape.BoundBox
    return {
        "x": round(bb.XLength, 3),
        "y": round(bb.YLength, 3),
        "z": round(bb.ZLength, 3),
        "xmin": round(bb.XMin, 3),
        "ymin": round(bb.YMin, 3),
        "zmin": round(bb.ZMin, 3),
        "xmax": round(bb.XMax, 3),
        "ymax": round(bb.YMax, 3),
        "zmax": round(bb.ZMax, 3),
    }


def shape_center_of_mass(shape: Part.Shape) -> App.Vector:
    solids = list(shape.Solids)
    if solids:
        total_volume = sum(solid.Volume for solid in solids)
        if total_volume > 0:
            weighted = App.Vector(0, 0, 0)
            for solid in solids:
                weighted += solid.CenterOfMass * solid.Volume
            return weighted / total_volume
    bb = shape.BoundBox
    return App.Vector(
        (bb.XMin + bb.XMax) / 2.0,
        (bb.YMin + bb.YMax) / 2.0,
        (bb.ZMin + bb.ZMax) / 2.0,
    )


def main() -> None:
    STL_DIR.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("NiulaiBomCompatibleFrameV02")
    printed_group = doc.addObject("App::DocumentObjectGroup", "PrintedParts")
    printed_group.Label = "01 可打印工程骨架（物料表兼容）"
    shell_group = doc.addObject("App::DocumentObjectGroup", "ShellPanels")
    shell_group.Label = "02 黄色 PLA 轻量壳板"
    alternative_group = doc.addObject("App::DocumentObjectGroup", "AlternativeParts")
    alternative_group.Label = "03 可选降级打印件"
    hardware_group = doc.addObject("App::DocumentObjectGroup", "HardwarePlaceholders")
    hardware_group.Label = "04 物料表硬件包络（非精确型号）"
    reserved_group = doc.addObject("App::DocumentObjectGroup", "ReservedInterfaces")
    reserved_group.Label = "05 混元头壳与未来接口"

    printed_specs = [
        ("ChassisBase", "底盘主板", make_chassis(), "01_chassis_base.stl", "承力主板；M3 通孔为初版通用孔位"),
        ("MotorMountLeft", "左 TT 电机卡箍座", make_motor_mount("left"), "02_motor_mount_left.stl", "70×23×25 mm 保守包络；长槽支持扎带/卡箍微调"),
        ("MotorMountRight", "右 TT 电机卡箍座", make_motor_mount("right"), "03_motor_mount_right.stl", "70×23×25 mm 保守包络；长槽支持扎带/卡箍微调"),
        ("BatteryTray", "下置可调电池托盘", make_battery_tray(), "04_battery_tray.stl", "最大约100×60 mm；使用绑带，不假定66号电池盒可驱动执行器"),
        ("ElectronicsDeck", "通用电子模块层板", make_electronics_deck(), "05_electronics_deck.stl", "长圆孔兼容主控、驱动、电源与音频模块，不画死PCB孔位"),
        ("StandoffSet", "电子层 M3 隔柱组", make_standoffs(), "06_standoff_set.stl", "建议实物优先使用金属 M3 隔柱"),
        ("NeckColumnLeft", "左颈部立柱", make_neck_column("left"), "07_neck_column_left.stl", "开架样机承力立柱，外壳不承力"),
        ("NeckColumnRight", "右颈部立柱", make_neck_column("right"), "08_neck_column_right.stl", "开架样机承力立柱，外壳不承力"),
        ("NeckCrossbeam", "颈部横梁及 PAN 座", make_neck_crossbeam(), "09_neck_crossbeam.stl", "安装 PAN 舵机；孔位为 SG90 名义尺寸"),
        ("PanPlatform", "头部旋转平台", make_pan_platform(), "10_pan_platform.stl", "由 PAN 舵机驱动，需设置软件与机械限位"),
        ("TiltBracket", "头部 TILT U 型架", make_tilt_bracket(), "11_tilt_bracket.stl", "头部俯仰；轴孔和舵机孔待实测"),
        ("HeadInterfacePlate", "头部外壳接口板", make_head_interface_plate(), "12_head_interface_plate.stl", "未来连接牛头外观网格，不依赖网格承力"),
        ("MouthBracket", "嘴部舵机与摇杆架", make_mouth_bracket(), "13_mouth_bracket.stl", "MOUTH 开合机构；连杆长度待牛嘴模型冻结"),
        ("FrontSkid", "前部防倾支点", make_front_skid(), "14_front_anti_tip_skid.stl", "防止急停前倾；离地间隙需实测"),
        ("CasterBracket", "后轮/滑块通用支架", make_caster_bracket(), "15_rear_caster_bracket.stl", "长槽兼容滚珠万向轮；若主办方不提供则安装打印滑块"),
    ]

    printed = []
    for name, label, shape, filename, notes in printed_specs:
        obj = add_feature(doc, printed_group, name, label, shape, "PRINTED", COLORS["print"], notes)
        obj.addProperty("App::PropertyString", "ExportFile", "Niulai")
        obj.ExportFile = filename
        printed.append(obj)

    shell_specs = [
        ("TorsoFrontPanel", "黄色 PLA 牛肚前壳", make_torso_panel("front"), "16_torso_front_panel.stl", "1.4 mm 薄壁非承力壳；混元头壳未生成也可先装车"),
        ("TorsoRearPanel", "黄色 PLA 背部检修壳", make_torso_panel("rear"), "17_torso_rear_panel.stl", "可拆背壳；四组通用M3/扎带耳位"),
    ]
    for name, label, shape, filename, notes in shell_specs:
        obj = add_feature(doc, shell_group, name, label, shape, "SHELL", COLORS["shell"], notes)
        obj.addProperty("App::PropertyString", "ExportFile", "Niulai")
        obj.ExportFile = filename
        printed.append(obj)

    alternative_specs = [
        ("RearSkidFallback", "后滑块降级件", make_rear_skid(), "18_rear_skid_fallback.stl", "物料表无万向轮时使用；与滚珠万向轮二选一"),
    ]
    alternatives = []
    for name, label, shape, filename, notes in alternative_specs:
        obj = add_feature(doc, alternative_group, name, label, shape, "ALTERNATIVE", COLORS["print"], notes)
        obj.addProperty("App::PropertyString", "ExportFile", "Niulai")
        obj.ExportFile = filename
        alternatives.append(obj)

    hardware_specs = [
        ("TTMotorLeft", "左 TT 电机保守包络", make_tt_motor("left"), COLORS["motor"], "70×23×25 mm；通用黄壳TT并非唯一型号"),
        ("TTMotorRight", "右 TT 电机保守包络", make_tt_motor("right"), COLORS["motor"], "70×23×25 mm；通用黄壳TT并非唯一型号"),
        ("WheelLeft", "左轮占位", make_wheel("left"), COLORS["wheel"], "直径65 mm、宽13 mm；物料表未列车轮，需确认是否随电机提供"),
        ("WheelRight", "右轮占位", make_wheel("right"), COLORS["wheel"], "直径65 mm、宽13 mm；物料表未列车轮，需确认是否随电机提供"),
        ("CasterBall", "后滚珠万向轮占位", make_caster_ball(), COLORS["metal"], "24 mm 滚珠占位；孔距待实物确认"),
        ("Battery2S", "执行器电池最大包络", make_battery_placeholder(), COLORS["battery"], "100×60×30 mm 可调包络；最终必须核验保护/BMS和放电能力"),
        ("ServoPan", "SG90-180 PAN 舵机占位", make_sg90("pan"), COLORS["servo"], "23×12.2×29 mm；禁止用 360°连续旋转舵机"),
        ("ServoTilt", "SG90-180 TILT 舵机占位", make_sg90("tilt"), COLORS["servo"], "23×12.2×29 mm；扭矩需按头部质量复核"),
        ("ServoMouth", "SG90-180 MOUTH 舵机占位", make_sg90("mouth"), COLORS["servo"], "23×12.2×29 mm；嘴部连杆待冻结"),
        ("ESP32Placeholder", "ESP32-S3 主控兼容包络", make_pcb_placeholder(P["esp32_board_length"], P["esp32_board_width"], -66, -42), COLORS["pcb"], "最大66×32 mm；覆盖官方DevKitC-1参考与主办方较小核心板照片"),
        ("DRV8833Placeholder", "DRV8833 兼容包络", make_pcb_placeholder(35, 28, 7, -40, 12), COLORS["pcb"], "靠近电机线束；型号不在物料表，孔位使用长槽"),
        ("PowerPlaceholder", "降压与保险兼容包络", make_pcb_placeholder(P["buck_envelope_length"], P["buck_envelope_width"], 12, 4, 16), COLORS["warning"], "按主办方照片采用48×28×16 mm保守空间，不采用迷你板22×17 mm画死尺寸"),
        ("RadarPlaceholder", "24GHz雷达兼容包络", make_vertical_module(P["radar_envelope_width"], P["radar_envelope_height"], -22.5, -74, 120), COLORS["pcb"], "60/61号型号不唯一；胸口保留45×35×8 mm窗口空间"),
        ("OLEDPlaceholder", "2.42寸OLED兼容包络", make_vertical_module(P["oled_module_width"], P["oled_module_height"], -33, -78, 296), COLORS["pcb"], "参考SSD1309模块61.5×39.5 mm，四周增加装配余量"),
        ("HCSR04Placeholder", "HC-SR04兼容包络", make_vertical_module(P["hcsr04_width"], P["hcsr04_height"], -24, -80, 270), COLORS["pcb"], "参考45×20×15 mm；最终在混元头壳鼻部开孔"),
    ]

    hardware = []
    for name, label, shape, color, notes in hardware_specs:
        hardware.append(add_feature(doc, hardware_group, name, label, shape, "PLACEHOLDER", color, notes))

    insta_interface = cut_vertical_holes(box(60, 40, 3, -30, 38, 198), [(-20, 48), (20, 48), (-20, 68), (20, 68)], 3.4, 197, 5)
    add_feature(
        doc,
        reserved_group,
        "Insta360ReservedInterface",
        "背部 Insta360 预留接口",
        insta_interface,
        "RESERVED",
        COLORS["metal"],
        "P0 不安装摄像机，仅保留四孔接口；具体云台/相机孔距未冻结",
    )
    add_feature(
        doc,
        reserved_group,
        "HunyuanHeadEnvelope",
        "混元3D牛头最大包络",
        make_head_shell_envelope(),
        "RESERVED",
        (0.92, 0.76, 0.20),
        "仅为头壳生成与缩放边界，不作为可打印牛头；正式网格需在FreeCAD中切眼、鼻、嘴和接口",
    )

    doc.recompute()
    doc.saveAs(str(FCSTD_PATH))

    for obj in printed + alternatives:
        export_stl(obj, obj.ExportFile)

    Part.export(printed + alternatives, str(PRINT_STEP_PATH))
    Part.export(printed + hardware, str(ASSEMBLY_STEP_PATH))

    print_parts = []
    all_printable_fit = True
    for obj in printed + alternatives:
        bb = bbox_dict(obj.Shape)
        fits = bb["x"] <= P["printer_x"] and bb["y"] <= P["printer_y"] and bb["z"] <= P["printer_z"]
        all_printable_fit = all_printable_fit and fits
        print_parts.append(
            {
                "name": obj.Name,
                "label": obj.Label,
                "bbox_mm": bb,
                "volume_mm3": round(obj.Shape.Volume, 2),
                "pla_mass_estimate_g": round(obj.Shape.Volume * 0.00124, 1),
                "fits_a2l": fits,
                "stl": obj.ExportFile,
            }
        )

    all_shapes = [obj.Shape for obj in printed + hardware]
    assembly_shape = Part.makeCompound(all_shapes)
    assembly_bbox = bbox_dict(assembly_shape)
    envelope_fit = (
        assembly_bbox["x"] <= P["envelope_w"]
        and assembly_bbox["y"] <= P["envelope_d"]
        and assembly_bbox["z"] <= P["envelope_h"]
    )

    collision_pairs = [
        ("TTMotorLeft", "TTMotorRight"),
        ("WheelLeft", "WheelRight"),
        ("Battery2S", "ElectronicsDeck"),
        ("ServoPan", "ServoTilt"),
        ("ServoPan", "ServoMouth"),
        ("ServoTilt", "ServoMouth"),
    ]
    collisions = []
    for a_name, b_name in collision_pairs:
        a = doc.getObject(a_name)
        b = doc.getObject(b_name)
        common_volume = a.Shape.common(b.Shape).Volume
        collisions.append(
            {
                "a": a_name,
                "b": b_name,
                "common_volume_mm3": round(common_volume, 4),
                "pass": common_volume < 0.01,
            }
        )

    estimated_masses = {
        "TTMotorLeft": 45.0,
        "TTMotorRight": 45.0,
        "WheelLeft": 15.0,
        "WheelRight": 15.0,
        "CasterBall": 18.0,
        "Battery2S": 180.0,
        "ServoPan": 9.0,
        "ServoTilt": 9.0,
        "ServoMouth": 9.0,
        "ESP32Placeholder": 25.0,
        "DRV8833Placeholder": 8.0,
        "PowerPlaceholder": 28.0,
        "RadarPlaceholder": 12.0,
        "OLEDPlaceholder": 28.0,
        "HCSR04Placeholder": 9.0,
    }
    weighted = App.Vector(0, 0, 0)
    total_mass = 0.0
    for obj in printed:
        mass = obj.Shape.Volume * 0.00124
        weighted += shape_center_of_mass(obj.Shape) * mass
        total_mass += mass
    for name, mass in estimated_masses.items():
        weighted += shape_center_of_mass(doc.getObject(name).Shape) * mass
        total_mass += mass
    com = weighted / total_mass

    support_proxy = {"xmin": -103.5, "xmax": 103.5, "ymin": -82.0, "ymax": 67.0}
    margin_proxy = min(
        com.x - support_proxy["xmin"],
        support_proxy["xmax"] - com.x,
        com.y - support_proxy["ymin"],
        support_proxy["ymax"] - com.y,
    )

    report = {
        "revision": "v0.2",
        "status": "BOM_COMPATIBLE_PARAMETRIC_PROTOTYPE_NOT_PRINT_FROZEN",
        "freecad_version": App.Version(),
        "parameters_mm": P,
        "dimension_basis": [
            {
                "component": "ESP32-S3 board",
                "design_envelope_mm": [66.0, 32.0, 12.0],
                "basis": "Espressif DevKitC-1 reference is 62.74 mm long and 25.40 mm between outer board edges in the official drawing; organizer photo may be a smaller core-board variant.",
                "mounting_strategy": "two-direction long slots plus zip ties/standoffs",
            },
            {
                "component": "generic yellow TT motor",
                "design_envelope_mm": [70.0, 23.0, 25.0],
                "basis": "BOM gives no vendor or ratio; common TT products are about 69.8-70 mm long and vary around the motor can.",
                "mounting_strategy": "open clamp tray with strap slots; no supplier-specific screw pattern",
            },
            {
                "component": "SG90-format positional servo",
                "design_envelope_mm": [23.0, 12.2, 29.0],
                "basis": "TowerPro published body dimensions; BOM's 360-degree unit is not used for positional head axes.",
                "mounting_strategy": "replaceable servo cassette and mechanical limit",
            },
            {
                "component": "2.42-inch OLED",
                "design_envelope_mm": [66.0, 8.0, 44.0],
                "basis": "Waveshare SSD1309 reference module is 61.5 x 39.5 mm; organizer model remains unknown.",
                "mounting_strategy": "oversize window and slotted retainer",
            },
            {
                "component": "HC-SR04",
                "design_envelope_mm": [48.0, 15.0, 23.0],
                "basis": "published module body is 45 x 20 x 15 mm plus connector clearance.",
                "mounting_strategy": "oversize nose pocket with removable retainer",
            },
            {
                "component": "MP1584EN-labelled buck module",
                "design_envelope_mm": [48.0, 28.0, 16.0],
                "basis": "generic mini boards are often 22 x 17 x 4 mm, but the organizer's reference photo shows a larger terminal-board layout.",
                "mounting_strategy": "large shared power bay with strap slots and airflow",
            },
        ],
        "files": {
            "fcstd": FCSTD_PATH.name,
            "assembly_step": ASSEMBLY_STEP_PATH.name,
            "print_parts_step": PRINT_STEP_PATH.name,
            "stl_directory": STL_DIR.name,
        },
        "assembly_bbox_mm": assembly_bbox,
        "fits_target_envelope": envelope_fit,
        "all_print_parts_fit_a2l": all_printable_fit,
        "print_parts": print_parts,
        "collision_checks": collisions,
        "collision_checks_pass": all(item["pass"] for item in collisions),
        "rough_mass_model": {
            "estimated_total_g": round(total_mass, 1),
            "center_of_mass_mm": {"x": round(com.x, 2), "y": round(com.y, 2), "z": round(com.z, 2)},
            "support_bbox_margin_proxy_mm": round(margin_proxy, 2),
            "warning": "仅用于早期布局；动态稳定性必须用最终重量假负载和实物急停测试确认。",
        },
        "unfrozen": [
            "TT 电机真实减速比、轴心、堵转电流和负载能力",
            "物料表未列车轮；直径、宽度、轮毂配合与是否随电机提供仍需主办方确认",
            "SG90/MG90S 实际型号、孔位、舵盘与扭矩",
            "66号UNO移动电源电池盒不能替代已验证的执行器电源；2S电池、BMS、保险、开关、充电口和接插件仍需自备/确认",
            "物料表未列滚珠万向轮；若无实物则使用18号打印后滑块降级件",
            "ESP32-S3 N16R8的具体开发板版型、USB口方向和实际板宽",
            "60/61号毫米波雷达的真实型号、接口和PCB尺寸",
            "正式头部质量、力臂、嘴部连杆和机械限位",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    doc.save()

    print(json.dumps({
        "fcstd": str(FCSTD_PATH),
        "assembly_step": str(ASSEMBLY_STEP_PATH),
        "stl_count": len(printed) + len(alternatives),
        "assembly_bbox_mm": assembly_bbox,
        "fits_target_envelope": envelope_fit,
        "all_print_parts_fit_a2l": all_printable_fit,
        "collision_checks_pass": report["collision_checks_pass"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"GENERATION_FAILED: {exc}", file=sys.stderr)
        raise
