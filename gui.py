import sys
import os
from pathlib import Path
from PIL import Image
import io
from rembg import remove
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFileDialog, QProgressBar, QMessageBox,
    QFrame, QScrollArea
)
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor, QDragEnterEvent, QDropEvent, QLinearGradient
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRect
from PyQt6.QtCore import QTimer


class RemoveBackgroundThread(QThread):
    finished = pyqtSignal(Image.Image)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, image_path, model_name):
        super().__init__()
        self.image_path = image_path
        self.model_name = model_name

    def run(self):
        try:
            self.progress.emit(20)
            img = Image.open(self.image_path)
            self.progress.emit(40)
            # Use session API for model selection
            from rembg.session_factory import new_session
            session = new_session(self.model_name)
            self.progress.emit(60)
            result = remove(img, session=session)
            self.progress.emit(100)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ModernImageLabel(QLabel):
    image_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #0f1419;
                border: 3px dashed #1a9fff;
                border-radius: 12px;
                color: #888;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("📁 Drag & Drop Image\nor Click to Browse")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.current_image = None
        self.image_file_path = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    background-color: #1a2332;
                    border: 3px dashed #00d4ff;
                    border-radius: 12px;
                    color: #00d4ff;
                    font-size: 13px;
                    font-weight: 500;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                background-color: #0f1419;
                border: 3px dashed #1a9fff;
                border-radius: 12px;
                color: #888;
                font-size: 13px;
                font-weight: 500;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self.image_dropped.emit(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please drop an image file (PNG, JPG, BMP, GIF, WEBP)")
        
        self.setStyleSheet("""
            QLabel {
                background-color: #0f1419;
                border: 3px dashed #1a9fff;
                border-radius: 12px;
                color: #888;
                font-size: 13px;
                font-weight: 500;
            }
        """)


class BackgroundRemovalGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover Pro - AI Powered")
        self.setGeometry(50, 50, 1400, 900)
        
        self.current_image_path = None
        self.current_result_image = None
        self.removal_thread = None
        
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # Left Panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(18)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Header with Icon
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        
        title = QLabel("🎨 Background Remover Pro")
        title_font = QFont("Segoe UI", 20, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #00d4ff; margin: 0px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_frame.setStyleSheet("background-color: transparent; border: none;")
        left_layout.addWidget(header_frame)

        subtitle = QLabel("Remove backgrounds with AI precision")
        subtitle.setStyleSheet("color: #888; font-size: 11px; margin-top: -8px;")
        left_layout.addWidget(subtitle)

        # Separator
        sep1 = QFrame()
        sep1.setStyleSheet("background-color: #1a2332; height: 1px;")
        sep1.setMaximumHeight(1)
        left_layout.addWidget(sep1)

        # Image Input Area
        input_label = QLabel("📸 Select Image")
        input_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 12px; margin-top: 8px;")
        left_layout.addWidget(input_label)
        
        self.image_input = ModernImageLabel()
        self.image_input.setMinimumHeight(180)
        self.image_input.image_dropped.connect(self.load_image)
        self.image_input.mousePressEvent = self.open_file_dialog
        left_layout.addWidget(self.image_input)

        # Model Selection
        model_label = QLabel("🤖 AI Model")
        model_label.setStyleSheet("color: #e0e0e0; font-weight: bold; font-size: 12px;")
        left_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "u2net",
            "u2netp",
            "u2net_human_seg",
            "siluette",
            "isnet-general-use"
        ])
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a2332;
                color: #e0e0e0;
                border: 2px solid #1a9fff;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox:hover {
                border: 2px solid #00d4ff;
                background-color: #1f2a38;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 5px;
            }
            QComboBox::down-arrow {
                image: none;
                color: #00d4ff;
            }
            QComboBox QAbstractItemView {
                background-color: #1a2332;
                color: #e0e0e0;
                border: 2px solid #1a9fff;
                border-radius: 8px;
                selection-background-color: #1a9fff;
            }
        """)
        left_layout.addWidget(self.model_combo)

        # model_info = QLabel("💡 Tip: u2net = Best Quality, u2netp = Faster")
        # model_info.setStyleSheet("color: #666; font-size: 9px; margin-top: -8px;")
        # left_layout.addWidget(model_info)

        # Remove Background Button
        self.remove_btn = QPushButton("⚡ Remove Background")
        self.remove_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.clicked.connect(self.remove_background)
        self.remove_btn.setMinimumHeight(55)
        self.remove_btn.setEnabled(False)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1a9fff, stop:1 #00d4ff);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00d4ff, stop:1 #1a9fff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #0088cc, stop:1 #0099dd);
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)
        left_layout.addWidget(self.remove_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #1a9fff;
                border-radius: 6px;
                text-align: center;
                background-color: #0f1419;
                color: #00d4ff;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #1a9fff, stop:1 #00d4ff);
                border-radius: 4px;
            }
        """)
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(25)
        left_layout.addWidget(self.progress_bar)

        # Separator
        sep2 = QFrame()
        sep2.setStyleSheet("background-color: #1a2332; height: 1px;")
        sep2.setMaximumHeight(1)
        left_layout.addWidget(sep2)

        # Export Button
        self.export_btn = QPushButton("💾 Export Image")
        self.export_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_image)
        self.export_btn.setMinimumHeight(50)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00a86b, stop:1 #00cc77);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
                padding: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #00cc77, stop:1 #00a86b);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #008855, stop:1 #009966);
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)
        left_layout.addWidget(self.export_btn)

        # Status Label
        self.status_label = QLabel("✓ Ready to process images")
        self.status_label.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: 500; margin-top: 5px;")
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        # Right Panel - Image Viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        result_title = QLabel("👁️ Preview")
        result_title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        result_title.setFont(result_title_font)
        result_title.setStyleSheet("color: #00d4ff;")
        right_layout.addWidget(result_title)

        # Result Container
        result_container = QFrame()
        result_container.setStyleSheet("""
            QFrame {
                background-color: #0f1419;
                border: 2px solid #1a9fff;
                border-radius: 12px;
            }
        """)
        result_container_layout = QVBoxLayout(result_container)
        result_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.result_label = QLabel()
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setText("No image processed yet\n\nLoad an image and click 'Remove Background'")
        self.result_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 13px;
                background-color: transparent;
                border: none;
            }
        """)
        self.result_label.setMinimumSize(500, 600)
        result_container_layout.addWidget(self.result_label)
        
        right_layout.addWidget(result_container)

        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)

    def apply_dark_theme(self):
        dark_stylesheet = """
            QMainWindow {
                background-color: #0a0e13;
            }
            QWidget {
                background-color: #0a0e13;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
            }
            QFrame {
                background-color: transparent;
                border: none;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def open_file_dialog(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        try:
            self.current_image_path = file_path
            self.image_input.image_file_path = file_path
            pixmap = QPixmap(file_path)
            
            scaled_pixmap = pixmap.scaledToWidth(140, Qt.TransformationMode.SmoothTransformation)
            self.image_input.setPixmap(scaled_pixmap)
            self.image_input.setText("")
            
            self.status_label.setText(f"✓ Loaded: {Path(file_path).name}")
            self.status_label.setStyleSheet("color: #00d4ff; font-size: 11px; font-weight: 500;")
            self.remove_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            self.status_label.setText("✗ Error loading image")
            self.status_label.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: 500;")

    def remove_background(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first")
            return

        model_name = self.model_combo.currentText()

        self.remove_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"⏳ Processing with {model_name}...")
        self.status_label.setStyleSheet("color: #ffaa00; font-size: 11px; font-weight: 500;")

        self.removal_thread = RemoveBackgroundThread(self.current_image_path, model_name)
        self.removal_thread.finished.connect(self.on_removal_finished)
        self.removal_thread.error.connect(self.on_removal_error)
        self.removal_thread.progress.connect(self.progress_bar.setValue)
        self.removal_thread.start()

    def on_removal_finished(self, result_image):
        self.current_result_image = result_image
        
        # Convert PIL image to QPixmap
        img_byte_arr = io.BytesIO()
        result_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr.getvalue())
        
        # Scale to fit label
        scaled_pixmap = pixmap.scaledToWidth(480, Qt.TransformationMode.SmoothTransformation)
        self.result_label.setPixmap(scaled_pixmap)
        
        self.progress_bar.setVisible(False)
        self.remove_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.status_label.setText("✓ Background removed successfully!")
        self.status_label.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 500;")

    def on_removal_error(self, error_msg):
        QMessageBox.critical(self, "Processing Error", f"Error: {error_msg}")
        self.progress_bar.setVisible(False)
        self.remove_btn.setEnabled(True)
        self.status_label.setText(f"✗ Error: {error_msg[:50]}")
        self.status_label.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: 500;")

    def export_image(self):
        if not self.current_result_image:
            QMessageBox.warning(self, "Warning", "No processed image to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Image (*.png);;JPG Image (*.jpg);;BMP Image (*.bmp)"
        )
        
        if file_path:
            try:
                self.current_result_image.save(file_path)
                QMessageBox.information(self, "✓ Success", f"Image exported successfully!\n{file_path}")
                self.status_label.setText(f"✓ Exported: {Path(file_path).name}")
                self.status_label.setStyleSheet("color: #00ff88; font-size: 11px; font-weight: 500;")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export image: {str(e)}")
                self.status_label.setText("✗ Export failed")
                self.status_label.setStyleSheet("color: #ff6b6b; font-size: 11px; font-weight: 500;")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BackgroundRemovalGUI()
    window.show()
    sys.exit(app.exec())



class ModernImageLabel(QLabel):
    image_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                color: #888;
                font-size: 14px;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Drag & Drop Image Here\nor Click to Select")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.current_image = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    background-color: #2a2a2a;
                    border: 2px dashed #0d7377;
                    border-radius: 8px;
                    color: #0d7377;
                    font-size: 14px;
                }
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                color: #888;
                font-size: 14px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.image_dropped.emit(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please drop an image file (PNG, JPG, BMP, GIF)")
        
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px dashed #3d3d3d;
                border-radius: 8px;
                color: #888;
                font-size: 14px;
            }
        """)


class BackgroundRemovalGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Background Remover - Professional Edition")
        self.setGeometry(100, 100, 1200, 800)
        
        self.current_image_path = None
        self.current_result_image = None
        self.removal_thread = None
        
        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Left Panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(15)

        # Title
        title = QLabel("Background Remover")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #0d7377; margin-bottom: 10px;")
        left_layout.addWidget(title)

        # Image Input Area
        self.image_input = ModernImageLabel()
        self.image_input.setMinimumHeight(200)
        self.image_input.image_dropped.connect(self.load_image)
        self.image_input.mousePressEvent = self.open_file_dialog
        left_layout.addWidget(self.image_input)

        # Model Selection
        model_label = QLabel("Select AI Model:")
        model_label.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        left_layout.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "u2net (Recommended - Slower, Better Quality)",
            "u2netp (Faster - Lower Quality)",
            "u2net_human_seg (Optimized for People)",
            "siluette (Ultra Fast)",
            "isnet-general-use (Good Balance)"
        ])
        self.model_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        left_layout.addWidget(self.model_combo)

        # Remove Background Button
        self.remove_btn = QPushButton("🎨 Remove Background")
        self.remove_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_btn.clicked.connect(self.remove_background)
        self.remove_btn.setMinimumHeight(50)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d7377;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #14919b;
            }
            QPushButton:pressed {
                background-color: #0a5a61;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)
        left_layout.addWidget(self.remove_btn)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                text-align: center;
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #0d7377;
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Export Button
        self.export_btn = QPushButton("💾 Export Image")
        self.export_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_image)
        self.export_btn.setMinimumHeight(50)
        self.export_btn.setEnabled(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #14919b;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0d7377;
            }
            QPushButton:pressed {
                background-color: #0a5a61;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #888;
            }
        """)
        left_layout.addWidget(self.export_btn)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 10px;")
        left_layout.addWidget(self.status_label)

        left_layout.addStretch()

        # Right Panel - Image Viewer
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)

        result_title = QLabel("Result Preview")
        result_title_font = QFont()
        result_title_font.setPointSize(14)
        result_title_font.setBold(True)
        result_title.setFont(result_title_font)
        result_title.setStyleSheet("color: #0d7377;")
        right_layout.addWidget(result_title)

        self.result_label = QLabel()
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setText("No image processed yet")
        self.result_label.setMinimumSize(400, 500)
        right_layout.addWidget(self.result_label)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

    def apply_dark_theme(self):
        dark_stylesheet = """
            QMainWindow {
                background-color: #121212;
            }
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def open_file_dialog(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        try:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path)
            
            scaled_pixmap = pixmap.scaledToWidth(150, Qt.TransformationMode.SmoothTransformation)
            self.image_input.setPixmap(scaled_pixmap)
            self.image_input.setText("")
            
            self.status_label.setText(f"Loaded: {Path(file_path).name}")
            self.remove_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
            self.status_label.setText("Error loading image")

    def remove_background(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Warning", "Please select an image first")
            return

        # Get selected model
        model_text = self.model_combo.currentText()
        model_name = model_text.split(" ")[0]

        self.remove_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Processing with {model_name}...")

        self.removal_thread = RemoveBackgroundThread(self.current_image_path, model_name)
        self.removal_thread.finished.connect(self.on_removal_finished)
        self.removal_thread.error.connect(self.on_removal_error)
        self.removal_thread.progress.connect(self.progress_bar.setValue)
        self.removal_thread.start()

    def on_removal_finished(self, result_image):
        self.current_result_image = result_image
        
        # Convert PIL image to QPixmap
        img_byte_arr = io.BytesIO()
        result_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(img_byte_arr.getvalue())
        
        # Scale to fit label
        scaled_pixmap = pixmap.scaledToWidth(450, Qt.TransformationMode.SmoothTransformation)
        self.result_label.setPixmap(scaled_pixmap)
        
        self.progress_bar.setVisible(False)
        self.remove_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.status_label.setText("✓ Background removed successfully!")

    def on_removal_error(self, error_msg):
        QMessageBox.critical(self, "Processing Error", f"Error: {error_msg}")
        self.progress_bar.setVisible(False)
        self.remove_btn.setEnabled(True)
        self.status_label.setText("Error during processing")

    def export_image(self):
        if not self.current_result_image:
            QMessageBox.warning(self, "Warning", "No processed image to export")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", "", "PNG Image (*.png);;JPG Image (*.jpg);;BMP Image (*.bmp)"
        )
        
        if file_path:
            try:
                self.current_result_image.save(file_path)
                QMessageBox.information(self, "Success", f"Image exported successfully!\n{file_path}")
                self.status_label.setText(f"Exported: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export image: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BackgroundRemovalGUI()
    window.show()
    sys.exit(app.exec())
