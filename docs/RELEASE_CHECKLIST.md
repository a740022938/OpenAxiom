# Release Checklist

## Before Every Release

- [ ] `WINDOW_OK` passes
- [ ] `launcher` passes
- [ ] `E:\Axiom` main line unmodified
- [ ] Staging directory ready (`E:\OpenAxiom_GitHub_Release_Staging`)
- [ ] `.venv` is NOT in staging
- [ ] Dataset is NOT in staging
- [ ] No `.bak`, `.tmp`, `.cache` files in staging
- [ ] No large files (>5 MB) in staging
- [ ] Sensitive info scan: **PASS**
- [ ] Local path scan: **PASS**
- [ ] `git status` shows no untracked secrets
- [ ] `README.md` is up to date
- [ ] `RELEASE_NOTES.md` is up to date
- [ ] `VERSION` file is correct
- [ ] `LICENSE` file exists
- [ ] `requirements.txt` exists and correct
- [ ] `.gitignore` covers all exclusion patterns

## Git Sealing

- [ ] `git add .`
- [ ] `git commit` with proper message
- [ ] `git tag` with version number
- [ ] `git status` clean after commit
- [ ] `git log --oneline --decorate` confirms tag

## Remote Release

- [ ] GitHub remote repository created
- [ ] `git remote add origin <url>`
- [ ] `git push origin main`
- [ ] `git push origin v1.0.0`
- [ ] GitHub Release page created
- [ ] Release notes written
- [ ] Zip archive not needed (GitHub auto-generates)
