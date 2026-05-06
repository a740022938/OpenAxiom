# OpenAxiom — Restore After Windows Reinstall

## Before Reinstalling

No need to manually back up:
- GitHub repository — just clone it again

Must back up manually:
1. **Dataset directory** — your images + YOLO labels
2. **`label_backups_batch`** — batch save backups (e.g. `YOUR_BACKUP_DIR\label_backups_batch`)
3. **`OpenAxiom_batch_audit`** — batch audit history (e.g. `YOUR_AUDIT_DIR\OpenAxiom_batch_audit`)
4. **Important reports** (manual copy)

Do NOT back up:
- `.venv` — always recreate
- `__pycache__` — auto-regenerated

## After Reinstalling

```bash
# 1. Install Python 3.11
# Download from python.org

# 2. Clone the repository
git clone https://github.com/a740022938/OpenAxiom.git
cd OpenAxiom

# 3. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Restore your dataset to a local directory
# Example: YOUR_DATASET_ROOT\dataset\

# 6. (Optional) Restore backups and audit
#   YOUR_BACKUP_DIR\label_backups_batch\
#   YOUR_AUDIT_DIR\OpenAxiom_batch_audit\

# 7. Launch OpenAxiom
python lab_launch_v0.3.2.py
```

## Verification

```bash
python --version            # Should print 3.11.x
pip list                     # Should show PySide6, PyYAML
python lab_launch_v0.3.2.py  # UI should start
```

## Common Issues

| Issue | Solution |
|---|---|
| PySide6 install fails | Install Microsoft Visual C++ Redistributable |
| No images found | Click "打开工程" and select the correct dataset root |
| No labels found | Ensure `labels/` subdirectory exists with `.txt` files |
| `.venv` missing | Recreate: `python -m venv .venv && .\.venv\Scripts\activate && pip install -r requirements.txt` |
| Paths changed after reinstall | The tool asks you to select the dataset directory at startup — no hardcoded paths |
| Batch backups lost | Copy `label_backups_batch` from your external backup |
