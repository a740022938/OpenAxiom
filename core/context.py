from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class Box:
    class_id: int
    cx: float
    cy: float
    w: float
    h: float
    class_name: str = ""

    @classmethod
    def from_yolo_line(cls, line: str, class_names: List[str]) -> Optional["Box"]:
        parts = line.strip().split()
        if len(parts) < 5:
            return None

        try:
            class_id = int(float(parts[0]))
            cx = float(parts[1])
            cy = float(parts[2])
            w = float(parts[3])
            h = float(parts[4])
        except ValueError:
            return None

        class_name = class_names[class_id] if 0 <= class_id < len(class_names) else f"class_{class_id}"
        return cls(class_id=class_id, cx=cx, cy=cy, w=w, h=h, class_name=class_name)

    def to_yolo_line(self) -> str:
        return f"{self.class_id} {self.cx:.6f} {self.cy:.6f} {self.w:.6f} {self.h:.6f}"


@dataclass
class DatasetInfo:
    project_root: Path
    dataset_root: Path
    yaml_path: Optional[Path]
    image_root: Path
    label_root: Path
    class_names: List[str] = field(default_factory=list)
    model_path: Optional[Path] = None
    training_outputs: Optional[Path] = None
    source_selected_path: Optional[Path] = None


@dataclass
class WorkbenchContext:
    project_root: Optional[Path] = None
    dataset_root: Optional[Path] = None
    image_root: Optional[Path] = None
    label_root: Optional[Path] = None
    model_path: Optional[Path] = None
    training_outputs: Optional[Path] = None

    class_names: List[str] = field(default_factory=list)
    image_list: List[str] = field(default_factory=list)
    current_image_rel: Optional[str] = None
    current_image_path: Optional[Path] = None
    boxes: List[Box] = field(default_factory=list)

    mode: str = "browse"
    aip_status: str = "disabled"
    last_message: str = "Ready"

    def apply_dataset_info(self, info: DatasetInfo) -> None:
        self.project_root = info.project_root
        self.dataset_root = info.dataset_root
        self.image_root = info.image_root
        self.label_root = info.label_root
        self.model_path = info.model_path
        self.training_outputs = info.training_outputs
        self.class_names = list(info.class_names or [])
        self.last_message = "Dataset loaded"
