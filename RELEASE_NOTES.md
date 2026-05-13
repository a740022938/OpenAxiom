# OpenAxiom Release Notes

## v1.0.8 - Launcher Docs Hotfix

- Add integrated AIP/Axiom tools launch command:
  `Set-Location E:\Axiom\tools\openaxiom` then `python .\launch.py`.
- Document desktop launcher:
  `C:\Users\74002\Desktop\StartOpenAxiom.bat`.
- Clarify that OpenAxiom GUI launches as a local desktop tool, not as a
  background service like AIP.
- Clarify the difference between AIP readonly bridge usage and direct
  OpenAxiom GUI annotation usage.
- No core annotation logic, safe save, safe restore, batch save, dataset,
  label, model, .venv, backup, or audit files changed.

## v1.0.7 - Docs Consistency Hotfix

- Fix README release badge and development status to reflect the current
  release line.
- Clarify that v1.0.6 included runtime UX source changes.
- Clarify that v1.0.6 did not modify core annotation logic, bbox drawing,
  coordinate conversion, safe save, safe restore, batch save, or multi-batch
  execution logic.
- No source code changes in v1.0.7.
- No data, labels, .venv, backups, or audit files included.

## v1.0.6 - Runtime UX Enhancement

- Add centralized version constant (ui/__init__.py).
- Show version in window title and status bar.
- Launcher now checks Python version and dependencies with friendly messages.
- Canvas shows helpful empty-state message instead of bare text.
- Open Project dialog validates image/label directories with clear warnings.
- Exception messages now point to README and TROUBLESHOOTING docs.
- No core annotation logic changes.
- No data, labels, .venv, backups, or audit files included.

## v1.0.4 - Documentation Final Fix

- Rewrite all Markdown files with Python to ensure proper multi-line formatting.
- Fix GitHub raw file rendering (previously displayed as single lines).
- All code blocks and tables now render correctly on GitHub.
- No source code logic changes.
- No data, labels, .venv, backups, or audit files included.

## v1.0.3 - GitHub Documentation Final Fix

- Sync master branch to match main content.
- Ensure GitHub default branch shows correct README.
- No source code logic changes.

## v1.0.2 - Markdown Formatting Fix

- Rewrite README.md with proper multi-line Markdown.
- Ensure all code blocks render correctly on GitHub.
- Remove all hardcoded local path examples.
- Use YOUR_* placeholders consistently.
- No source code changes.

## v1.0.1 - Documentation Hotfix

- Fix README clone URL.
- Fix Windows .venv activation command.
- Fix restore guide to use YOUR_* placeholders.
- GitHub default branch changed to main.

## v1.0.0 - GitHub Release

- First GitHub release of OpenAxiom.
- Annotation MVP complete.
- Batch save and restore capabilities.
- Safety gates and audit trails.

---
Release history note:
v1.0.1 through v1.0.5 were documentation-oriented releases.
v1.0.6 included runtime UX source changes for startup checks, version display,
launcher messages, and empty dataset hints, without changing core annotation,
bbox, coordinate conversion, safe save, safe restore, batch save, or
multi-batch execution logic.
v1.0.7 is a documentation consistency hotfix only.
v1.0.8 is a launcher documentation hotfix only.

