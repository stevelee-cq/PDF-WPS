import sys
import fitz  # PyMuPDF
import numpy as np
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QLabel, QScrollArea, QLineEdit,
    QToolBar, QAction, QPushButton, QMessageBox, QWidget, QVBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QColor

class PDFPageLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(QSize(400, 500))

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 文献阅读器（简化版 WPS）")
        self.resize(1200, 850)
        self.setWindowIcon(QIcon())

        # 状态
        self.pdf_path = None
        self.doc = None
        self.total_pages = 0
        self.current_page = 0
        self.scale = 1.0
        self.bg_mode = "default"  # default/night/eye
        self.bg_color_map = {
            "default": QColor(Qt.white),
            "night": QColor(Qt.black),
            "eye": QColor(220, 238, 209)
        }

        # ======= 工具栏 =======
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        logo = QLabel("🧑‍💻 PDF Reader")
        logo.setStyleSheet("font-weight:bold; font-size:18px; color:#3c6eae;")
        self.toolbar.addWidget(logo)
        self.toolbar.addSeparator()

        open_action = QAction("打开PDF", self)
        open_action.triggered.connect(self.open_pdf)
        self.toolbar.addAction(open_action)
        self.toolbar.addSeparator()

        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)
        fit_action = QAction("适应窗口", self)
        fit_action.triggered.connect(self.fit_to_window)
        self.toolbar.addAction(fit_action)
        self.toolbar.addSeparator()

        night_btn = QPushButton("夜间模式")
        night_btn.clicked.connect(self.set_night_mode)
        self.toolbar.addWidget(night_btn)
        eye_btn = QPushButton("护眼模式")
        eye_btn.clicked.connect(self.set_eye_mode)
        self.toolbar.addWidget(eye_btn)
        default_btn = QPushButton("默认模式")
        default_btn.clicked.connect(self.set_default_mode)
        self.toolbar.addWidget(default_btn)
        self.toolbar.addSeparator()

        self.page_edit = QLineEdit()
        self.page_edit.setFixedWidth(50)
        self.page_edit.setPlaceholderText("页码")
        self.page_edit.returnPressed.connect(self.goto_page)
        self.toolbar.addWidget(self.page_edit)
        goto_btn = QPushButton("跳转")
        goto_btn.clicked.connect(self.goto_page)
        self.toolbar.addWidget(goto_btn)
        self.page_label = QLabel("第 0 / 0 页")
        self.toolbar.addWidget(self.page_label)

        # ======= 内容布局 =======
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.vlayout = QVBoxLayout(self.central_widget)
        self.vlayout.setContentsMargins(0, 0, 0, 0)
        self.vlayout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.vlayout.addWidget(self.scroll_area, stretch=1)

        self.page_widget = PDFPageLabel()
        self.scroll_area.setWidget(self.page_widget)

        self.scroll_area.viewport().installEventFilter(self)
        self.set_bg_color()

    def set_bg_color(self):
        color = self.bg_color_map[self.bg_mode]
        self.page_widget.setStyleSheet(f"background-color: {color.name()};")
        self.scroll_area.setStyleSheet(f"background-color: {color.name()};")
        self.central_widget.setStyleSheet(f"background-color: {color.name()};")

    def open_pdf(self):
        pdf_path, _ = QFileDialog.getOpenFileName(self, "选择PDF文件", "", "PDF Files (*.pdf)")
        if pdf_path:
            try:
                doc = fitz.open(pdf_path)
                self.pdf_path = pdf_path
                self.doc = doc
                self.total_pages = doc.page_count
                self.current_page = 0
                self.scale = 1.0
                self.show_page()
            except Exception as e:
                QMessageBox.warning(self, "打开失败", f"无法打开PDF: {e}")

    def show_page(self):
        if self.doc is None or not (0 <= self.current_page < self.total_pages):
            self.page_widget.clear()
            return
        page = self.doc.load_page(self.current_page)
        zoom_matrix = fitz.Matrix(self.scale, self.scale)
        pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

        # ==== 模式处理 ====
        arr = np.frombuffer(img.bits(), dtype=np.uint8).reshape((pix.height, pix.width, 3)).copy()
        if self.bg_mode == "night":
            arr = 255 - arr
        elif self.bg_mode == "eye":
            # 护眼模式：绿色通道轻度提升，降低蓝色
            arr = arr.astype(np.float32)
            arr[..., 1] = np.clip(arr[..., 1] + 30, 0, 255)  # Green
            arr[..., 2] = np.clip(arr[..., 2] * 0.85, 0, 255)  # Blue
            arr = arr.astype(np.uint8)
        qimg = QImage(arr.data, arr.shape[1], arr.shape[0], QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.page_widget.setPixmap(pixmap)
        self.page_label.setText(f"第 {self.current_page + 1} / {self.total_pages} 页")
        self.page_edit.setText(str(self.current_page + 1))
        self.set_bg_color()

    def zoom_in(self):
        self.scale *= 1.2
        self.show_page()

    def zoom_out(self):
        self.scale /= 1.2
        self.show_page()

    def fit_to_window(self):
        if self.doc is None:
            return
        page = self.doc.load_page(self.current_page)
        view_width = self.scroll_area.viewport().width()
        view_height = self.scroll_area.viewport().height()
        rect = page.rect
        scale_x = view_width / rect.width
        scale_y = view_height / rect.height
        self.scale = min(scale_x, scale_y)
        self.show_page()

    def set_night_mode(self):
        self.bg_mode = "night"
        self.show_page()

    def set_eye_mode(self):
        self.bg_mode = "eye"
        self.show_page()

    def set_default_mode(self):
        self.bg_mode = "default"
        self.show_page()

    def goto_page(self):
        try:
            n = int(self.page_edit.text().strip()) - 1
            if self.doc and 0 <= n < self.total_pages:
                self.current_page = n
                self.show_page()
            else:
                QMessageBox.warning(self, "错误", "页码超出范围")
        except Exception:
            QMessageBox.warning(self, "错误", "请输入有效页码")

    # 支持滚轮翻页，Ctrl+滚轮缩放
    def eventFilter(self, source, event):
        if event.type() == event.Wheel and source is self.scroll_area.viewport():
            if QApplication.keyboardModifiers() == Qt.ControlModifier:
                if event.angleDelta().y() > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
            else:
                if event.angleDelta().y() > 0:
                    self.prev_page()
                else:
                    self.next_page()
            return True
        return super().eventFilter(source, event)

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page()

    def next_page(self):
        if self.doc and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.show_page()

    def resizeEvent(self, event):
        self.show_page()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PDFViewer()
    win.show()
    sys.exit(app.exec_())
