from __future__ import annotations

from pathlib import Path

from core.dataset_manager import detect_dataset
from core.image_manager import load_images
from core.label_manager import load_labels, label_path_for_image


def main() -> None:
    project = Path(r"E:\Mahjong_V1_Project")

    info = detect_dataset(project)
    print("PROJECT_ROOT =", info.project_root)
    print("DATASET_ROOT =", info.dataset_root)
    print("YAML_PATH    =", info.yaml_path)
    print("IMAGE_ROOT   =", info.image_root)
    print("LABEL_ROOT   =", info.label_root)
    print("MODEL_PATH   =", info.model_path)
    print("CLASSES      =", len(info.class_names))

    images = load_images(info.image_root)
    print("IMAGE_COUNT  =", len(images))

    if not images:
        raise RuntimeError("No images found.")

    sample = images[0]
    label_path = label_path_for_image(info.label_root, sample)
    boxes = load_labels(info.label_root, sample, info.class_names)

    print("SAMPLE_IMAGE =", sample)
    print("SAMPLE_LABEL =", label_path)
    print("LABEL_EXISTS =", label_path.exists())
    print("BOX_COUNT    =", len(boxes))

    for i, box in enumerate(boxes[:10]):
        print(i, box.class_id, box.class_name, box.cx, box.cy, box.w, box.h)


if __name__ == "__main__":
    main()
