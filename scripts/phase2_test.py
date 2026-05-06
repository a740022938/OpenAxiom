import os
import sys
# Ensure package import path includes project root (E:\Axiom)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
from core.dataset_manager import detect_dataset
from core.image_manager import load_images
from core.label_manager import load_labels

def main():
    root = r"E:\Mahjong_V1_Project"
    # Step 1: detect dataset
    ds = detect_dataset(root)
    print("Dataset detect:", ds)
    if not ds:
        print("No YOLO dataset detected; exiting test.")
        return
    image_root = getattr(ds, 'image_root', None)
    label_root = getattr(ds, 'label_root', None)
    if image_root is None or label_root is None and isinstance(ds, dict):
        image_root = ds.get('image_root') if isinstance(ds, dict) else None
        label_root = ds.get('label_root') if isinstance(ds, dict) else None
    class_names = getattr(ds, 'class_names', [])
    if isinstance(ds, dict):
        class_names = ds.get('class_names', class_names)
    print("image_root:", image_root)
    print("label_root:", label_root)
    print("class_names:", class_names)
    images = load_images(image_root) if image_root else []
    print("Images:", images[:5], '... total', len(images))
    if images:
        img = images[0]
        label_map = load_labels(label_root, [img], image_root, class_names)
        boxes = label_map.get(img, [])
        print("First image:", img, "boxes:", boxes)

if __name__ == '__main__':
    main()
