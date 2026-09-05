"""File-level verification for the NiuLai open-frame v0.1 deliverables."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parent


def verify_binary_stl(path: Path) -> int:
    data = path.read_bytes()
    if len(data) < 84:
        raise AssertionError(f"STL too short: {path.name}")
    triangle_count = struct.unpack("<I", data[80:84])[0]
    expected_length = 84 + triangle_count * 50
    if len(data) != expected_length:
        raise AssertionError(
            f"STL length mismatch: {path.name}, "
            f"expected {expected_length}, got {len(data)}"
        )
    if triangle_count == 0:
        raise AssertionError(f"STL has no triangles: {path.name}")
    return triangle_count


def verify_preview(path: Path) -> tuple[int, int, float]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path).convert("RGB") as image:
        width, height = image.size
        if width < 800 or height < 600:
            raise AssertionError(f"Preview resolution too small: {path.name}")
        grayscale = image.convert("L")
        spread = ImageStat.Stat(grayscale).extrema[0]
        if spread[1] - spread[0] < 20:
            raise AssertionError(f"Preview appears blank: {path.name}")
        mean = ImageStat.Stat(grayscale).mean[0]
    return width, height, round(mean, 2)


def main() -> None:
    required_files = [
        ROOT / "niulai-open-frame-v0.1.FCStd",
        ROOT / "niulai-open-frame-assembly-v0.1.step",
        ROOT / "niulai-open-frame-print-parts-v0.1.step",
        ROOT / "validation-report-v0.1.json",
        ROOT / "niulai-open-frame-overview-v0.1.png",
        ROOT / "niulai-open-frame-chassis-v0.1.png",
        ROOT / "niulai-open-frame-head-mechanism-v0.1.png",
        ROOT / "niulai-open-frame-v0.1.png",
        ROOT / "niulai-open-frame-mechanisms-v0.1.png",
    ]
    missing = [path.name for path in required_files if not path.is_file()]
    if missing:
        raise AssertionError(f"Missing deliverables: {missing}")

    report = json.loads((ROOT / "validation-report-v0.1.json").read_text("utf-8"))
    if not report["fits_target_envelope"]:
        raise AssertionError("Assembly exceeds the target envelope")
    if not report["all_print_parts_fit_a2l"]:
        raise AssertionError("At least one print part exceeds the A2L envelope")
    failed_collisions = [
        f"{result['a']} / {result['b']}"
        for result in report["collision_checks"]
        if not result["pass"]
    ]
    if failed_collisions:
        raise AssertionError(f"Collision gates failed: {failed_collisions}")

    stl_paths = sorted((ROOT / "stl").glob("*.stl"))
    if len(stl_paths) != 15:
        raise AssertionError(f"Expected 15 STL files, found {len(stl_paths)}")
    triangle_counts = {path.name: verify_binary_stl(path) for path in stl_paths}

    previews = {
        path.name: verify_preview(path)
        for path in required_files
        if path.suffix.lower() == ".png"
    }

    print(
        json.dumps(
            {
                "required_files": len(required_files),
                "stl_files": len(stl_paths),
                "stl_triangles_total": sum(triangle_counts.values()),
                "previews": previews,
                "assembly_bbox_mm": report["assembly_bbox_mm"],
                "collision_gates": len(report["collision_checks"]),
                "status": "PASS",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
