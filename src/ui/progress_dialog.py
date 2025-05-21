from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
import logging

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
import logging

logger = logging.getLogger(__name__)


class ProgressDialog(QDialog):
    """Simple progress dialog for showing processing status"""

    canceled = pyqtSignal()

    def __init__(self, parent=None):
        logger.info("ProgressDialog.__init__ called")
        super().__init__(parent)
        logger.info("ProgressDialog super().__init__ completed")
        self.init_ui()
        self.is_canceled = False
        logger.info("ProgressDialog initialization completed")

    def init_ui(self):
        logger.info("ProgressDialog.init_ui called")
        self.setWindowTitle("Processing Files...")
        self.setModal(False)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Progress bar (indeterminate style)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        logger.info("ProgressDialog.init_ui completed")

    def update_status(self, message: str):
        """Update the status message"""
        logger.info(f"Progress update_status called with: {message}")
        self.status_label.setText(message)
        logger.info(f"Progress: {message}")

    def set_progress(self, current: int, total: int):
        """Set determinate progress"""
        logger.info(f"Progress set_progress called: {current}/{total}")
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)

    def cancel_operation(self):
        """Handle cancel button click"""
        self.is_canceled = True
        self.canceled.emit()
        self.close()