# Troubleshooting

## UI Won't Start

Check:
- python --version (must be 3.8+, 3.11 recommended)
- pip list (must show PySide6 and PyYAML)

Fix:
- Activate .venv
- pip install -r requirements.txt

If PySide6 install fails, install Microsoft Visual C++ Redistributable.

## No Images or No Labels

- Click Open Project.
- Select the root dataset directory.
- The tool expects images/ and labels/ subdirectories.
- Label files must be .txt in YOLO format.

## Bounding Boxes Not Displaying

- Ensure labels are in YOLO format: class_id cx cy w h
- Normalized coordinates (0.0 to 1.0)
- File names must match image names.

## Labels Were Accidentally Overwritten

- Check label_backups_batch directory.
- Find the backup by timestamp.
- Copy the original .txt back.

## Zero-Byte Label Found

- Stop all batch operations immediately.
- Restore from label_backups_batch.
- Re-run zero-byte scan until count is zero.

## Paths Changed After Reinstall

OpenAxiom uses an Open Project dialog.
No hardcoded paths. Simply point to the new dataset location.
