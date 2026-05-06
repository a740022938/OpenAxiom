from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml

from core.context import DatasetInfo


YAML_CANDIDATES = ("data.yaml", "dataset.yaml", "yolov8.yaml")


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path.absolute()


def _has_yolo_roots(path: Path) -> bool:
    return (path / "images").exists() and (path / "labels").exists()


def _find_yaml_near(selected: Path) -> Optional[Path]:
    selected = _safe_resolve(selected)

    if selected.is_file() and selected.name.lower() in YAML_CANDIDATES:
        return selected

    search_dirs = []

    if selected.is_dir():
        search_dirs.append(selected)

        if (selected / "dataset").exists():
            search_dirs.append(selected / "dataset")

    current = selected if selected.is_dir() else selected.parent
    for parent in [current, *current.parents][:8]:
        search_dirs.append(parent)
        if (parent / "dataset").exists():
            search_dirs.append(parent / "dataset")

    seen = set()
    for d in search_dirs:
        d = _safe_resolve(d)
        if d in seen or not d.exists() or not d.is_dir():
            continue
        seen.add(d)

        for name in YAML_CANDIDATES:
            p = d / name
            if p.exists():
                return _safe_resolve(p)

    recursive_roots = []
    if selected.is_dir():
        recursive_roots.append(selected)
        if (selected / "dataset").exists():
            recursive_roots.insert(0, selected / "dataset")

    for root in recursive_roots:
        for name in YAML_CANDIDATES:
            found = list(root.rglob(name))
            if found:
                found.sort(key=lambda p: len(p.parts))
                return _safe_resolve(found[0])

    return None


def _load_yaml(yaml_path: Path) -> Dict[str, Any]:
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _extract_names(data: Dict[str, Any]) -> List[str]:
    names = data.get("names")

    if isinstance(names, list):
        return [str(x) for x in names]

    if isinstance(names, dict):
        def key_sort(x):
            try:
                return int(x)
            except Exception:
                return str(x)
        return [str(names[k]) for k in sorted(names.keys(), key=key_sort)]

    try:
        nc = int(data.get("nc"))
        return [f"class_{i}" for i in range(nc)]
    except Exception:
        return []


def _resolve_candidate_path(base: Path, value: Any) -> Optional[Path]:
    if value is None:
        return None

    if isinstance(value, list):
        if not value:
            return None
        value = value[0]

    p = Path(str(value))
    if p.is_absolute():
        return _safe_resolve(p)
    return _safe_resolve(base / p)


def _choose_dataset_base(selected: Path, yaml_path: Path, data: Dict[str, Any]) -> Path:
    """
    Robustness rule:
    If copied data.yaml keeps an old absolute path, e.g.
      path: E:\数据集_v1_synth_2000
    but the actual copied dataset lives beside data.yaml, prefer the local
    directory that has images/labels.
    """
    yaml_dir = _safe_resolve(yaml_path.parent)

    if _has_yolo_roots(yaml_dir):
        return yaml_dir

    selected = _safe_resolve(selected)
    if selected.is_dir() and _has_yolo_roots(selected / "dataset"):
        return _safe_resolve(selected / "dataset")

    raw_path = data.get("path")
    if raw_path:
        p = Path(str(raw_path))
        candidate = _safe_resolve(p if p.is_absolute() else yaml_dir / p)
        if candidate.exists() and _has_yolo_roots(candidate):
            return candidate

    for key in ("train", "val", "test"):
        candidate = _resolve_candidate_path(yaml_dir, data.get(key))
        if not candidate:
            continue

        parts = [part.lower() for part in candidate.parts]
        if "images" in parts:
            idx = parts.index("images")
            root = Path(*candidate.parts[:idx]) if idx > 0 else Path(candidate.anchor)
            if root.exists() and _has_yolo_roots(root):
                return _safe_resolve(root)

        if candidate.name.lower() in ("train", "val", "valid", "test") and candidate.parent.name.lower() == "images":
            root = candidate.parent.parent
            if root.exists() and _has_yolo_roots(root):
                return _safe_resolve(root)

    return yaml_dir


def _detect_image_and_label_roots(dataset_base: Path, data: Dict[str, Any]) -> tuple[Path, Path]:
    image_root = dataset_base / "images"
    label_root = dataset_base / "labels"

    if image_root.exists() and label_root.exists():
        return _safe_resolve(image_root), _safe_resolve(label_root)

    for key in ("train", "val", "test"):
        candidate = _resolve_candidate_path(dataset_base, data.get(key))
        if not candidate:
            continue

        if candidate.name.lower() in ("train", "val", "valid", "test"):
            image_root = candidate.parent
        else:
            image_root = candidate

        if image_root.name.lower() == "images":
            label_root = image_root.parent / "labels"
        else:
            label_root = dataset_base / "labels"
        break

    return _safe_resolve(image_root), _safe_resolve(label_root)


def _infer_project_root(selected: Path, dataset_root: Path) -> Path:
    selected = _safe_resolve(selected)
    dataset_root = _safe_resolve(dataset_root)

    if dataset_root.name.lower() == "dataset":
        return _safe_resolve(dataset_root.parent)

    if selected.is_dir() and (selected / "dataset").exists():
        return _safe_resolve(selected)

    return dataset_root


def _find_model(project_root: Path) -> Optional[Path]:
    candidates = [
        project_root / "models" / "best.pt",
        project_root / "models" / "last.pt",
    ]
    for p in candidates:
        if p.exists():
            return _safe_resolve(p)

    model_dir = project_root / "models"
    if model_dir.exists():
        pts = sorted(model_dir.glob("*.pt"))
        if pts:
            return _safe_resolve(pts[0])

    return None


def detect_dataset(selected_dir: str | Path) -> DatasetInfo:
    selected = _safe_resolve(Path(selected_dir))
    yaml_path = _find_yaml_near(selected)

    if not yaml_path:
        raise FileNotFoundError(
            f"No YOLO yaml found near: {selected}. Expected data.yaml / dataset.yaml / yolov8.yaml."
        )

    data = _load_yaml(yaml_path)
    dataset_root = _choose_dataset_base(selected, yaml_path, data)
    image_root, label_root = _detect_image_and_label_roots(dataset_root, data)

    if not image_root.exists():
        raise FileNotFoundError(
            f"Image root not found: {image_root}\n"
            f"YAML: {yaml_path}\n"
            f"Dataset root: {dataset_root}\n"
            f"Tip: data.yaml may contain an old absolute path. Axiom tried local fallback but images were still not found."
        )

    if not label_root.exists():
        raise FileNotFoundError(
            f"Label root not found: {label_root}\n"
            f"YAML: {yaml_path}\n"
            f"Dataset root: {dataset_root}"
        )

    class_names = _extract_names(data)
    if not class_names:
        class_names = ["class_0"]

    project_root = _infer_project_root(selected, dataset_root)
    training_outputs = project_root / "training_outputs"
    model_path = _find_model(project_root)

    return DatasetInfo(
        project_root=_safe_resolve(project_root),
        dataset_root=_safe_resolve(dataset_root),
        yaml_path=_safe_resolve(yaml_path),
        image_root=_safe_resolve(image_root),
        label_root=_safe_resolve(label_root),
        class_names=class_names,
        model_path=model_path,
        training_outputs=_safe_resolve(training_outputs) if training_outputs.exists() else None,
        source_selected_path=selected,
    )
