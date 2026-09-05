from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


ROOT = Path(__file__).resolve().parent
SHELL_STL_DIR = ROOT / "stl"
REPORT_PATH = ROOT / "body-mount-point-scan-v0.5.json"


def read_binary_stl_vertices(path: Path) -> np.ndarray:
    with path.open("rb") as handle:
        handle.seek(80)
        triangle_count = struct.unpack("<I", handle.read(4))[0]
    dtype = np.dtype(
        [("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]
    )
    triangles = np.memmap(path, dtype=dtype, mode="r", offset=84, shape=(triangle_count,))
    return np.asarray(triangles["vertices"].reshape(-1, 3))


def post_surface_points(x: float, y: float, radius: float = 7.0) -> np.ndarray:
    angles = np.linspace(0.0, 2.0 * np.pi, 72, endpoint=False)
    heights = np.linspace(46.0, 80.0, 18)
    aa, zz = np.meshgrid(angles, heights)
    return np.column_stack(
        [
            x + radius * np.cos(aa).ravel(),
            y + radius * np.sin(aa).ravel(),
            zz.ravel(),
        ]
    )


shell_vertices = np.concatenate(
    [
        read_binary_stl_vertices(SHELL_STL_DIR / "05_body_front_shell.stl"),
        read_binary_stl_vertices(SHELL_STL_DIR / "06_body_rear_shell.stl"),
    ],
    axis=0,
)
tree = cKDTree(shell_vertices)

candidates = []
for x in np.arange(25.0, 56.0, 5.0):
    for zone, ys in [
        ("front", np.arange(-55.0, -24.0, 5.0)),
        ("rear", np.arange(40.0, 66.0, 5.0)),
    ]:
        for y in ys:
            side_results = []
            for signed_x in (-x, x):
                samples = post_surface_points(float(signed_x), float(y))
                distances, indices = tree.query(samples, k=1, workers=-1)
                nearest_index = int(np.argmin(distances))
                side_results.append(
                    {
                        "x_mm": float(signed_x),
                        "raw_min_vertex_distance_mm": round(float(distances[nearest_index]), 3),
                        "nearest_post_point_mm": [
                            round(float(value), 3) for value in samples[nearest_index]
                        ],
                        "nearest_shell_vertex_mm": [
                            round(float(value), 3) for value in shell_vertices[int(indices[nearest_index])]
                        ],
                    }
                )
            pair_minimum = min(item["raw_min_vertex_distance_mm"] for item in side_results)
            candidates.append(
                {
                    "zone": zone,
                    "abs_x_mm": float(x),
                    "y_mm": float(y),
                    "symmetric_pair_raw_min_mm": pair_minimum,
                    "sides": side_results,
                }
            )

# Prefer a 3-8 mm raw nearest-vertex gap: enough for a conservative 1.5 mm
# anti-rub margin after subtracting the 0.8 mm mesh allowance, yet close enough
# for a practical epoxy fillet or a short custom saddle.
viable = [item for item in candidates if 3.0 <= item["symmetric_pair_raw_min_mm"] <= 8.0]
viable.sort(key=lambda item: abs(item["symmetric_pair_raw_min_mm"] - 5.0))
report = {
    "method": "symmetric 14 mm diameter post scan, z=46..80 mm",
    "preferred_raw_gap_mm": [3.0, 8.0],
    "candidate_count": len(candidates),
    "viable_count": len(viable),
    "recommended_candidates": viable[:20],
    "all_candidates": sorted(
        candidates,
        key=lambda item: item["symmetric_pair_raw_min_mm"],
        reverse=True,
    ),
}
REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "all_candidates"}, ensure_ascii=False, indent=2))
