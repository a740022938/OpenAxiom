from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.dataset_manager import detect_dataset


class YOLOAdapter:
    name = "YOLO"

    def detect(self, path: str | Path) -> Dict[str, Any]:
        info = detect_dataset(path)
        return {
            "project_root": str(info.project_root),
            "dataset_root": str(info.dataset_root),
            "image_root": str(info.image_root),
            "label_root": str(info.label_root),
            "class_names": info.class_names,
            "model_path": str(info.model_path) if info.model_path else "",
        }
