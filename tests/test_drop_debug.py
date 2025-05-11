# test_drop_debug.py - Debug the drop functionality
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# Import from our application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.ui.main_window import PhotoDropZone
from src.core import FileProcessor, ExifHandler


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_processor = FileProcessor(ExifHandler())
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Drop Test")
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create drop zone
        self.drop_zone = PhotoDropZone("Drop any file here", parent=self)
        self.drop_zone.file_dropped.connect(self.file_dropped)
        layout.addWidget(self.drop_zone)

    def file_dropped(self, file_path):
        print(f"File dropped: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        print(f"Extension: {ext}")
        print(f"Supported: {ext in self.file_processor.supported_extensions}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())