#!/usr/bin/env python3
import sys
import traceback
from pathlib import Path

def main():
    try:
        from ui.main_window import MainWindow
        from PySide6.QtWidgets import QApplication
        app = QApplication(sys.argv)
        win = MainWindow()
        win.show()
        app.exec()
    except Exception:
        tb = traceback.format_exc()
        with open(r"E:\_AXIOM_BACKUPS\launcher_error_v0.3.2.txt", "w", encoding="utf-8") as f:
            f.write(tb)
        print("Launcher failed, details written to launcher_error_v0.3.2.txt")

if __name__ == '__main__':
    main()
