import json
import os
from pathlib import Path

from PySide6 import QtWidgets


DEFAULT_CONFIG_PATH = Path.home() / ".openaxiom" / "config_settings.json"


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, master=None, on_saved_callback=None):
        super().__init__(master)
        self.setWindowTitle("设置")
        self.resize(380, 120)
        self.on_saved_callback = on_saved_callback

        layout = QtWidgets.QVBoxLayout(self)
        label = QtWidgets.QLabel("语言")
        layout.addWidget(label)
        self.lang_combo = QtWidgets.QComboBox()
        self.lang_combo.addItems(["中文", "英文"])
        layout.addWidget(self.lang_combo)

        btns = QtWidgets.QHBoxLayout()
        save = QtWidgets.QPushButton("保存")
        cancel = QtWidgets.QPushButton("取消")
        save.clicked.connect(self.save_settings)
        cancel.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def save_settings(self):
        lang = self.lang_combo.currentText()
        cfg_path = DEFAULT_CONFIG_PATH
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
        if lang == "简体中文":
            cfg.setdefault("ui", {})["language"] = "zh_CN"
        else:
            cfg.setdefault("ui", {})["language"] = "en_US"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.on_saved_callback:
            self.on_saved_callback(cfg)
        self.accept()
