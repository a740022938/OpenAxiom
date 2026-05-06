from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPen, QColor, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QTableWidget,
    QTableWidgetItem,
    QStatusBar,
    QMessageBox,
    QFrame,
    QGroupBox,
    QSizePolicy,
)

from core.context import WorkbenchContext, DatasetInfo, Box
from core.dataset_manager import detect_dataset
from core.image_manager import load_images, absolute_image_path
from core.label_manager import load_labels, save_labels


DARK_STYLE = """
QMainWindow {
    background: #0f0f10;
    color: #f2f2f2;
}

QWidget {
    background: #0f0f10;
    color: #f2f2f2;
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 13px;
}

QFrame#TopBar, QFrame#ContextBar, QFrame#StatusPanel {
    background: #111214;
    border: 1px solid #2f3035;
    border-radius: 8px;
}

QGroupBox {
    background: #1a1b1e;
    border: 1px solid #2f3035;
    border-radius: 10px;
    margin-top: 12px;
    padding: 10px;
    color: #f2f2f2;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #a8a8a8;
}

QPushButton {
    background: #202124;
    border: 1px solid #2f3035;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f2f2f2;
}

QPushButton:hover {
    background: #2a2b30;
    border-color: #3a3b41;
}

QPushButton:pressed {
    background: #10a37f;
    color: #0f0f10;
}

QListWidget, QTableWidget {
    background: #111214;
    border: 1px solid #2f3035;
    border-radius: 8px;
    color: #f2f2f2;
    selection-background-color: #10a37f;
    selection-color: #0f0f10;
    alternate-background-color: #1a1b1e;
}

QHeaderView::section {
    background: #202124;
    color: #a8a8a8;
    border: 1px solid #2f3035;
    padding: 5px;
}

QGraphicsView {
    background: #0f0f10;
    border: 1px solid #2f3035;
    border-radius: 10px;
}

QSplitter::handle {
    background: #2f3035;
}

QLabel#TitleLabel {
    font-size: 18px;
    font-weight: 600;
    color: #f2f2f2;
}

QLabel#SubtleLabel {
    color: #a8a8a8;
}

QStatusBar {
    background: #0f0f10;
    color: #a8a8a8;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ctx = WorkbenchContext()
        self.current_pixmap: Optional[QPixmap] = None
        self.current_rect_items: List[QGraphicsRectItem] = []

        self.setWindowTitle("Axiom — Data Workspace")
        self.setStyleSheet(DARK_STYLE)

        self._build_ui()
        self._connect_signals()
        self._update_context_bar()
        self._set_status("Ready. Open a project to begin.")

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        self.top_bar = QFrame()
        self.top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(8)

        self.title_label = QLabel("Axiom")
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel("数据工作区")
        self.subtitle_label.setObjectName("SubtleLabel")

        self.open_button = QPushButton("打开工程")
        self.save_button = QPushButton("保存标注")
        self.settings_button = QPushButton("设置")
        self.mode_button = QPushButton("模式：浏览")

        top_layout.addWidget(self.title_label)
        top_layout.addWidget(self.subtitle_label)
        top_layout.addStretch()
        top_layout.addWidget(self.open_button)
        top_layout.addWidget(self.save_button)
        top_layout.addWidget(self.mode_button)
        top_layout.addWidget(self.settings_button)

        self.context_bar = QFrame()
        self.context_bar.setObjectName("ContextBar")
        context_layout = QHBoxLayout(self.context_bar)
        context_layout.setContentsMargins(12, 6, 12, 6)
        self.context_label = QLabel("工程：-    数据集：-    图像：-    模型：-    AI 预标注：已禁用")
        self.context_label.setObjectName("SubtleLabel")
        context_layout.addWidget(self.context_label)

        self.main_splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.project_box = QGroupBox("工程")
        project_layout = QVBoxLayout(self.project_box)
        self.project_info = QLabel("未加载工程")
        self.project_info.setWordWrap(True)
        self.project_info.setObjectName("SubtleLabel")
        project_layout.addWidget(self.project_info)

        self.image_box = QGroupBox("图片")
        image_layout = QVBoxLayout(self.image_box)
        self.image_list = QListWidget()
        image_layout.addWidget(self.image_list)

        self.stats_box = QGroupBox("数据集统计")
        stats_layout = QVBoxLayout(self.stats_box)
        self.stats_label = QLabel("图片数：0\n标注数：0\n类别数：0")
        self.stats_label.setObjectName("SubtleLabel")
        stats_layout.addWidget(self.stats_label)

        left_layout.addWidget(self.project_box)
        left_layout.addWidget(self.image_box, stretch=1)
        left_layout.addWidget(self.stats_box)

        # Center panel
        center_splitter = QSplitter(Qt.Vertical)

        canvas_panel = QWidget()
        canvas_layout = QVBoxLayout(canvas_panel)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(8)

        self.canvas_title = QLabel("画布")
        self.canvas_title.setObjectName("SubtleLabel")
        self.scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.scene)
        self.graphics_view.setRenderHints(self.graphics_view.renderHints())
        self.graphics_view.setDragMode(QGraphicsView.ScrollHandDrag)
        canvas_layout.addWidget(self.canvas_title)
        canvas_layout.addWidget(self.graphics_view, stretch=1)

        table_panel = QWidget()
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        self.table_title = QLabel("标注")
        self.table_title.setObjectName("SubtleLabel")
        self.annotation_table = QTableWidget(0, 6)
        self.annotation_table.setHorizontalHeaderLabels(["序号", "类别", "名称", "x 中心", "y 中心", "宽/高"])
        self.annotation_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_title)
        table_layout.addWidget(self.annotation_table)

        center_splitter.addWidget(canvas_panel)
        center_splitter.addWidget(table_panel)
        center_splitter.setStretchFactor(0, 5)
        center_splitter.setStretchFactor(1, 2)

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.class_box = QGroupBox("类别")
        class_layout = QVBoxLayout(self.class_box)
        self.class_list = QListWidget()
        class_layout.addWidget(self.class_list)

        self.box_box = QGroupBox("选中框")
        box_layout = QVBoxLayout(self.box_box)
        self.selected_box_label = QLabel("未选择框")
        self.selected_box_label.setWordWrap(True)
        self.selected_box_label.setObjectName("SubtleLabel")
        box_layout.addWidget(self.selected_box_label)

        self.ops_box = QGroupBox("操作")
        ops_layout = QVBoxLayout(self.ops_box)
        self.add_box_button = QPushButton("添加框")
        self.delete_box_button = QPushButton("删除框")
        self.change_class_button = QPushButton("修改类别")
        self.predict_button = QPushButton("预测 / 预标注（保留）")
        self.predict_button.setEnabled(False)
        ops_layout.addWidget(self.add_box_button)
        ops_layout.addWidget(self.delete_box_button)
        ops_layout.addWidget(self.change_class_button)
        ops_layout.addWidget(self.predict_button)

        self.aip_box = QGroupBox("AI 预标注")
        aip_layout = QVBoxLayout(self.aip_box)
        self.aip_label = QLabel("状态：禁用\n基础 URL：未配置")
        self.aip_label.setObjectName("SubtleLabel")
        aip_layout.addWidget(self.aip_label)

        right_layout.addWidget(self.class_box, stretch=2)
        right_layout.addWidget(self.box_box)
        right_layout.addWidget(self.ops_box)
        right_layout.addWidget(self.aip_box)

        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(center_splitter)
        self.main_splitter.addWidget(right_panel)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 6)
        self.main_splitter.setStretchFactor(2, 2)

        root_layout.addWidget(self.top_bar)
        root_layout.addWidget(self.context_bar)
        root_layout.addWidget(self.main_splitter, stretch=1)

        self.setCentralWidget(root)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _connect_signals(self) -> None:
        self.open_button.clicked.connect(self.open_project)
        self.save_button.clicked.connect(self.save_current_labels)
        self.image_list.currentItemChanged.connect(self.on_image_selection_changed)
        self.annotation_table.itemSelectionChanged.connect(self.on_annotation_selection_changed)

    def _set_status(self, message: str) -> None:
        self.ctx.last_message = message
        self.status_bar.showMessage(message)
        self._update_context_bar()

    def _update_context_bar(self) -> None:
        project = str(self.ctx.project_root) if self.ctx.project_root else "-"
        dataset = str(self.ctx.dataset_root) if self.ctx.dataset_root else "-"
        image = self.ctx.current_image_rel or "-"
        model = self.ctx.model_path.name if self.ctx.model_path else "-"
        aip = self.ctx.aip_status or "disabled"

        self.context_label.setText(
            f"工程：{project}    数据集：{dataset}    图像：{image}    模型：{model}    AI 预标注：{aip}"
        )

    def open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "打开工程",
            str(self.ctx.project_root or Path("E:/")),
        )
        if not folder:
            return

        try:
            info = detect_dataset(folder)
            self.ctx.apply_dataset_info(info)
            self.ctx.image_list = load_images(info.image_root)
            self._populate_project(info)
            self._populate_images()
            self._populate_classes()

            if self.ctx.image_list:
                self.image_list.setCurrentRow(0)
                self._set_status(f"工程已加载：{info.project_root}")
            else:
                self._set_status("Dataset detected, but no images were found.")

        except Exception as exc:
            QMessageBox.critical(self, "打开工程失败", str(exc))
            self._set_status(f"打开工程失败：{exc}")

    def _populate_project(self, info: DatasetInfo) -> None:
        self.project_info.setText(
            f"工程：\n{info.project_root}\n\n"
            f"数据集：\n{info.dataset_root}\n\n"
            f"图片：\n{info.image_root}\n\n"
            f"标注：\n{info.label_root}\n\n"
            f"YAML：\n{info.yaml_path or '-'}"
        )

        label_count = 0
        if info.label_root.exists():
            label_count = sum(1 for _ in info.label_root.rglob("*.txt"))

        self.stats_label.setText(
            f"图片数：{len(self.ctx.image_list)}\n"
            f"标注数：{label_count}\n"
            f"类别数：{len(info.class_names)}"
        )

    def _populate_images(self) -> None:
        self.image_list.clear()
        for rel in self.ctx.image_list:
            self.image_list.addItem(QListWidgetItem(rel))

    def _populate_classes(self) -> None:
        self.class_list.clear()
        for idx, name in enumerate(self.ctx.class_names):
            self.class_list.addItem(QListWidgetItem(f"{idx}: {name}"))

    def on_image_selection_changed(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        if not current:
            return
        self.display_image_and_boxes(current.text())

    def display_image_and_boxes(self, image_rel: str) -> None:
        if not self.ctx.image_root or not self.ctx.label_root:
            return

        image_path = absolute_image_path(self.ctx.image_root, image_rel)
        if not image_path.exists():
            self._set_status(f"Image not found: {image_path}")
            return

        self.ctx.current_image_rel = image_rel
        self.ctx.current_image_path = image_path
        self.ctx.boxes = load_labels(self.ctx.label_root, image_rel, self.ctx.class_names)

        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self._set_status(f"Failed to load image: {image_path}")
            return

        self.current_pixmap = pixmap
        self.scene.clear()
        self.current_rect_items.clear()

        pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(pixmap_item)

        self._draw_boxes(pixmap.width(), pixmap.height())
        self._refresh_annotation_table()
        self._update_right_panel()
        self.graphics_view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

        self._set_status(f"已加载图像: {image_rel} | 框数量: {len(self.ctx.boxes)}")

    def _draw_boxes(self, image_w: int, image_h: int) -> None:
        pen = QPen(QColor("#10a37f"))
        pen.setWidth(2)

        for box in self.ctx.boxes:
            x = (box.cx - box.w / 2.0) * image_w
            y = (box.cy - box.h / 2.0) * image_h
            w = box.w * image_w
            h = box.h * image_h

            rect = QGraphicsRectItem(QRectF(x, y, w, h))
            rect.setPen(pen)
            rect.setZValue(10)
            self.scene.addItem(rect)
            self.current_rect_items.append(rect)

    def _refresh_annotation_table(self) -> None:
        self.annotation_table.setRowCount(len(self.ctx.boxes))

        for row, box in enumerate(self.ctx.boxes):
            self.annotation_table.setItem(row, 0, QTableWidgetItem(str(row)))
            self.annotation_table.setItem(row, 1, QTableWidgetItem(str(box.class_id)))
            self.annotation_table.setItem(row, 2, QTableWidgetItem(box.class_name))
            self.annotation_table.setItem(row, 3, QTableWidgetItem(f"{box.cx:.6f}"))
            self.annotation_table.setItem(row, 4, QTableWidgetItem(f"{box.cy:.6f}"))
            self.annotation_table.setItem(row, 5, QTableWidgetItem(f"{box.w:.6f} / {box.h:.6f}"))

        self.annotation_table.resizeColumnsToContents()

    def _update_right_panel(self, selected_row: int = 0) -> None:
        if not self.ctx.boxes:
            self.selected_box_label.setText(
                f"Image: {self.ctx.current_image_rel or '-'}\n"
                f"Boxes: 0\n"
                f"No labels found or empty label file."
            )
            return

        selected_row = max(0, min(selected_row, len(self.ctx.boxes) - 1))
        box = self.ctx.boxes[selected_row]
        self.selected_box_label.setText(
            f"Image: {self.ctx.current_image_rel}\n"
            f"Box: #{selected_row}\n"
            f"Class: {box.class_id} — {box.class_name}\n"
            f"cx: {box.cx:.6f}\n"
            f"cy: {box.cy:.6f}\n"
            f"w:  {box.w:.6f}\n"
            f"h:  {box.h:.6f}"
        )

    def on_annotation_selection_changed(self) -> None:
        rows = self.annotation_table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        self._update_right_panel(row)

        # Highlight selected rect with a warmer color.
        for idx, rect in enumerate(self.current_rect_items):
            pen = QPen(QColor("#f5a524" if idx == row else "#10a37f"))
            pen.setWidth(3 if idx == row else 2)
            rect.setPen(pen)

    def save_current_labels(self) -> None:
        if not self.ctx.label_root or not self.ctx.current_image_rel:
            self._set_status("No current image to save.")
            return

        try:
            path = save_labels(self.ctx.label_root, self.ctx.current_image_rel, self.ctx.boxes)
            self._set_status(f"Labels saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status(f"Save failed: {exc}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.scene.items():
            self.graphics_view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
