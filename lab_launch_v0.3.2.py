#!/usr/bin/env python3
"""
OpenAxiom launcher.
Provides friendly error messages when dependencies or environment are missing.
"""
import sys
import traceback
from pathlib import Path

def check_python():
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or later is required.")
        print(f"Current: {sys.version}")
        sys.exit(1)

def check_dependencies():
    try:
        import PySide6
    except ImportError:
        print("Error: PySide6 is not installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is not installed.")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

def main():
    check_python()
    check_dependencies()
    try:
        from ui.main_window import MainWindow
        from ui import APP_NAME, APP_VERSION
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        win = MainWindow()
        win.show()
        return app.exec()
    except Exception:
        tb = traceback.format_exc()
        msg = (
            f"OpenAxiom {APP_VERSION} failed to start.\n\n"
            f"Error details:\n{tb}\n\n"
            f"Troubleshooting:\n"
            f"- Check README.md for installation steps\n"
            f"- Run: python -m venv .venv\n"
            f"- Run: .\\.venv\\Scripts\\activate\n"
            f"- Run: pip install -r requirements.txt\n"
            f"- See docs/TROUBLESHOOTING.md for more help"
        )
        print(msg)
        sys.exit(1)

if __name__ == '__main__':
    main()
