from __future__ import annotations

from pathlib import Path
from typing import List


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_images(image_root: str | Path) -> List[str]:
    root = Path(image_root)
    if not root.exists():
        raise FileNotFoundError(f"Image root not found: {root}")

    images = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            rel = p.relative_to(root).as_posix()
            images.append(rel)

    # Keep train/val/test order, then alphabetic.
    order = {"train": 0, "val": 1, "valid": 1, "test": 2}
    def sort_key(rel: str):
        first = rel.split("/", 1)[0].lower() if "/" in rel else ""
        return (order.get(first, 9), rel.lower())

    return sorted(images, key=sort_key)


def absolute_image_path(image_root: str | Path, image_rel: str) -> Path:
    return Path(image_root) / Path(image_rel)
