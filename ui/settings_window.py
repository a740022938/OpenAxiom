from PySide6 import QtWidgets

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
        # 简易：仅保存语言设定到用户配置文件（路径简单实现）
        lang = self.lang_combo.currentText()
        import json
        cfg_path = os.path.join("E:\", "Axiom_UI_Lab", "config_settings.json")
        cfg = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                try:
                    cfg = json.load(f)
                except Exception:
                    cfg = {}
        if lang == "简体中文":
            cfg["ui"] = cfg.get("ui", {})
            cfg["ui"]["language"] = "zh_CN"
        else:
            cfg["ui"] = cfg.get("ui", {})
            cfg["ui"]["language"] = "en_US"
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        if self.on_saved_callback:
            self.on_saved_callback(cfg)
        self.accept()
