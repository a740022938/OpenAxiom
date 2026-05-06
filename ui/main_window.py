from __future__ import annotations

from pathlib import Path
from typing import Optional, List

from PySide6.QtCore import Qt, QRectF, Signal, QPoint, QPointF
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QFont, QAction, QClipboard
)
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
    QTableWidget,
    QTableWidgetItem,
    QStatusBar,
    QMessageBox,
    QFrame,
    QGroupBox,
    QFormLayout,
    QHeaderView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QScrollArea,
    QMenu,
    QInputDialog,
    QApplication,
    QTabWidget,
)

from core.context import WorkbenchContext, Box
from core.dataset_manager import detect_dataset
from core.image_manager import load_images, absolute_image_path
from core.label_manager import load_labels, label_path_for_image, save_labels


THEME_QSS = """
QMainWindow, QWidget {
    background: #0f0f10;
    color: #f2f2f2;
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 13px;
}

QFrame#topBar, QFrame#contextBar {
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
    border-color: #10a37f;
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

QLabel#subtle {
    color: #a8a8a8;
}

QStatusBar {
    background: #0f0f10;
    color: #a8a8a8;
}

QComboBox, QDoubleSpinBox {
    background: #202124;
    border: 1px solid #2f3035;
    border-radius: 6px;
    padding: 5px;
    color: #f2f2f2;
}
"""


class SettingsWindow(QDialog):
    def __init__(self, parent=None, current_language: str = "zh_CN"):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(360, 160)
        self.setStyleSheet(THEME_QSS)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("语言"))

        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh_CN")
        self.language_combo.addItem("英文", "en_US")
        idx = self.language_combo.findData(current_language)
        self.language_combo.setCurrentIndex(max(0, idx))
        layout.addWidget(self.language_combo)

        hint = QLabel("此版本仅保存语言选项，完整 UI 翻译保留。")
        hint.setObjectName("subtle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.addStretch()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        row.addWidget(self.ok_btn)
        row.addWidget(self.cancel_btn)
        layout.addLayout(row)

        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    @property
    def selected_language(self) -> str:
        return str(self.language_combo.currentData())


class ImageCanvas(QWidget):
    boxClicked = Signal(int)
    canvasClicked = Signal()
    boxRightClicked = Signal(int, object)  # index, global_pos
    canvasRightClicked = Signal(object)    # global_pos
    zoomChanged = Signal(float)            # zoom factor
    dragBoxCreated = Signal(float, float, float, float)  # norm_cx, norm_cy, norm_w, norm_h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 320)
        self.setMouseTracking(True)
        self.pixmap: Optional[QPixmap] = None
        self.confirmed_indexes: set = set()
        self.boxes: List[Box] = []
        self.selected_index: int = -1
        self._render_rect = QRectF()
        # 缩放与平移状态
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self._is_panning = False
        self._pan_start = QPointF()
        # 新增框模式
        self.add_box_mode = False
        self._is_dragging = False
        self._drag_start = QPointF()
        self._drag_current = QPointF()
        self.setStyleSheet("background: #111214; border: 1px solid #2f3035; border-radius: 10px;")

    def set_image_and_boxes(self, pixmap: Optional[QPixmap], boxes: List[Box]) -> None:
        self.pixmap = pixmap
        self.boxes = list(boxes or [])
        self.selected_index = 0 if self.boxes else -1
        self._reset_view()
        self.update()

    def set_selected_index(self, index: int) -> None:
        self.selected_index = index
        self.update()

    def _compute_base_rect(self) -> QRectF:
        """计算无缩放、无平移的基准渲染矩形"""
        if not self.pixmap or self.pixmap.isNull():
            return QRectF()
        canvas_w = max(1, self.width() - 24)
        canvas_h = max(1, self.height() - 24)
        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        scale = min(canvas_w / img_w, canvas_h / img_h)
        render_w = img_w * scale
        render_h = img_h * scale
        x = (self.width() - render_w) / 2
        y = (self.height() - render_h) / 2
        return QRectF(x, y, render_w, render_h)

    def _compute_render_rect(self) -> QRectF:
        """计算包含缩放与平移的最终渲染矩形"""
        base = self._compute_base_rect()
        if base.isNull():
            return QRectF()
        center = base.center() + self._pan_offset
        w = base.width() * self._zoom_factor
        h = base.height() * self._zoom_factor
        return QRectF(center.x() - w / 2, center.y() - h / 2, w, h)

    def _reset_view(self) -> None:
        """重置缩放和平移到默认（适配窗口）"""
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self.zoomChanged.emit(self._zoom_factor)

    def _set_zoom(self, factor: float, anchor: Optional[QPointF] = None) -> None:
        """设置缩放倍数，可选以某点为缩放中心"""
        if not self.pixmap or self.pixmap.isNull():
            return
        old_factor = self._zoom_factor
        new_factor = max(0.25, min(4.0, factor))
        if new_factor == old_factor:
            return

        base = self._compute_base_rect()
        if base.isNull():
            return

        if anchor is not None:
            # 以鼠标位置为缩放中心，调整平移偏移量
            old_rect = self._compute_render_rect()
            if old_rect.width() > 0 and old_rect.height() > 0:
                rx = (anchor.x() - old_rect.left()) / old_rect.width()
                ry = (anchor.y() - old_rect.top()) / old_rect.height()
            else:
                rx, ry = 0.5, 0.5

            self._zoom_factor = new_factor
            new_w = base.width() * new_factor
            new_h = base.height() * new_factor
            # 计算新的平移偏移量，使 anchor 位置保持不动
            self._pan_offset = QPointF(
                anchor.x() - base.center().x() + new_w * (0.5 - rx),
                anchor.y() - base.center().y() + new_h * (0.5 - ry),
            )
        else:
            self._zoom_factor = new_factor

        self.zoomChanged.emit(self._zoom_factor)
        self.update()

    def fit_to_window(self) -> None:
        """适配窗口：重置缩放与平移"""
        self._reset_view()
        self.update()

    def reset_view(self) -> None:
        """重置视图：与适配窗口同义"""
        self.fit_to_window()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111214"))

        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#a8a8a8"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignCenter, "打开工程并选择图片")
            return

        self._render_rect = self._compute_render_rect()
        painter.drawPixmap(self._render_rect, self.pixmap, QRectF(self.pixmap.rect()))

        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        sx = self._render_rect.width() / img_w
        sy = self._render_rect.height() / img_h

        for idx, box in enumerate(self.boxes):
            x = self._render_rect.left() + (box.cx - box.w / 2.0) * img_w * sx
            y = self._render_rect.top() + (box.cy - box.h / 2.0) * img_h * sy
            w = box.w * img_w * sx
            h = box.h * img_h * sy

            # 每个框绘制前强制清空画刷，禁止填充
            painter.setBrush(Qt.NoBrush)

            if idx == self.selected_index and idx in self.confirmed_indexes:
                color = QColor("#ff4d4d")
            else:
                color = QColor("#f5a524") if idx == self.selected_index else QColor("#10a37f")
            pen = QPen(color)
            pen.setWidth(3 if idx == self.selected_index else 2)
            painter.setPen(pen)
            painter.drawRect(QRectF(x, y, w, h))

            # 选中框附加高亮（外发光 + 控制点 + 编号）
            if idx == self.selected_index:
                painter.save()
                # 外发光 - 仅边框，不填充
                painter.setBrush(Qt.NoBrush)
                glow_pen = QPen(QColor(0, 170, 255, 120))
                glow_pen.setWidth(6)
                painter.setPen(glow_pen)
                painter.drawRect(QRectF(x - 3, y - 3, w + 6, h + 6))
                # 四角控制点 - 白色不透明小方块
                handle_sz = 6
                corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(Qt.NoPen)
                for (hx, hy) in corners:
                    painter.drawRect(QRectF(hx - handle_sz/2, hy - handle_sz/2, handle_sz, handle_sz))
                # 选中编号文字
                painter.setPen(QColor("#ffffff"))
                painter.setBrush(Qt.NoBrush)
                painter.drawText(QRectF(x + 4, max(self._render_rect.top(), y - 22), 40, 16), Qt.AlignVCenter, f"#{idx}")
                painter.restore()

            # 类别标签背景（只填充标签区域，不碰画布）
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, max(self._render_rect.top(), y - 18), min(110, max(38, w)), 18))
            painter.setPen(QColor("#f2f2f2"))
            painter.setBrush(Qt.NoBrush)
            painter.drawText(QRectF(x + 4, max(self._render_rect.top(), y - 18), 120, 18), Qt.AlignVCenter, box.class_name)

        # 新增框拖拽预览
        if self._is_dragging:
            painter.save()
            painter.setBrush(QColor(16, 163, 127, 40))
            pen = QPen(QColor("#10a37f"))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            rect = QRectF(self._drag_start, self._drag_current).normalized()
            painter.drawRect(rect)
            painter.restore()

    def mousePressEvent(self, event) -> None:
        # 中键拖拽平移
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # 新增框模式
        if self.add_box_mode and event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start = event.position()
            self._drag_current = event.position()
            self.setCursor(Qt.CrossCursor)
            return

        if not self.pixmap or self.pixmap.isNull() or not self.boxes:
            if event.button() == Qt.RightButton:
                self.canvasRightClicked.emit(event.globalPosition().toPoint())
            else:
                self.canvasClicked.emit()
            return

        pt = event.position()
        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        sx = self._render_rect.width() / img_w
        sy = self._render_rect.height() / img_h

        for idx in reversed(range(len(self.boxes))):
            box = self.boxes[idx]
            x = self._render_rect.left() + (box.cx - box.w / 2.0) * img_w * sx
            y = self._render_rect.top() + (box.cy - box.h / 2.0) * img_h * sy
            w = box.w * img_w * sx
            h = box.h * img_h * sy
            if QRectF(x, y, w, h).contains(pt):
                self.selected_index = idx
                self.update()
                if event.button() == Qt.RightButton:
                    self.boxRightClicked.emit(idx, event.globalPosition().toPoint())
                else:
                    self.boxClicked.emit(idx)
                return

        if event.button() == Qt.RightButton:
            self.canvasRightClicked.emit(event.globalPosition().toPoint())
        else:
            self.canvasClicked.emit()

    def mouseMoveEvent(self, event) -> None:
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self._pan_offset += delta
            self.update()
            return
        if self._is_dragging:
            self._drag_current = event.position()
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        if event.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.setCursor(Qt.ArrowCursor)
            self._drag_current = event.position()
            self.update()
            # 计算归一化坐标
            rr = self._render_rect
            if rr.isNull() or rr.width() <= 0 or rr.height() <= 0 or not self.pixmap:
                return
            x1 = max(0.0, min(1.0, (self._drag_start.x() - rr.left()) / rr.width()))
            y1 = max(0.0, min(1.0, (self._drag_start.y() - rr.top()) / rr.height()))
            x2 = max(0.0, min(1.0, (self._drag_current.x() - rr.left()) / rr.width()))
            y2 = max(0.0, min(1.0, (self._drag_current.y() - rr.top()) / rr.height()))
            if abs(x2 - x1) < 0.005 or abs(y2 - y1) < 0.005:
                return
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            w = abs(x2 - x1)
            h = abs(y2 - y1)
            self.dragBoxCreated.emit(cx, cy, w, h)
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        if not self.pixmap or self.pixmap.isNull():
            return
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1.15 if delta > 0 else 1 / 1.15
        self._set_zoom(self._zoom_factor * step, anchor=event.position())

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ctx = WorkbenchContext()
        self.language = getattr(self.ctx, "language", "zh_CN")
        self.selected_box_index = -1
        self.zoom_label = QLabel("缩放: 100%")
        self.zoom_label.setObjectName("subtle")
        self.session_deleted_count = 0
        self.session_class_changed_count = 0
        self.session_confirmed_count = 0
        self.last_save_status = "未保存"
        self.last_save_path = ""
        self.last_backup_path = ""
        self.last_restore_status = "未恢复"
        self.last_restore_source = ""
        self.last_restore_backup_path = ""
        self.undo_stack: list = []
        self.redo_stack: list = []
        self.session_added_count = 0
        self._max_undo = 50
        self.is_dirty = False
        self.dirty_reason = ""
        self.project_scan_results: dict = {}
        self.issue_image_queue: list = []
        self.issue_image_index: int = -1
        self.cross_image_position: int = -1
        self.last_batch_check_summary: str = ""
        self.last_batch_yolo_summary: str = ""
        self.batch_save_plan: list = []
        self.batch_backup_plan: list = []
        self.last_batch_save_count: int = 0
        self.last_batch_backup_dir: str = ""
        self.last_batch_audit: str = ""
        self._max_batch_save = 5
        self.batch_size = 5
        self.batch_plan: list = []
        self.current_batch_index: int = -1
        self.current_batch_items: list = []
        self.last_batch_audit_info: dict = {}
        self._batch_size_options = [5, 10, 20]
        self.batch_progress_items: list = []
        self.batch_audit_index: list = []
        self.multi_batch_count = 3
        self.multi_batch_audit_info: dict = {}

        self.setWindowTitle("OpenAxiom — 数据工作区")
        self.resize(1440, 900)
        self.setStyleSheet(THEME_QSS)

        self._build_ui()
        self._connect()
        self._update_undo_redo_buttons()
        self._set_status("就绪。请打开一个工程以开始。")
        self._update_context_bar()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        top = QFrame()
        top.setObjectName("topBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(12, 8, 12, 8)
        self.title_label = QLabel("OpenAxiom")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.sub_label = QLabel("数据工作区")
        self.sub_label.setObjectName("subtle")
        self.open_btn = QPushButton("打开工程")
        self.save_btn = QPushButton("保存标注")
        self.mode_btn = QPushButton("模式：浏览")
        self.settings_btn = QPushButton("设置")
        self.prev_btn = QPushButton("上一张")
        self.next_btn = QPushButton("下一张")
        top_layout.addWidget(self.title_label)
        top_layout.addWidget(self.sub_label)
        top_layout.addStretch()
        top_layout.addWidget(self.open_btn)
        top_layout.addWidget(self.save_btn)
        top_layout.addWidget(self.mode_btn)
        top_layout.addWidget(self.settings_btn)
        top_layout.addWidget(self.prev_btn)
        top_layout.addWidget(self.next_btn)

        context = QFrame()
        context.setObjectName("contextBar")
        context_layout = QHBoxLayout(context)
        context_layout.setContentsMargins(12, 5, 12, 5)
        self.context_label = QLabel("")
        self.context_label.setObjectName("subtle")
        context_layout.addWidget(self.context_label)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.project_group = QGroupBox("工程")
        pg_layout = QVBoxLayout(self.project_group)
        self.project_label = QLabel("未加载工程")
        self.project_label.setObjectName("subtle")
        self.project_label.setWordWrap(True)
        pg_layout.addWidget(self.project_label)

        self.images_group = QGroupBox("图片")
        ig_layout = QVBoxLayout(self.images_group)
        self.image_list = QListWidget()
        ig_layout.addWidget(self.image_list)

        self.stats_group = QGroupBox("数据集统计")
        st_layout = QVBoxLayout(self.stats_group)
        self.stats_label = QLabel("图片数：0\n标注数：0\n类别数：0")
        self.stats_label.setObjectName("subtle")
        st_layout.addWidget(self.stats_label)

        left_layout.addWidget(self.project_group)
        left_layout.addWidget(self.images_group, 1)
        left_layout.addWidget(self.stats_group)

        center_splitter = QSplitter(Qt.Vertical)
        canvas_wrap = QGroupBox("画布")
        canvas_layout = QVBoxLayout(canvas_wrap)
        self.canvas = ImageCanvas()
        canvas_layout.addWidget(self.canvas)

        table_wrap = QGroupBox("标注")
        table_layout = QVBoxLayout(table_wrap)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["序号", "类别", "名称", "x 中心", "y 中心", "宽/高", "状态"])
        self.table.horizontalHeaderItem(6).setToolTip("状态列仅用于提示当前类别匹配，不影响数据和筛选")
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        table_layout.addWidget(self.table)

        center_splitter.addWidget(canvas_wrap)
        center_splitter.addWidget(table_wrap)
        center_splitter.setStretchFactor(0, 5)
        center_splitter.setStretchFactor(1, 2)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.classes_group = QGroupBox("类别")
        cls_layout = QVBoxLayout(self.classes_group)
        self.class_list = QListWidget()
        cls_layout.addWidget(self.class_list)

        self.box_group = QGroupBox("选中框")
        box_layout = QVBoxLayout(self.box_group)
        self.box_label = QLabel("未选择框")
        self.box_label.setObjectName("subtle")
        self.box_label.setWordWrap(True)
        box_layout.addWidget(self.box_label)

        self.ops_tabs = QTabWidget()
        # Tab 1: 编辑
        edit_tab = QWidget(); el = QVBoxLayout(edit_tab)
        self.add_box_toggle = QPushButton("新增框模式：关闭")
        self.add_box_toggle.setCheckable(True)
        self.add_box_toggle.setToolTip("开启后在画布中拖拽创建新 bbox，松开鼠标后选择类别")
        self.delete_box_btn = QPushButton("删除框")
        self.change_class_btn = QPushButton("修改类别")
        self.undo_btn = QPushButton("撤销"); self.redo_btn = QPushButton("重做")
        el.addWidget(self.add_box_toggle); el.addWidget(self.delete_box_btn)
        el.addWidget(self.change_class_btn); el.addWidget(self.undo_btn); el.addWidget(self.redo_btn)
        # Tab 2: 保存/恢复
        save_tab = QWidget(); sl = QVBoxLayout(save_tab)
        self.pre_save_check_btn = QPushButton("保存前检查")
        self.yolo_preview_btn = QPushButton("YOLO 预览")
        self.safe_save_btn = QPushButton("安全保存当前标签")
        self.safe_save_btn.setToolTip("只操作当前单张 label 文件，会自动备份原 label，需要二次确认")
        self.restore_preview_btn = QPushButton("恢复预览")
        self.restore_preview_btn.setToolTip("预览最近备份与当前 label 的差异，不写文件")
        self.restore_btn = QPushButton("恢复当前标签")
        self.restore_btn.setToolTip("只恢复当前单张 label，恢复前自动备份当前 label，需要二次确认")
        self.mvp_check_btn = QPushButton("MVP 总检查")
        self.mvp_check_btn.setToolTip("检查当前工程是否满足标注 MVP 条件，只读不写文件")
        sl.addWidget(self.pre_save_check_btn); sl.addWidget(self.yolo_preview_btn)
        sl.addWidget(self.safe_save_btn); sl.addWidget(self.restore_preview_btn)
        sl.addWidget(self.restore_btn); sl.addWidget(self.mvp_check_btn)
        # Tab 3: 项目检查
        proj_tab = QWidget(); pl = QVBoxLayout(proj_tab)
        self.project_scan_btn = QPushButton("项目扫描")
        self.project_scan_btn.setToolTip("扫描当前项目所有图片和 label，生成索引")
        self.prev_issue_btn = QPushButton("上一个问题图片")
        self.next_issue_btn = QPushButton("下一个问题图片")
        self.prev_issue_btn.setToolTip("跳转到上一张有问题的图片")
        self.next_issue_btn.setToolTip("跳转到下一张有问题的图片")
        self.batch_check_btn = QPushButton("批量检查 dry-run")
        self.batch_check_btn.setToolTip("对当前项目所有图片执行保存前检查，只读不写")
        self.batch_yolo_btn = QPushButton("批量 YOLO dry-run")
        self.batch_yolo_btn.setToolTip("验证全项目 label 能否生成 YOLO 文本，不写文件")
        self.batch_save_plan_btn = QPushButton("批量保存计划")
        self.batch_save_plan_btn.setToolTip("生成批量保存计划，不写文件")
        self.batch_backup_plan_btn = QPushButton("批量备份计划")
        self.batch_backup_plan_btn.setToolTip("生成批量备份计划，不写文件")
        self.gate_check_btn = QPushButton("全量保存前总门禁")
        self.zero_byte_btn = QPushButton("扫描 0 字节 label")
        self.recent_audit_btn = QPushButton("最近批次审计")
        pl.addWidget(self.project_scan_btn)
        nav_row = QHBoxLayout(); nav_row.addWidget(self.prev_issue_btn); nav_row.addWidget(self.next_issue_btn)
        pl.addLayout(nav_row)
        pl.addWidget(self.batch_check_btn); pl.addWidget(self.batch_yolo_btn)
        pl.addWidget(self.batch_save_plan_btn); pl.addWidget(self.batch_backup_plan_btn)
        pl.addWidget(self.gate_check_btn); pl.addWidget(self.zero_byte_btn); pl.addWidget(self.recent_audit_btn)
        # Tab 4: 分批/多批
        batch_tab = QWidget(); bl = QVBoxLayout(batch_tab)
        self.batch_size_combo = QComboBox(); self.batch_size_combo.addItems(["5", "10", "20"])
        bs_row = QHBoxLayout(); bs_row.addWidget(QLabel("批大小：")); bs_row.addWidget(self.batch_size_combo)
        bl.addLayout(bs_row)
        self.batch_position_label = QLabel("当前批次：- / -"); self.batch_position_label.setObjectName("subtle")
        self.batch_range_label = QLabel("本批范围：-"); self.batch_range_label.setObjectName("subtle")
        bl.addWidget(self.batch_position_label); bl.addWidget(self.batch_range_label)
        self.gen_batch_plan_btn = QPushButton("生成分批计划")
        self.preview_batch_btn = QPushButton("预览当前批")
        self.save_batch_btn = QPushButton("安全保存当前批")
        self.batch_restore_preview_btn2 = QPushButton("当前批恢复预览")
        self.batch_progress_btn = QPushButton("批次进度预览")
        self.retry_check_btn = QPushButton("重试当前批检查")
        self.prev_batch_btn = QPushButton("上一批"); self.next_batch_btn = QPushButton("下一批")
        bl.addWidget(self.gen_batch_plan_btn)
        bnav = QHBoxLayout(); bnav.addWidget(self.prev_batch_btn); bnav.addWidget(self.next_batch_btn)
        bl.addLayout(bnav)
        bl.addWidget(self.preview_batch_btn); bl.addWidget(self.save_batch_btn)
        bl.addWidget(self.batch_restore_preview_btn2); bl.addWidget(self.batch_progress_btn)
        bl.addWidget(self.retry_check_btn)
        self.mb_count_combo = QComboBox(); self.mb_count_combo.addItems(["3", "5", "10", "20"])
        mb_row2 = QHBoxLayout(); mb_row2.addWidget(QLabel("连续执行批次数：")); mb_row2.addWidget(self.mb_count_combo)
        bl.addLayout(mb_row2)
        self.mb_range_label = QLabel("执行范围：-"); self.mb_range_label.setObjectName("subtle")
        self.mb_est_label = QLabel("预计写入：-"); self.mb_est_label.setObjectName("subtle")
        bl.addWidget(self.mb_range_label); bl.addWidget(self.mb_est_label)
        self.mb_preview_btn = QPushButton("多批执行预览")
        self.mb_execute_btn = QPushButton("安全执行多批")
        self.mb_audit_btn = QPushButton("多批执行审计")
        self.mb_zero_check_btn = QPushButton("多批执行后 0 字节复查")
        self.mb_status_btn = QPushButton("停止/中断状态检查")
        bl.addWidget(self.mb_preview_btn); bl.addWidget(self.mb_execute_btn)
        bl.addWidget(self.mb_audit_btn); bl.addWidget(self.mb_zero_check_btn); bl.addWidget(self.mb_status_btn)
        # 旧版按钮
        self.small_batch_save_btn = QPushButton("小批安全保存候选")
        self.small_batch_save_btn.setToolTip("真实写入小批 label，本版本最多 5 张；会自动备份；需要二次确认；不会全量覆盖")
        self.batch_restore_preview_btn = QPushButton("小批恢复预览")
        self.batch_restore_preview_btn.setToolTip("预览最近小批保存的备份，不写文件")
        bl.addWidget(self.small_batch_save_btn); bl.addWidget(self.batch_restore_preview_btn)
        # 组装
        self.ops_tabs.addTab(edit_tab, "编辑")
        self.ops_tabs.addTab(save_tab, "保存/恢复")
        self.ops_tabs.addTab(proj_tab, "项目检查")
        self.ops_tabs.addTab(batch_tab, "分批/多批")

        self.aip_group = QGroupBox("AI 预标注")
        aip_layout = QVBoxLayout(self.aip_group)
        self.aip_label = QLabel("状态：禁用\n基础 URL：未配置")
        self.aip_label.setObjectName("subtle")
        aip_layout.addWidget(self.aip_label)

        # 标注属性面板（最小闭环）
        self.properties_group = QGroupBox("标注属性")
        prop_layout = QVBoxLayout(self.properties_group)
        self.prop_form = QFormLayout()
        self.prop_class = QLabel("-")
        self.prop_conf = QLabel("-")
        self.prop_x = QLabel("-")
        self.prop_y = QLabel("-")
        self.prop_w = QLabel("-")
        self.prop_h = QLabel("-")
        self.prop_id = QLabel("-")
        self.prop_confirm_btn = QPushButton("确认")
        self.prop_delete_btn = QPushButton("删除")
        self.prop_cancel_btn = QPushButton("取消选择")
        self.prop_form.addRow(QLabel("类别名称"), self.prop_class)
        self.prop_form.addRow(QLabel("置信度"), self.prop_conf)
        self.prop_form.addRow(QLabel("坐标 x"), self.prop_x)
        self.prop_form.addRow(QLabel("坐标 y"), self.prop_y)
        self.prop_form.addRow(QLabel("宽度"), self.prop_w)
        self.prop_form.addRow(QLabel("高度"), self.prop_h)
        self.prop_form.addRow(QLabel("标注框 ID"), self.prop_id)
        prop_layout.addLayout(self.prop_form)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.prop_confirm_btn)
        btn_row.addWidget(self.prop_delete_btn)
        btn_row.addWidget(self.prop_cancel_btn)
        prop_layout.addLayout(btn_row)

        # 右侧上下分割
        right_splitter = QSplitter(Qt.Vertical)
        # 上半：类别 + 选中框 + 操作标签页
        right_top = QWidget()
        rtl = QVBoxLayout(right_top)
        rtl.setContentsMargins(0, 0, 0, 0)
        rtl.setSpacing(4)
        self.classes_group.setMaximumHeight(150)
        self.box_group.setMaximumHeight(130)
        rtl.addWidget(self.classes_group, 1)
        rtl.addWidget(self.box_group)
        ops_scroll = QScrollArea()
        ops_scroll.setWidgetResizable(True)
        ops_scroll.setWidget(self.ops_tabs)
        ops_scroll.setFrameShape(QFrame.NoFrame)
        rtl.addWidget(ops_scroll, 2)
        right_splitter.addWidget(right_top)

        # 下半：信息标签页 (AI预标注 / 筛选 / 标注属性)
        self.info_tabs = QTabWidget()
        # AI 预标注标签页
        aip_tab = QWidget(); aip_lt = QVBoxLayout(aip_tab)
        self.aip_label = QLabel("状态：禁用\n基础 URL：未配置")
        self.aip_label.setObjectName("subtle")
        aip_lt.addWidget(self.aip_label)
        aip_lt.addStretch()
        self.info_tabs.addTab(aip_tab, "AI 预标注")
        # 筛选标签页
        filter_tab = QWidget(); fl = QVBoxLayout(filter_tab)
        self.category_filter_combo = QComboBox()
        self.category_filter_combo.addItem("全部类别")
        fl.addWidget(QLabel("类别筛选")); fl.addWidget(self.category_filter_combo)
        self.category_count_label = QLabel("当前类别数量：-")
        self.category_count_label.setObjectName("subtle")
        fl.addWidget(self.category_count_label)
        self.low_conf_spin = QDoubleSpinBox()
        self.low_conf_spin.setRange(0.0, 1.0); self.low_conf_spin.setSingleStep(0.01); self.low_conf_spin.setValue(0.50)
        fl.addWidget(QLabel("低置信度阈值")); fl.addWidget(self.low_conf_spin)
        self.under_conf_cb = QCheckBox("仅低置信度"); fl.addWidget(self.under_conf_cb)
        self.low_conf_count_label = QLabel("低置信度：-"); self.low_conf_count_label.setObjectName("subtle")
        fl.addWidget(self.low_conf_count_label)
        self.review_queue_label = QLabel("待复核：-"); self.review_queue_label.setObjectName("subtle")
        fl.addWidget(self.review_queue_label)
        nav_row = QHBoxLayout()
        self.prev_low_btn = QPushButton("上一个低置信度"); self.next_low_btn = QPushButton("下一个低置信度")
        nav_row.addWidget(self.prev_low_btn); nav_row.addWidget(self.next_low_btn)
        fl.addLayout(nav_row)
        self.confirm_next_btn = QPushButton("确认并下一个"); fl.addWidget(self.confirm_next_btn)
        self.session_summary_label = QLabel("会话摘要：-"); self.session_summary_label.setObjectName("subtle")
        fl.addWidget(self.session_summary_label)
        self.cross_image_label = QLabel("跨图复核：-"); self.cross_image_label.setObjectName("subtle")
        fl.addWidget(self.cross_image_label)
        self.project_stats_label = QLabel("项目统计：-"); self.project_stats_label.setObjectName("subtle")
        fl.addWidget(self.project_stats_label)
        self.info_tabs.addTab(filter_tab, "筛选")
        # 标注属性标签页
        prop_tab = QWidget(); prl = QVBoxLayout(prop_tab)
        self.prop_form = QFormLayout()
        self.prop_class = QLabel("-"); self.prop_conf = QLabel("-"); self.prop_x = QLabel("-")
        self.prop_y = QLabel("-"); self.prop_w = QLabel("-"); self.prop_h = QLabel("-"); self.prop_id = QLabel("-")
        self.prop_confirm_btn = QPushButton("确认"); self.prop_delete_btn = QPushButton("删除")
        self.prop_cancel_btn = QPushButton("取消选择")
        self.prop_form.addRow(QLabel("类别名称"), self.prop_class)
        self.prop_form.addRow(QLabel("置信度"), self.prop_conf)
        self.prop_form.addRow(QLabel("坐标 x"), self.prop_x)
        self.prop_form.addRow(QLabel("坐标 y"), self.prop_y)
        self.prop_form.addRow(QLabel("宽度"), self.prop_w)
        self.prop_form.addRow(QLabel("高度"), self.prop_h)
        self.prop_form.addRow(QLabel("标注框 ID"), self.prop_id)
        prl.addLayout(self.prop_form)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.prop_confirm_btn); btn_row.addWidget(self.prop_delete_btn); btn_row.addWidget(self.prop_cancel_btn)
        prl.addLayout(btn_row)
        prl.addStretch()
        self.info_tabs.addTab(prop_tab, "标注属性")
        # 筛选组框不再单独创建，filter_tab 代替
        # 属性滚动区域不再单独创建，prop_tab 代替

        right_splitter.addWidget(self.info_tabs)
        right_splitter.setStretchFactor(0, 4)
        right_splitter.setStretchFactor(1, 3)
        right_splitter.setSizes([450, 250])
        right_layout.addWidget(right_splitter)

        splitter.addWidget(left)
        splitter.addWidget(center_splitter)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 6)
        splitter.setStretchFactor(2, 2)

        root_layout.addWidget(top)
        root_layout.addWidget(context)
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(root)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.zoom_label = QLabel("缩放: 100%")
        self.zoom_label.setObjectName("subtle")
        self.status.addPermanentWidget(self.zoom_label)

    def _connect(self) -> None:
        self.open_btn.clicked.connect(self.open_project)
        self.save_btn.clicked.connect(self.save_current_labels)
        self.settings_btn.clicked.connect(self.open_settings)
        self.image_list.currentRowChanged.connect(self.on_image_row_changed)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.canvas.boxClicked.connect(self.select_box)
        self.canvas.dragBoxCreated.connect(self._on_drag_box_created)
        self.prev_btn.clicked.connect(self._prev_image)
        self.next_btn.clicked.connect(self._next_image)
        # 右击事件
        self.canvas.boxRightClicked.connect(self.on_box_right_clicked)
        self.canvas.canvasRightClicked.connect(self.on_canvas_right_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_right_clicked)
        # 空白区域取消选中
        self.canvas.canvasClicked.connect(self.clear_selection)
        # 标注属性面板按钮事件
        self.prop_confirm_btn.clicked.connect(self.confirm_current_box)
        self.prop_delete_btn.clicked.connect(self.delete_current_box)
        self.prop_cancel_btn.clicked.connect(self.cancel_selection)
        # 缩放信号
        self.canvas.zoomChanged.connect(self._on_zoom_changed)
        # 类别筛选下拉框
        self.category_filter_combo.currentIndexChanged.connect(self._on_category_filter_changed)
        # 低置信度控件
        self.low_conf_spin.valueChanged.connect(self._on_low_conf_changed)
        self.under_conf_cb.stateChanged.connect(self._on_low_conf_changed)
        # 下一个低置信度按钮
        self.next_low_btn.clicked.connect(self._go_to_next_low_conf)
        self.prev_low_btn.clicked.connect(self._go_to_prev_low_conf)
        self.confirm_next_btn.clicked.connect(self._confirm_and_next)
        # 操作区按钮
        self.change_class_btn.clicked.connect(lambda: self._change_class_via_dialog(self.selected_box_index))
        self.pre_save_check_btn.clicked.connect(self._run_pre_save_check)
        self.yolo_preview_btn.clicked.connect(self._show_yolo_preview)
        self.safe_save_btn.clicked.connect(self._safe_save_current_label)
        self.restore_preview_btn.clicked.connect(self._show_restore_preview)
        self.restore_btn.clicked.connect(self._safe_restore_current_label)
        self.mvp_check_btn.clicked.connect(self._run_mvp_check)
        # 跨图 / 批量按钮
        self.project_scan_btn.clicked.connect(self._run_project_scan)
        self.prev_issue_btn.clicked.connect(self._go_to_prev_issue_image)
        self.next_issue_btn.clicked.connect(self._go_to_next_issue_image)
        self.batch_check_btn.clicked.connect(self._batch_pre_save_check_dry_run)
        self.batch_yolo_btn.clicked.connect(self._batch_yolo_dry_run)
        # 批量保存/备份/恢复
        self.batch_save_plan_btn.clicked.connect(self._generate_batch_save_plan)
        self.batch_backup_plan_btn.clicked.connect(self._generate_batch_backup_plan)
        self.small_batch_save_btn.clicked.connect(self._small_batch_safe_save)
        self.batch_restore_preview_btn.clicked.connect(self._show_batch_restore_preview)
        # 分批控制台
        self.batch_size_combo.currentTextChanged.connect(self._on_batch_size_changed)
        self.gen_batch_plan_btn.clicked.connect(self._generate_batch_plan)
        self.prev_batch_btn.clicked.connect(self._go_to_prev_batch)
        self.next_batch_btn.clicked.connect(self._go_to_next_batch)
        self.preview_batch_btn.clicked.connect(self._preview_current_batch)
        self.save_batch_btn.clicked.connect(self._safe_save_current_batch)
        self.batch_restore_preview_btn2.clicked.connect(self._show_batch_restore_preview)
        self.gate_check_btn.clicked.connect(self._run_full_save_gate_check)
        self.batch_progress_btn.clicked.connect(self._show_batch_progress)
        self.retry_check_btn.clicked.connect(self._retry_current_batch_check)
        self.zero_byte_btn.clicked.connect(self._scan_zero_byte_labels)
        self.recent_audit_btn.clicked.connect(self._show_recent_batch_audit)
        # 多批执行器
        self.mb_count_combo.currentTextChanged.connect(self._on_mb_count_changed)
        self.mb_preview_btn.clicked.connect(self._preview_multi_batch)
        self.mb_execute_btn.clicked.connect(self._safe_execute_multi_batch)
        self.mb_audit_btn.clicked.connect(self._show_multi_batch_audit)
        self.mb_zero_check_btn.clicked.connect(self._post_multi_batch_zero_check)
        self.mb_status_btn.clicked.connect(self._check_multi_batch_status)
        # 撤销/重做
        self.undo_btn.clicked.connect(self._undo)
        self.redo_btn.clicked.connect(self._redo)
        # 新增框模式
        self.add_box_toggle.toggled.connect(self._on_add_box_toggled)

    def _populate_category_filter(self) -> None:
        """从当前图片框提取实际类别名称，填充下拉框（按首次出现顺序）"""
        self.category_filter_combo.blockSignals(True)
        self.category_filter_combo.clear()
        self.category_filter_combo.addItem("全部类别")
        seen = set()
        for box in self.ctx.boxes:
            name = box.class_name
            if name and name not in seen:
                seen.add(name)
                self.category_filter_combo.addItem(name)
        self.category_filter_combo.setCurrentIndex(0)
        self.category_filter_combo.blockSignals(False)
        self._refresh_filter_status_ui()

    def _get_box_conf(self, box) -> float:
        conf = getattr(box, 'conf', None)
        if conf is None:
            conf = getattr(box, 'confidence', None)
        if conf is None:
            return 1.0
        try:
            return float(conf)
        except (ValueError, TypeError):
            return 1.0

    def _is_low_conf_box(self, box) -> bool:
        return self._get_box_conf(box) < self.low_conf_spin.value()

    def _matches_current_category(self, box) -> bool:
        cat_name = self.category_filter_combo.currentText()
        return cat_name == "全部类别" or box.class_name == cat_name

    def _build_low_conf_review_queue(self) -> list[int]:
        if not self.ctx.boxes:
            return []
        return [idx for idx, b in enumerate(self.ctx.boxes)
                if self._matches_current_category(b) and self._is_low_conf_box(b)]

    def _build_pending_review_queue(self) -> list[int]:
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        return [idx for idx in self._build_low_conf_review_queue()
                if idx not in self.confirmed_ids]

    def _update_category_count_label(self) -> None:
        name = self.category_filter_combo.currentText()
        if not self.ctx.boxes or name == "全部类别":
            self.category_count_label.setText("当前类别数量：-")
        else:
            count = sum(1 for b in self.ctx.boxes if b.class_name == name)
            self.category_count_label.setText(f"当前类别数量：{count}")

    def _update_low_conf_label(self) -> None:
        if not self.under_conf_cb.isChecked() or not self.ctx.boxes:
            self.low_conf_count_label.setText("低置信度：-")
            return
        count = len(self._build_low_conf_review_queue())
        self.low_conf_count_label.setText(f"低置信度：{count}")

    def _update_review_queue_label(self) -> None:
        queue = self._build_pending_review_queue()
        if not queue:
            self.review_queue_label.setText("待复核：0 / 0")
            return
        idx = self.selected_box_index
        if idx in queue:
            pos = queue.index(idx) + 1
            self.review_queue_label.setText(f"待复核：{pos} / {len(queue)}")
        else:
            self.review_queue_label.setText(f"待复核：未定位 / {len(queue)}")

    def _update_table_category_markers(self) -> None:
        cat_name = self.category_filter_combo.currentText()
        low_conf_queue = self._build_low_conf_review_queue()
        pending_queue = self._build_pending_review_queue()
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 6)
            if item is None:
                continue
            parts = []
            tips = []
            if cat_name != "全部类别" and row < len(self.ctx.boxes) and self.ctx.boxes[row].class_name == cat_name:
                parts.append("当前类别")
                tips.append("当前类别匹配，仅用于提示，不影响筛选")
            if row in low_conf_queue:
                if row in self.confirmed_ids:
                    parts.append("已确认")
                    tips.append("已人工确认")
                else:
                    parts.append("低置信度")
                    tips.append("置信度低于阈值")
                if row in pending_queue:
                    pos = pending_queue.index(row) + 1
                    parts.append("当前复核")
                    tips.append(f"待复核第 {pos} 项")
            item.setText(" / ".join(parts))
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip("；".join(tips) if tips else "")

    def _refresh_filter_status_ui(self) -> None:
        self._update_category_count_label()
        self._update_low_conf_label()
        self._update_review_queue_label()
        self._update_table_category_markers()
        self._update_session_summary()

    def _get_label_backup_dir(self) -> Path:
        return Path("E:/_AXIOM_BACKUPS/label_backups")

    def _get_label_stem(self) -> str:
        if not self.ctx.current_image_rel:
            return ""
        return Path(self.ctx.current_image_rel).stem

    def _list_label_backups(self, label_stem: str = "") -> list[Path]:
        if not label_stem:
            label_stem = self._get_label_stem()
        if not label_stem:
            return []
        backup_dir = self._get_label_backup_dir()
        if not backup_dir.exists():
            return []
        pattern = f"{label_stem}_*.txt"
        files = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def _find_latest_label_backup(self, label_stem: str = "") -> Path | None:
        files = self._list_label_backups(label_stem)
        return files[0] if files else None

    def _set_dirty(self, reason: str = "") -> None:
        self.is_dirty = True
        if reason:
            self.dirty_reason = reason
        self._update_undo_redo_buttons()

    def _clear_dirty(self) -> None:
        self.is_dirty = False
        self.dirty_reason = ""
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        self.undo_btn.setEnabled(len(self.undo_stack) > 0)
        self.redo_btn.setEnabled(len(self.redo_stack) > 0)
        if not self.undo_stack:
            self.undo_btn.setToolTip("无可撤销操作")
        else:
            self.undo_btn.setToolTip(f"可撤销 {len(self.undo_stack)} 步 (Ctrl+Z)")
        if not self.redo_stack:
            self.redo_btn.setToolTip("无可重做操作")
        else:
            self.redo_btn.setToolTip(f"可重做 {len(self.redo_stack)} 步 (Ctrl+Y)")

    def _update_session_summary(self) -> None:
        total = len(self.ctx.boxes)
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        confirmed = len(self.confirmed_ids)
        pending = len(self._build_pending_review_queue())
        label_path = self._get_current_label_path()
        label_lines = 0
        if label_path and label_path.exists():
            try:
                label_lines = len([l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()])
            except Exception:
                pass
        dirty_text = "未保存" if self.is_dirty else "已保存"
        self.session_summary_label.setText(
            f"框：{total} | 已确认：{confirmed} | 待复核：{pending} | "
            f"已删：{self.session_deleted_count} | 已改：{self.session_class_changed_count} | "
            f"已增：{self.session_added_count} | "
            f"修改：{dirty_text} | 保存：{self.last_save_status} | 恢复：{self.last_restore_status}"
        )

    def _reload_current_image_labels(self) -> None:
        if not self.ctx.current_image_rel:
            return
        self.display_image(self.ctx.current_image_rel)

    def _show_restore_preview(self) -> None:
        if not self.ctx.current_image_rel:
            QMessageBox.information(self, "恢复预览", "当前图片未加载")
            return
        label_path = self._get_current_label_path()
        if not label_path:
            QMessageBox.information(self, "恢复预览", "无法解析 label 路径")
            return
        backup = self._find_latest_label_backup()
        if not backup:
            QMessageBox.information(self, "恢复预览", "当前标签暂无可恢复备份")
            return
        current_lines = []
        if label_path.exists():
            current_lines = [l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        backup_lines = [l for l in backup.read_text(encoding="utf-8").splitlines() if l.strip()]
        same = len(current_lines) == len(backup_lines)
        msg = (
            f"当前 label：{label_path}\n"
            f"最近备份：{backup}\n\n"
            f"当前行数：{len(current_lines)}\n"
            f"备份行数：{len(backup_lines)}\n"
            f"行数一致：{'是' if same else '否'}\n\n"
            f"当前前 10 行：\n" + "\n".join(current_lines[:10]) + "\n\n"
            f"备份前 10 行：\n" + "\n".join(backup_lines[:10])
        )
        QMessageBox.information(self, "恢复预览（dry-run）", msg)
        self._set_status(f"恢复预览：备份={backup.name}；当前={len(current_lines)} 行；备份={len(backup_lines)} 行")

    def _safe_restore_current_label(self) -> None:
        if not self.ctx.current_image_rel:
            QMessageBox.critical(self, "恢复失败", "当前图片未加载")
            return
        label_path = self._get_current_label_path()
        if not label_path:
            QMessageBox.critical(self, "恢复失败", "无法解析 label 路径")
            return
        backup = self._find_latest_label_backup()
        if not backup:
            QMessageBox.information(self, "恢复失败", "当前标签暂无可恢复备份")
            return
        current_lines = []
        if label_path.exists():
            current_lines = [l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        backup_lines = [l for l in backup.read_text(encoding="utf-8").splitlines() if l.strip()]
        pre_restore_backup_dir = self._get_label_backup_dir()
        pre_restore_backup_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = self._get_label_stem()
        pre_name = f"{stem}_{ts}_restore_before.txt"
        pre_path = pre_restore_backup_dir / pre_name
        if label_path.exists():
            import shutil
            shutil.copy2(str(label_path), str(pre_path))
            if not pre_path.exists():
                QMessageBox.critical(self, "恢复前备份失败", f"恢复前备份未生成：{pre_path}")
                return
        confirm_msg = (
            f"将真实恢复当前单张 label 文件：\n\n"
            f"目标路径：{label_path}\n"
            f"恢复来源备份：{backup}\n"
            f"恢复前自动备份：{pre_path}\n"
            f"当前行数：{len(current_lines)}\n"
            f"备份行数：{len(backup_lines)}\n\n"
            f"将真实覆盖当前单张 label 文件。确认？"
        )
        reply = QMessageBox.question(self, "确认恢复", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self._set_status("恢复已取消")
            return
        try:
            text = backup.read_text(encoding="utf-8")
            label_path.write_text(text, encoding="utf-8")
        except Exception as exc:
            self.last_restore_status = "失败"
            QMessageBox.critical(self, "恢复写入失败", f"写入 label 失败：{exc}")
            self._refresh_filter_status_ui()
            return
        verify_ok = True
        try:
            restored = [l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            if len(restored) != len(backup_lines):
                verify_ok = False
            for rl in restored:
                parts = rl.split()
                if len(parts) < 5:
                    verify_ok = False
                    break
                try:
                    float(parts[0]); float(parts[1]); float(parts[2]); float(parts[3]); float(parts[4])
                except (ValueError, TypeError):
                    verify_ok = False
                    break
        except Exception:
            verify_ok = False
        if not verify_ok:
            self.last_restore_status = "校验失败"
            QMessageBox.warning(self, "恢复校验失败", f"恢复写入完成但校验异常，恢复前备份：{pre_path}")
        else:
            self.last_restore_status = "成功"
        self.last_restore_source = str(backup)
        self.last_restore_backup_path = str(pre_path)
        self._clear_dirty()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_undo_redo_buttons()
        self._set_status(f"恢复成功：来源={backup.name}；恢复前备份={pre_path.name}")
        self._reload_current_image_labels()
        QMessageBox.information(self, "恢复完成",
            f"恢复成功\n\n当前 label：{label_path}\n来源备份：{backup}\n恢复前备份：{pre_path}\n行数：{len(backup_lines)}")

    def _run_mvp_check(self) -> None:
        blocks = []
        warns = []
        passes = []
        label_path = self._get_current_label_path()
        # BLOCK checks
        if not self.ctx.current_image_rel:
            blocks.append("当前图片未加载")
        else:
            passes.append("当前图片已加载")
        if not self.ctx.label_root:
            blocks.append("label_root 不存在")
        else:
            passes.append("label_root 存在")
        if label_path is None:
            blocks.append("label 路径不可解析")
        elif not label_path.exists():
            blocks.append("label 文件不存在")
        else:
            passes.append("label 文件存在")
        if not self.ctx.boxes:
            warns.append("boxes 为空")
        else:
            passes.append(f"boxes={len(self.ctx.boxes)}")
        check_result = self._run_pre_save_check_core()
        if check_result['level'] == 'BLOCK':
            blocks.append(f"保存前检查 BLOCK（{len(check_result['issues'])} 个错误）")
        else:
            passes.append(f"保存前检查 {check_result['level']}")
        try:
            yolo_lines = self._build_yolo_lines()
            passes.append(f"YOLO 可生成 {len(yolo_lines)} 行")
            if self.ctx.boxes and len(yolo_lines) != len(self.ctx.boxes):
                blocks.append(f"YOLO 行数 ({len(yolo_lines)}) 与 boxes 数量 ({len(self.ctx.boxes)}) 不一致")
        except Exception:
            blocks.append("YOLO 预览生成失败")
        backup = self._find_latest_label_backup()
        if backup:
            passes.append("最近备份存在")
        else:
            blocks.append("无最近备份，恢复能力不可用")
        # WARN checks
        pending = check_result["info"].get("pending_review", 0)
        if pending:
            warns.append(f"待复核队列未完成（{pending} 个）")
        if self.is_dirty:
            warns.append(f"当前图片有未保存修改（{self.dirty_reason}）")
        if self.last_save_status == "未保存":
            warns.append("当前图片未保存")
        if self.last_save_status == "失败":
            warns.append("最近保存失败")
        if self.last_restore_status == "未恢复":
            warns.append("未执行过恢复")
        if self.canvas.add_box_mode:
            warns.append("新增框模式已开启")
        if self.undo_stack:
            warns.append(f"撤销栈有 {len(self.undo_stack)} 步")
        if self.redo_stack:
            warns.append(f"重做栈有 {len(self.redo_stack)} 步")
        # PASS capability checks
        passes.append("安全保存能力可用")
        passes.append("安全恢复能力可用")
        passes.append("自动备份能力可用")
        passes.append("恢复预览能力可用")
        passes.append("撤销重做能力可用")
        passes.append("新增框能力可用")
        passes.append("MVP 总检查能力可用")
        label_lines = 0
        if label_path and label_path.exists():
            try:
                label_lines = len([l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()])
            except Exception:
                pass
        passes.append(f"当前 label 行数={label_lines}")
        # Determine level
        if blocks:
            level = "BLOCK"
        elif warns:
            level = "WARN"
        else:
            level = "PASS"
        # Build message
        msg = f"MVP 总检查：{level}\n\n"
        msg += f"通过 ({len(passes)})：\n" + "\n".join(f"  ✅ {x}" for x in passes) + "\n"
        if warns:
            msg += f"\n警告 ({len(warns)})：\n" + "\n".join(f"  ⚠️ {x}" for x in warns) + "\n"
        if blocks:
            msg += f"\n阻塞 ({len(blocks)})：\n" + "\n".join(f"  ❌ {x}" for x in blocks) + "\n"
        self._set_status(f"MVP 总检查：{level}；通过={len(passes)}；警告={len(warns)}；阻塞={len(blocks)}")
        QMessageBox.information(self, f"MVP 总检查结果（{level}）", msg)

    def _run_pre_save_check_core(self) -> dict:
        result = {"level": "PASS", "issues": [], "warnings": [], "info": {}}
        if not self.ctx.current_image_rel:
            result["issues"].append("当前图片未加载")
            result["level"] = "BLOCK"
        if not self.ctx.label_root:
            result["issues"].append("label_root 不存在")
            result["level"] = "BLOCK"
        boxes = self.ctx.boxes
        result["info"]["boxes_count"] = len(boxes)
        if not boxes:
            result["warnings"].append("boxes 为空")
        else:
            bad_class_id = 0
            bad_class_name = 0
            bad_coord = 0
            bad_cxcy = 0
            bad_wh = 0
            bad_wh_zero = 0
            tiny_box = 0
            class_names = getattr(self.ctx, 'class_names', [])
            for b in boxes:
                if not isinstance(b.class_id, int):
                    bad_class_id += 1
                elif class_names and b.class_id not in range(len(class_names)):
                    bad_class_id += 1
                if not b.class_name:
                    bad_class_name += 1
                try:
                    cx, cy, w, h = float(b.cx), float(b.cy), float(b.w), float(b.h)
                except (ValueError, TypeError):
                    bad_coord += 1
                    continue
                if not (0 <= cx <= 1) or not (0 <= cy <= 1):
                    bad_cxcy += 1
                if w <= 0 or h <= 0:
                    bad_wh_zero += 1
                elif w > 1 or h > 1:
                    bad_wh += 1
                if w < 0.001 or h < 0.001:
                    tiny_box += 1
            if bad_class_id:
                result["issues"].append(f"{bad_class_id} 个框 class_id 异常")
                result["level"] = "BLOCK"
            if bad_coord:
                result["issues"].append(f"{bad_coord} 个框坐标非数字")
                result["level"] = "BLOCK"
            if bad_wh_zero:
                result["issues"].append(f"{bad_wh_zero} 个框 w/h <= 0")
                result["level"] = "BLOCK"
            if bad_cxcy:
                result["warnings"].append(f"{bad_cxcy} 个框 cx/cy 超出 0~1")
            if bad_wh:
                result["warnings"].append(f"{bad_wh} 个框 w/h > 1")
            if bad_class_name:
                result["warnings"].append(f"{bad_class_name} 个框 class_name 为空")
            if tiny_box:
                result["warnings"].append(f"{tiny_box} 个框宽高过小 (<0.001)")
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        result["info"]["confirmed"] = len(self.confirmed_ids)
        pending = len(self._build_pending_review_queue())
        result["info"]["pending_review"] = pending
        if pending:
            result["warnings"].append(f"待复核队列未完成（{pending} 个）")
        if not result["issues"] and result["warnings"]:
            if result["level"] == "PASS":
                result["level"] = "WARN"
        return result

    def _run_pre_save_check(self) -> None:
        result = self._run_pre_save_check_core()
        boxes = self.ctx.boxes
        pending = result["info"].get("pending_review", 0)
        all_issues = result["issues"] + result["warnings"]
        message = f"保存前检查：{len(boxes)} 框\n级别：{result['level']}"
        if result["issues"]:
            message += "\n\n禁止保存：\n" + "\n".join(f"  • {x}" for x in result["issues"])
        if result["warnings"]:
            message += "\n\n警告：\n" + "\n".join(f"  • {x}" for x in result["warnings"])
        if not all_issues:
            message += "\n\n全部通过"
        self._set_status(f"保存前检查：{result['level']}；boxes={len(boxes)}；待复核={pending}")
        QMessageBox.information(self, "保存前检查结果", message)

    def _get_current_label_path(self):
        if not self.ctx.current_image_rel or not self.ctx.label_root:
            return None
        return self.ctx.label_root / (Path(self.ctx.current_image_rel).stem + ".txt")

    def _build_yolo_lines(self) -> list[str]:
        lines = []
        for b in self.ctx.boxes:
            class_id = b.class_id if isinstance(b.class_id, int) else 0
            lines.append(f"{class_id} {b.cx:.6f} {b.cy:.6f} {b.w:.6f} {b.h:.6f}")
        return lines

    def _show_yolo_preview(self) -> None:
        if not self.ctx.current_image_rel:
            QMessageBox.information(self, "YOLO 预览", "当前图片未加载")
            return
        if not self.ctx.label_root:
            QMessageBox.information(self, "YOLO 预览", "label_root 不存在")
            return
        lines = self._build_yolo_lines()
        label_path = self._get_current_label_path()
        preview = "\n".join(lines[:20])
        if len(lines) > 20:
            preview += f"\n... 共 {len(lines)} 行，仅显示前 20 行"
        result = self._run_pre_save_check_core()
        pending = result["info"].get("pending_review", 0)
        msg = (
            f"目标路径：{label_path}\n"
            f"行数：{len(lines)}\n"
            f"保存前检查：{result['level']}\n"
            f"待复核：{pending}\n\n"
            f"预览（前 20 行）：\n{preview}"
        )
        QMessageBox.information(self, "YOLO 标签预览（dry-run）", msg)
        self._set_status(f"YOLO 预览：{len(lines)} 行；保存前检查={result['level']}")

    def _backup_original_label(self, label_path) -> str:
        import shutil
        from datetime import datetime
        backup_dir = Path("E:/_AXIOM_BACKUPS/label_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = Path(self.ctx.current_image_rel).stem if self.ctx.current_image_rel else "unknown"
        if label_path and label_path.exists():
            backup_name = f"{stem}_{ts}_backup.txt"
            backup_path = backup_dir / backup_name
            shutil.copy2(str(label_path), str(backup_path))
            if not backup_path.exists():
                raise RuntimeError(f"备份文件未生成：{backup_path}")
            if backup_path.stat().st_size == 0 and label_path.stat().st_size > 0:
                raise RuntimeError(f"备份文件为空，但原文件有内容：{backup_path}")
        else:
            backup_name = f"{stem}_{ts}_missing.txt"
            backup_path = backup_dir / backup_name
            missing_note = f"原 label 不存在，保存前无可备份文件。\nlabel_path={label_path}\nimage_rel={self.ctx.current_image_rel}\ntimestamp={ts}"
            backup_path.write_text(missing_note, encoding="utf-8")
            if not backup_path.exists():
                raise RuntimeError(f"缺失标记文件未生成：{backup_path}")
        self.last_backup_path = str(backup_path)
        return str(backup_path)

    def _safe_save_current_label(self) -> None:
        # Step 1: basic checks
        if not self.ctx.current_image_rel:
            QMessageBox.critical(self, "保存失败", "当前图片未加载")
            return
        if not self.ctx.label_root:
            QMessageBox.critical(self, "保存失败", "label_root 不存在")
            return
        label_path = self._get_current_label_path()
        if label_path is None:
            QMessageBox.critical(self, "保存失败", "无法确定 label 路径")
            return
        # Step 2: pre-save check
        result = self._run_pre_save_check_core()
        if result["level"] == "BLOCK":
            msg = "保存前检查存在严重错误，禁止保存：\n" + "\n".join(f"  • {x}" for x in result["issues"])
            QMessageBox.critical(self, "禁止保存", msg)
            return
        # Step 3: secondary confirm
        pending = result["info"].get("pending_review", 0)
        warn_text = ""
        if result["warnings"]:
            warn_text = "\n\n警告：\n" + "\n".join(f"  • {x}" for x in result["warnings"])
        backup_dir = "E:/_AXIOM_BACKUPS/label_backups"
        confirm_msg = (
            f"将真实写入当前单张 label 文件：\n\n"
            f"目标路径：{label_path}\n"
            f"boxes 数量：{len(self.ctx.boxes)}\n"
            f"待复核：{pending}\n"
            f"检查级别：{result['level']}\n"
            f"备份目录：{backup_dir}\n"
            f"{warn_text}\n\n"
            f"确认写入？"
        )
        reply = QMessageBox.question(self, "确认保存", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self._set_status("保存已取消")
            return
        # Step 4: backup original
        try:
            backup_path = self._backup_original_label(label_path)
        except Exception as exc:
            QMessageBox.critical(self, "备份失败", f"备份原 label 失败，禁止保存：{exc}")
            return
        # Step 5: write new label
        try:
            lines = self._build_yolo_lines()
            text = "\n".join(lines) + ("\n" if lines else "")
            with open(str(label_path), "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as exc:
            self.last_save_status = "失败"
            err = f"写入失败：{exc}\n备份位于：{backup_path}"
            QMessageBox.critical(self, "写入失败", err)
            self._refresh_filter_status_ui()
            return
        # Step 6: verify written file
        verify_ok = True
        try:
            with open(str(label_path), "r", encoding="utf-8") as f:
                written_lines = f.readlines()
            written_count = len([l for l in written_lines if l.strip()])
            if written_count != len(self.ctx.boxes):
                verify_ok = False
            for wl in written_lines:
                wl = wl.strip()
                if not wl:
                    continue
                parts = wl.split()
                if len(parts) < 5:
                    verify_ok = False
                    break
                try:
                    float(parts[0])
                    float(parts[1])
                    float(parts[2])
                    float(parts[3])
                    float(parts[4])
                except (ValueError, TypeError):
                    verify_ok = False
                    break
        except Exception:
            verify_ok = False
        if not verify_ok:
            self.last_save_status = "校验失败"
            QMessageBox.warning(self, "校验失败",
                f"写入完成但校验异常，备份位于：{backup_path}")
        else:
            self.last_save_status = "成功"
            self._clear_dirty()
        self.last_save_path = str(label_path)
        self._set_status(f"保存成功：lines={len(self.ctx.boxes)}；backup={backup_path}")
        self._refresh_filter_status_ui()
        QMessageBox.information(self, "保存完成",
            f"保存成功\n\n路径：{label_path}\n行数：{len(lines)}\n备份：{backup_path}")

    def _update_cross_image_label(self) -> None:
        total = len(self.issue_image_queue)
        if total == 0:
            self.cross_image_label.setText("跨图复核：-")
            return
        pos = self.issue_image_index + 1
        self.cross_image_label.setText(f"跨图复核：{pos} / {total}")

    def _update_project_stats_from_scan(self) -> None:
        if not self.project_scan_results:
            self.project_stats_label.setText("项目统计：-")
            return
        r = self.project_scan_results
        issues = len(self.issue_image_queue)
        self.project_stats_label.setText(
            f"项目统计：{r.get('total_images', 0)} 图 | {r.get('total_labels', 0)} label | "
            f"{r.get('total_boxes', 0)} boxes | 问题图={issues}"
        )

    def _run_project_scan(self) -> None:
        if not self.ctx.image_list:
            QMessageBox.information(self, "项目扫描", "当前项目无图片列表，请先打开工程")
            return
        from core.label_manager import load_labels, label_path_for_image
        total_images = len(self.ctx.image_list)
        total_labels = 0
        missing_labels = 0
        empty_labels = 0
        total_boxes = 0
        issue_images = []
        for rel in self.ctx.image_list:
            label_path = label_path_for_image(self.ctx.label_root, rel) if self.ctx.label_root else None
            path_ok = label_path and label_path.exists()
            boxes = []
            if path_ok:
                try:
                    boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
                except Exception:
                    boxes = []
            if not path_ok:
                missing_labels += 1
                issue_images.append((rel, "缺失 label"))
            elif not boxes:
                empty_labels += 1
                issue_images.append((rel, "空 label"))
            total_boxes += len(boxes)
            total_labels += 1
        self.project_scan_results = {
            "total_images": total_images,
            "total_labels": total_labels,
            "missing_labels": missing_labels,
            "empty_labels": empty_labels,
            "total_boxes": total_boxes,
        }
        self.issue_image_queue = [rel for rel, _ in issue_images]
        self.issue_image_index = -1
        self._update_project_stats_from_scan()
        self._update_cross_image_label()
        msg = (
            f"项目扫描完成\n\n"
            f"图片总数：{total_images}\n"
            f"label 数：{total_labels}\n"
            f"缺失 label：{missing_labels}\n"
            f"空 label：{empty_labels}\n"
            f"总 boxes：{total_boxes}\n"
            f"问题图片：{len(self.issue_image_queue)}"
        )
        QMessageBox.information(self, "项目扫描结果", msg)
        self._set_status(f"项目扫描完成：{total_images} 图，{total_boxes} boxes，{len(self.issue_image_queue)} 问题图")

    def _navigate_to_issue_image(self, rel: str) -> None:
        if not self._confirm_discard_changes():
            return
        self.display_image(rel)
        self._update_cross_image_label()

    def _go_to_next_issue_image(self) -> None:
        if not self.issue_image_queue:
            self._set_status("暂未进行项目扫描或没有问题图片")
            return
        next_idx = self.issue_image_index + 1
        if next_idx >= len(self.issue_image_queue):
            self._set_status("已到达最后一张问题图片")
            return
        self.issue_image_index = next_idx
        rel = self.issue_image_queue[self.issue_image_index]
        self._navigate_to_issue_image(rel)

    def _go_to_prev_issue_image(self) -> None:
        if not self.issue_image_queue:
            self._set_status("暂未进行项目扫描或没有问题图片")
            return
        prev_idx = self.issue_image_index - 1
        if prev_idx < 0:
            self._set_status("已到达第一张问题图片")
            return
        self.issue_image_index = prev_idx
        rel = self.issue_image_queue[self.issue_image_index]
        self._navigate_to_issue_image(rel)

    def _batch_pre_save_check_dry_run(self) -> None:
        if not self.ctx.image_list:
            QMessageBox.information(self, "批量检查", "当前项目无图片列表")
            return
        from core.label_manager import load_labels, label_path_for_image
        total = len(self.ctx.image_list)
        pass_count = 0
        warn_count = 0
        block_count = 0
        missing_label_count = 0
        empty_label_count = 0
        coord_issue_count = 0
        class_id_issue_count = 0
        pending_review_count = 0
        low_conf_count = 0
        warn_block_list = []
        for rel in self.ctx.image_list:
            label_path = label_path_for_image(self.ctx.label_root, rel) if self.ctx.label_root else None
            if not label_path or not label_path.exists():
                missing_label_count += 1
                block_count += 1
                warn_block_list.append((rel, "缺失 label"))
                continue
            try:
                boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
            except Exception:
                block_count += 1
                warn_block_list.append((rel, "label 加载失败"))
                continue
            if not boxes:
                empty_label_count += 1
                warn_count += 1
                warn_block_list.append((rel, "空 label"))
                continue
            issues = []
            has_pending = False
            for b in boxes:
                conf = getattr(b, 'conf', None)
                if conf is None:
                    conf = getattr(b, 'confidence', None)
                if conf is not None:
                    try:
                        if float(conf) < self.low_conf_spin.value():
                            low_conf_count += 1
                            has_pending = True
                    except Exception:
                        pass
                if not isinstance(b.class_id, int):
                    class_id_issue_count += 1
                    issues.append("class_id 异常")
                try:
                    cx, cy, w, h = float(b.cx), float(b.cy), float(b.w), float(b.h)
                    if w <= 0 or h <= 0:
                        coord_issue_count += 1
                        issues.append("w/h <= 0")
                    if not (0 <= cx <= 1) or not (0 <= cy <= 1):
                        coord_issue_count += 1
                except (ValueError, TypeError):
                    coord_issue_count += 1
                    issues.append("坐标非数字")
            if has_pending:
                pending_review_count += 1
            if issues:
                block_count += 1
                warn_block_list.append((rel, "; ".join(issues)))
            else:
                pass_count += 1
        self.last_batch_check_summary = f"PASS={pass_count} WARN={warn_count} BLOCK={block_count}"
        msg = (
            f"批量保存前检查 dry-run 完成\n\n"
            f"总图片：{total}\n"
            f"PASS：{pass_count}\n"
            f"WARN：{warn_count}\n"
            f"BLOCK：{block_count}\n"
            f"缺失 label：{missing_label_count}\n"
            f"空 label：{empty_label_count}\n"
            f"坐标异常：{coord_issue_count}\n"
            f"class_id 异常：{class_id_issue_count}\n"
            f"待复核图片：{pending_review_count}\n"
            f"低置信度图片：{low_conf_count}\n"
        )
        if warn_block_list:
            msg += f"\n前 20 个 WARN/BLOCK 图片：\n"
            for rel, reason in warn_block_list[:20]:
                msg += f"  • {rel}: {reason}\n"
        QMessageBox.information(self, "批量检查结果 (dry-run)", msg)
        self._set_status(f"批量检查：{self.last_batch_check_summary}")

    def _batch_yolo_dry_run(self) -> None:
        if not self.ctx.image_list:
            QMessageBox.information(self, "批量 YOLO", "当前项目无图片列表")
            return
        from core.label_manager import load_labels, label_path_for_image
        total = len(self.ctx.image_list)
        ok_count = 0
        fail_count = 0
        total_lines = 0
        max_boxes = 0
        max_boxes_rel = ""
        min_boxes = 10**9
        min_boxes_rel = ""
        failures = []
        for rel in self.ctx.image_list:
            try:
                boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
            except Exception:
                fail_count += 1
                failures.append((rel, "label 加载失败"))
                continue
            if not boxes:
                fail_count += 1
                failures.append((rel, "空 label"))
                continue
            n = len(boxes)
            ok_count += 1
            total_lines += n
            if n > max_boxes:
                max_boxes = n
                max_boxes_rel = rel
            if n < min_boxes:
                min_boxes = n
                min_boxes_rel = rel
        self.last_batch_yolo_summary = f"OK={ok_count} FAIL={fail_count} 行={total_lines}"
        msg = (
            f"批量 YOLO dry-run 完成\n\n"
            f"总图片：{total}\n"
            f"可生成：{ok_count}\n"
            f"生成失败：{fail_count}\n"
            f"总行数：{total_lines}\n"
            f"最大 boxes：{max_boxes}（{max_boxes_rel}）\n"
            f"最小 boxes：{min_boxes if min_boxes < 10**9 else 0}（{min_boxes_rel}）\n"
        )
        if failures:
            msg += f"\n前 20 个失败项：\n"
            for rel, reason in failures[:20]:
                msg += f"  • {rel}: {reason}\n"
        QMessageBox.information(self, "批量 YOLO 结果 (dry-run)", msg)
        self._set_status(f"批量 YOLO：{self.last_batch_yolo_summary}")

    def _generate_batch_save_plan(self) -> None:
        if not self.ctx.image_list:
            QMessageBox.information(self, "批量保存计划", "当前项目无图片列表")
            return
        if not self.project_scan_results:
            QMessageBox.information(self, "批量保存计划", "请先执行项目扫描")
            return
        from core.label_manager import load_labels, label_path_for_image
        total = len(self.ctx.image_list)
        pass_list = []
        warn_list = []
        block_list = []
        for rel in self.ctx.image_list:
            label_path = label_path_for_image(self.ctx.label_root, rel) if self.ctx.label_root else None
            if not label_path or not label_path.exists():
                block_list.append((rel, "缺失 label"))
                continue
            try:
                boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
            except Exception:
                block_list.append((rel, "label 加载失败"))
                continue
            if not boxes:
                warn_list.append((rel, "空 label", 0))
                continue
            yolo_lines = len(boxes)
            pass_list.append((rel, str(label_path), len(boxes), yolo_lines))
        self.batch_save_plan = {"pass": pass_list, "warn": warn_list, "block": block_list}
        msg = (
            f"批量保存计划 (dry-run)\n\n"
            f"总图片：{total}\n"
            f"PASS 可保存：{len(pass_list)}\n"
            f"WARN 排除：{len(warn_list)}\n"
            f"BLOCK 排除：{len(block_list)}\n"
            f"预计写入 label 数：{len(pass_list)}\n"
            f"预计 YOLO 总行数：{sum(x[2] for x in pass_list)}\n"
        )
        if pass_list:
            msg += f"\n前 20 个候选项：\n"
            for rel, lp, n, yl in pass_list[:20]:
                msg += f"  {rel} ({n} boxes, {yl} 行)\n"
        QMessageBox.information(self, "批量保存计划结果", msg)
        self._set_status(f"批量保存计划：PASS={len(pass_list)} WARN={len(warn_list)} BLOCK={len(block_list)}")

    def _generate_batch_backup_plan(self) -> None:
        if not self.batch_save_plan or not self.batch_save_plan.get("pass"):
            QMessageBox.information(self, "批量备份计划", "请先生成批量保存计划")
            return
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = Path(f"E:/_AXIOM_BACKUPS/label_backups_batch/{ts}")
        plan_items = []
        for rel, lp, n, yl in self.batch_save_plan["pass"]:
            label_path = Path(lp)
            stem = label_path.stem
            backup_name = f"{stem}_{ts}_batch_backup.txt"
            backup_path = backup_root / backup_name
            exists = label_path.exists()
            readable = label_path.is_file() if exists else False
            plan_items.append((rel, lp, str(backup_path), exists, readable))
        self.batch_backup_plan = {"root": str(backup_root), "items": plan_items}
        backup_root_str = str(backup_root)
        can_backup = sum(1 for _, _, _, e, r in plan_items if e and r)
        missing = sum(1 for _, _, _, e, _ in plan_items if not e)
        msg = (
            f"批量备份计划 (dry-run)\n\n"
            f"备份目录：{backup_root_str}\n"
            f"待备份 label 数：{len(plan_items)}\n"
            f"可备份数：{can_backup}\n"
            f"缺失 label 数：{missing}\n"
            f"路径冲突数：0 (时间戳确保唯一)\n"
        )
        if plan_items:
            msg += f"\n前 10 个备份项：\n"
            for rel, lp, bp, e, r in plan_items[:10]:
                status = "可备份" if e and r else ("缺失" if not e else "不可读")
                msg += f"  {rel} -> {Path(bp).name} [{status}]\n"
        QMessageBox.information(self, "批量备份计划结果", msg)
        self._set_status(f"批量备份计划：可备份={can_backup} 缺失={missing}")

    def _run_batch_save_gate_check(self) -> str:
        if not self.project_scan_results:
            return "请先执行项目扫描"
        if not self.last_batch_check_summary:
            return "请先执行批量检查 dry-run"
        if not self.last_batch_yolo_summary:
            return "请先执行批量 YOLO dry-run"
        if not self.batch_save_plan:
            return "请先生成批量保存计划"
        if not self.batch_backup_plan:
            return "请先生成批量备份计划"
        pass_count = len(self.batch_save_plan.get("pass", []))
        if pass_count == 0:
            return "没有可保存的 PASS 候选"
        block_count = len(self.batch_save_plan.get("block", []))
        if block_count > 0:
            return f"{block_count} 个 BLOCK 项被排除，无法批量保存"
        return ""

    def _small_batch_safe_save(self) -> None:
        gate = self._run_batch_save_gate_check()
        if gate:
            QMessageBox.critical(self, "批量保存门禁", gate)
            return
        candidates = self.batch_save_plan.get("pass", [])[:self._max_batch_save]
        if not candidates:
            QMessageBox.information(self, "小批保存", "无候选可保存")
            return
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = Path(f"E:/_AXIOM_BACKUPS/label_backups_batch/{ts}")
        backup_root.mkdir(parents=True, exist_ok=True)
        N = len(candidates)
        confirm_msg = (
            f"将真实写入小批 label（最多 5 张）：\n\n"
            f"本版本不是全量批量保存。\n"
            f"本版本最多真实保存 {self._max_batch_save} 张。\n\n"
            f"将写入 {N} 个 label：\n"
        )
        for rel, lp, n, yl in candidates:
            confirm_msg += f"  • {rel} ({n} boxes, {yl} 行)\n"
        confirm_msg += f"\n批量备份目录：{backup_root}\n\n确认写入？"
        reply = QMessageBox.question(self, "确认小批保存", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self._set_status("小批保存已取消")
            return
        import shutil
        success_list = []
        fail_list = []
        for rel, lp, n, yl in candidates:
            label_path = Path(lp)
            stem = label_path.stem
            backup_name = f"{stem}_{ts}_batch_backup.txt"
            backup_path = backup_root / backup_name
            try:
                if label_path.exists():
                    shutil.copy2(str(label_path), str(backup_path))
                    if not backup_path.exists():
                        raise RuntimeError(f"备份未生成：{backup_path}")
                else:
                    backup_path.write_text(f"原 label 不存在，小批保存前无可备份文件。\nlabel_path={label_path}", encoding="utf-8")
            except Exception as exc:
                fail_list.append((rel, f"备份失败：{exc}"))
                continue
            try:
                boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
                lines = [f"{b.class_id if isinstance(b.class_id, int) else 0} {b.cx:.6f} {b.cy:.6f} {b.w:.6f} {b.h:.6f}" for b in boxes]
                text = "\n".join(lines) + ("\n" if lines else "")
                label_path.write_text(text, encoding="utf-8")
                written = [l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                ok = len(written) == len(boxes)
                for wl in written:
                    parts = wl.split()
                    if len(parts) < 5:
                        ok = False
                        break
                if not ok:
                    raise RuntimeError("校验失败")
                success_list.append((rel, len(lines)))
            except Exception as exc:
                fail_list.append((rel, f"写入失败：{exc}"))
        self.last_batch_save_count = len(success_list)
        self.last_batch_backup_dir = str(backup_root)
        msg = f"小批保存审计\n批次：{ts}\n\n成功写入：{len(success_list)}\n失败：{len(fail_list)}\n备份目录：{backup_root}\n"
        if success_list:
            msg += "\n成功项：\n" + "\n".join(f"  ✅ {rel} ({n} 行)" for rel, n in success_list)
        if fail_list:
            msg += "\n失败项：\n" + "\n".join(f"  ❌ {rel}: {reason}" for rel, reason in fail_list)
        msg += "\n\n本版本不是全量批量保存。最多真实保存 5 张。"
        self.last_batch_audit = msg
        QMessageBox.information(self, "小批保存审计", msg)
        self._set_status(f"小批保存完成：成功={len(success_list)} 失败={len(fail_list)}")

    def _show_batch_restore_preview(self) -> None:
        if not self.last_batch_backup_dir:
            QMessageBox.information(self, "小批恢复预览", "暂无可恢复的小批保存记录")
            return
        backup_root = Path(self.last_batch_backup_dir)
        if not backup_root.exists():
            QMessageBox.information(self, "小批恢复预览", f"备份目录不存在：{backup_root}")
            return
        files = list(backup_root.glob("*_batch_backup.txt"))
        if not files:
            QMessageBox.information(self, "小批恢复预览", "备份目录中无备份文件")
            return
        msg = f"小批恢复预览 (dry-run)\n\n备份目录：{backup_root}\n可恢复 label 数：{len(files)}\n\n"
        for f in sorted(files)[:10]:
            try:
                lines = len([l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()])
            except Exception:
                lines = 0
            msg += f"  • {f.name} ({lines} 行)\n"
        QMessageBox.information(self, "小批恢复预览结果", msg)
        self._set_status(f"小批恢复预览：可恢复 {len(files)} 个 label")

    def _update_batch_console_ui(self) -> None:
        total = len(self.batch_plan)
        if total == 0 or self.current_batch_index < 0:
            self.batch_position_label.setText("当前批次：- / -")
            self.batch_range_label.setText("本批范围：-")
            return
        pos = self.current_batch_index + 1
        items = self.batch_plan[self.current_batch_index]
        first = next((i for i, bp in enumerate(self.batch_save_plan.get("pass", [])) if bp in items), -1) + 1
        last = first + len(items) - 1
        self.batch_position_label.setText(f"当前批次：第 {pos} 批 / 共 {total} 批")
        self.batch_range_label.setText(f"本批范围：第 {first} ~ {last} 项")

    def _on_batch_size_changed(self, text: str) -> None:
        try:
            self.batch_size = int(text)
        except (ValueError, TypeError):
            self.batch_size = 5
        if self.batch_plan:
            self._generate_batch_plan()

    def _generate_batch_plan(self) -> None:
        if not self.batch_save_plan or not self.batch_save_plan.get("pass"):
            QMessageBox.information(self, "分批计划", "请先生成批量保存计划")
            return
        pass_list = self.batch_save_plan["pass"]
        bs = self.batch_size
        self.batch_plan = [pass_list[i:i+bs] for i in range(0, len(pass_list), bs)]
        self.current_batch_index = 0 if self.batch_plan else -1
        self._update_batch_console_ui()
        self._update_mb_est_labels()
        msg = (
            f"分批计划已生成\n\n"
            f"PASS 可保存数：{len(pass_list)}\n"
            f"批大小：{bs}\n"
            f"总批次数：{len(self.batch_plan)}\n"
            f"当前批项数：{len(self.batch_plan[0]) if self.batch_plan else 0}\n"
            f"预计 YOLO 总行数：{sum(x[2] for x in pass_list)}"
        )
        QMessageBox.information(self, "分批计划结果", msg)
        self._set_status(f"分批计划：{len(self.batch_plan)} 批，批大小={bs}")

    def _go_to_next_batch(self) -> None:
        if not self.batch_plan:
            self._set_status("请先生成分批计划")
            return
        if self.current_batch_index >= len(self.batch_plan) - 1:
            self._set_status("已到达最后一批")
            return
        self.current_batch_index += 1
        self._update_batch_console_ui()
        self._set_status(f"已切换到第 {self.current_batch_index + 1} 批")

    def _go_to_prev_batch(self) -> None:
        if not self.batch_plan:
            self._set_status("请先生成分批计划")
            return
        if self.current_batch_index <= 0:
            self._set_status("已到达第一批")
            return
        self.current_batch_index -= 1
        self._update_batch_console_ui()
        self._set_status(f"已切换到第 {self.current_batch_index + 1} 批")

    def _preview_current_batch(self) -> None:
        if not self.batch_plan or self.current_batch_index < 0:
            QMessageBox.information(self, "当前批预览", "请先生成分批计划")
            return
        items = self.batch_plan[self.current_batch_index]
        if not items:
            QMessageBox.information(self, "当前批预览", "当前批为空")
            return
        msg = f"当前批次预览 (dry-run)\n\n"
        msg += f"批次号：第 {self.current_batch_index + 1} 批\n"
        msg += f"本批 label 数：{len(items)}\n\n"
        for rel, lp, n, yl in items:
            msg += f"  • {rel}\n    label={lp}\n    boxes={n}  YOLO 行={yl}\n\n"
        msg += f"备份目录：E:/_AXIOM_BACKUPS/label_backups_batch/{{批次时间戳}}\n\n"
        msg += "这是预览，不会写文件。只有点击\"安全保存当前批\"才会真实写入。"
        QMessageBox.information(self, "当前批预览 (dry-run)", msg)

    def _safe_save_current_batch(self) -> None:
        if not self.batch_plan or self.current_batch_index < 0:
            QMessageBox.critical(self, "保存失败", "请先生成分批计划")
            return
        items = self.batch_plan[self.current_batch_index]
        if not items:
            QMessageBox.critical(self, "保存失败", "当前批为空")
            return
        if len(items) > 20:
            QMessageBox.critical(self, "保存失败", f"当前批 {len(items)} 张，超过上限 20")
            return
        if self.is_dirty:
            reply = QMessageBox.question(self, "未保存修改",
                "当前图片存在未保存修改。继续保存当前批？未保存修改不会被自动保存。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = Path(f"E:/_AXIOM_BACKUPS/label_backups_batch/{ts}")
        confirm_msg = (
            f"将真实写入当前批 label：\n\n"
            f"批次：第 {self.current_batch_index + 1} 批\n"
            f"本批写入 {len(items)} 个 label\n"
            f"本操作不是全量保存。本批最多 20 张。已将排除 WARN/BLOCK 项。\n\n"
            f"目标 label：\n"
        )
        for rel, lp, n, yl in items:
            confirm_msg += f"  • {rel} ({n} boxes, {yl} 行)\n"
        confirm_msg += f"\n备份目录：{backup_root}\n\n确认写入？"
        reply = QMessageBox.question(self, "确认批量保存", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self._set_status("批量保存已取消")
            return
        import shutil
        from core.label_manager import load_labels
        backup_root.mkdir(parents=True, exist_ok=True)
        success_list = []
        fail_list = []
        for rel, lp, n, yl in items:
            label_path = Path(lp)
            stem = label_path.stem
            backup_name = f"{stem}_{ts}_batch_backup.txt"
            backup_path = backup_root / backup_name
            try:
                if label_path.exists():
                    shutil.copy2(str(label_path), str(backup_path))
                    if not backup_path.exists():
                        raise RuntimeError(f"备份未生成：{backup_path}")
                else:
                    backup_path.write_text(f"原 label 不存在。path={label_path}", encoding="utf-8")
            except Exception as exc:
                fail_list.append((rel, f"备份失败：{exc}"))
                break
            try:
                boxes = load_labels(self.ctx.label_root, rel, self.ctx.class_names)
                if not boxes:
                    raise RuntimeError(f"该图片 boxes 为空，无法生成 YOLO 文本")
                lines = [f"{b.class_id if isinstance(b.class_id, int) else 0} {b.cx:.6f} {b.cy:.6f} {b.w:.6f} {b.h:.6f}" for b in boxes]
                if n > 0 and len(lines) == 0:
                    raise RuntimeError(f"生成 YOLO lines 为空（预期 {n} 行）")
                if n > 0 and len(lines) != n:
                    raise RuntimeError(f"生成 YOLO lines 数 {len(lines)} 与预期 {n} 不一致")
                text = "\n".join(lines) + ("\n" if lines else "")
                if not text.strip():
                    raise RuntimeError("写入文本为空")
                label_path.write_text(text, encoding="utf-8")
                if not label_path.exists():
                    raise RuntimeError("目标 label 未生成")
                if label_path.stat().st_size == 0:
                    raise RuntimeError("目标 label 写入后为空 (0 bytes)")
                written = [l for l in label_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                if n > 0 and len(written) != n:
                    raise RuntimeError(f"写入后行数 {len(written)} 与预期 {n} 不一致")
                if len(written) != len(boxes):
                    raise RuntimeError(f"写入后行数 {len(written)} 与 boxes 数 {len(boxes)} 不一致")
                for wl in written:
                    if len(wl.split()) < 5:
                        raise RuntimeError("校验失败：某行不足 5 列")
                success_list.append((rel, len(lines)))
            except Exception as exc:
                fail_list.append((rel, f"写入失败：{exc}"))
                self._update_batch_progress_on_fail(str(exc))
                break
        self.last_batch_save_count = len(success_list)
        self.last_batch_backup_dir = str(backup_root)
        audit_msg = (
            f"批次审计\n时间：{ts}\n批次号：{self.current_batch_index + 1}\n\n"
            f"成功写入：{len(success_list)}\n失败：{len(fail_list)}\n备份目录：{backup_root}\n"
        )
        if success_list:
            audit_msg += "\n成功项：\n" + "\n".join(f"  ✅ {rel} ({n} 行)" for rel, n in success_list)
        if fail_list:
            audit_msg += "\n失败项：\n" + "\n".join(f"  ❌ {rel}: {reason}" for rel, reason in fail_list)
        self.last_batch_audit_info = {
            "ts": ts, "batch": self.current_batch_index + 1,
            "success": len(success_list), "fail": len(fail_list),
            "backup_dir": str(backup_root)
        }
        # Write audit file
        audit_dir = Path("E:/_AXIOM_REPORTS/OpenAxiom_batch_audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_file = audit_dir / f"batch_audit_{ts}.txt"
        try:
            audit_file.write_text(audit_msg, encoding="utf-8")
            self.batch_audit_index.append(str(audit_file))
        except Exception:
            pass
        QMessageBox.information(self, "批次审计", audit_msg)
        self._set_status(f"当前批保存完成：成功={len(success_list)} 失败={len(fail_list)}")
        self._update_batch_progress_from_save()

    def _update_batch_progress_from_save(self) -> None:
        idx = self.current_batch_index
        if idx < 0 or not self.batch_plan or idx >= len(self.batch_plan):
            return
        items = self.batch_plan[idx]
        total_lines = sum(x[2] for x in items)
        while len(self.batch_progress_items) <= idx:
            self.batch_progress_items.append({})
        self.batch_progress_items[idx] = {
            "batch_index": idx, "item_count": len(items),
            "expected_yolo_lines": total_lines,
            "status": "已保存", "saved_at": self.last_batch_audit_info.get("ts", ""),
            "success_count": self.last_batch_audit_info.get("success", 0),
            "fail_count": self.last_batch_audit_info.get("fail", 0),
            "backup_dir": self.last_batch_audit_info.get("backup_dir", ""),
        }

    def _update_batch_progress_on_fail(self, reason: str) -> None:
        idx = self.current_batch_index
        if idx < 0:
            return
        while len(self.batch_progress_items) <= idx:
            self.batch_progress_items.append({})
        self.batch_progress_items[idx] = {
            "batch_index": idx, "status": "保存失败", "failure_reason": reason,
        }

    def _run_full_save_gate_check(self) -> None:
        blocks = []; warns = []; passes = []
        if not self.ctx.image_list:
            blocks.append("项目未打开或无图片列表"); level = "BLOCK"
        else:
            passes.append(f"项目已打开，图片总数={len(self.ctx.image_list)}")
            if self.project_scan_results:
                r = self.project_scan_results
                passes.append(f"项目扫描已执行")
                if r.get("missing_labels", 0) > 0:
                    blocks.append(f"缺失 label={r['missing_labels']}")
                if r.get("empty_labels", 0) > 0:
                    blocks.append(f"空 label={r['empty_labels']}")
            else:
                blocks.append("项目扫描未执行")
            if self.last_batch_check_summary:
                passes.append("批量检查 dry-run 已执行")
            else:
                blocks.append("批量检查 dry-run 未执行")
            if self.last_batch_yolo_summary:
                passes.append("批量 YOLO dry-run 已执行")
            else:
                blocks.append("批量 YOLO dry-run 未执行")
            if self.batch_save_plan:
                pass_count = len(self.batch_save_plan.get("pass", []))
                warn_count = len(self.batch_save_plan.get("warn", []))
                block_count = len(self.batch_save_plan.get("block", []))
                passes.append(f"批量保存计划已生成，PASS={pass_count}")
                if warn_count > 0:
                    warns.append(f"WARN 数={warn_count}")
                if block_count > 0:
                    blocks.append(f"BLOCK 数={block_count}")
            else:
                blocks.append("批量保存计划未生成")
            if self.batch_plan:
                passes.append(f"分批计划已生成，共 {len(self.batch_plan)} 批")
            else:
                blocks.append("分批计划未生成")
            if self.is_dirty:
                warns.append("当前图片有未保存修改")
            bs = self.batch_size
            if bs > 20:
                blocks.append(f"批大小 {bs} > 20")
            else:
                passes.append(f"批大小={bs} <= 20")
        level = "BLOCK" if blocks else ("WARN" if warns else "PASS")
        msg = f"全量保存前总门禁：{level}\n\n"
        msg += f"通过 ({len(passes)})：\n" + "\n".join(f"  ✅ {x}" for x in passes) + "\n"
        if warns:
            msg += f"\n警告 ({len(warns)})：\n" + "\n".join(f"  ⚠️ {x}" for x in warns) + "\n"
        if blocks:
            msg += f"\n阻塞 ({len(blocks)})：\n" + "\n".join(f"  ❌ {x}" for x in blocks) + "\n"
        QMessageBox.information(self, "全量保存前总门禁", msg)
        self._set_status(f"全量保存前总门禁：{level}")

    def _show_batch_progress(self) -> None:
        if not self.batch_plan:
            QMessageBox.information(self, "批次进度", "请先生成分批计划")
            return
        total = len(self.batch_plan)
        saved = sum(1 for p in self.batch_progress_items if p.get("status") == "已保存")
        failed = sum(1 for p in self.batch_progress_items if p.get("status") == "保存失败")
        unsaved = total - saved - failed
        msg = f"批次进度预览 (dry-run)\n\n"
        msg += f"总批次数：{total}\n批大小：{self.batch_size}\n"
        msg += f"已保存：{saved}\n未保存：{unsaved}\n失败：{failed}\n"
        msg += f"当前批次：第 {self.current_batch_index + 1} 批\n\n"
        for i, bp in enumerate(self.batch_plan[:20]):
            status = self.batch_progress_items[i].get("status", "未保存") if i < len(self.batch_progress_items) else "未保存"
            item_count = len(bp)
            total_yl = sum(x[2] for x in bp)
            msg += f"  第 {i+1} 批：{item_count} 项, {total_yl} 行, 状态={status}\n"
        if total > 20:
            msg += f"  ... 共 {total} 批，仅显示前 20 批"
        msg += "\n\n这是预览，不会写文件。"
        QMessageBox.information(self, "批次进度预览", msg)

    def _retry_current_batch_check(self) -> None:
        if self.current_batch_index < 0 or not self.batch_plan:
            QMessageBox.information(self, "重试检查", "请先生成分批计划")
            return
        idx = self.current_batch_index
        prog = self.batch_progress_items[idx] if idx < len(self.batch_progress_items) else {}
        status = prog.get("status", "未保存")
        if status != "保存失败" and status != "可重试":
            QMessageBox.information(self, "重试检查", f"当前批状态为「{status}」，无需重试")
            return
        items = self.batch_plan[idx]
        issues = []
        for rel, lp, n, yl in items:
            label_path = Path(lp)
            if not label_path.exists():
                issues.append(f"label 不存在：{rel}")
            elif label_path.stat().st_size == 0:
                issues.append(f"0 字节 label：{rel}")
        backup_dir = prog.get("backup_dir", "")
        if backup_dir and not Path(backup_dir).exists():
            issues.append(f"备份目录不存在：{backup_dir}")
        if issues:
            msg = "不可重试，存在以下问题：\n" + "\n".join(f"  ❌ {x}" for x in issues)
            QMessageBox.critical(self, "重试检查结果", msg)
        else:
            QMessageBox.information(self, "重试检查结果", "可重试。请使用「安全保存当前批」重试。")

    def _scan_zero_byte_labels(self) -> None:
        if not self.ctx.label_root:
            QMessageBox.information(self, "0 字节扫描", "label_root 不存在")
            return
        label_root = Path(self.ctx.label_root)
        zero_files = []
        for f in label_root.rglob("*.txt"):
            try:
                if f.stat().st_size == 0:
                    zero_files.append(f)
            except Exception:
                pass
        if not zero_files:
            QMessageBox.information(self, "0 字节扫描", "0 字节 label：0，安全。")
            self._set_status("0 字节 label 扫描：0 个，安全")
        else:
            msg = f"发现 {len(zero_files)} 个 0 字节 label：\n\n"
            for f in zero_files[:50]:
                msg += f"  • {f}\n"
            if len(zero_files) > 50:
                msg += f"  ... 共 {len(zero_files)} 个，仅显示前 50"
            QMessageBox.warning(self, "0 字节扫描", msg)
            self._set_status(f"0 字节 label 扫描：发现 {len(zero_files)} 个")

    def _show_recent_batch_audit(self) -> None:
        if not self.batch_audit_index:
            QMessageBox.information(self, "最近批次审计", "暂无可查看的审计记录")
            return
        last = self.batch_audit_index[-1]
        p = Path(last)
        if not p.exists():
            QMessageBox.information(self, "最近批次审计", f"审计文件不存在：{last}")
            return
        try:
            content = p.read_text(encoding="utf-8")
        except Exception:
            content = "(读取失败)"
        lines = content.splitlines()
        preview = "\n".join(lines[:30])
        if len(lines) > 30:
            preview += f"\n... 共 {len(lines)} 行，仅显示前 30 行"
        msg = f"最近审计文件：{last}\n大小：{p.stat().st_size} 字节\n\n{preview}"
        QMessageBox.information(self, "最近批次审计", msg)

    def _update_mb_est_labels(self) -> None:
        if not self.batch_plan or self.current_batch_index < 0:
            self.mb_range_label.setText("执行范围：-")
            self.mb_est_label.setText("预计写入：-")
            return
        try:
            cnt = int(self.mb_count_combo.currentText())
        except (ValueError, TypeError):
            cnt = 3
        start = self.current_batch_index
        end = min(start + cnt - 1, len(self.batch_plan) - 1)
        actual = end - start + 1
        total_labels = sum(len(self.batch_plan[i]) for i in range(start, end + 1))
        total_lines = sum(sum(x[2] for x in self.batch_plan[i]) for i in range(start, end + 1))
        self.mb_range_label.setText(f"执行范围：第 {start+1} ~ {end+1} 批")
        self.mb_est_label.setText(f"预计写入：{total_labels} label, {total_lines} 行")

    def _on_mb_count_changed(self, text: str) -> None:
        try:
            self.multi_batch_count = int(text)
        except (ValueError, TypeError):
            self.multi_batch_count = 3
        self._update_mb_est_labels()

    def _preview_multi_batch(self) -> None:
        if not self.batch_plan or self.current_batch_index < 0:
            QMessageBox.information(self, "多批预览", "请先生成分批计划")
            return
        start = self.current_batch_index
        cnt = self.multi_batch_count
        end = min(start + cnt - 1, len(self.batch_plan) - 1)
        items = []
        for i in range(start, end + 1):
            for item in self.batch_plan[i]:
                items.append(item)
        total_labels = len(items)
        if total_labels > 400:
            QMessageBox.warning(self, "多批预览", f"预计写入 {total_labels} label，超过上限 400，请减小批次数")
            return
        msg = f"多批执行预览 (dry-run)\n\n起始批次：第 {start+1} 批\n结束批次：第 {end+1} 批\n批次数：{end-start+1}\nlabel 数：{total_labels}\nYOLO 总行数：{sum(x[2] for x in items)}\n\n"
        for item in items[:30]:
            msg += f"  • {item[0]} ({item[2]} boxes)\n"
        if len(items) > 30:
            msg += f"  ... 共 {len(items)} 项，仅显示前 30\n"
        msg += "\n这是预览，不会写文件。"
        QMessageBox.information(self, "多批执行预览", msg)

    def _run_multi_batch_gate_check(self) -> tuple[str, str]:
        if not self.project_scan_results:
            return "BLOCK", "项目扫描未执行"
        if not self.last_batch_check_summary:
            return "BLOCK", "批量检查 dry-run 未执行"
        if not self.last_batch_yolo_summary:
            return "BLOCK", "批量 YOLO dry-run 未执行"
        if not self.batch_save_plan:
            return "BLOCK", "批量保存计划未生成"
        if not self.batch_plan:
            return "BLOCK", "分批计划未生成"
        if self.is_dirty:
            return "WARN", "当前图片有未保存修改"
        start = self.current_batch_index
        if start < 0:
            return "BLOCK", "当前批次索引无效"
        end = min(start + self.multi_batch_count - 1, len(self.batch_plan) - 1)
        total = sum(len(self.batch_plan[i]) for i in range(start, end + 1))
        if total > 400:
            return "BLOCK", f"预计写入 {total} label，超过 400 上限"
        return "PASS", ""

    def _safe_execute_multi_batch(self) -> None:
        level, reason = self._run_multi_batch_gate_check()
        if level == "BLOCK":
            QMessageBox.critical(self, "禁止执行", reason)
            return
        start = self.current_batch_index
        cnt = self.multi_batch_count
        end = min(start + cnt - 1, len(self.batch_plan) - 1)
        total_labels = sum(len(self.batch_plan[i]) for i in range(start, end + 1))
        confirm_msg = (
            f"本操作不是全量保存。\n\n"
            f"将连续保存 {end-start+1} 批\n"
            f"起始批次：第 {start+1} 批\n"
            f"结束批次：第 {end+1} 批\n"
            f"预计写入 label 数：{total_labels}\n"
            f"每批最大 20\n"
            f"任一批失败将自动停止\n"
            f"每批都会自动备份和审计\n\n"
            f"确认执行？"
        )
        if level == "WARN":
            confirm_msg = f"警告：{reason}\n\n" + confirm_msg
        reply = QMessageBox.question(self, "确认多批执行", confirm_msg,
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self._set_status("多批执行已取消")
            return
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        overall_success = 0
        overall_fail = 0
        batch_results = []
        for bi in range(start, end + 1):
            self.current_batch_index = bi
            self._update_batch_console_ui()
            self._safe_save_current_batch()
            prog = self.batch_progress_items[bi] if bi < len(self.batch_progress_items) else {}
            if prog.get("status") == "已保存":
                overall_success += 1
                batch_results.append((bi, "成功", prog.get("saved_at", ""), prog.get("backup_dir", "")))
            else:
                overall_fail += 1
                batch_results.append((bi, "失败", prog.get("failure_reason", "未知原因"), ""))
                break
        actual_saved = sum(len(self.batch_plan[i]) for i, st, _, _ in batch_results if st == "成功")
        audit_msg = (
            f"多批执行审计\n时间：{ts}\n"
            f"起始批次：{start+1}\n结束批次：{end+1}\n"
            f"请求执行批次数：{cnt}\n实际成功批次数：{overall_success}\n"
            f"失败批次数：{overall_fail}\n成功写入 label 数：{actual_saved}\n"
            f"失败 label 数：{sum(len(self.batch_plan[i]) for i, s, _, _ in batch_results if s == '失败')}\n"
            f"是否自动停止：{'是' if overall_fail > 0 else '否'}\n"
            f"是否发生全量保存：否\n是否超过执行上限：否\n\n"
        )
        for bi, st, detail, bdir in batch_results:
            audit_msg += f"  第 {bi+1} 批：{st}"
            if detail:
                audit_msg += f" ({detail})"
            if bdir:
                audit_msg += f" 备份：{bdir}"
            audit_msg += "\n"
        self.multi_batch_audit_info = {"ts": ts, "success": overall_success, "fail": overall_fail, "audit": audit_msg}
        audit_dir = Path("E:/_AXIOM_REPORTS/OpenAxiom_batch_audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        af = audit_dir / f"multi_batch_audit_{ts}.txt"
        try:
            af.write_text(audit_msg, encoding="utf-8")
            self.batch_audit_index.append(str(af))
        except Exception:
            pass
        QMessageBox.information(self, "多批执行审计", audit_msg)
        self._set_status(f"多批执行完成：成功={overall_success} 批, 失败={overall_fail} 批")

    def _show_multi_batch_audit(self) -> None:
        if not self.multi_batch_audit_info:
            QMessageBox.information(self, "多批执行审计", "暂无可查看的多批执行审计记录")
            return
        QMessageBox.information(self, "最近多批执行审计", self.multi_batch_audit_info.get("audit", "(无内容)"))

    def _post_multi_batch_zero_check(self) -> None:
        if not self.ctx.label_root:
            QMessageBox.information(self, "0 字节复查", "label_root 不存在")
            return
        lr = Path(self.ctx.label_root)
        zeros = []
        for f in lr.rglob("*.txt"):
            try:
                if f.stat().st_size == 0:
                    zeros.append(f)
            except Exception:
                pass
        if not zeros:
            QMessageBox.information(self, "0 字节复查", "0 字节 label：0，复查通过。")
            self._set_status("多批执行后 0 字节复查：0 个，通过")
        else:
            msg = f"发现 {len(zeros)} 个 0 字节 label：\n"
            for f in zeros[:50]:
                msg += f"  ❌ {f}\n"
            if len(zeros) > 50:
                msg += f"  ... 共 {len(zeros)} 个"
            QMessageBox.warning(self, "0 字节复查失败", msg)
            self._set_status(f"多批执行后 0 字节复查：发现 {len(zeros)} 个")

    def _check_multi_batch_status(self) -> None:
        info = self.multi_batch_audit_info
        if not info:
            QMessageBox.information(self, "中断状态检查", "最近未执行过多批保存。请先生成批量保存计划并执行多批保存。")
            return
        msg = (
            f"最近多批执行状态\n\n"
            f"执行完成：{'是' if info.get('fail', 0) == 0 else '否（有失败批次）'}\n"
            f"成功批次数：{info.get('success', 0)}\n"
            f"失败批次数：{info.get('fail', 0)}\n"
            f"最后成功批次：第 {self.current_batch_index} 批\n"
            f"执行时间：{info.get('ts', '-')}\n\n"
            f"下一建议：请使用「安全保存当前批」或「安全执行多批」继续。"
        )
        QMessageBox.information(self, "中断状态检查", msg)

    def _on_low_conf_changed(self) -> None:
        self._refresh_filter_status_ui()
        if self.under_conf_cb.isChecked() and self.ctx.boxes:
            threshold = self.low_conf_spin.value()
            count = len(self._build_low_conf_review_queue())
            self._set_status(f"低置信度提示：已启用（阈值：{threshold:.2f}）；当前低置信度数量：{count}")
        else:
            self._set_status("低置信度提示：已关闭")

    def _go_to_next_low_conf(self) -> None:
        if not self.ctx.boxes:
            self._set_status("没有标注框")
            return
        candidates = self._build_pending_review_queue()
        if not candidates:
            self._set_status("当前条件下低置信度复核已完成")
            return
        start = self.selected_box_index
        found = None
        for c in candidates:
            if c > start:
                found = c
                break
        if found is None:
            found = candidates[0]
        self.select_box(found)
        self._set_status(f"已跳转到待复核框 #{found}")

    def _go_to_prev_low_conf(self) -> None:
        if not self.ctx.boxes:
            self._set_status("没有标注框")
            return
        candidates = self._build_pending_review_queue()
        if not candidates:
            self._set_status("当前条件下低置信度复核已完成")
            return
        start = self.selected_box_index
        found = None
        for c in reversed(candidates):
            if c < start:
                found = c
                break
        if found is None:
            found = candidates[-1]
        self.select_box(found)
        self._set_status(f"已跳转到待复核框 #{found}")

    def _confirm_and_next(self) -> None:
        if self.selected_box_index < 0:
            return
        self._push_undo()
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        if self.selected_box_index in self.confirmed_ids:
            self._set_status("当前框已确认")
        else:
            self.confirmed_ids.add(self.selected_box_index)
            self.canvas.confirmed_indexes = self.confirmed_ids
            self.canvas.update()
            self.session_confirmed_count += 1
            self._set_status("已确认")
        self._set_dirty("确认并下一个")
        self._refresh_filter_status_ui()
        pending = self._build_pending_review_queue()
        if not pending:
            self._set_status("当前条件下低置信度复核已完成")
            return
        start = self.selected_box_index
        found = None
        for c in pending:
            if c > start:
                found = c
                break
        if found is None:
            found = pending[0]
        self.select_box(found)
        self._set_status(f"已确认并跳转到待复核框 #{found}")

    def _push_undo(self) -> None:
        import copy
        snapshot = {
            "boxes": copy.deepcopy(self.ctx.boxes),
            "selected_box_index": self.selected_box_index,
            "confirmed_ids": set(getattr(self, 'confirmed_ids', set())),
            "session_deleted_count": self.session_deleted_count,
            "session_class_changed_count": self.session_class_changed_count,
            "session_confirmed_count": self.session_confirmed_count,
            "session_added_count": self.session_added_count,
            "is_dirty": self.is_dirty,
            "dirty_reason": self.dirty_reason,
        }
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self._max_undo:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self._update_undo_redo_buttons()

    def _restore_snapshot(self, snapshot: dict) -> None:
        self.ctx.boxes = list(snapshot["boxes"])
        self.selected_box_index = snapshot["selected_box_index"]
        self.confirmed_ids = set(snapshot["confirmed_ids"])
        self.canvas.confirmed_indexes = self.confirmed_ids
        self.session_deleted_count = snapshot["session_deleted_count"]
        self.session_class_changed_count = snapshot["session_class_changed_count"]
        self.session_confirmed_count = snapshot["session_confirmed_count"]
        self.session_added_count = snapshot["session_added_count"]
        self.is_dirty = snapshot.get("is_dirty", True)
        self.dirty_reason = snapshot.get("dirty_reason", "")
        self.canvas.set_image_and_boxes(self.canvas.pixmap, self.ctx.boxes)
        self.canvas.set_selected_index(self.selected_box_index)
        self.refresh_table()
        self.update_box_panel()
        if self.selected_box_index >= 0 and self.selected_box_index < len(self.ctx.boxes):
            self.update_properties_panel(self.ctx.boxes[self.selected_box_index])
        else:
            self.update_properties_panel(None)
        self._refresh_filter_status_ui()

    def _undo(self) -> None:
        if not self.undo_stack:
            self._set_status("没有可撤销的操作")
            return
        import copy
        current = {
            "boxes": copy.deepcopy(self.ctx.boxes),
            "selected_box_index": self.selected_box_index,
            "confirmed_ids": set(getattr(self, 'confirmed_ids', set())),
            "session_deleted_count": self.session_deleted_count,
            "session_class_changed_count": self.session_class_changed_count,
            "session_confirmed_count": self.session_confirmed_count,
            "session_added_count": self.session_added_count,
            "is_dirty": self.is_dirty,
            "dirty_reason": self.dirty_reason,
        }
        self.redo_stack.append(current)
        snapshot = self.undo_stack.pop()
        self._restore_snapshot(snapshot)
        self._set_dirty("撤销")
        self._update_undo_redo_buttons()
        self._set_status("已撤销")

    def _redo(self) -> None:
        if not self.redo_stack:
            self._set_status("没有可重做的操作")
            return
        import copy
        current = {
            "boxes": copy.deepcopy(self.ctx.boxes),
            "selected_box_index": self.selected_box_index,
            "confirmed_ids": set(getattr(self, 'confirmed_ids', set())),
            "session_deleted_count": self.session_deleted_count,
            "session_class_changed_count": self.session_class_changed_count,
            "session_confirmed_count": self.session_confirmed_count,
            "session_added_count": self.session_added_count,
            "is_dirty": self.is_dirty,
            "dirty_reason": self.dirty_reason,
        }
        self.undo_stack.append(current)
        snapshot = self.redo_stack.pop()
        self._restore_snapshot(snapshot)
        self._set_dirty("重做")
        self._update_undo_redo_buttons()
        self._set_status("已重做")

    def _on_add_box_toggled(self, checked: bool) -> None:
        self.canvas.add_box_mode = checked
        self.add_box_toggle.setText("新增框模式：开启" if checked else "新增框模式：关闭")
        if checked:
            self.canvas.setCursor(Qt.CrossCursor)
            self._set_status("新增框模式已开启，在画布中拖拽创建新 bbox")
        else:
            self.canvas.setCursor(Qt.ArrowCursor)
            self._set_status("已切换回选择模式")

    def _on_drag_box_created(self, norm_cx: float, norm_cy: float, norm_w: float, norm_h: float) -> None:
        self._push_undo()
        names = getattr(self.ctx, 'class_names', [])
        if not names:
            QMessageBox.information(self, "新增框", "暂无可用类别列表，无法创建新框")
            return
        cat_name = self.category_filter_combo.currentText()
        default_idx = 0
        if cat_name != "全部类别" and cat_name in names:
            default_idx = names.index(cat_name)
        sel, ok = QInputDialog.getItem(self, "新增框 - 选择类别", "选择新框类别：", names, current=default_idx, editable=False)
        if not ok:
            return
        new_id = names.index(sel)
        from core.context import Box
        new_box = Box(class_id=new_id, cx=norm_cx, cy=norm_cy, w=norm_w, h=norm_h, class_name=sel)
        self.ctx.boxes.append(new_box)
        self.session_added_count += 1
        idx = len(self.ctx.boxes) - 1
        self.select_box(idx)
        self._set_dirty("新增框")
        self._refresh_filter_status_ui()
        self._set_status(f"已新增框 #{idx}：{sel} ({norm_cx:.4f}, {norm_cy:.4f}, {norm_w:.4f}, {norm_h:.4f})")

    def _on_category_filter_changed(self, index: int) -> None:
        self._refresh_filter_status_ui()
        if index <= 0 or not self.ctx.boxes:
            total = len(self.ctx.boxes)
            self._set_status(f"当前类别筛选：全部类别；当前图片总框数：{total}")
        else:
            name = self.category_filter_combo.currentText()
            count = sum(1 for b in self.ctx.boxes if b.class_name == name)
            self._set_status(f"当前类别筛选：{name}；当前图片数量：{count}")

    def update_properties_panel(self, box) -> None:
        if not hasattr(self, 'prop_class'):
            return
        if box is None:
            self.prop_class.setText('-')
            self.prop_conf.setText('-')
            self.prop_x.setText('-')
            self.prop_y.setText('-')
            self.prop_w.setText('-')
            self.prop_h.setText('-')
            self.prop_id.setText('-')
            self.prop_confirm_btn.setEnabled(False)
            self.prop_delete_btn.setEnabled(False)
            self.prop_cancel_btn.setEnabled(False)
            return
        self.prop_class.setText(box.class_name)
        conf = getattr(box, 'conf', None)
        if conf is None:
            conf = getattr(box, 'confidence', '-')
        self.prop_conf.setText(str(conf))
        self.prop_x.setText(f"{box.cx:.6f}")
        self.prop_y.setText(f"{box.cy:.6f}")
        self.prop_w.setText(f"{box.w:.6f}")
        self.prop_h.setText(f"{box.h:.6f}")
        self.prop_id.setText(str(self.selected_box_index))
        self.prop_confirm_btn.setEnabled(True)
        self.prop_delete_btn.setEnabled(True)
        self.prop_cancel_btn.setEnabled(True)

    def clear_selection(self) -> None:
        self.selected_box_index = -1
        self.canvas.set_selected_index(-1)
        self.table.blockSignals(True)
        self.refresh_table()
        self.table.blockSignals(False)
        self.update_properties_panel(None)
        self._set_status("已取消选中")

    def delete_current_box(self) -> None:
        self._push_undo()
        idx = self.selected_box_index
        if idx < 0 or idx >= len(self.ctx.boxes):
            return
        del self.ctx.boxes[idx]
        if hasattr(self, 'confirmed_ids'):
            self.confirmed_ids.discard(idx)
            self.confirmed_ids = {i - 1 if i > idx else i for i in self.confirmed_ids}
            self.canvas.confirmed_indexes = self.confirmed_ids
        if len(self.ctx.boxes) > 0:
            self.selected_box_index = min(idx, len(self.ctx.boxes) - 1)
        else:
            self.selected_box_index = -1
        self.canvas.set_image_and_boxes(self.canvas.pixmap, self.ctx.boxes)
        self.refresh_table()
        if self.selected_box_index >= 0:
            self.update_properties_panel(self.ctx.boxes[self.selected_box_index])
        else:
            self.update_properties_panel(None)
        self.session_deleted_count += 1
        self._set_dirty("删除框")
        self._refresh_filter_status_ui()
        self._set_status("标注框已删除")

    def confirm_current_box(self) -> None:
        if self.selected_box_index < 0:
            return
        self._push_undo()
        if not hasattr(self, 'confirmed_ids'):
            self.confirmed_ids = set()
        if self.selected_box_index not in self.confirmed_ids:
            self.session_confirmed_count += 1
        self.confirmed_ids.add(self.selected_box_index)
        self.canvas.confirmed_indexes = self.confirmed_ids
        self.canvas.update()
        if self.selected_box_index >= 0 and self.selected_box_index < len(self.ctx.boxes):
            self.update_properties_panel(self.ctx.boxes[self.selected_box_index])
        self._set_dirty("确认框")
        self._refresh_filter_status_ui()
        self._set_status("已确认")

    def cancel_selection(self) -> None:
        self.clear_selection()

    # ── 右键菜单 ──────────────────────────────────────────

    def on_box_right_clicked(self, index: int, global_pos: QPoint) -> None:
        """画布标注框上的右键菜单"""
        self.select_box(index)
        menu = QMenu(self)
        menu.addAction("确认此框", self.confirm_current_box)
        menu.addAction("修改类别", lambda: self._change_class_via_dialog(self.selected_box_index))
        menu.addAction("删除此框", self.delete_current_box)
        menu.addAction("查看属性", self._focus_properties_panel)
        menu.addAction("复制框信息", lambda: self._copy_box_info(self.selected_box_index))
        menu.exec(global_pos)

    def on_canvas_right_clicked(self, global_pos: QPoint) -> None:
        """画布空白区域的右键菜单"""
        menu = QMenu(self)
        menu.addAction("添加新框（预留）")
        menu.addAction("取消选择", self.clear_selection)
        menu.addAction("适配窗口", lambda: self.canvas.fit_to_window())
        menu.addAction("重置视图", lambda: self.canvas.reset_view())
        menu.exec(global_pos)

    def on_table_right_clicked(self, pos: QPoint) -> None:
        """底部标注表格行上的右键菜单"""
        item = self.table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        self.select_box(row)

        global_pos = self.table.viewport().mapToGlobal(pos)
        menu = QMenu(self)
        menu.addAction("定位到画布", self._focus_canvas)
        menu.addAction("修改类别", lambda: self._change_class_via_dialog(self.selected_box_index))
        menu.addAction("删除标注", self.delete_current_box)
        menu.addAction("复制坐标", lambda: self._copy_box_coords(self.selected_box_index))
        menu.exec(global_pos)

    # ------------- Navigation & Shortcuts -------------
    def _confirm_discard_changes(self) -> bool:
        if not self.is_dirty:
            return True
        reply = QMessageBox.question(self, "未保存修改",
            "当前图片存在未保存修改，切换后这些修改将不会写入 label 文件。\n\n继续切换？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return reply == QMessageBox.Yes

    def _prev_image(self) -> None:
        if self.image_list.count() <= 0:
            return
        if not self._confirm_discard_changes():
            return
        idx = self.image_list.currentRow()
        if idx <= 0:
            self._set_status("已到达第一张图片")
            return
        new_idx = idx - 1
        self.image_list.blockSignals(True)
        self.image_list.setCurrentRow(new_idx)
        self.image_list.blockSignals(False)
        self.clear_selection()
        self.display_image(self.ctx.image_list[new_idx])

    def _next_image(self) -> None:
        if self.image_list.count() <= 0:
            return
        if not self._confirm_discard_changes():
            return
        idx = self.image_list.currentRow()
        if idx < 0:
            if self.image_list.count() > 0:
                self.image_list.blockSignals(True)
                self.image_list.setCurrentRow(0)
                self.image_list.blockSignals(False)
                self.display_image(self.ctx.image_list[0])
            return
        if idx >= self.image_list.count() - 1:
            self._set_status("已到达最后一张图片")
            return
        new_idx = idx + 1
        self.image_list.blockSignals(True)
        self.image_list.setCurrentRow(new_idx)
        self.image_list.blockSignals(False)
        self.clear_selection()
        self.display_image(self.ctx.image_list[new_idx])

    # ── 右键辅助方法 ──────────────────────────────────────

    def _change_class_via_dialog(self, index: int) -> None:
        if index < 0 or index >= len(self.ctx.boxes):
            return
        self._push_undo()
        names = getattr(self.ctx, 'class_names', [])
        if not names:
            QMessageBox.information(self, "修改类别", "暂无可用类别列表")
            return
        current = self.ctx.boxes[index].class_name
        idx, ok = QInputDialog.getItem(self, "修改类别", "选择新类别：", names, current=names.index(current) if current in names else 0, editable=False)
        if not ok or self.ctx.boxes[index].class_name == idx:
            return
        new_id = names.index(idx)
        self.ctx.boxes[index].class_id = new_id
        self.ctx.boxes[index].class_name = idx
        self.canvas.update()
        self.refresh_table()
        self.select_box(index)
        self.session_class_changed_count += 1
        self._set_dirty("修改类别")
        self._refresh_filter_status_ui()
        self._update_session_summary()
        self._set_status(f"类别已修改为：{idx}")

    def _focus_properties_panel(self) -> None:
        """聚焦到右侧属性面板"""
        self._set_status("已在属性面板中查看当前框信息")

    def _focus_canvas(self) -> None:
        """定位到画布"""
        self._set_status("已在画布中定位选中框")

    def _copy_box_info(self, index: int) -> None:
        """复制框信息到剪贴板"""
        if index < 0 or index >= len(self.ctx.boxes):
            return
        box = self.ctx.boxes[index]
        text = (
            f"框 ID: {index}\n"
            f"类别: {box.class_name} (ID: {box.class_id})\n"
            f"中心 x: {box.cx:.6f}\n"
            f"中心 y: {box.cy:.6f}\n"
            f"宽度: {box.w:.6f}\n"
            f"高度: {box.h:.6f}\n"
        )
        clip = QApplication.clipboard()
        clip.setText(text)
        self._set_status("框信息已复制到剪贴板")

    def _copy_box_coords(self, index: int) -> None:
        """复制框坐标到剪贴板"""
        if index < 0 or index >= len(self.ctx.boxes):
            return
        box = self.ctx.boxes[index]
        text = f"{box.cx:.6f} {box.cy:.6f} {box.w:.6f} {box.h:.6f}"
        clip = QApplication.clipboard()
        clip.setText(text)
        self._set_status("坐标已复制到剪贴板")

    def _set_status(self, message: str) -> None:
        self.status.showMessage(message)
        self._update_context_bar()

    def _on_zoom_changed(self, factor: float) -> None:
        """更新缩放比例显示"""
        pct = int(round(factor * 100))
        self.zoom_label.setText(f"缩放: {pct}%")
        self._set_status(f"缩放: {pct}%")

    def _update_context_bar(self) -> None:
        project = str(self.ctx.project_root) if self.ctx.project_root else "-"
        dataset = str(self.ctx.dataset_root) if self.ctx.dataset_root else "-"
        image = self.ctx.current_image_rel if self.ctx.current_image_rel else "-"
        model = self.ctx.model_path.name if self.ctx.model_path else "-"
        self.context_label.setText(
            f"工程: {project}    数据集: {dataset}    图像: {image}    模型: {model}    AI 预标注: 已禁用"
        )

    def open_project(self) -> None:
        if self.is_dirty and not self._confirm_discard_changes():
            return
        folder = QFileDialog.getExistingDirectory(self, "打开工程", "E:/")
        if not folder:
            return

        try:
            info = detect_dataset(folder)
            self.ctx.apply_dataset_info(info)
            self.ctx.image_list = load_images(info.image_root)

            self.project_label.setText(
                f"工程：\n{info.project_root}\n\n"
                f"数据集：\n{info.dataset_root}\n\n"
                f"图片：\n{info.image_root}\n\n"
                f"标注：\n{info.label_root}\n\n"
                f"YAML：\n{info.yaml_path or '-'}"
            )

            label_count = sum(1 for _ in info.label_root.rglob("*.txt")) if info.label_root.exists() else 0
            self.stats_label.setText(
                f"图片数：{len(self.ctx.image_list)}\n"
                f"标注数：{label_count}\n"
                f"类别数：{len(self.ctx.class_names)}"
            )

            self.image_list.clear()
            for rel in self.ctx.image_list:
                self.image_list.addItem(QListWidgetItem(rel))

            self.class_list.clear()
            for i, name in enumerate(self.ctx.class_names):
                self.class_list.addItem(QListWidgetItem(f"{i}: {name}"))

            if self.ctx.image_list:
                self.image_list.setCurrentRow(0)
                self.display_image(self.ctx.image_list[0])

            self._set_status(f"工程已加载。图片数={len(self.ctx.image_list)} 标注数={label_count} 类别数={len(self.ctx.class_names)}")

        except Exception as exc:
            QMessageBox.critical(self, "打开工程失败", str(exc))
            self._set_status(f"打开失败：{exc}")

    # 键盘快捷键：Delete/Esc/Enter、A/D 画面导航
    def keyPressEvent(self, event) -> None:
        key = event.key()
        ctrl = event.modifiers() & Qt.ControlModifier
        if ctrl and key == Qt.Key_Z:
            self._undo()
            return
        if ctrl and key == Qt.Key_Y:
            self._redo()
            return
        if key == Qt.Key_Delete:
            self.delete_current_box()
            return
        if key == Qt.Key_Escape:
            if self.canvas._is_dragging:
                self.canvas._is_dragging = False
                self.canvas.setCursor(Qt.ArrowCursor if not self.canvas.add_box_mode else Qt.CrossCursor)
                self.canvas.update()
                self._set_status("已取消拖拽")
                return
            if self.canvas.add_box_mode:
                self.add_box_toggle.setChecked(False)
                self._on_add_box_toggled(False)
                return
            self.clear_selection()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self.confirm_current_box()
            return
        if key == Qt.Key_A:
            self._prev_image()
            return
        if key == Qt.Key_D:
            self._next_image()
            return
        super().keyPressEvent(event)

    def on_image_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self.ctx.image_list):
            return
        if not self._confirm_discard_changes():
            self.image_list.blockSignals(True)
            self.image_list.setCurrentRow(self.image_list.currentRow())
            self.image_list.blockSignals(False)
            return
        self.display_image(self.ctx.image_list[row])

    def display_image(self, image_rel: str) -> None:
        if not self.ctx.image_root or not self.ctx.label_root:
            return
        self.session_deleted_count = 0
        self.session_class_changed_count = 0
        self.session_confirmed_count = 0
        self.last_save_status = "未保存"
        self.last_save_path = ""
        self.last_backup_path = ""
        self.last_restore_status = "未恢复"
        self.last_restore_source = ""
        self.last_restore_backup_path = ""
        self.session_added_count = 0
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_undo_redo_buttons()

        image_path = absolute_image_path(self.ctx.image_root, image_rel)
        label_path = label_path_for_image(self.ctx.label_root, image_rel)

        pix = QPixmap(str(image_path))
        pix_loaded = not pix.isNull()
        boxes = load_labels(self.ctx.label_root, image_rel, self.ctx.class_names)

        self.ctx.current_image_rel = image_rel
        self.ctx.current_image_path = image_path
        self.ctx.boxes = boxes
        self.selected_box_index = 0 if boxes else -1

        self.canvas.set_image_and_boxes(pix if pix_loaded else None, boxes)
        self.canvas.set_selected_index(self.selected_box_index)
        self.refresh_table()
        self.update_box_panel()
        if boxes:
            self.update_properties_panel(boxes[self.selected_box_index])
        self._populate_category_filter()
        self._update_context_bar()
        self._update_cross_image_label()
        self._update_project_stats_from_scan()

        self._set_status(
            f"image_rel={image_rel}; image_exists={image_path.exists()}; "
            f"pix_loaded={pix_loaded}; label_exists={label_path.exists()}; boxes_count={len(boxes)}"
        )

    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.ctx.boxes))

        for row, box in enumerate(self.ctx.boxes):
            values = [
                str(row),
                str(box.class_id),
                box.class_name,
                f"{box.cx:.6f}",
                f"{box.cy:.6f}",
                f"{box.w:.6f} / {box.h:.6f}",
                "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

        if self.ctx.boxes:
            self.table.selectRow(0)
        self._refresh_filter_status_ui()

    def on_table_selection_changed(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self.select_box(rows[0].row())

    def select_box(self, index: int) -> None:
        if index < 0 or index >= len(self.ctx.boxes):
            return

        self.selected_box_index = index
        self.canvas.set_selected_index(index)
        self.update_box_panel()
        if index >= 0 and index < len(self.ctx.boxes):
            self.update_properties_panel(self.ctx.boxes[index])

        if self.table.currentRow() != index:
            self.table.blockSignals(True)
            self.table.selectRow(index)
            self.table.blockSignals(False)
        self._refresh_filter_status_ui()

    def update_box_panel(self) -> None:
        if not self.ctx.boxes or self.selected_box_index < 0:
            self.box_label.setText("No box selected")
            return

        box = self.ctx.boxes[self.selected_box_index]
        self.box_label.setText(
            f"Image:\n{self.ctx.current_image_rel}\n\n"
            f"Box: #{self.selected_box_index}\n"
            f"Class: {box.class_id} — {box.class_name}\n"
            f"cx: {box.cx:.6f}\n"
            f"cy: {box.cy:.6f}\n"
            f"w:  {box.w:.6f}\n"
            f"h:  {box.h:.6f}"
        )

    def save_current_labels(self) -> None:
        if not self.ctx.label_root or not self.ctx.current_image_rel:
            self._set_status("Nothing to save.")
            return

        try:
            path = save_labels(self.ctx.label_root, self.ctx.current_image_rel, self.ctx.boxes)
            self._set_status(f"Labels saved: {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status(f"Save failed: {exc}")

    def open_settings(self) -> None:
        dlg = SettingsWindow(self, current_language=self.language)
        if dlg.exec() == QDialog.Accepted:
            self.language = dlg.selected_language
            setattr(self.ctx, "language", self.language)
            self._set_status(f"Language option saved: {self.language}")
