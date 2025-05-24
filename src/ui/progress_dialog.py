from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
import logging

import logging
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal

logger = logging.getLogger(__name__)


class ProgressDialog(QDialog):
    """Enhanced progress dialog for group-based processing"""

    canceled = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.is_canceled = False

    def init_ui(self):
        self.setWindowTitle("Processing Files...")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(150)

        layout = QVBoxLayout()

        # Main status label
        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)

        # Progress details label
        self.progress_details = QLabel("0 / 0 files processed")
        self.progress_details.setAlignment(Qt.AlignCenter)
        self.progress_details.setStyleSheet("font-size: 12px; color: #666; margin: 5px;")
        layout.addWidget(self.progress_details)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.setStyleSheet("margin: 10px; padding: 8px;")
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def update_progress(self, current: int, total: int, status: str = ""):
        """Update progress with current/total files and status"""
        if not self.is_canceled:
            # Update progress bar
            if total > 0:
                self.progress_bar.setRange(0, total)
                self.progress_bar.setValue(current)

                # Update window title with percentage
                percentage = int((current / total) * 100) if total > 0 else 0
                self.setWindowTitle(f"Processing Files... ({percentage}%)")
            else:
                self.progress_bar.setRange(0, 0)  # Indeterminate progress

            # Update status label
            if status:
                self.status_label.setText(status)

            # Update progress details
            self.progress_details.setText(f"{current} / {total} files processed")

    def update_status(self, message: str):
        """Update just the status message"""
        if not self.is_canceled:
            self.status_label.setText(message)

    def cancel_operation(self):
        """Handle cancel button click"""
        if not self.is_canceled:
            self.is_canceled = True
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText("Cancelling...")
            self.status_label.setText("Cancelling operation...")
            self.canceled.emit()

    def closeEvent(self, event):
        """Handle window close event"""
        if not self.is_canceled:
            self.cancel_operation()
        event.accept()
