# OpenAxiom

![Python](https://img.shields.io/badge/python-3.11-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.11-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Release](https://img.shields.io/badge/release-v1.0.2-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows-blueviolet)

OpenAxiom is a local PySide6 UI Lab annotation MVP and batch-safe YOLO label tool.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Windows Installation](#windows-installation)
- [Restore After Windows Reinstall](#restore-after-windows-reinstall)
- [Data Folder Setup](#data-folder-setup)
- [Backup and Recovery Policy](#backup-and-recovery-policy)
- [Safety Notes](#safety-notes)
- [Development Status](#development-status)
- [License](#license)

---

## Features

### Core

- Open project with image + label directory
- Canvas zoom, pan, fit-to-window
- Bounding box selection, add, delete, category edit
- Undo / Redo (Ctrl+Z / Ctrl+Y)
- Dirty state protection
- Keyboard shortcuts: Delete / Esc / Enter / A / D

### Safety Save & Restore

- Pre-save check (PASS / WARN / BLOCK)
- YOLO preview (dry-run)
- Single-label safe save (auto-backup + confirm + verify)
- Single-label safe restore (auto-backup + confirm + verify)
- Backup to label_backups_batch directory

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
- Multi-batch executor (up to 20 batches, max 400 labels)
- Per-batch audit trail
- Batch restore preview

### Review

- Category filter + low-confidence review queue
- Next / previous low-confidence box
- Confirm and next
- Cross-image issue navigation
- Session change summary

---

## Quick Start

```powershell
git clone https://github.com/a740022938/OpenAxiom.git
cd OpenAxiom
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python lab_launch_v0.3.2.py
```

The UI starts and you can open a YOLO dataset.

---

## Windows Installation

### Prerequisites

- Windows 10 / 11 (64-bit)
- Python 3.11 (recommended)
- Git

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/a740022938/OpenAxiom.git
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

> **Note:** You do NOT need to copy .venv from another machine.
> Always recreate it with pip install -r requirements.txt.

---

## Restore After Windows Reinstall

### Before reinstalling, back up these:

| Item | What to back up | Why |
|---|---|---|
| Dataset | YOUR_DATASET_ROOT | Contains images + labels |
| label_backups_batch | Full directory | Batch backup history |
| OpenAxiom_batch_audit | Full directory | Batch audit trails |
| Important reports | Manual copy | Reports and governance docs |

### After reinstalling Windows

```powershell
# 1. Install Python 3.11
# Download from https://www.python.org/downloads/

# 2. Clone the code
git clone https://github.com/a740022938/OpenAxiom.git
cd OpenAxiom

# 3. Recreate virtual environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 4. Restore dataset
# Copy your dataset back to a local directory, for example:
#   YOUR_DATASET_ROOT/dataset/

# 5. (Optional) Restore backups and audit
#   YOUR_BACKUP_DIR/label_backups_batch/
#   YOUR_AUDIT_DIR/OpenAxiom_batch_audit/

# 6. Launch and verify
python lab_launch_v0.3.2.py
```

### Verify the restore

```powershell
python --version
pip list
python lab_launch_v0.3.2.py
```

### Recommended directory layout

```
YOUR_PROJECT_ROOT/               cloned from GitHub
YOUR_DATASET_ROOT/dataset/       your images + labels
YOUR_BACKUP_DIR/label_backups_batch/   batch backups
YOUR_AUDIT_DIR/OpenAxiom_batch_audit/  batch audit
```

> These are examples, not hardcoded requirements.

---

## Data Folder Setup

OpenAxiom lets you choose your dataset at runtime:

1. Click Open Project
2. Select the dataset root directory
3. The tool detects images/ and labels/ subdirectories
4. If auto-detection fails, configure paths manually

---

## Backup and Recovery Policy

### Three backup layers

| Layer | Content |
|---|---|
| source_only | Source code, config, scripts |
| full_backup | Source + .venv |
| data_backup | label_backups_batch + audit |

### Why no .venv in source backups

.venv contains platform-specific binaries. Always recreate:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Using the backup script

```powershell
# Dry-run
powershell -ExecutionPolicy Bypass -File .\scripts\backup_openaxiom_source_only.ps1

# Execute
powershell -ExecutionPolicy Bypass -File .\scripts\backup_openaxiom_source_only.ps1 -Execute
```

---

## Safety Notes

- Always run batch pre-save check dry-run before any batch save
- Always run zero-byte label scan after batch save
- If a batch fails, stop immediately
- Test with 1-2 batches before full-dataset operations
- All batch saves require manual confirmation per batch

---

## Development Status

- v1.0.2 — Markdown formatting release
- Platform: Windows 10/11, Python 3.11, PySide6

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
