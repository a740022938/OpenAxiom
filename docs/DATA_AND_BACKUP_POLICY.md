# OpenAxiom - Data and Backup Policy

## What GitHub Contains

GitHub stores only source code and documentation.
- Python source files (main.py, ui/, core/, scripts/)
- Documentation (README.md, docs/, LICENSE)
- Config files (.gitignore, requirements.txt)

GitHub does NOT contain:
- Dataset (images, labels)
- .venv
- Backup files
- Audit logs
- Model weights
- User-specific config

## Backup Layers

| Layer | Command |
|---|---|
| source_only | scripts/backup_openaxiom_source_only.ps1 |
| full_backup | Manual robocopy |
| data_backup | Manual Copy-Item |

## Backup Retention

| Item | Retention |
|---|---|
| Official version backup | Permanent |
| label_backups_batch | Permanent |
| OpenAxiom_batch_audit | Permanent |
| RC interim backups | Keep last 1-2 |

## What Can Be Safely Deleted

- Old rc backups
- __pycache__ directories
- .venv (can recreate)
- cleanup_quarantine

## What Must NEVER Be Deleted

- label_backups_batch
- OpenAxiom_batch_audit
- Official version backups
- Current project source

## Summary

Keep your backups organized and documented.
Test your restore process periodically.


## Recommended Practices

- Perform source_only backup after each significant change.
- Perform full_backup only for major version milestones.
- Keep at least the last 2 RC backups for rollback.
- Label batch backups should never be deleted.
- Audit trails should be preserved for compliance.

## Backup Location Examples
These are example paths, not requirements:
YOUR_STORAGE/OpenAxiom/source_only/
YOUR_STORAGE/OpenAxiom/full_backup/
YOUR_STORAGE/OpenAxiom/data_backup/


---
This policy document is a reference guide.
Follow the practices that match your workflow.

