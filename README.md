# OpenAxiom v1.0.0

**OpenAxiom — UI Lab Annotation MVP / Batch-Safe YOLO Label Tool**

OpenAxiom is a desktop annotation workspace built with PySide6. It provides a complete annotation workflow: browse, edit, save, restore, and batch-process YOLO-format labels — all with safety gates, automatic backups, and audit trails.

---

## 1. Features

### Core
- Open project with image + label directory
- Canvas zoom, pan, fit-to-window
- Bounding box selection, add, delete, category edit
- Undo / Redo (Ctrl+Z / Ctrl+Y)
- Dirty state protection (warns on unsaved changes)
- Keyboard shortcuts: Delete / Esc / Enter / A / D

### Safety Save & Restore
- Pre-save check (PASS / WARN / BLOCK)
- YOLO preview (dry-run)
- Single-label safe save (auto-backup + confirm + verify)
- Single-label safe restore (auto-backup + confirm + verify)
- Backup to `E:\_AXIOM_BACKUPS\label_backups_batch\`

### Quality Gates
- MVP total check
- Project scan (full dataset label consistency)
- Batch pre-save check dry-run
- Batch YOLO dry-run
- Zero-byte label scan
- Full-save gate check (26 items)

### Batch Save
- Batch save plan (PASS / WARN / BLOCK)
- Batch backup plan
- Batch console: batch size 5 / 10 / 20
- Multi-batch executor (up to 20 batches, ≤400 labels)
- Per-batch audit trail
- Batch restore preview

### Review
- Category filter + low-confidence review queue
- Next / previous low-confidence box
- Confirm and next
- Cross-image issue navigation
- Session change summary

---

## 2. What Is NOT Included

- Dataset (images / labels)
- Mahjong game images
- Model weights (`.pt`, `.onnx`)
- Python virtual environment (`.venv`)
- Local backup directories (`label_backups_batch`, `_AXIOM_BACKUPS`)
- Audit logs (`OpenAxiom_batch_audit`)
- API keys, tokens, passwords
- User-specific local paths

---

## 3. Windows Installation

### Prerequisites
- Windows 10 / 11 (64-bit)
- Python 3.11 (recommended)
- Git (optional, for cloning)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/OpenAxiom.git
cd OpenAxiom

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.\.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch
python lab_launch_v0.3.2.py
```

> **Note:** You do NOT need to copy `.venv` from another machine. Always recreate it with `pip install -r requirements.txt`.

---

## 4. Restore After Windows Reinstall

### Before reinstalling, back up these:

| Item | What to back up | Why |
|---|---|---|
| Dataset | `<your_dataset_root>/` | Contains images + labels |
| `label_backups_batch` | Full directory | Batch backup history |
| `OpenAxiom_batch_audit` | Full directory | Batch audit trails |
| Important reports | `_AXIOM_REPORTS/` manually | Reports and governance docs |

**Do NOT** manually back up `.venv` or `__pycache__`.

### After reinstalling Windows:

```bash
# 1. Install Python 3.11
# Download from https://www.python.org/downloads/

# 2. Clone the code
git clone https://github.com/your-org/OpenAxiom.git
cd OpenAxiom

# 3. Recreate virtual environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 4. Restore dataset
# Copy your dataset back to, for example:
#   E:\Mahjong_V1_Project\dataset\

# 5. (Optional) Restore backups and audit
#   E:\_AXIOM_BACKUPS\label_backups_batch\
#   E:\_AXIOM_REPORTS\OpenAxiom_batch_audit\

# 6. Launch and verify
python lab_launch_v0.3.2.py
```

### Verify the restore:

```bash
python --version            # Should print Python 3.11.x
pip list                     # Should show PySide6, PyYAML
python lab_launch_v0.3.2.py  # UI should start
```

### Recommended directory layout (example — NOT hardcoded):

```
E:\Axiom_UI_Lab\Axiom        ← cloned from GitHub
E:\Mahjong_V1_Project\dataset\     ← your images + labels
E:\_AXIOM_BACKUPS\label_backups_batch\   ← batch backups
E:\_AXIOM_REPORTS\OpenAxiom_batch_audit\  ← batch audit
```

---

## 5. Data Folder Setup

OpenAxiom lets you choose your dataset at runtime:

1. Click **"打开工程"** (Open Project)
2. Select the dataset root directory
3. The tool will detect `images/` and `labels/` subdirectories
4. If auto-detection fails, you can configure paths manually

Use placeholders in documentation — never hardcode personal paths like `<your_username>`.

---

## 6. Backup and Recovery Policy

### Three backup layers

| Layer | Command | Content | Frequency |
|---|---|---|---|
| **source_only** (default) | `.\scripts\backup_openaxiom_source_only.ps1` | Source code, config, scripts | Every RC / release |
| **full_backup** | Manual (user decides) | Source + .venv | Major releases |
| **data_backup** | Manual (user decides) | `label_backups_batch` + audit | After batch save |

### Why no .venv in source backups

`.venv` contains platform-specific binaries (pip, PySide6 builds). It is **not portable** across machines. Always recreate with:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Using the backup script

```powershell
# Dry-run (default — shows what will be backed up)
powershell -ExecutionPolicy Bypass -File .\scripts\backup_openaxiom_source_only.ps1 -DryRun

# Execute (actually create backup)
powershell -ExecutionPolicy Bypass -File .\scripts\backup_openaxiom_source_only.ps1 -Execute
```

---

## 7. Safety Notes

- Always run **batch pre-save check dry-run** before any batch save
- Always run **zero-byte label scan** after batch save
- If a batch fails, **stop immediately** — do NOT skip failed batches
- Before full-dataset batch operations, **test with 1–2 batches first**
- All batch saves require **manual confirmation** per batch
- This tool does **NOT** auto-continue to the next batch

---

## 8. Development Status

- **v1.0.0** — First GitHub-sealed release of OpenAxiom UI Lab Annotation MVP
- Platform: Windows 10/11, Python 3.11, PySide6
- Next direction: merge with `E:\Axiom` mainline, cross-platform support, model integration, plugin architecture

---

## 9. License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
