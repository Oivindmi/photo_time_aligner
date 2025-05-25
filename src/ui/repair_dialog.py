# - Dialog for user repair decision

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class RepairDecisionDialog(QDialog):
    """Dialog to get user decision on file repair"""

    def __init__(self, corruption_summary, corruption_results, parent=None):
        super().__init__(parent)
        self.corruption_summary = corruption_summary
        self.corruption_results = corruption_results
        self.repair_choice = False

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Corrupted Files Detected")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout()

        # Title
        title = QLabel("File Corruption Analysis Complete")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Summary section
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout()

        total_files = self.corruption_summary['total_files']
        healthy_files = self.corruption_summary['healthy_files']
        repairable_files = self.corruption_summary['repairable_files']
        unrepairable_files = self.corruption_summary['unrepairable_files']

        summary_layout.addWidget(QLabel(f"• {total_files} total files to process"))
        summary_layout.addWidget(QLabel(f"• {healthy_files} files are healthy"))

        if repairable_files > 0:
            repair_label = QLabel(f"• {repairable_files} files have repairable corruption")
            repair_label.setStyleSheet("color: orange; font-weight: bold;")
            summary_layout.addWidget(repair_label)

        if unrepairable_files > 0:
            unrepairable_label = QLabel(f"• {unrepairable_files} files have severe corruption")
            unrepairable_label.setStyleSheet("color: red; font-weight: bold;")
            summary_layout.addWidget(unrepairable_label)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        # Corruption types section
        if self.corruption_summary['corruption_types']:
            types_group = QGroupBox("Corruption Types Detected")
            types_layout = QVBoxLayout()

            for corruption_type, count in self.corruption_summary['corruption_types'].items():
                if corruption_type != 'healthy':
                    success_rate = self._get_estimated_success_rate(corruption_type)
                    type_label = QLabel(f"• {count} files: {self._format_corruption_type(corruption_type)} "
                                        f"(~{success_rate:.0%} repair success rate)")
                    types_layout.addWidget(type_label)

            types_group.setLayout(types_layout)
            layout.addWidget(types_group)

        # Options section
        options_group = QGroupBox("Repair Options")
        options_layout = QVBoxLayout()

        option1_text = ("✅ Attempt to repair corrupted files first, then process all files normally\n"
                        "   • Best results if repair succeeds\n"
                        "   • Backups will be created automatically\n"
                        "   • Failed repairs will fall back to filesystem-only updates")

        option2_text = ("⚠️ Process files as-is with hybrid approach\n"
                        "   • Safe, guaranteed to work\n"
                        "   • Corrupted files will only get filesystem date updates\n"
                        "   • No internal EXIF metadata restoration for corrupted files")

        options_layout.addWidget(QLabel(option1_text))
        options_layout.addWidget(QLabel(""))
        options_layout.addWidget(QLabel(option2_text))

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Time estimate
        if repairable_files > 0:
            time_estimate = max(1, repairable_files // 3)  # Rough estimate: 3 files per minute
            time_label = QLabel(f"⏱️ Estimated repair time: {time_estimate}-{time_estimate * 2} minutes")
            time_label.setStyleSheet("color: #666; font-style: italic;")
            layout.addWidget(time_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.repair_button = QPushButton("Attempt Repair")
        self.repair_button.setStyleSheet("font-size: 14px; padding: 8px 16px; background-color: #4CAF50; color: white;")
        self.repair_button.clicked.connect(self.accept_repair)

        self.skip_button = QPushButton("Skip Repair")
        self.skip_button.setStyleSheet("font-size: 14px; padding: 8px 16px;")
        self.skip_button.clicked.connect(self.skip_repair)

        button_layout.addStretch()
        button_layout.addWidget(self.skip_button)
        button_layout.addWidget(self.repair_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _format_corruption_type(self, corruption_type: str) -> str:
        """Format corruption type for display"""
        type_names = {
            'exif_structure': 'EXIF structure errors',
            'makernotes': 'MakerNotes issues',
            'severe_corruption': 'Severe corruption',
            'filesystem_only': 'Missing EXIF metadata'
        }
        return type_names.get(corruption_type, corruption_type)

    def _get_estimated_success_rate(self, corruption_type: str) -> float:
        """Get estimated success rate for corruption type"""
        # Get average success rate for this corruption type
        files_of_type = [
            info for info in self.corruption_results.values()
            if info.corruption_type.value == corruption_type
        ]

        if files_of_type:
            avg_success_rate = sum(info.estimated_success_rate for info in files_of_type) / len(files_of_type)
            return avg_success_rate

        return 0.5  # Default 50%

    def accept_repair(self):
        """User chose to attempt repair"""
        self.repair_choice = True
        self.accept()

    def skip_repair(self):
        """User chose to skip repair"""
        self.repair_choice = False
        self.accept()

    def get_repair_choice(self) -> bool:
        """Get the user's repair choice"""
        return self.repair_choice


class RepairProgressDialog(QDialog):
    """Dialog showing repair progress"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Repairing Corrupted Files")
        self.setModal(True)
        self.resize(500, 200)

        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Preparing repair...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)

        # Details text
        self.details_text = QTextEdit()
        self.details_text.setMaximumHeight(100)
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)

        self.setLayout(layout)

    def update_progress(self, current: int, total: int, status: str):
        """Update progress display"""
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
            percentage = int((current / total) * 100)
            self.setWindowTitle(f"Repairing Corrupted Files ({percentage}%)")

        self.status_label.setText(status)

    def add_detail(self, message: str):
        """Add detail message to the log"""
        self.details_text.append(message)
        # Auto-scroll to bottom
        cursor = self.details_text.textCursor()
        cursor.movePosition(cursor.End)
        self.details_text.setTextCursor(cursor)