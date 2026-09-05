from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App
import Mesh


ROOT = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
FRAME_DIR = ROOT.parent / "v0.3"
FRAME_REPORT = json.loads((FRAME_DIR / "frame-validation-report-v0.3.json").read_text(encoding="utf-8"))
MOUNT_REPORT = json.loads((ROOT / "body-mount-clearance-report-v0.5.json").read_text(encoding="utf-8"))
CRITICAL_REPORT = json.loads((ROOT / "clearance-report-v0.5.json").read_text(encoding="utf-8"))
SHELL_REPORT = json.loads((ROOT / "validation-report-v0.4.json").read_text(encoding="utf-8"))

assert FRAME_REPORT["fits_target_envelope"] is True
assert FRAME_REPORT["all_print_parts_fit_a2l"] is True
assert FRAME_REPORT["collision_checks_pass"] is True
assert not [item for item in FRAME_REPORT["body_mount_internal_checks"] if not item["pass"]]
assert MOUNT_REPORT["failed_count"] == 0
assert CRITICAL_REPORT["failed_count"] == 0
assert len(CRITICAL_REPORT["parts"]) == 18
assert SHELL_REPORT["target_width_mm"] == 220
assert SHELL_REPORT["target_depth_mm"] == 200
assert SHELL_REPORT["target_height_mm"] == 330
printer_sorted = sorted([330.0, 320.0, 325.0])
for shell_part in SHELL_REPORT["parts"].values():
    assert shell_part["boundary_edges"] == 0
    assert shell_part["non_manifold_edges"] == 0
    assert all(
        part_edge <= printer_edge
        for part_edge, printer_edge in zip(sorted(shell_part["dimensions_mm"]), printer_sorted)
    )

doc = App.openDocument(str(FRAME_DIR / "niulai-shell-interface-frame-v0.3.FCStd"))
required_objects = {
    "ChassisBase",
    "BatteryTray",
    "BodyMountPads",
    "M3HeatsetCoupon",
}
missing_objects = sorted(name for name in required_objects if doc.getObject(name) is None)
assert not missing_objects, missing_objects
invalid_objects = []
for name in required_objects:
    shape = doc.getObject(name).Shape
    if shape.isNull() or not shape.isValid():
        invalid_objects.append(name)
assert not invalid_objects, invalid_objects

stl_results = []
for item in FRAME_REPORT["print_parts"]:
    path = FRAME_DIR / "stl" / item["stl"]
    assert path.exists() and path.stat().st_size > 84, path
    mesh = Mesh.Mesh(str(path))
    assert mesh.CountFacets > 0, path
    stl_results.append({"file": path.name, "facets": mesh.CountFacets, "bytes": path.stat().st_size})

assert len(stl_results) == 19
assert not (FRAME_DIR / "stl" / "17_body_mount_collar.stl").exists()
assert not list((FRAME_DIR / "preview_meshes_v0.3").glob("*BodyMountCollar*.stl"))

summary = {
    "status": "PASS",
    "external_target_mm": [220, 200, 330],
    "assembly_bbox_mm": FRAME_REPORT["assembly_bbox_mm"],
    "critical_internal_bbox_mm": [114.0, 105.0, 289.0],
    "printable_stl_count": len(stl_results),
    "freecad_required_shapes_valid": True,
    "all_print_parts_fit_a2l": True,
    "all_five_shell_parts_fit_a2l_and_are_manifold": True,
    "freecad_collision_failures": 0,
    "critical_clearance_failures": CRITICAL_REPORT["failed_count"],
    "body_mount_clearance_failures": MOUNT_REPORT["failed_count"],
    "body_mount_pad_conservative_clearance_mm": MOUNT_REPORT["checks"][0]["conservative_clearance_mm"],
    "body_mount_tower_conservative_clearance_mm": MOUNT_REPORT["checks"][1]["conservative_clearance_mm"],
    "m3_heatset_coupon": "19_m3_heatset_coupon.stl",
}
(ROOT / "artifact-verification-report-v0.5.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
App.closeDocument(doc.Name)
print(json.dumps(summary, ensure_ascii=False, indent=2))
