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
