# Troubleshooting

## UI Won't Start

**Symptom:** `python lab_launch_v0.3.2.py` raises an error.

**Check:**
```bash
python --version           # Must be 3.8+ (3.11 recommended)
pip list | findstr PySide6 # Must show PySide6
pip list | findstr PyYAML  # Must show PyYAML
```

**Fix:**
```bash
.\.venv\Scripts\activate
pip install -r requirements.txt
```

If PySide6 install fails, install Microsoft Visual C++ Redistributable:
https://aka.ms/vs/17/release/vc_redist.x64.exe

## No Images / No Labels

- Click "打开工程" (Open Project)
- Select the root dataset directory
- The tool expects `images/` and `labels/` subdirectories
- Label files must be `.txt` in YOLO format

## Bounding Boxes Not Displaying

- Ensure labels are in YOLO format: `class_id cx cy w h`
- Normalized coordinates (0.0 to 1.0)
- File names must match image names (same stem, `.txt` extension)

## Labels Were Accidentally Overwritten

**Immediately:**
1. Check `E:\_AXIOM_BACKUPS\label_backups_batch\`
2. Find the backup by timestamp
3. Copy the original `.txt` back to the label directory

**For batch saves:** each batch has its own backup directory.

## Zero-Byte Label Found

- Stop all batch operations immediately
- Restore from `label_backups_batch`
- Re-run zero-byte scan until count is zero
- Investigate what caused the empty write

## Paths Changed After System Reinstall

OpenAxiom uses a "打开工程" (Open Project) dialog — no hardcoded paths. Simply point to the new dataset location.
