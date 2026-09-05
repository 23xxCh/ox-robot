from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parent
FRAME_STL_DIR = ROOT.parent / "v0.3" / "stl"
SHELL_STL_DIR = ROOT / "stl"
REPORT_PATH = ROOT / "body-mount-clearance-report-v0.5.json"

BODY_MOUNT_POINTS = [(-50.0, -40.0), (50.0, -40.0), (-45.0, 40.0), (45.0, 40.0)]
INTERFACE_GATE_MM = 1.5
# The v0.4 shell was voxelized at 0.6 mm.  Nearest-vertex distance is a slight
# over-estimate of true point-to-triangle distance, so subtract 0.8 mm and gate
# the conservative value rather than reporting false precision.
MESH_SURFACE_ALLOWANCE_MM = 0.8


def read_binary_stl_vertices(path: Path) -> np.ndarray:
    with path.open("rb") as handle:
        handle.seek(80)
        triangle_count = struct.unpack("<I", handle.read(4))[0]
    expected_size = 84 + triangle_count * 50
    if path.stat().st_size != expected_size:
        raise ValueError(f"only binary STL is supported: {path}")
    dtype = np.dtype(
        [
            ("normal", "<f4", (3,)),
            ("vertices", "<f4", (3, 3)),
            ("attribute", "<u2"),
        ]
    )
    triangles = np.memmap(path, dtype=dtype, mode="r", offset=84, shape=(triangle_count,))
    return np.asarray(triangles["vertices"].reshape(-1, 3))


def cylinder_surface_points(
    center_x: float,
    center_y: float,
    radius: float,
    z_min: float,
    z_max: float,
    angular_samples: int = 180,
    height_samples: int = 24,
) -> np.ndarray:
    angles = np.linspace(0.0, 2.0 * np.pi, angular_samples, endpoint=False)
    heights = np.linspace(z_min, z_max, height_samples)
    aa, zz = np.meshgrid(angles, heights)
    return np.column_stack(
        [
            center_x + radius * np.cos(aa).ravel(),
            center_y + radius * np.sin(aa).ravel(),
            zz.ravel(),
        ]
    )


def bounds(vertices: np.ndarray) -> dict[str, list[float]]:
    minimum = vertices.min(axis=0)
    maximum = vertices.max(axis=0)
    return {
        "min_mm": [round(float(value), 3) for value in minimum],
        "max_mm": [round(float(value), 3) for value in maximum],
        "dimensions_mm": [round(float(value), 3) for value in maximum - minimum],
    }


shell_vertices = np.concatenate(
    [
        read_binary_stl_vertices(SHELL_STL_DIR / "05_body_front_shell.stl"),
        read_binary_stl_vertices(SHELL_STL_DIR / "06_body_rear_shell.stl"),
    ],
    axis=0,
)
shell_tree = cKDTree(shell_vertices)

pad_vertices = read_binary_stl_vertices(FRAME_STL_DIR / "17_body_mount_pads.stl")
tower_surfaces = []
for x, y in BODY_MOUNT_POINTS:
    tower_surfaces.extend(
        [
            cylinder_surface_points(x, y, 7.0, 46.0, 49.0),
            cylinder_surface_points(x, y, 5.0, 49.0, 72.0),
            cylinder_surface_points(x, y, 4.0, 72.0, 74.0),
        ]
    )
tower_vertices = np.concatenate(tower_surfaces, axis=0)


def clearance_result(name: str, vertices: np.ndarray) -> dict[str, object]:
    distances, indices = shell_tree.query(vertices, k=1, workers=-1)
    index = int(np.argmin(distances))
    raw_distance = float(distances[index])
    conservative_distance = max(0.0, raw_distance - MESH_SURFACE_ALLOWANCE_MM)
    return {
        "name": name,
        "nearest_vertex_distance_mm": round(raw_distance, 3),
        "mesh_surface_allowance_mm": MESH_SURFACE_ALLOWANCE_MM,
        "conservative_clearance_mm": round(conservative_distance, 3),
        "target_mm": INTERFACE_GATE_MM,
        "margin_to_target_mm": round(conservative_distance - INTERFACE_GATE_MM, 3),
        "nearest_mount_point_mm": [round(float(value), 3) for value in vertices[index]],
        "nearest_shell_vertex_mm": [
            round(float(value), 3) for value in shell_vertices[int(indices[index])]
        ],
        "status": "PASS" if conservative_distance >= INTERFACE_GATE_MM else "FAIL",
    }


checks = [
    clearance_result("BodyMountPads", pad_vertices),
    clearance_result("BodyMountTowers", tower_vertices),
]

shell_band = shell_vertices[(shell_vertices[:, 2] >= 71.5) & (shell_vertices[:, 2] <= 80.5)]
report = {
    "method": "binary STL nearest-vertex check with conservative voxel allowance",
    "interface_gate_mm": INTERFACE_GATE_MM,
    "shell_mesh_surface_allowance_mm": MESH_SURFACE_ALLOWANCE_MM,
    "body_shell_band_71_5_to_80_5_mm": bounds(shell_band),
    "body_mount_pad_bounds": bounds(pad_vertices),
    "mount_points_xy_mm": BODY_MOUNT_POINTS,
    "failed_count": sum(item["status"] == "FAIL" for item in checks),
    "checks": checks,
    "warning": "This verifies nominal CAD mesh clearance. Print the heat-set coupon and dry-fit the four pads on the chassis jig before epoxy putty because the actual insert, shell warp and slicer shrinkage are not yet measured.",
}
REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
