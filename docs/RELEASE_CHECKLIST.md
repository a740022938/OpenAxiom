# Release Checklist

## Before Every Release

- [ ] WINDOW_OK passes
- [ ] launcher passes
- [ ] E:\\Axiom main line unmodified
- [ ] Staging directory ready
- [ ] .venv is NOT in staging
- [ ] Dataset is NOT in staging
- [ ] No .bak, .tmp, .cache files
- [ ] No large files (>5 MB)
- [ ] Sensitive info scan: PASS
- [ ] Local path scan: PASS
- [ ] README.md is up to date
- [ ] RELEASE_NOTES.md is up to date
- [ ] LICENSE file exists
- [ ] requirements.txt is correct
- [ ] .gitignore covers all exclusions

## Git Sealing

- [ ] git add .
- [ ] git commit with proper message
- [ ] git tag with version number
- [ ] git status clean after commit

## Remote Release

- [ ] GitHub remote repository created
- [ ] git push origin main
- [ ] git push origin tag
- [ ] GitHub Release page created

## Post-Release Checks

- [ ] Verify README on GitHub homepage
- [ ] Verify docs render correctly
- [ ] Verify no sensitive info exposed
- [ ] Verify .venv and data are excluded


## Environment Checks
- [ ] Python 3.11 is installed
- [ ] Virtual environment is activated
- [ ] pip install -r requirements.txt succeeds
- [ ] python lab_launch_v0.3.2.py starts without errors

## Data Checks
- [ ] Dataset is NOT in staging
- [ ] Labels are NOT in staging
- [ ] .venv is NOT in staging
- [ ] Backup files are NOT in staging
- [ ] Audit files are NOT in staging


---
Complete all checks before pushing to GitHub.
If any check fails, fix the issue before proceeding.

