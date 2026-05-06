from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from core.context import Box


def label_path_for_image(label_root: str | Path, image_rel: str) -> Path:
    """
    Correct YOLO mapping:
      image_root/train/foo.png -> label_root/train/foo.txt
      image_root/val/foo.jpg   -> label_root/val/foo.txt
      image_root/test/foo.jpg  -> label_root/test/foo.txt
    """
    rel = Path(image_rel)
    return Path(label_root) / rel.with_suffix(".txt")


def load_labels(label_root: str | Path, image_rel: str, class_names: List[str]) -> List[Box]:
    label_path = label_path_for_image(label_root, image_rel)
    if not label_path.exists():
        return []

    boxes: List[Box] = []
    with label_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            box = Box.from_yolo_line(line, class_names)
            if box is not None:
                boxes.append(box)

    return boxes


def save_labels(label_root: str | Path, image_rel: str, boxes: List[Box]) -> Path:
    label_path = label_path_for_image(label_root, image_rel)
    label_path.parent.mkdir(parents=True, exist_ok=True)

    with label_path.open("w", encoding="utf-8") as f:
        for box in boxes:
            f.write(box.to_yolo_line() + "\n")

    return label_path
