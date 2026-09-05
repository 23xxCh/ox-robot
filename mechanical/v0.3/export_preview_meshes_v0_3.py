from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App
import Mesh


root = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
preview_dir = root / "preview_meshes_v0.3"
preview_dir.mkdir(parents=True, exist_ok=True)
for stale_mesh in preview_dir.glob("*.stl"):
    stale_mesh.unlink()
doc = App.openDocument(str(root / "niulai-shell-interface-frame-v0.3.FCStd"))

manifest = []
index = 1
for obj in doc.Objects:
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        continue
    filename = f"{index:02d}_{obj.Name}.stl"
    Mesh.export([obj], str(preview_dir / filename))
    color = getattr(obj, "DisplayColor", "0.65,0.65,0.65")
    manifest.append(
        {
            "name": obj.Name,
            "label": obj.Label,
            "category": getattr(obj, "Category", "UNKNOWN"),
            "color": [float(value) for value in color.split(",")],
            "file": filename,
        }
    )
    index += 1

(preview_dir / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
App.closeDocument(doc.Name)
print(json.dumps({"preview_meshes": len(manifest), "directory": str(preview_dir)}, ensure_ascii=False))
