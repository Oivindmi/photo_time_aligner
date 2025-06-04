# src/ui/repair_dialog.py - Complete repair dialog with strategy selection

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextEdit, QButtonGroup, QRadioButton,
                             QGroupBox, QScrollArea, QWidget, QLineEdit, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import logging
import os
from typing import Dict
from ..core.repair_strategies import RepairStrategy

logger = logging.getLogger(__name__)


class RepairDecisionDialog(QDialog):
    """Dialog for user to decide on repair approach with strategy selection"""

    def __init__(self, corruption_summary: Dict, corruption_results: Dict, parent=None):
        super().__init__(parent)
        self.corruption_summary = corruption_summary
        self.corruption_results = corruption_results
        self.repair_choice = False
        self.selected_strategy = RepairStrategy.SAFEST  # Default to automatic (safest first)
        self.force_strategy = False  # Whether to force a specific strategy

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Corrupted Files Detected")
        self.setModal(True)
        self.setMinimumSize(800, 700)  # Made wider and taller

        layout = QVBoxLayout()

        # Title
        title = QLabel("File Corruption Analysis")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(title)

        # Summary section
        summary_text = self._generate_summary_text()
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Detailed corruption info - Made larger and more prominent
        details_group = QGroupBox("Corruption Details")
        details_layout = QVBoxLayout()

        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMinimumHeight(250)  # Increased from 200
        details_text.setMaximumHeight(350)  # Set max height
        details_text.setPlainText(self._generate_details_text())
        details_text.setFontFamily("Consolas")  # Use monospace font for better formatting
        details_text.setStyleSheet("QTextEdit { background-color: #f8f8f8; }")
        details_layout.addWidget(details_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Repair strategy selection - Made more compact
        strategy_group = QGroupBox("Repair Strategy Selection")
        strategy_layout = QVBoxLayout()

        # Explanation
        strategy_info = QLabel(
            "Choose repair approach:\n"
            "• Automatic: Try strategies in order until one works (recommended)\n"
            "• Force Specific: Use only the selected strategy"
        )
        strategy_info.setStyleSheet("color: #666; font-style: italic; margin-bottom: 5px;")
        strategy_info.setWordWrap(True)
        strategy_layout.addWidget(strategy_info)

        # Radio buttons for strategy selection in a more compact layout
        self.strategy_button_group = QButtonGroup()

        # Automatic mode (default)
        self.auto_radio = QRadioButton("Automatic (Recommended)")
        self.auto_radio.setChecked(True)
        self.auto_radio.setToolTip("Try strategies in order until one works")
        self.strategy_button_group.addButton(self.auto_radio)
        strategy_layout.addWidget(self.auto_radio)

        # Create horizontal layout for force options
        force_layout = QHBoxLayout()

        self.safest_radio = QRadioButton("Force Safest")
        self.safest_radio.setToolTip("Minimal changes (~90% success)")
        self.strategy_button_group.addButton(self.safest_radio)
        force_layout.addWidget(self.safest_radio)

        self.thorough_radio = QRadioButton("Force Thorough")
        self.thorough_radio.setToolTip("Rebuild structure (~70% success)")
        self.strategy_button_group.addButton(self.thorough_radio)
        force_layout.addWidget(self.thorough_radio)

        self.aggressive_radio = QRadioButton("Force Aggressive")
        self.aggressive_radio.setToolTip("Complete rebuild (~50% success)")
        self.strategy_button_group.addButton(self.aggressive_radio)
        force_layout.addWidget(self.aggressive_radio)

        self.filesystem_radio = QRadioButton("Filesystem Only")
        self.filesystem_radio.setToolTip("Skip EXIF repair (~30% success)")
        self.strategy_button_group.addButton(self.filesystem_radio)
        force_layout.addWidget(self.filesystem_radio)

        force_layout.addStretch()
        strategy_layout.addLayout(force_layout)

        strategy_group.setLayout(strategy_layout)
        layout.addWidget(strategy_group)

        # Time estimate and backup info in horizontal layout
        info_layout = QHBoxLayout()

        # Estimated time
        time_estimate = self._calculate_time_estimate()
        time_label = QLabel(f"⏱️ Time: {time_estimate}")
        time_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        info_layout.addWidget(time_label)

        info_layout.addStretch()

        # Backup information
        backup_info = QLabel("📁 Backups will be created automatically")
        backup_info.setStyleSheet("color: #0066cc;")
        info_layout.addWidget(backup_info)

        layout.addLayout(info_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        skip_button = QPushButton("Skip Repair")
        skip_button.setToolTip("Process files without repair")
        skip_button.clicked.connect(self.skip_repair)
        button_layout.addWidget(skip_button)

        repair_button = QPushButton("Attempt Repair")
        repair_button.setToolTip("Create backups and attempt repair")
        repair_button.clicked.connect(self.attempt_repair)
        repair_button.setDefault(True)
        repair_button.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        button_layout.addWidget(repair_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _generate_summary_text(self) -> str:
        """Generate summary text for the dialog"""
        # Handle missing keys gracefully
        total = self.corruption_summary.get('total_files', 0)
        healthy = self.corruption_summary.get('healthy_files', 0)
        repairable = self.corruption_summary.get('repairable_files', 0)
        unrepairable = self.corruption_summary.get('unrepairable_files', 0)

        # Calculate total if not provided
        if total == 0:
            total = healthy + repairable + unrepairable

        text = f"Corruption Analysis Complete:\n"
        text += f"• {healthy} files are healthy\n"

        if repairable > 0:
            text += f"• {repairable} files have repairable corruption\n"

            # Break down by corruption type
            corruption_types = self.corruption_summary.get('corruption_types', {})
            for corruption_type, count in corruption_types.items():
                if corruption_type != 'healthy' and count > 0:
                    success_rate = self._get_success_rate_for_type(corruption_type)
                    text += f"  - {count} files: {corruption_type.replace('_', ' ').title()} (~{success_rate}% repair success rate)\n"

        if unrepairable > 0:
            text += f"• {unrepairable} files have severe corruption\n"

        return text

    def _get_success_rate_for_type(self, corruption_type: str) -> int:
        """Get estimated success rate for corruption type"""
        rates = {
            'makernotes': 90,
            'exif_structure': 70,
            'filesystem_only': 30,
            'severe_corruption': 20
        }
        return rates.get(corruption_type, 50)

    def _generate_details_text(self) -> str:
        """Generate detailed corruption information"""
        details = []

        if not self.corruption_results:
            details.append("No corruption details available.")
            return "\n".join(details)

        # Group files by corruption type for better organization
        corruption_groups = {}

        for file_path, corruption_info in self.corruption_results.items():
            if corruption_info.corruption_type.value != 'healthy':
                corruption_type = corruption_info.corruption_type.value
                if corruption_type not in corruption_groups:
                    corruption_groups[corruption_type] = []
                corruption_groups[corruption_type].append((file_path, corruption_info))

        if not corruption_groups:
            details.append("All files are healthy - no corruption detected.")
            return "\n".join(details)

        # Display each corruption type group
        for corruption_type, files_list in corruption_groups.items():
            details.append(f"=== {corruption_type.replace('_', ' ').upper()} ({len(files_list)} files) ===")
            details.append("")

            for file_path, corruption_info in files_list:
                filename = os.path.basename(file_path)
                details.append(f"📁 File: {filename}")

                # Show corruption type and repairability
                details.append(f"   Type: {corruption_info.corruption_type.value}")
                details.append(f"   Repairable: {'✅ Yes' if corruption_info.is_repairable else '❌ No'}")
                details.append(f"   Success Rate: ~{int(corruption_info.estimated_success_rate * 100)}%")

                # Show error message if available, but clean it up
                if corruption_info.error_message:
                    # Clean up the error message - remove file paths and make it readable
                    error_msg = corruption_info.error_message

                    # Remove long file paths from error messages
                    if "C:/" in error_msg or "c:/" in error_msg:
                        # Extract just the core error without the file path
                        if " - " in error_msg:
                            error_msg = error_msg.split(" - ")[0]

                    # Limit error message length
                    if len(error_msg) > 100:
                        error_msg = error_msg[:100] + "..."

                    details.append(f"   Error: {error_msg}")

                details.append("")  # Empty line between files

            details.append("")  # Empty line between corruption types

        return "\n".join(details)

    def _calculate_time_estimate(self) -> str:
        """Calculate estimated repair time"""
        repairable_count = self.corruption_summary['repairable_files']

        if repairable_count == 0:
            return "No repairs needed"
        elif repairable_count <= 5:
            return "30 seconds - 1 minute"
        elif repairable_count <= 20:
            return "1-3 minutes"
        elif repairable_count <= 50:
            return "3-8 minutes"
        else:
            return f"8-15 minutes ({repairable_count} files)"

    def attempt_repair(self):
        """User chose to attempt repair"""
        self.repair_choice = True

        # Determine selected strategy and mode
        if self.auto_radio.isChecked():
            self.force_strategy = False
            self.selected_strategy = None  # Use automatic progression
        elif self.safest_radio.isChecked():
            self.force_strategy = True
            self.selected_strategy = RepairStrategy.SAFEST
        elif self.thorough_radio.isChecked():
            self.force_strategy = True
            self.selected_strategy = RepairStrategy.THOROUGH
        elif self.aggressive_radio.isChecked():
            self.force_strategy = True
            self.selected_strategy = RepairStrategy.AGGRESSIVE
        elif self.filesystem_radio.isChecked():
            self.force_strategy = True
            self.selected_strategy = RepairStrategy.FILESYSTEM_ONLY

        logger.info(f"User selected repair with strategy: {self.selected_strategy}, force: {self.force_strategy}")
        self.accept()

    def skip_repair(self):
        """User chose to skip repair"""
        self.repair_choice = False
        logger.info("User chose to skip repair")
        self.accept()

    def get_repair_choice(self) -> bool:
        """Get whether user wants to attempt repair"""
        return self.repair_choice

    def get_strategy_choice(self) -> tuple:
        """Get user's strategy choice as (force_strategy: bool, strategy: RepairStrategy)"""
        return (self.force_strategy, self.selected_strategy)


class RepairProgressDialog(QDialog):
    """Dialog showing repair progress with real-time updates"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Repairing Files")
        self.setModal(True)
        self.setMinimumSize(500, 300)

        layout = QVBoxLayout()

        # Title
        self.title_label = QLabel("Repairing Corrupted Files...")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.title_label)

        # Progress info
        self.progress_label = QLabel("Preparing repair operations...")
        layout.addWidget(self.progress_label)

        # Current file being processed
        self.current_file_label = QLabel("")
        self.current_file_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        layout.addWidget(self.current_file_label)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        layout.addWidget(self.results_text)

        # Cancel button (initially)
        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.cancel_button)

        layout.addLayout(self.button_layout)
        self.setLayout(layout)

    def update_progress(self, current: int, total: int, current_file: str = "", status: str = ""):
        """Update progress information"""
        self.progress_label.setText(f"Progress: {current}/{total} files processed")

        if current_file:
            self.current_file_label.setText(f"Processing: {current_file}")

        if status:
            self.results_text.append(status)
            # Auto-scroll to bottom
            cursor = self.results_text.textCursor()
            cursor.movePosition(cursor.End)
            self.results_text.setTextCursor(cursor)

    def repair_completed(self):
        """Called when repair is completed"""
        self.title_label.setText("Repair Complete")
        self.current_file_label.setText("")

        # Replace cancel button with close button
        self.cancel_button.setText("Close")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self.accept)