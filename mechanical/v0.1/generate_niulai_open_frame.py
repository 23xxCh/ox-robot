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
FCSTD_PATH = ROOT / "niulai-open-frame-v0.1.FCStd"
ASSEMBLY_STEP_PATH = ROOT / "niulai-open-frame-assembly-v0.1.step"
PRINT_STEP_PATH = ROOT / "niulai-open-frame-print-parts-v0.1.step"
REPORT_PATH = ROOT / "validation-report-v0.1.json"


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
    "tt_length": 68.0,
    "tt_width": 23.0,
    "tt_height": 18.0,
    "wheel_radius": 32.0,
    "wheel_width": 12.0,
    "sg90_length": 23.0,
    "sg90_width": 12.2,
    "sg90_height": 29.0,
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
    obj.Revision = "v0.1"
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
    return cut_vertical_holes(shape, mounting_points, P["m3_clearance"], z - 1, P["chassis_t"] + 2)


def make_motor_mount(side: str) -> Part.Shape:
    if side == "left":
        x0 = -90.0
        inner_x = -63.0
    else:
        x0 = 60.0
        inner_x = 60.0
    base = box(30, 76, 3, x0, -38, 20)
    inner_wall = box(3, 76, 24, inner_x, -38, 20)
    front_stop = box(30, 3, 18, x0, -38, 20)
    rear_stop = box(30, 3, 18, x0, 35, 20)
    mount = fused(base, inner_wall, front_stop, rear_stop)
    slots = [(-4, -27), (-4, 27)] if side == "left" else [(4, -27), (4, 27)]
    for x_offset, y in slots:
        x = inner_x + x_offset
        hole = Part.makeCylinder(1.7, 8, App.Vector(x, y, 37), App.Vector(1, 0, 0))
        mount = mount.cut(hole)
    return mount.removeSplitter()


def make_battery_tray() -> Part.Shape:
    base = box(86, 50, 3, -43, 18, 46)
    left = box(3, 50, 12, -43, 18, 49)
    right = box(3, 50, 12, 40, 18, 49)
    front = box(80, 3, 12, -40, 18, 49)
    rear = box(80, 3, 12, -40, 65, 49)
    return fused(base, left, right, front, rear)


def make_electronics_deck() -> Part.Shape:
    deck = box(130, 90, 3, -65, -50, 78)
    points = [(-55, -40), (55, -40), (-55, 30), (55, 30), (-25, -20), (25, -20)]
    return cut_vertical_holes(deck, points, P["m3_clearance"], 77, 5)


def make_standoffs() -> Part.Shape:
    shapes = []
    for x, y in [(-55, -40), (55, -40), (-55, 30), (55, 30)]:
        outer = Part.makeCylinder(4.0, 32.0, App.Vector(x, y, 46))
        inner = Part.makeCylinder(1.7, 32.0, App.Vector(x, y, 46))
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
    return fused(top, left, right)


def make_tt_motor(side: str) -> Part.Shape:
    x0 = -88 if side == "left" else 65
    body = box(23, 68, 18, x0, -34, 23)
    if side == "left":
        axle = Part.makeCylinder(3, 18, App.Vector(-106, 0, 32), App.Vector(1, 0, 0))
    else:
        axle = Part.makeCylinder(3, 18, App.Vector(88, 0, 32), App.Vector(1, 0, 0))
    return fused(body, axle)


def make_wheel(side: str) -> Part.Shape:
    x = -103 if side == "left" else 91
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
    return box(76, 40, 20, -38, 23, 49)


def make_pcb_placeholder(dx: float, dy: float, x: float, y: float) -> Part.Shape:
    return box(dx, dy, 8, x, y, 81)


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
    doc = App.newDocument("NiulaiOpenFrameV01")
    printed_group = doc.addObject("App::DocumentObjectGroup", "PrintedParts")
    printed_group.Label = "01 可打印工程骨架"
    hardware_group = doc.addObject("App::DocumentObjectGroup", "HardwarePlaceholders")
    hardware_group.Label = "02 硬件占位模型（到货后复测）"
    reserved_group = doc.addObject("App::DocumentObjectGroup", "ReservedInterfaces")
    reserved_group.Label = "03 外壳与未来接口"

    printed_specs = [
        ("ChassisBase", "底盘主板", make_chassis(), "01_chassis_base.stl", "承力主板；M3 通孔为初版通用孔位"),
        ("MotorMountLeft", "左 TT 电机座", make_motor_mount("left"), "02_motor_mount_left.stl", "标准 TT 占位，实物到货后复测壳体与轴心"),
        ("MotorMountRight", "右 TT 电机座", make_motor_mount("right"), "03_motor_mount_right.stl", "标准 TT 占位，实物到货后复测壳体与轴心"),
        ("BatteryTray", "下置电池仓", make_battery_tray(), "04_battery_tray.stl", "2S 电池占位；正式电池/BMS/接插件未冻结"),
        ("ElectronicsDeck", "电子模块层板", make_electronics_deck(), "05_electronics_deck.stl", "ESP32、驱动、电源与音频模块安装层"),
        ("StandoffSet", "电子层 M3 隔柱组", make_standoffs(), "06_standoff_set.stl", "建议实物优先使用金属 M3 隔柱"),
        ("NeckColumnLeft", "左颈部立柱", make_neck_column("left"), "07_neck_column_left.stl", "开架样机承力立柱，外壳不承力"),
        ("NeckColumnRight", "右颈部立柱", make_neck_column("right"), "08_neck_column_right.stl", "开架样机承力立柱，外壳不承力"),
        ("NeckCrossbeam", "颈部横梁及 PAN 座", make_neck_crossbeam(), "09_neck_crossbeam.stl", "安装 PAN 舵机；孔位为 SG90 名义尺寸"),
        ("PanPlatform", "头部旋转平台", make_pan_platform(), "10_pan_platform.stl", "由 PAN 舵机驱动，需设置软件与机械限位"),
        ("TiltBracket", "头部 TILT U 型架", make_tilt_bracket(), "11_tilt_bracket.stl", "头部俯仰；轴孔和舵机孔待实测"),
        ("HeadInterfacePlate", "头部外壳接口板", make_head_interface_plate(), "12_head_interface_plate.stl", "未来连接牛头外观网格，不依赖网格承力"),
        ("MouthBracket", "嘴部舵机与摇杆架", make_mouth_bracket(), "13_mouth_bracket.stl", "MOUTH 开合机构；连杆长度待牛嘴模型冻结"),
        ("FrontSkid", "前部防倾支点", make_front_skid(), "14_front_anti_tip_skid.stl", "防止急停前倾；离地间隙需实测"),
        ("CasterBracket", "后滚珠万向轮支架", make_caster_bracket(), "15_rear_caster_bracket.stl", "滚珠万向轮具体孔距待实物确认"),
    ]

    printed = []
    for name, label, shape, filename, notes in printed_specs:
        obj = add_feature(doc, printed_group, name, label, shape, "PRINTED", COLORS["print"], notes)
        obj.addProperty("App::PropertyString", "ExportFile", "Niulai")
        obj.ExportFile = filename
        printed.append(obj)

    hardware_specs = [
        ("TTMotorLeft", "左 TT 电机占位", make_tt_motor("left"), COLORS["motor"], "70×23×18 mm 名义包络；到货后复测"),
        ("TTMotorRight", "右 TT 电机占位", make_tt_motor("right"), COLORS["motor"], "70×23×18 mm 名义包络；到货后复测"),
        ("WheelLeft", "左轮占位", make_wheel("left"), COLORS["wheel"], "直径 64 mm、宽 12 mm 名义尺寸"),
        ("WheelRight", "右轮占位", make_wheel("right"), COLORS["wheel"], "直径 64 mm、宽 12 mm 名义尺寸"),
        ("CasterBall", "后滚珠万向轮占位", make_caster_ball(), COLORS["metal"], "24 mm 滚珠占位；孔距待实物确认"),
        ("Battery2S", "2S 电池包占位", make_battery_placeholder(), COLORS["battery"], "76×40×20 mm 占位；必须带保护/BMS"),
        ("ServoPan", "SG90-180 PAN 舵机占位", make_sg90("pan"), COLORS["servo"], "23×12.2×29 mm；禁止用 360°连续旋转舵机"),
        ("ServoTilt", "SG90-180 TILT 舵机占位", make_sg90("tilt"), COLORS["servo"], "23×12.2×29 mm；扭矩需按头部质量复核"),
        ("ServoMouth", "SG90-180 MOUTH 舵机占位", make_sg90("mouth"), COLORS["servo"], "23×12.2×29 mm；嘴部连杆待冻结"),
        ("ESP32Placeholder", "ESP32-S3 占位", make_pcb_placeholder(55, 30, -55, -42), COLORS["pcb"], "单套主控，不重复堆料"),
        ("DRV8833Placeholder", "DRV8833 占位", make_pcb_placeholder(28, 22, 10, -40), COLORS["pcb"], "靠近电机线束，保留散热与插拔空间"),
        ("PowerPlaceholder", "降压与保险占位", make_pcb_placeholder(38, 25, 20, 2), COLORS["warning"], "逻辑/舵机/电机分域供电，公共地"),
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

    doc.recompute()
    doc.saveAs(str(FCSTD_PATH))

    for obj, spec in zip(printed, printed_specs):
        export_stl(obj, spec[3])

    Part.export(printed, str(PRINT_STEP_PATH))
    Part.export(printed + hardware, str(ASSEMBLY_STEP_PATH))

    print_parts = []
    all_printable_fit = True
    for obj in printed:
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
        "TTMotorLeft": 30.0,
        "TTMotorRight": 30.0,
        "WheelLeft": 15.0,
        "WheelRight": 15.0,
        "CasterBall": 18.0,
        "Battery2S": 110.0,
        "ServoPan": 9.0,
        "ServoTilt": 9.0,
        "ServoMouth": 9.0,
        "ESP32Placeholder": 18.0,
        "DRV8833Placeholder": 8.0,
        "PowerPlaceholder": 20.0,
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

    support_proxy = {"xmin": -103.0, "xmax": 103.0, "ymin": -82.0, "ymax": 67.0}
    margin_proxy = min(
        com.x - support_proxy["xmin"],
        support_proxy["xmax"] - com.x,
        com.y - support_proxy["ymin"],
        support_proxy["ymax"] - com.y,
    )

    report = {
        "revision": "v0.1",
        "status": "PARAMETRIC_PLACEHOLDER_NOT_BUILD_RELEASE",
        "freecad_version": App.Version(),
        "parameters_mm": P,
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
            "TT 电机真实包络、轴心、安装孔和堵转电流",
            "车轮直径、宽度和轮毂配合",
            "SG90/MG90S 实际型号、孔位、舵盘与扭矩",
            "2S 电池、BMS、保险、开关、充电口和接插件",
            "滚珠万向轮孔距与工作高度",
            "正式头部质量、力臂、嘴部连杆和机械限位",
        ],
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    doc.save()

    print(json.dumps({
        "fcstd": str(FCSTD_PATH),
        "assembly_step": str(ASSEMBLY_STEP_PATH),
        "stl_count": len(printed),
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
