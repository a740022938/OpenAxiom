# OpenAxiom - Restore After Windows Reinstall

## Before Reinstalling

No need to manually back up:
- GitHub repository (just clone it again)

Must back up manually:
1. Dataset directory - your images + YOLO labels.
2. label_backups_batch - batch save backups.
3. OpenAxiom_batch_audit - batch audit history.
4. Important reports - manual copy.

Do NOT back up:
- .venv (always recreate)
- __pycache__ (auto-regenerated)

## After Reinstalling

```powershell
# 1. Install Python 3.11
# Download from https://www.python.org/downloads/

# 2. Clone the repository
git clone https://github.com/a740022938/OpenAxiom.git
cd OpenAxiom

# 3. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Restore your dataset
# Example: YOUR_DATASET_ROOT/dataset/

# 6. (Optional) Restore backups and audit
#   YOUR_BACKUP_DIR/label_backups_batch/
#   YOUR_AUDIT_DIR/OpenAxiom_batch_audit/

# 7. Launch OpenAxiom
python lab_launch_v0.3.2.py
```

## Verification

```powershell
python --version
pip list
python lab_launch_v0.3.2.py
```

## Common Issues

| Issue | Solution |
|---|---|
| PySide6 install fails | Install Microsoft Visual C++ Redistributable. |
| No images found | Click Open Project and select the correct root. |
| No labels found | Ensure labels/ subdirectory exists. |
| .venv missing | Recreate: python -m venv .venv then activate. |
| Paths changed | The tool asks for dataset path at startup. |
| Batch backups lost | Copy label_backups_batch from external backup. |
