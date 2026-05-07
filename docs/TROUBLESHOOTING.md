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

## Getting Help

If the above steps do not resolve your issue,
please open a GitHub issue with: your OS version,
Python version, OpenAxiom version, and steps to reproduce.


## Performance Issues
- Large datasets may take longer to scan.
- Batch operations on 2000+ images require patience.
- Close other applications to free memory.

## File Format Issues
- Label files must be UTF-8 encoded.
- Line endings (CRLF vs LF) are handled automatically.
- Each line must have exactly 5 columns: class_id cx cy w h.
- Coordinates must be space-separated, not tab-separated.

