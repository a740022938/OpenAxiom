# Contributing to OpenAxiom

## Local Development

```bash
git clone https://github.com/a740022938/OpenAxiom.git
cd OpenAxiom
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python lab_launch_v0.3.2.py
```

## Before Submitting a Pull Request

- [ ] Run `WINDOW_OK` check
- [ ] Confirm no `.venv` in the repository
- [ ] Confirm no dataset files (images, labels) in the repository
- [ ] Confirm no backup / audit directories in the repository
- [ ] Confirm no API keys, tokens, or secrets
- [ ] Confirm no user-specific local paths

## What NOT to Commit

- `.venv/` — always recreate with `pip install -r requirements.txt`
- `__pycache__/` — auto-generated
- Dataset files (images, labels)
- Backup directories (`*_BACKUPS/`, `label_backups_batch/`)
- Audit directories (`*_REPORTS/`, `OpenAxiom_batch_audit/`)
- Personal configuration files
- API keys or tokens

## Branch Strategy

- `main` — stable release branch
- Create feature branches from `main`
- Use conventional commit messages

## Code Style

- Follow PEP 8 for Python code
- Keep imports sorted
- Use type hints where applicable
