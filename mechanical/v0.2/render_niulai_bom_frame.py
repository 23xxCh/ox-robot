from __future__ import annotations

import json
import shutil
import struct
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


ROOT = Path(__file__).resolve().parent
PREVIEW_DIR = ROOT / "preview_meshes"

OVERVIEW_OUTPUT = ROOT / "niulai-bom-compatible-overview-v0.2.png"
CHASSIS_OUTPUT = ROOT / "niulai-bom-compatible-chassis-v0.2.png"
HEAD_OUTPUT = ROOT / "niulai-bom-compatible-head-v0.2.png"

# Keep the original links usable, but replace both confusing legacy renders.
LEGACY_OVERVIEW_OUTPUT = ROOT / "niulai-bom-compatible-frame-v0.2.png"
LEGACY_DETAIL_OUTPUT = ROOT / "niulai-bom-compatible-mechanisms-v0.2.png"

# These are FreeCAD document groups exported as compounds. Rendering them together
# with their children caused every solid to be drawn twice in the old preview.
GROUP_OBJECTS = {"PrintedParts", "ShellPanels", "AlternativeParts", "HardwarePlaceholders", "ReservedInterfaces"}

FRAME_COLOR = (0.78, 0.63, 0.26)
COLORS = {
    "ServoPan": (0.08, 0.38, 0.90),
    "ServoTilt": (0.55, 0.20, 0.78),
    "ServoMouth": (0.92, 0.22, 0.12),
    "TTMotorLeft": (0.96, 0.58, 0.05),
    "TTMotorRight": (0.96, 0.58, 0.05),
    "WheelLeft": (0.10, 0.11, 0.13),
    "WheelRight": (0.10, 0.11, 0.13),
    "Battery2S": (0.16, 0.56, 0.25),
    "ESP32Placeholder": (0.04, 0.48, 0.48),
    "DRV8833Placeholder": (0.05, 0.62, 0.58),
    "PowerPlaceholder": (0.94, 0.32, 0.08),
    "RadarPlaceholder": (0.16, 0.42, 0.74),
    "OLEDPlaceholder": (0.05, 0.18, 0.28),
    "HCSR04Placeholder": (0.24, 0.58, 0.74),
    "CasterBall": (0.58, 0.62, 0.68),
    "Insta360ReservedInterface": (0.55, 0.58, 0.64),
    "TorsoFrontPanel": (0.98, 0.72, 0.03),
    "TorsoRearPanel": (0.98, 0.72, 0.03),
    "HunyuanHeadEnvelope": (0.96, 0.78, 0.18),
}

CHASSIS_NAMES = {
    "ChassisBase",
    "MotorMountLeft",
    "MotorMountRight",
    "BatteryTray",
    "ElectronicsDeck",
    "StandoffSet",
    "FrontSkid",
    "CasterBracket",
    "TTMotorLeft",
    "TTMotorRight",
    "WheelLeft",
    "WheelRight",
    "CasterBall",
    "Battery2S",
    "ESP32Placeholder",
    "DRV8833Placeholder",
    "PowerPlaceholder",
    "RadarPlaceholder",
}

HEAD_NAMES = {
    "NeckCrossbeam",
    "PanPlatform",
    "TiltBracket",
    "HeadInterfacePlate",
    "MouthBracket",
    "ServoPan",
    "ServoTilt",
    "ServoMouth",
    "OLEDPlaceholder",
    "HCSR04Placeholder",
}


def read_binary_stl(path: Path) -> np.ndarray:
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"Invalid STL: {path}")
    count = struct.unpack_from("<I", data, 80)[0]
    expected = 84 + count * 50
    if len(data) != expected:
        raise ValueError(f"Only binary STL is supported: {path}")
    record = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("v1", "<f4", (3,)),
            ("v2", "<f4", (3,)),
            ("v3", "<f4", (3,)),
            ("attr", "<u2"),
        ]
    )
    triangles = np.frombuffer(data, dtype=record, count=count, offset=84)
    return np.stack([triangles["v1"], triangles["v2"], triangles["v3"]], axis=1)


def load_meshes() -> dict[str, dict]:
    manifest = json.loads((PREVIEW_DIR / "manifest.json").read_text(encoding="utf-8"))
    meshes: dict[str, dict] = {}
    for item in manifest:
        if item["name"] in GROUP_OBJECTS or item["category"] == "ALTERNATIVE":
            continue
        meshes[item["name"]] = {
            **item,
            "triangles": read_binary_stl(PREVIEW_DIR / item["file"]),
        }
    return meshes


def mesh_color(item: dict) -> tuple[float, float, float]:
    if item["name"] in COLORS:
        return COLORS[item["name"]]
    if item["category"] == "PRINTED":
        return FRAME_COLOR
    return tuple(item["color"])


def add_item(ax, item: dict, translation=(0, 0, 0)) -> None:
    triangles = item["triangles"] + np.asarray(translation, dtype=float)
    color = mesh_color(item)
    if item["category"] == "PRINTED":
        edge = (*tuple(component * 0.62 for component in color), 0.32)
        linewidth = 0.045
    else:
        edge = (*tuple(max(0.0, component * 0.34) for component in color), 0.72)
        linewidth = 0.11
    alpha = 0.34 if item["category"] in {"SHELL", "RESERVED"} else 1.0
    ax.add_collection3d(
        Poly3DCollection(
            triangles,
            facecolor=color,
            edgecolor=edge,
            linewidth=linewidth,
            alpha=alpha,
        )
    )


def add_meshes(ax, meshes: dict[str, dict], names: set[str] | None = None) -> None:
    selected = meshes.values() if names is None else (meshes[name] for name in names)
    for item in selected:
        add_item(ax, item)


def center_of(meshes: dict[str, dict], name: str) -> np.ndarray:
    return meshes[name]["triangles"].reshape(-1, 3).mean(axis=0)


def number_marker(ax, meshes: dict[str, dict], name: str, number: int, offset=(0, 0, 0)) -> None:
    center = center_of(meshes, name) + np.asarray(offset, dtype=float)
    ax.text(
        center[0],
        center[1],
        center[2],
        str(number),
        color="white",
        fontsize=11,
        weight="bold",
        ha="center",
        va="center",
        bbox={"boxstyle": "circle,pad=0.28", "facecolor": "#17202a", "edgecolor": "white", "linewidth": 1.2},
    )


def style_axis(ax, xlim, ylim, zlim, aspect, elev, azim) -> None:
    ax.set_proj_type("ortho")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_zlim(*zlim)
    ax.set_box_aspect(aspect)
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("X 宽度 / mm", labelpad=8)
    ax.set_ylabel("Y 深度 / mm", labelpad=8)
    ax.set_zlabel("Z 高度 / mm", labelpad=7)
    ax.grid(True, color="#d9dde2", linewidth=0.55)
    ax.xaxis.pane.set_facecolor((0.97, 0.98, 0.99, 1.0))
    ax.yaxis.pane.set_facecolor((0.97, 0.98, 0.99, 1.0))
    ax.zaxis.pane.set_facecolor((0.98, 0.98, 0.98, 1.0))


def add_legend(fig, entries, x=0.78, y=0.77) -> None:
    handles = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=color, markeredgecolor="#333333", markersize=11, label=label)
        for label, color in entries
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(x, y), framealpha=0.96, fontsize=10)


def save_overview(meshes: dict[str, dict]) -> None:
    fig = plt.figure(figsize=(14, 10), dpi=140, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    add_meshes(ax, meshes)
    style_axis(ax, (-125, 125), (-105, 95), (0, 315), (1.0, 0.82, 1.22), 22, -57)
    ax.set_title("牛来机器人 P0｜物料表兼容骨架 + 黄色薄壳包络 v0.2", fontsize=18, pad=20, weight="bold")

    number_marker(ax, meshes, "TTMotorLeft", 1, (0, 0, 20))
    number_marker(ax, meshes, "Battery2S", 2, (0, 0, 14))
    number_marker(ax, meshes, "ESP32Placeholder", 3, (0, 0, 16))
    number_marker(ax, meshes, "ServoPan", 4, (0, 0, 12))
    number_marker(ax, meshes, "ServoTilt", 5, (0, 0, 12))
    number_marker(ax, meshes, "ServoMouth", 6, (0, -8, 12))

    fig.text(
        0.78,
        0.70,
        "装配索引\n\n"
        "① 左右 TT 差速驱动\n"
        "② 低位 2S 电池\n"
        "③ ESP32-S3 电子层\n"
        "④ PAN 左右转头\n"
        "⑤ TILT 上下点头\n"
        "⑥ MOUTH 嘴部执行器",
        fontsize=12,
        linespacing=1.65,
        va="top",
        bbox={"boxstyle": "round,pad=0.7", "facecolor": "#f8f5ec", "edgecolor": "#b79a51"},
    )
    add_legend(
        fig,
        [
            ("打印结构件", FRAME_COLOR),
            ("TT 电机", COLORS["TTMotorLeft"]),
            ("舵机", COLORS["ServoPan"]),
            ("电池 / 电路板", COLORS["Battery2S"]),
        ],
        x=0.77,
        y=0.43,
    )
    fig.text(0.5, 0.025, "半透明黄体仅表示1.4 mm前后薄壳包络｜混元牛头尚未导入，模块孔位采用可调接口", ha="center", color="#8b2c1d", fontsize=11, weight="bold")
    fig.subplots_adjust(left=0.01, right=0.78, bottom=0.06, top=0.93)
    fig.savefig(OVERVIEW_OUTPUT, facecolor="white")
    plt.close(fig)


def save_chassis(meshes: dict[str, dict]) -> None:
    fig = plt.figure(figsize=(14, 9), dpi=140, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    exploded_offsets = {
        "TTMotorLeft": (-18, 0, 0),
        "WheelLeft": (-28, 0, 0),
        "TTMotorRight": (18, 0, 0),
        "WheelRight": (28, 0, 0),
        "Battery2S": (0, 28, 10),
        "ESP32Placeholder": (0, 0, 30),
        "DRV8833Placeholder": (0, 0, 30),
        "PowerPlaceholder": (0, 0, 30),
        "CasterBall": (0, 18, 0),
    }
    for name in CHASSIS_NAMES:
        add_item(ax, meshes[name], exploded_offsets.get(name, (0, 0, 0)))
    style_axis(ax, (-142, 142), (-100, 108), (0, 132), (1.25, 0.9, 0.62), 31, -58)
    ax.set_title("兼容底盘爆炸图｜TT卡箍 + 可调电子层 + 电池绑带 + 后轮/滑块接口", fontsize=17, pad=18, weight="bold")

    markers = [
        ("TTMotorLeft", 1, (-18, 0, 14)),
        ("TTMotorRight", 2, (18, 0, 14)),
        ("Battery2S", 3, (0, 28, 21)),
        ("ESP32Placeholder", 4, (0, 0, 43)),
        ("DRV8833Placeholder", 5, (0, 0, 43)),
        ("CasterBall", 6, (0, 18, 11)),
        ("FrontSkid", 7, (0, -3, 8)),
    ]
    for name, number, offset in markers:
        number_marker(ax, meshes, name, number, offset)

    fig.text(
        0.76,
        0.78,
        "部件索引\n\n"
        "① 左 TT 电机 + 左轮\n"
        "② 右 TT 电机 + 右轮\n"
        "③ 低位 2S 电池仓\n"
        "④ ESP32-S3 主控\n"
        "⑤ DRV8833 电机驱动\n"
        "⑥ 后轮/打印滑块接口\n"
        "⑦ 前部防倾支点",
        fontsize=12,
        linespacing=1.65,
        va="top",
        bbox={"boxstyle": "round,pad=0.7", "facecolor": "#f5f8f6", "edgecolor": "#6f9282"},
    )
    fig.text(
        0.76,
        0.31,
        "动力链\nESP32 → DRV8833 → 左/右 TT 电机\n\n"
        "供电链\n2S 电池 → 保险/急停 → 降压与各电源域",
        fontsize=11,
        linespacing=1.5,
        va="top",
        bbox={"boxstyle": "round,pad=0.65", "facecolor": "#fff7eb", "edgecolor": "#cf8a33"},
    )
    fig.text(0.5, 0.025, "底盘显示层爆炸图｜硬件仅为看清安装关系而拉开，不是第二台机器人", ha="center", color="#8b2c1d", fontsize=11, weight="bold")
    fig.subplots_adjust(left=0.01, right=0.76, bottom=0.07, top=0.92)
    fig.savefig(CHASSIS_OUTPUT, facecolor="white")
    plt.close(fig)


def save_head(meshes: dict[str, dict]) -> None:
    fig = plt.figure(figsize=(14, 9), dpi=140, facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    exploded_offsets = {
        "NeckCrossbeam": (0, 0, -5),
        "ServoPan": (0, 0, 0),
        "PanPlatform": (0, 0, 20),
        "TiltBracket": (0, 0, 45),
        "ServoTilt": (-35, 0, 45),
        "HeadInterfacePlate": (0, 0, 75),
        "MouthBracket": (0, -25, 75),
        "ServoMouth": (40, -25, 75),
        "OLEDPlaceholder": (0, -8, 88),
        "HCSR04Placeholder": (0, -8, 70),
    }
    for name in HEAD_NAMES:
        add_item(ax, meshes[name], exploded_offsets[name])
    style_axis(ax, (-118, 108), (-126, -2), (184, 365), (1.08, 0.72, 0.9), 22, -52)
    ax.set_title("头部接口爆炸图｜PAN / TILT / MOUTH + OLED / HC-SR04包络", fontsize=17, pad=18, weight="bold")

    number_marker(ax, meshes, "ServoPan", 1, (14, 0, 2))
    number_marker(ax, meshes, "PanPlatform", 2, (30, 20, 28))
    number_marker(ax, meshes, "TiltBracket", 3, (40, 15, 58))
    number_marker(ax, meshes, "ServoTilt", 4, (-45, 0, 53))
    number_marker(ax, meshes, "HeadInterfacePlate", 5, (20, 10, 85))
    number_marker(ax, meshes, "ServoMouth", 6, (55, -30, 63))

    # Motion axes and dashed guides are display-only annotations.
    ax.plot([0, 0], [-46, -46], [195, 352], color="#5f6770", linestyle="--", linewidth=1.5)
    ax.quiver(0, -46, 194, 0, 0, 72, color=COLORS["ServoPan"], linewidth=3.0, arrow_length_ratio=0.10)
    ax.text(4, -44, 267, "PAN Z轴", color="#0a4fae", fontsize=11, weight="bold")
    ax.quiver(-112, -46.5, 308, 176, 0, 0, color=COLORS["ServoTilt"], linewidth=3.0, arrow_length_ratio=0.07)
    ax.text(18, -44, 312, "TILT X轴", color="#6d2993", fontsize=11, weight="bold")
    ax.plot([-82, -47], [-46.5, -46.5], [308, 308], color="#6d2993", linestyle="--", linewidth=1.6)
    ax.quiver(40, -95, 314, 0, 0, 46, color=COLORS["ServoMouth"], linewidth=2.7, arrow_length_ratio=0.13)
    ax.text(44, -96, 360, "MOUTH舵盘轴", color="#b52619", fontsize=10, weight="bold")
    ax.plot([40, 0], [-95, -111], [349, 349], color="#b52619", linestyle="--", linewidth=1.6)
    ax.text(-2, -104, 238, "① PAN", color="white", fontsize=10, weight="bold", bbox={"boxstyle": "round,pad=0.28", "facecolor": "#0a4fae", "edgecolor": "white"})
    ax.text(-106, -100, 350, "④ TILT", color="white", fontsize=10, weight="bold", bbox={"boxstyle": "round,pad=0.28", "facecolor": "#6d2993", "edgecolor": "white"})
    ax.text(62, -98, 310, "③ U型架", color="white", fontsize=10, weight="bold", bbox={"boxstyle": "round,pad=0.28", "facecolor": "#8d6e1e", "edgecolor": "white"})
    ax.text(25, -104, 326, "⑥ MOUTH", color="white", fontsize=10, weight="bold", bbox={"boxstyle": "round,pad=0.28", "facecolor": "#b52619", "edgecolor": "white"})

    fig.text(
        0.75,
        0.80,
        "结构链（自下而上）\n\n"
        "① PAN 定位舵机\n"
        "② 头部旋转平台\n"
        "③ TILT U 型承力架\n"
        "④ TILT 定位舵机\n"
        "⑤ 头部 / 牛头接口板\n"
        "⑥ MOUTH 舵机与支架",
        fontsize=12,
        linespacing=1.65,
        va="top",
        bbox={"boxstyle": "round,pad=0.7", "facecolor": "#f6f3fb", "edgecolor": "#8061a8"},
    )
    fig.text(
        0.75,
        0.34,
        "运动方向\n"
        "蓝：左右转头（Z 轴）\n"
        "紫：上下点头（X 轴）\n"
        "红：嘴部舵盘；连杆尚未冻结\n\n"
        "注意：三颗必须是 180°定位舵机，\n"
        "不能使用 360°连续旋转 SG90。",
        fontsize=11,
        linespacing=1.5,
        va="top",
        bbox={"boxstyle": "round,pad=0.65", "facecolor": "#fff6f2", "edgecolor": "#cf685b"},
    )
    fig.text(0.5, 0.025, "头部显示层爆炸图｜零件仅为看清结构而拉开；虚线和箭头不是实体零件", ha="center", color="#8b2c1d", fontsize=11, weight="bold")
    fig.subplots_adjust(left=0.01, right=0.75, bottom=0.07, top=0.92)
    fig.savefig(HEAD_OUTPUT, facecolor="white")
    plt.close(fig)


def main() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    meshes = load_meshes()
    save_overview(meshes)
    save_chassis(meshes)
    save_head(meshes)

    shutil.copyfile(OVERVIEW_OUTPUT, LEGACY_OVERVIEW_OUTPUT)
    shutil.copyfile(HEAD_OUTPUT, LEGACY_DETAIL_OUTPUT)

    for path in (OVERVIEW_OUTPUT, CHASSIS_OUTPUT, HEAD_OUTPUT, LEGACY_OVERVIEW_OUTPUT, LEGACY_DETAIL_OUTPUT):
        print(path)


if __name__ == "__main__":
    main()
