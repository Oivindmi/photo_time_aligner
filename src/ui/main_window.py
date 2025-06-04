from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QListWidget,
                             QRadioButton, QCheckBox, QFileDialog, QButtonGroup,
                             QGroupBox, QMessageBox, QScrollArea, QSpinBox)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap
import os
from datetime import datetime, timedelta
from typing import List
from ..core import ExifHandler, ConfigManager, FileProcessor, TimeCalculator
from ..utils import FileProcessingError
from .file_scanner_thread import FileScannerThread
from ..core.supported_formats import is_supported_format
from .progress_dialog import ProgressDialog
from .metadata_dialog import MetadataInvestigationDialog
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from typing import Dict, List, Optional
import os
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QApplication

logger = logging.getLogger(__name__)


class PhotoDropZone(QLabel):
    """Widget for drag and drop media functionality"""

    file_dropped = pyqtSignal(str)

    def __init__(self, text="Drop media file here", parent=None):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(300, 200)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 25px;
                background-color: #f9f9f9;
                font-size: 14px;
            }
        """)
        self.file_path = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet().replace('#f9f9f9', '#e6f3ff'))

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace('#e6f3ff', '#f9f9f9'))

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]

            if is_supported_format(file_path):
                self.file_path = file_path
                self.setText(os.path.basename(file_path))
                self.file_dropped.emit(file_path)
            else:
                ext = os.path.splitext(file_path)[1].lower()
                QMessageBox.warning(self, "Unsupported File",
                                    f"File type '{ext}' is not supported.")

        self.setStyleSheet(self.styleSheet().replace('#e6f3ff', '#f9f9f9'))


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager, exif_handler: ExifHandler):
        super().__init__()
        self.config_manager = config_manager
        self.exif_handler = exif_handler
        self.file_processor = FileProcessor(self.exif_handler)
        self.reference_file = None
        self.target_file = None
        self.reference_metadata = {}
        self.target_metadata = {}
        self.reference_group_files = []
        self.target_group_files = []
        self.time_offset = None

        # Single file mode state
        self.single_file_mode = False

        # Thread references
        self.ref_scanner_thread = None
        self.target_scanner_thread = None

        # Manual offset controls (will be set in init_ui)
        self.manual_years = None
        self.manual_days = None
        self.manual_hours = None
        self.manual_minutes = None
        self.manual_seconds = None
        self.manual_add_radio = None
        self.manual_subtract_radio = None
        self.manual_direction_group = None
        self.manual_offset_container = None
        self.manual_note_label = None

        # UI element references for mode control
        self.target_section_widgets = []
        self.ref_group_box = None
        self.target_group_box = None
        self.ref_files_group = None
        self.target_files_group = None

        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("Photo & Video Time Aligner")
        self.setMinimumSize(900, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Add Single File Mode toggle and Corruption Detection at the top
        top_controls_layout = QHBoxLayout()

        self.single_file_mode_check = QCheckBox("Single File Mode (Investigation Only)")
        self.single_file_mode_check.setToolTip("Enable to investigate single files without processing groups")
        self.single_file_mode_check.stateChanged.connect(self.toggle_single_file_mode)
        top_controls_layout.addWidget(self.single_file_mode_check)

        # Add some spacing
        top_controls_layout.addSpacing(30)

        # Add corruption detection checkbox
        self.corruption_detection_check = QCheckBox("Enable Corruption Detection & Repair")
        self.corruption_detection_check.setChecked(True)  # Default to enabled
        self.corruption_detection_check.setToolTip(
            "Scan files for corruption before processing and offer repair options.\n"
            "Disable this to skip corruption analysis for faster processing."
        )
        top_controls_layout.addWidget(self.corruption_detection_check)

        top_controls_layout.addStretch()
        main_layout.addLayout(top_controls_layout)

        # Create top section with drop zones
        drop_section = QHBoxLayout()

        # Reference photo section
        reference_section = QVBoxLayout()
        reference_section.addWidget(QLabel("Reference Media"))
        self.reference_drop = PhotoDropZone("Drop Reference Photo/Video", parent=self)
        self.reference_drop.file_dropped.connect(self.load_reference_photo)
        reference_section.addWidget(self.reference_drop)
        self.reference_info = QLabel("No media loaded")
        reference_section.addWidget(self.reference_info)

        # Target photo section - store widgets for disabling
        target_section = QVBoxLayout()
        target_label = QLabel("Media to Align")
        target_section.addWidget(target_label)
        self.target_drop = PhotoDropZone("Drop Photo/Video to Align", parent=self)
        self.target_drop.file_dropped.connect(self.load_target_photo)
        target_section.addWidget(self.target_drop)
        self.target_info = QLabel("No media loaded")
        target_section.addWidget(self.target_info)

        # Store target section widgets for disabling
        self.target_section_widgets = [target_label, self.target_drop, self.target_info]

        drop_section.addLayout(reference_section)
        drop_section.addLayout(target_section)
        main_layout.addLayout(drop_section)

        # Create middle section with group rules and time fields
        middle_section = QHBoxLayout()

        # Reference group settings - store reference for disabling
        self.ref_group_box = QGroupBox("Reference Group Settings")
        ref_layout = QVBoxLayout()

        self.ref_camera_check = QCheckBox("Match Camera Model")
        self.ref_camera_check.setChecked(True)
        self.ref_camera_check.stateChanged.connect(self.update_reference_files)
        ref_layout.addWidget(self.ref_camera_check)

        self.ref_extension_check = QCheckBox("Match File Extension")
        self.ref_extension_check.setChecked(True)
        self.ref_extension_check.stateChanged.connect(self.update_reference_files)
        ref_layout.addWidget(self.ref_extension_check)

        self.ref_pattern_check = QCheckBox("Match Filename Pattern")
        self.ref_pattern_check.setChecked(False)
        self.ref_pattern_check.stateChanged.connect(self.update_reference_files)
        ref_layout.addWidget(self.ref_pattern_check)

        self.ref_pattern_label = QLabel("Pattern: Not detected")
        self.ref_pattern_label.setStyleSheet("color: #666; font-style: italic;")
        ref_layout.addWidget(self.ref_pattern_label)

        self.ref_file_count = QLabel("Matching files: 0")
        ref_layout.addWidget(self.ref_file_count)

        ref_layout.addWidget(QLabel("Time Field:"))
        self.ref_time_group = QButtonGroup()
        self.ref_time_radios = {}
        self.ref_time_container = QVBoxLayout()
        ref_layout.addLayout(self.ref_time_container)

        self.ref_group_box.setLayout(ref_layout)

        # Target group settings - store reference for disabling
        self.target_group_box = QGroupBox("Target Group Settings")
        target_layout = QVBoxLayout()

        self.target_camera_check = QCheckBox("Match Camera Model")
        self.target_camera_check.setChecked(True)
        self.target_camera_check.stateChanged.connect(self.update_target_files)
        target_layout.addWidget(self.target_camera_check)

        self.target_extension_check = QCheckBox("Match File Extension")
        self.target_extension_check.setChecked(True)
        self.target_extension_check.stateChanged.connect(self.update_target_files)
        target_layout.addWidget(self.target_extension_check)

        self.target_pattern_check = QCheckBox("Match Filename Pattern")
        self.target_pattern_check.setChecked(False)
        self.target_pattern_check.stateChanged.connect(self.update_target_files)
        target_layout.addWidget(self.target_pattern_check)

        self.target_pattern_label = QLabel("Pattern: Not detected")
        self.target_pattern_label.setStyleSheet("color: #666; font-style: italic;")
        target_layout.addWidget(self.target_pattern_label)

        self.target_file_count = QLabel("Matching files: 0")
        target_layout.addWidget(self.target_file_count)

        target_layout.addWidget(QLabel("Time Field:"))
        self.target_time_group = QButtonGroup()
        self.target_time_radios = {}
        self.target_time_container = QVBoxLayout()
        target_layout.addLayout(self.target_time_container)

        self.target_group_box.setLayout(target_layout)

        middle_section.addWidget(self.ref_group_box)
        middle_section.addWidget(self.target_group_box)
        main_layout.addLayout(middle_section)

        # File lists section - store references for disabling
        file_lists_section = QHBoxLayout()

        # Reference files list
        self.ref_files_group = QGroupBox("Reference Files")
        ref_files_layout = QVBoxLayout()
        self.ref_files_list = QListWidget()
        ref_files_layout.addWidget(self.ref_files_list)
        self.ref_files_group.setLayout(ref_files_layout)

        # Target files list
        self.target_files_group = QGroupBox("Target Files")
        target_files_layout = QVBoxLayout()
        self.target_files_list = QListWidget()
        target_files_layout.addWidget(self.target_files_list)
        self.target_files_group.setLayout(target_files_layout)

        file_lists_section.addWidget(self.ref_files_group)
        file_lists_section.addWidget(self.target_files_group)
        main_layout.addLayout(file_lists_section)

        # Time offset display
        offset_layout = QVBoxLayout()
        self.offset_label = QLabel("Time Offset: Not calculated")
        self.offset_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        offset_layout.addWidget(self.offset_label)

        # Manual time offset section
        self.create_manual_offset_section(offset_layout)

        main_layout.addLayout(offset_layout)

        # Master folder section - store references for disabling
        master_folder_layout = QHBoxLayout()
        master_folder_layout.addWidget(QLabel("Master Folder:"))
        self.master_folder_input = QLineEdit()
        master_folder_layout.addWidget(self.master_folder_input)
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_master_folder)
        master_folder_layout.addWidget(self.browse_button)

        self.move_files_check = QCheckBox("Move processed files to master folder")
        self.move_files_check.setChecked(True)

        main_layout.addLayout(master_folder_layout)
        main_layout.addWidget(self.move_files_check)

        # Add folder organization options - store reference for disabling
        self.folder_org_group = QGroupBox("Master Folder Organization")
        folder_org_layout = QVBoxLayout()

        self.folder_org_group_buttons = QButtonGroup()
        self.org_root_radio = QRadioButton("Move to root folder")
        self.org_root_radio.setChecked(True)
        self.org_camera_radio = QRadioButton("Create camera-specific subfolders")

        self.folder_org_group_buttons.addButton(self.org_root_radio)
        self.folder_org_group_buttons.addButton(self.org_camera_radio)

        folder_org_layout.addWidget(self.org_root_radio)
        folder_org_layout.addWidget(self.org_camera_radio)

        self.folder_org_group.setLayout(folder_org_layout)

        # Only show organization options when move files is checked
        self.folder_org_group.setEnabled(self.move_files_check.isChecked())
        self.move_files_check.stateChanged.connect(
            lambda state: self.folder_org_group.setEnabled(state == Qt.Checked)
        )

        main_layout.addWidget(self.folder_org_group)

        # Apply and investigate buttons section
        button_layout = QHBoxLayout()

        self.apply_button = QPushButton("Apply Alignment")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_alignment)
        self.apply_button.setStyleSheet("font-size: 16px; padding: 10px;")
        button_layout.addWidget(self.apply_button)

        # Add the clear button right after apply_button:
        self.clear_button = QPushButton("Clear Files")
        self.clear_button.clicked.connect(self.clear_loaded_files)
        self.clear_button.setStyleSheet("font-size: 16px; padding: 10px;")
        button_layout.addWidget(self.clear_button)

        # Investigate metadata button
        self.investigate_button = QPushButton("Investigate Metadata")
        self.investigate_button.clicked.connect(self.investigate_metadata)
        self.investigate_button.setStyleSheet("font-size: 16px; padding: 10px;")
        button_layout.addWidget(self.investigate_button)

        # Radio buttons for file selection
        button_layout.addWidget(QLabel("("))

        self.investigate_ref_radio = QRadioButton("Reference")
        self.investigate_ref_radio.setChecked(True)
        button_layout.addWidget(self.investigate_ref_radio)

        button_layout.addWidget(QLabel("•"))

        self.investigate_target_radio = QRadioButton("Target")
        button_layout.addWidget(self.investigate_target_radio)

        button_layout.addWidget(QLabel(")"))

        # Group the radio buttons
        self.investigate_file_group = QButtonGroup()
        self.investigate_file_group.addButton(self.investigate_ref_radio)
        self.investigate_file_group.addButton(self.investigate_target_radio)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

    def toggle_single_file_mode(self, state):
        """Toggle between single file mode and normal mode"""
        self.single_file_mode = (state == Qt.Checked)

        # Update UI state
        self.update_ui_for_single_file_mode()

        # Clear current processing if switching modes
        if self.single_file_mode:
            # Stop any running file scans
            self.stop_file_scanning()
            # Clear file lists
            self.clear_file_lists()
            # Shutdown ExifTool pool and create single process for single file operations
            logger.info("Single file mode: Shutting down ExifTool pool, creating single process")
            self.exif_handler.exiftool_pool.shutdown()
            # Create single ExifTool process for single file operations
            from ..core.exiftool_process import ExifToolProcess
            self.exif_handler._single_process = ExifToolProcess()
            self.exif_handler._single_process.start()
            # Update status
            self.statusBar().showMessage("Single File Mode - Investigation Only (Using single ExifTool process)")
        else:
            # Re-enable normal processing
            # Clean up single process if it exists
            if hasattr(self.exif_handler, '_single_process'):
                logger.info("Normal mode: Stopping single process, restarting ExifTool pool")
                self.exif_handler._single_process.stop()
                delattr(self.exif_handler, '_single_process')

            # Restart ExifTool pool for batch operations
            from ..core.exiftool_pool import ExifToolProcessPool
            self.exif_handler.exiftool_pool = ExifToolProcessPool(pool_size=4)
            self.statusBar().showMessage("Normal Mode - Full Processing (ExifTool pool active)")
            # If we have files loaded, restart normal scanning
            if self.reference_file:
                self.update_reference_files()
            if self.target_file:
                self.update_target_files()

    def update_ui_for_single_file_mode(self):
        """Update UI elements based on single file mode state"""
        # Inverse logic: disable when in single file mode
        normal_mode = not self.single_file_mode

        # Disable target section completely in single file mode
        for widget in self.target_section_widgets:
            widget.setEnabled(normal_mode)

        # Disable group settings but keep time fields enabled in single mode
        if self.single_file_mode:
            # In single file mode: disable matching controls but keep time fields enabled
            self.ref_camera_check.setEnabled(False)
            self.ref_extension_check.setEnabled(False)
            self.ref_pattern_check.setEnabled(False)
            self.ref_pattern_label.setEnabled(False)
            self.ref_file_count.setEnabled(False)
            # Keep time fields enabled by not disabling the whole group box
        else:
            # In normal mode: enable everything
            self.ref_camera_check.setEnabled(True)
            self.ref_extension_check.setEnabled(True)
            self.ref_pattern_check.setEnabled(True)
            self.ref_pattern_label.setEnabled(True)
            self.ref_file_count.setEnabled(True)

        self.target_group_box.setEnabled(normal_mode)

        # Disable file lists
        self.ref_files_group.setEnabled(normal_mode)
        self.target_files_group.setEnabled(normal_mode)

        # Disable processing controls
        self.apply_button.setEnabled(normal_mode and self.can_apply_alignment())

        # Disable master folder controls
        self.master_folder_input.setEnabled(normal_mode)
        self.browse_button.setEnabled(normal_mode)
        self.move_files_check.setEnabled(normal_mode)
        self.folder_org_group.setEnabled(normal_mode and self.move_files_check.isChecked())

        # Disable manual offset controls
        if hasattr(self, 'manual_offset_container'):
            self.manual_offset_container.setEnabled(normal_mode)

        # Keep investigation button enabled - it's useful in both modes
        self.investigate_button.setEnabled(True)

        # Update investigate radio buttons
        self.update_investigate_button_state()

    def stop_file_scanning(self):
        """Stop any running file scanning threads"""
        if self.ref_scanner_thread and self.ref_scanner_thread.isRunning():
            self.ref_scanner_thread.stop()
            self.ref_scanner_thread.wait()

        if self.target_scanner_thread and self.target_scanner_thread.isRunning():
            self.target_scanner_thread.stop()
            self.target_scanner_thread.wait()

    def clear_file_lists(self):
        """Clear file lists and reset counters"""
        self.ref_files_list.clear()
        self.target_files_list.clear()
        self.reference_group_files = []
        self.target_group_files = []
        self.ref_file_count.setText("Matching files: 0")
        self.target_file_count.setText("Matching files: 0")

    def can_apply_alignment(self):
        """Check if alignment can be applied"""
        if self.single_file_mode:
            return False

        if self.reference_file:
            if self.target_file:
                # Both photos loaded - use calculated offset
                return self.time_offset is not None
            else:
                # Only reference loaded - can apply with or without manual offset
                return True
        return False

    def investigate_metadata(self):
        """Open metadata investigation dialog"""
        try:
            # Determine which file to investigate
            if self.investigate_ref_radio.isChecked():
                if not self.reference_file:
                    QMessageBox.warning(self, "Warning", "No reference file loaded.")
                    return
                file_to_investigate = self.reference_file
                logger.info(f"Investigating reference file: {file_to_investigate}")
            else:
                if not self.target_file:
                    QMessageBox.warning(self, "Warning", "No target file loaded.")
                    return
                file_to_investigate = self.target_file
                logger.info(f"Investigating target file: {file_to_investigate}")

            # Open investigation dialog
            dialog = MetadataInvestigationDialog(file_to_investigate, self.exif_handler, self)
            dialog.exec_()

        except Exception as e:
            logger.error(f"Error in investigate_metadata: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error investigating metadata: {str(e)}")

    def update_investigate_button_state(self):
        """Update investigate button and radio button states"""
        has_ref = self.reference_file is not None
        has_target = self.target_file is not None

        # Enable investigate button if at least one file is loaded
        self.investigate_button.setEnabled(has_ref or has_target)

        # Enable/disable radio buttons based on loaded files and mode
        self.investigate_ref_radio.setEnabled(has_ref)
        self.investigate_target_radio.setEnabled(has_target and not self.single_file_mode)

        # Auto-select available option if current selection is disabled
        if self.investigate_ref_radio.isChecked() and not has_ref and has_target:
            self.investigate_target_radio.setChecked(True)
        elif self.investigate_target_radio.isChecked() and (not has_target or self.single_file_mode) and has_ref:
            self.investigate_ref_radio.setChecked(True)

        # Default to reference if both available
        if has_ref and not self.investigate_ref_radio.isChecked() and not self.investigate_target_radio.isChecked():
            self.investigate_ref_radio.setChecked(True)

    def load_reference_photo(self, file_path: str):
        """Load reference photo and scan for matching files (unless in single file mode)"""
        try:
            self.reference_file = file_path
            self.reference_metadata = self.exif_handler.read_metadata(file_path)
            camera_info = self.exif_handler.get_camera_info(file_path)

            # Update UI with camera info AND file path
            camera_str = f"{camera_info['make']} {camera_info['model']}".strip() or "Unknown Camera"
            folder_path = os.path.dirname(file_path)
            self.reference_info.setText(f"{camera_str}\nPath: {folder_path}")

            # Load time fields
            self.load_time_fields_for_reference()

            # Only find matching files if NOT in single file mode
            if not self.single_file_mode:
                self.update_reference_files()
                # Calculate offset if both files are loaded
                self.calculate_time_offset()
                # Update manual offset state
                self.update_manual_offset_state()
                # Update apply button state
                self.update_apply_button_state()

            # Update investigate button state
            self.update_investigate_button_state()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading reference photo: {str(e)}")

    def load_target_photo(self, file_path: str):
        """Load target photo and scan for matching files (unless in single file mode)"""
        try:
            self.target_file = file_path
            self.target_metadata = self.exif_handler.read_metadata(file_path)
            camera_info = self.exif_handler.get_camera_info(file_path)

            # Update UI with camera info AND file path
            camera_str = f"{camera_info['make']} {camera_info['model']}".strip() or "Unknown Camera"
            folder_path = os.path.dirname(file_path)
            self.target_info.setText(f"{camera_str}\nPath: {folder_path}")

            # Load time fields
            self.load_time_fields_for_target()

            # Only find matching files if NOT in single file mode
            if not self.single_file_mode:
                self.update_target_files()
                # Calculate offset if both files are loaded
                self.calculate_time_offset()
                # Update manual offset state
                self.update_manual_offset_state()
                # Update apply button state
                self.update_apply_button_state()

            # Update investigate button state
            self.update_investigate_button_state()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading target photo: {str(e)}")

    def load_time_fields_for_reference(self):
        """Load available time fields for reference photo"""
        # Clear existing radio buttons
        for radio in self.ref_time_radios.values():
            container = radio.parent()
            self.ref_time_container.removeWidget(container)
            container.deleteLater()
        self.ref_time_radios.clear()

        # Get datetime fields and raw metadata
        datetime_fields = self.exif_handler.get_datetime_fields(self.reference_file)
        raw_metadata = self.exif_handler.read_metadata(self.reference_file)

        # Create radio buttons for each field
        first = True
        for field_name, parsed_value in datetime_fields.items():
            if parsed_value:
                raw_value = raw_metadata.get(field_name, "")

                # Create a widget to hold the radio button and labels
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                # Create radio button
                radio = QRadioButton()
                radio.setProperty("field_name", field_name)
                radio.toggled.connect(self.calculate_time_offset)
                self.ref_time_group.addButton(radio)
                self.ref_time_radios[field_name] = radio

                # Create labels with fixed widths
                field_label = QLabel(f"{field_name}:")
                field_label.setFixedWidth(150)

                raw_label = QLabel(f"Raw: {raw_value}")
                raw_label.setFixedWidth(300)

                parsed_label = QLabel(f"Parsed: {parsed_value.strftime('%Y-%m-%d %H:%M:%S')}")
                parsed_label.setFixedWidth(250)

                # Add widgets to layout
                layout.addWidget(radio)
                layout.addWidget(field_label)
                layout.addWidget(raw_label)
                layout.addWidget(parsed_label)
                layout.addStretch()

                self.ref_time_container.addWidget(container)

                if first:
                    radio.setChecked(True)
                    first = False

    def load_time_fields_for_target(self):
        """Load available time fields for target photo"""
        # Clear existing radio buttons
        for radio in self.target_time_radios.values():
            container = radio.parent()
            self.target_time_container.removeWidget(container)
            container.deleteLater()
        self.target_time_radios.clear()

        # Get datetime fields and raw metadata
        datetime_fields = self.exif_handler.get_datetime_fields(self.target_file)
        raw_metadata = self.exif_handler.read_metadata(self.target_file)

        # Create radio buttons for each field
        first = True
        for field_name, parsed_value in datetime_fields.items():
            if parsed_value:
                raw_value = raw_metadata.get(field_name, "")

                # Create a widget to hold the radio button and labels
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(10)

                # Create radio button
                radio = QRadioButton()
                radio.setProperty("field_name", field_name)
                radio.toggled.connect(self.calculate_time_offset)
                self.target_time_group.addButton(radio)
                self.target_time_radios[field_name] = radio

                # Create labels with fixed widths
                field_label = QLabel(f"{field_name}:")
                field_label.setFixedWidth(150)

                raw_label = QLabel(f"Raw: {raw_value}")
                raw_label.setFixedWidth(300)

                parsed_label = QLabel(f"Parsed: {parsed_value.strftime('%Y-%m-%d %H:%M:%S')}")
                parsed_label.setFixedWidth(250)

                # Add widgets to layout
                layout.addWidget(radio)
                layout.addWidget(field_label)
                layout.addWidget(raw_label)
                layout.addWidget(parsed_label)
                layout.addStretch()

                self.target_time_container.addWidget(container)

                if first:
                    radio.setChecked(True)
                    first = False

    def update_reference_files(self):
        """Update list of files matching reference photo criteria (skip in single file mode)"""
        if not self.reference_file or self.single_file_mode:
            return

        # Cancel previous scan if running
        if self.ref_scanner_thread and self.ref_scanner_thread.isRunning():
            self.ref_scanner_thread.stop()
            self.ref_scanner_thread.wait()

        # Update UI to show scanning
        self.ref_file_count.setText("Scanning...")
        self.ref_files_list.clear()
        self.reference_group_files = []

        # Reset pattern label if pattern matching is disabled
        if not self.ref_pattern_check.isChecked():
            self.ref_pattern_label.setText("Pattern: Not detected")

        # Create and start scanner thread
        self.ref_scanner_thread = FileScannerThread(
            self.file_processor,
            self.reference_file,
            self.ref_camera_check.isChecked(),
            self.ref_extension_check.isChecked(),
            self.ref_pattern_check.isChecked()
        )

        # Connect signals
        self.ref_scanner_thread.file_found.connect(self._on_reference_file_found)
        self.ref_scanner_thread.scanning_complete.connect(self._on_reference_scanning_complete)
        self.ref_scanner_thread.error.connect(self._on_reference_scan_error)
        self.ref_scanner_thread.status_update.connect(
            lambda msg: self.statusBar().showMessage(msg)
        )
        self.ref_scanner_thread.pattern_detected.connect(
            lambda pattern: self.ref_pattern_label.setText(f"Pattern: {pattern}")
        )

        self.ref_scanner_thread.start()

    def update_target_files(self):
        """Update list of files matching target photo criteria (skip in single file mode)"""
        if not self.target_file or self.single_file_mode:
            return

        # Cancel previous scan if running
        if self.target_scanner_thread and self.target_scanner_thread.isRunning():
            self.target_scanner_thread.stop()
            self.target_scanner_thread.wait()

        # Update UI to show scanning
        self.target_file_count.setText("Scanning...")
        self.target_files_list.clear()
        self.target_group_files = []

        # Reset pattern label if pattern matching is disabled
        if not self.target_pattern_check.isChecked():
            self.target_pattern_label.setText("Pattern: Not detected")

        # Create and start scanner thread
        self.target_scanner_thread = FileScannerThread(
            self.file_processor,
            self.target_file,
            self.target_camera_check.isChecked(),
            self.target_extension_check.isChecked(),
            self.target_pattern_check.isChecked()
        )

        # Connect signals
        self.target_scanner_thread.file_found.connect(self._on_target_file_found)
        self.target_scanner_thread.scanning_complete.connect(self._on_target_scanning_complete)
        self.target_scanner_thread.error.connect(self._on_target_scan_error)
        self.target_scanner_thread.status_update.connect(
            lambda msg: self.statusBar().showMessage(msg)
        )
        self.target_scanner_thread.pattern_detected.connect(
            lambda pattern: self.target_pattern_label.setText(f"Pattern: {pattern}")
        )

        self.target_scanner_thread.start()

    def _on_reference_file_found(self, file_path: str):
        """Handle individual file found by reference scanner thread"""
        self.reference_group_files.append(file_path)
        self.ref_files_list.addItem(os.path.basename(file_path))
        self.ref_file_count.setText(f"Matching files: {len(self.reference_group_files)}")

    def _on_target_file_found(self, file_path: str):
        """Handle individual file found by target scanner thread"""
        self.target_group_files.append(file_path)
        self.target_files_list.addItem(os.path.basename(file_path))
        self.target_file_count.setText(f"Matching files: {len(self.target_group_files)}")

    def _on_reference_scanning_complete(self):
        """Handle completion of reference file scanning"""
        logger.info(f"Reference scanning complete, found {len(self.reference_group_files)} matching files")
        self.reference_group_files.sort()

    def _on_target_scanning_complete(self):
        """Handle completion of target file scanning"""
        logger.info(f"Target scanning complete, found {len(self.target_group_files)} matching files")
        self.target_group_files.sort()

    def _on_reference_scan_error(self, error_msg: str):
        """Handle scanning errors"""
        self.statusBar().showMessage(f"Error scanning reference files: {error_msg}")
        self.ref_file_count.setText("Error scanning files")

    def _on_target_scan_error(self, error_msg: str):
        """Handle scanning errors"""
        self.statusBar().showMessage(f"Error scanning target files: {error_msg}")
        self.target_file_count.setText("Error scanning files")

    def calculate_time_offset(self):
        """Calculate time offset between selected fields"""
        if not (self.reference_file and self.target_file):
            return

        # Get selected fields
        ref_field = None
        target_field = None

        for radio in self.ref_time_radios.values():
            if radio.isChecked():
                ref_field = radio.property("field_name")
                break

        for radio in self.target_time_radios.values():
            if radio.isChecked():
                target_field = radio.property("field_name")
                break

        if not (ref_field and target_field):
            return

        try:
            # Get datetime values
            ref_datetime = self.exif_handler.get_datetime_fields(self.reference_file)[ref_field]
            target_datetime = self.exif_handler.get_datetime_fields(self.target_file)[target_field]

            if ref_datetime and target_datetime:
                # Calculate the offset
                self.time_offset = TimeCalculator.calculate_offset(ref_datetime, target_datetime)

                # Format offset display
                offset_str, direction = TimeCalculator.format_offset(self.time_offset)

                display_text = f"Time Offset: {offset_str}\n"
                display_text += f"Target photo is {direction} reference photo"

                self.offset_label.setText(display_text)
                self.update_apply_button_state()
        except Exception as e:
            self.statusBar().showMessage(f"Error calculating offset: {str(e)}")

    def browse_master_folder(self):
        """Browse for master folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Master Folder")
        if folder:
            self.master_folder_input.setText(folder)

    def apply_alignment(self):
        """Apply time alignment to all matching files with optional corruption detection and repair"""
        logger.info("=== Starting enhanced apply_alignment with optional repair functionality ===")

        try:
            # Determine which offset to use
            offset_to_use = None

            if self.target_file:
                # Both photos loaded - use calculated offset
                if self.time_offset is None:
                    QMessageBox.warning(self, "Warning", "Please load both photos first.")
                    return
                offset_to_use = self.time_offset
                logger.info(f"Using calculated offset: {self.time_offset}")
            else:
                # Only reference loaded - use manual offset
                offset_to_use = self.get_manual_offset_timedelta()
                logger.info(f"Using manual offset: {offset_to_use}")

            # Get selected time fields
            ref_field = None
            target_field = None

            for radio in self.ref_time_radios.values():
                if radio.isChecked():
                    ref_field = radio.property("field_name")
                    break

            # For single photo mode, use reference field for both
            if not self.target_file:
                target_field = ref_field
            else:
                for radio in self.target_time_radios.values():
                    if radio.isChecked():
                        target_field = radio.property("field_name")
                        break

            if not ref_field:
                QMessageBox.warning(self, "Warning", "Please select a time field for the reference group.")
                return

            # Determine which files to process
            reference_files = self.reference_group_files if self.reference_group_files else []
            target_files = self.target_group_files if self.target_group_files else []

            if not reference_files and not target_files:
                QMessageBox.warning(self, "Warning", "No files to process.")
                return

            # Get master folder settings
            master_folder = self.master_folder_input.text() if self.move_files_check.isChecked() else None
            use_camera_folders = self.org_camera_radio.isChecked() if self.move_files_check.isChecked() else False

            if self.move_files_check.isChecked() and not master_folder:
                QMessageBox.warning(self, "Warning", "Please specify a master folder.")
                return

            # Show enhanced progress dialog
            self.progress_dialog = ProgressDialog(self)
            self.progress_dialog.show()

            # Set up progress callback
            def progress_callback(current, total, status):
                if hasattr(self, 'progress_dialog') and self.progress_dialog:
                    self.progress_dialog.update_progress(current, total, status)
                    QApplication.processEvents()

            # Record start time
            start_time = datetime.now()

            # Create enhanced processor and run with optional repair functionality
            from ..core import AlignmentProcessor, AlignmentReport
            processor = AlignmentProcessor(self.exif_handler, self.file_processor)

            # Check if corruption detection is enabled
            if self.corruption_detection_check.isChecked():
                logger.info("Corruption detection enabled - will scan files for corruption")
                # Override the repair choice method to show our UI dialog
                processor._get_user_repair_choice = self._show_repair_dialog
            else:
                logger.info("Corruption detection disabled - skipping corruption analysis")
                # Override to always return no repair
                processor._get_user_repair_choice = lambda summary, results: (False, False, None)

            # Process files using enhanced approach with optional corruption detection
            if not self.target_file:
                # Manual mode: treat reference files as target files so they get the offset
                manual_offset = offset_to_use
                # Invert the sign because AlignmentProcessor subtracts target offset
                inverted_offset = -manual_offset
                logger.info(f"Manual mode: Processing {len(reference_files)} files as targets")

                status = processor.process_files(
                    reference_files=[],
                    target_files=reference_files,
                    reference_field=ref_field,
                    target_field=ref_field,
                    time_offset=inverted_offset,
                    master_folder=master_folder,
                    move_files=self.move_files_check.isChecked(),
                    use_camera_folders=use_camera_folders,
                    progress_callback=progress_callback
                )
            else:
                # Two-photo mode: normal behavior
                logger.info(
                    f"Two-photo mode: Processing {len(reference_files)} reference + {len(target_files)} target files")
                status = processor.process_files(
                    reference_files=reference_files,
                    target_files=target_files,
                    reference_field=ref_field,
                    target_field=target_field,
                    time_offset=offset_to_use,
                    master_folder=master_folder,
                    move_files=self.move_files_check.isChecked(),
                    use_camera_folders=use_camera_folders,
                    progress_callback=progress_callback
                )

            # Record end time
            end_time = datetime.now()

            # Hide progress dialog
            self.progress_dialog.close()

            # Generate enhanced report with repair information
            report_generator = AlignmentReport(self.config_manager)
            report_text = self._generate_enhanced_report(
                status, offset_to_use, start_time, end_time, use_camera_folders
            )

            # Print to console
            print("\n" + report_text)

            # Save log file
            log_path = report_generator.save_log_file(report_text, status)
            if log_path:
                report_text += f"\n\nLog saved to: {log_path}"

            # Show enhanced results dialog
            self.show_results_dialog(status, report_text)

            # Reload files after alignment
            self.reload_files_after_alignment(status, master_folder, use_camera_folders)

        except Exception as e:
            import traceback
            logger.error(f"Error during alignment: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")

            # Close progress dialog if it exists
            if hasattr(self, 'progress_dialog') and self.progress_dialog:
                self.progress_dialog.close()

            QMessageBox.critical(self, "Error", f"An error occurred during alignment:\n{str(e)}")

        finally:
            # Cleanup progress callback
            if hasattr(self.file_processor, 'progress_callback'):
                self.file_processor.progress_callback = None

    def _show_repair_dialog(self, corruption_summary: Dict, corruption_results: Dict) -> tuple:
        """Show repair decision dialog to user and return (repair_choice, force_strategy, selected_strategy)"""
        try:
            from .repair_dialog import RepairDecisionDialog

            # Validate corruption_summary has required keys
            required_keys = ['total_files', 'healthy_files', 'repairable_files', 'unrepairable_files',
                             'corruption_types', 'has_corruption']
            for key in required_keys:
                if key not in corruption_summary:
                    logger.warning(f"Missing key '{key}' in corruption_summary, adding default value")
                    if key == 'total_files':
                        corruption_summary[key] = len(corruption_results)
                    elif key in ['healthy_files', 'repairable_files', 'unrepairable_files']:
                        corruption_summary[key] = 0
                    elif key == 'corruption_types':
                        corruption_summary[key] = {}
                    elif key == 'has_corruption':
                        corruption_summary[key] = False

            logger.info(f"Showing repair dialog with summary: {corruption_summary}")

            dialog = RepairDecisionDialog(corruption_summary, corruption_results, self)
            dialog.exec_()

            repair_choice = dialog.get_repair_choice()
            force_strategy, selected_strategy = dialog.get_strategy_choice()

            logger.info(
                f"User repair choice: repair={repair_choice}, force={force_strategy}, strategy={selected_strategy}")
            return repair_choice, force_strategy, selected_strategy

        except Exception as e:
            logger.error(f"Error showing repair dialog: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Fallback to simple message box
            repairable_count = corruption_summary.get('repairable_files', 0)
            reply = QMessageBox.question(
                self,
                "Corrupted Files Detected",
                f"Found {repairable_count} corrupted files.\n\n"
                "Attempt to repair them before processing?\n\n"
                "• Yes: Try to repair files (backups will be created)\n"
                "• No: Process as-is (corrupted files get filesystem dates only)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            return reply == QMessageBox.Yes, False, None

    def _generate_enhanced_report(self, status, time_offset, start_time, end_time, use_camera_folders):
        """Generate enhanced report including repair information and backup paths"""

        from ..core.time_calculator import TimeCalculator
        offset_str, direction = TimeCalculator.format_offset(time_offset)

        report = []
        report.append("=== Enhanced Photo Time Alignment Report ===")
        report.append(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append(f"Time Offset Applied: {offset_str}")
        report.append("")

        # Repair section (if any repairs were attempted)
        if hasattr(status, 'repair_attempted') and status.repair_attempted > 0:
            report.append("File Repair Operations:")
            report.append(f"✓ Repair attempted: {status.repair_attempted} files")
            report.append(f"✓ Successfully repaired: {status.repair_successful} files")
            report.append(f"✗ Repair failed: {status.repair_failed} files")
            report.append("")

            # Repair details with backup paths
            if hasattr(status, 'repair_results') and status.repair_results:
                report.append("Repair Details:")
                for file_path, repair_result in status.repair_results.items():
                    filename = os.path.basename(file_path)
                    if repair_result.success:
                        report.append(f"✓ {filename}: Repaired using {repair_result.strategy_used.value}")
                        if repair_result.backup_path:
                            report.append(f"  📁 Backup: {repair_result.backup_path}")
                    else:
                        report.append(f"✗ {filename}: {repair_result.error_message}")
                        if repair_result.backup_path:
                            report.append(f"  📁 Backup preserved: {repair_result.backup_path}")
                report.append("")

            # Backup summary
            backup_paths = [rr.backup_path for rr in status.repair_results.values() if rr.backup_path]
            if backup_paths:
                report.append("Backup File Locations:")
                for backup_path in backup_paths:
                    report.append(f"📁 {backup_path}")
                report.append("")

        # Metadata updates section
        report.append("Metadata Updates:")
        report.append(f"✓ Successfully updated: {status.metadata_updated} files")
        if hasattr(status, 'repair_successful') and status.repair_successful > 0:
            report.append(f"✓ Mandatory fields added: {status.repair_successful} files")
        if status.metadata_errors:
            report.append(f"✗ Errors: {len(status.metadata_errors)} files")
        if status.metadata_skipped:
            report.append(f"⚠ Skipped: {len(status.metadata_skipped)} files")
        report.append("")

        # File moves section
        if status.files_moved > 0 or status.move_skipped or status.move_errors:
            report.append("File Moves:")
            report.append(f"✓ Successfully moved: {status.files_moved} files")
            if status.move_skipped:
                report.append(f"⚠ Skipped: {len(status.move_skipped)} files")
            if status.move_errors:
                report.append(f"✗ Errors: {len(status.move_errors)} files")
            report.append("")

        # Summary
        report.append("Summary:")
        report.append(f"- Total files processed: {status.total_files}")
        report.append(f"- Successfully processed: {status.metadata_updated}/{status.total_files} files")

        if hasattr(status, 'repair_successful') and status.repair_successful > 0:
            report.append(f"- Files repaired: {status.repair_successful} files")
            report.append(
                f"- Backup files created: {len([rr for rr in status.repair_results.values() if rr.backup_path])} files")

        if status.metadata_errors:
            report.append(f"- Metadata update errors: {len(status.metadata_errors)} files")
        if status.files_moved > 0:
            report.append(f"- Files moved to master folder: {status.files_moved} files")

        # Master folder organization
        if status.camera_folders:
            report.append("")
            folder_org = "Camera-specific subfolders" if use_camera_folders else "Root folder"
            report.append(f"Master Folder Organization: {folder_org}")
            for camera_id, folder_path in sorted(status.camera_folders.items()):
                file_count = self._count_files_in_folder(folder_path)
                report.append(f"- {folder_path}: {file_count} files")

        return "\n".join(report)

    def _count_files_in_folder(self, folder_path: str) -> int:
        """Count the number of files in a folder"""
        try:
            return len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        except:
            return 0

    def show_results_dialog(self, status, report_text):
        """Show enhanced results dialog with selectable backup paths"""
        from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox,
                                     QTabWidget, QWidget, QHBoxLayout, QListWidget,
                                     QListWidgetItem, QPushButton, QLabel, QSplitter)
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont, QColor, QBrush  # Added QColor and QBrush

        dialog = QDialog(self)
        dialog.setWindowTitle("Alignment Results")
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout()

        # Create tab widget for different views
        tab_widget = QTabWidget()

        # Tab 1: Summary Report
        summary_tab = QWidget()
        summary_layout = QVBoxLayout()

        # Summary text area
        summary_text = QTextEdit()
        summary_text.setReadOnly(True)
        summary_text.setPlainText(report_text)
        summary_text.setFontFamily("Courier New")
        summary_layout.addWidget(summary_text)

        summary_tab.setLayout(summary_layout)
        tab_widget.addTab(summary_tab, "Summary Report")

        # Tab 2: Backup Files (if any repairs were made)
        if hasattr(status, 'repair_results') and status.repair_results:
            backup_tab = QWidget()
            backup_layout = QVBoxLayout()

            # Instructions
            backup_info = QLabel(
                "Backup files created during repair process:\n"
                "• Select any path below to copy it to clipboard\n"
                "• These files contain your original, unmodified data\n"
                "• Keep these backups until you're satisfied with the repair results"
            )
            backup_info.setStyleSheet(
                "background-color: #e8f4fd; padding: 10px; border-radius: 5px; margin-bottom: 10px;")
            backup_info.setWordWrap(True)
            backup_layout.addWidget(backup_info)

            # Create splitter for backup list and details
            splitter = QSplitter(Qt.Horizontal)

            # Backup files list
            backup_list_widget = QListWidget()
            backup_list_widget.setToolTip("Click on any backup path to copy it to clipboard")

            # Populate backup list
            backup_files = []
            for file_path, repair_result in status.repair_results.items():
                if repair_result.backup_path:
                    # Create display item
                    original_name = os.path.basename(file_path)
                    backup_path = repair_result.backup_path
                    backup_name = os.path.basename(backup_path)

                    display_text = f"{original_name} → {backup_name}"

                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, backup_path)  # Store full path
                    item.setToolTip(f"Click to copy path to clipboard:\n{backup_path}")

                    # Color code by repair success - Fixed method names
                    if repair_result.success:
                        # Light green background for successful repairs
                        item.setBackground(QBrush(QColor(200, 255, 200)))
                        item.setToolTip(item.toolTip() + "\n\n✅ Repair successful")
                    else:
                        # Light yellow background for failed repairs
                        item.setBackground(QBrush(QColor(255, 255, 200)))
                        item.setToolTip(item.toolTip() + "\n\n⚠️ Repair failed - backup preserved")

                    backup_list_widget.addItem(item)
                    backup_files.append((file_path, backup_path, repair_result))

            # Details panel
            details_widget = QTextEdit()
            details_widget.setReadOnly(True)
            details_widget.setPlainText("Select a backup file to see details...")

            def on_backup_selected():
                current_item = backup_list_widget.currentItem()
                if current_item:
                    backup_path = current_item.data(Qt.UserRole)

                    # Copy to clipboard
                    clipboard = QApplication.clipboard()
                    clipboard.setText(backup_path)

                    # Show details
                    file_path = None
                    repair_result = None
                    for fp, bp, rr in backup_files:
                        if bp == backup_path:
                            file_path = fp
                            repair_result = rr
                            break

                    if repair_result:
                        details_text = f"Backup Details:\n\n"
                        details_text += f"Original File: {os.path.basename(file_path)}\n"
                        details_text += f"Original Path: {file_path}\n\n"
                        details_text += f"Backup File: {os.path.basename(backup_path)}\n"
                        details_text += f"Backup Path: {backup_path}\n\n"
                        details_text += f"Repair Strategy: {repair_result.strategy_used.value}\n"
                        details_text += f"Repair Success: {'✅ Yes' if repair_result.success else '❌ No'}\n"
                        details_text += f"Verification Passed: {'✅ Yes' if repair_result.verification_passed else '❌ No'}\n\n"

                        if not repair_result.success and repair_result.error_message:
                            details_text += f"Error Message: {repair_result.error_message}\n\n"

                        details_text += f"📋 Path copied to clipboard!"

                        details_widget.setPlainText(details_text)

            backup_list_widget.itemClicked.connect(on_backup_selected)
            backup_list_widget.itemSelectionChanged.connect(on_backup_selected)

            splitter.addWidget(backup_list_widget)
            splitter.addWidget(details_widget)
            splitter.setSizes([300, 400])  # Give more space to details

            backup_layout.addWidget(splitter)

            # Copy all paths button
            button_layout = QHBoxLayout()
            copy_all_button = QPushButton("Copy All Backup Paths")
            copy_all_button.setToolTip("Copy all backup file paths to clipboard")

            def copy_all_paths():
                all_paths = []
                for _, backup_path, _ in backup_files:
                    all_paths.append(backup_path)

                if all_paths:
                    clipboard = QApplication.clipboard()
                    clipboard.setText('\n'.join(all_paths))
                    copy_all_button.setText("✅ Copied!")
                    # Reset button text after 2 seconds
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(2000, lambda: copy_all_button.setText("Copy All Backup Paths"))

            copy_all_button.clicked.connect(copy_all_paths)
            button_layout.addWidget(copy_all_button)
            button_layout.addStretch()

            backup_layout.addLayout(button_layout)
            backup_tab.setLayout(backup_layout)
            tab_widget.addTab(backup_tab, f"Backup Files ({len(backup_files)})")

        # Tab 3: Detailed Results (if there were any issues)
        if (status.metadata_errors or status.move_errors or
                (hasattr(status, 'repair_failed') and status.repair_failed > 0)):

            details_tab = QWidget()
            details_layout = QVBoxLayout()

            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setFontFamily("Courier New")

            # Build detailed error information
            detailed_info = []

            if hasattr(status, 'repair_failed') and status.repair_failed > 0:
                detailed_info.append("=== REPAIR FAILURES ===")
                for file_path, repair_result in getattr(status, 'repair_results', {}).items():
                    if not repair_result.success:
                        detailed_info.append(f"File: {os.path.basename(file_path)}")
                        detailed_info.append(f"  Strategy Attempted: {repair_result.strategy_used.value}")
                        detailed_info.append(f"  Error: {repair_result.error_message}")
                        if repair_result.backup_path:
                            detailed_info.append(f"  Backup: {repair_result.backup_path}")
                        detailed_info.append("")

            if status.metadata_errors:
                detailed_info.append("=== METADATA UPDATE ERRORS ===")
                for file_path, error_msg in status.metadata_errors:
                    detailed_info.append(f"File: {os.path.basename(file_path)}")
                    detailed_info.append(f"  Error: {error_msg}")
                    detailed_info.append("")

            if status.move_errors:
                detailed_info.append("=== FILE MOVE ERRORS ===")
                for file_path, error_msg in status.move_errors:
                    detailed_info.append(f"File: {os.path.basename(file_path)}")
                    detailed_info.append(f"  Error: {error_msg}")
                    detailed_info.append("")

            details_text.setPlainText("\n".join(detailed_info))
            details_layout.addWidget(details_text)

            details_tab.setLayout(details_layout)
            tab_widget.addTab(details_tab, "Detailed Errors")

        layout.addWidget(tab_widget)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec_()

    def reload_files_after_alignment(self, status, master_folder, use_camera_folders):
        """Reload files after alignment to show updated metadata"""
        logger.info("Reloading files after alignment...")

        # Remember the original file paths
        ref_path = self.reference_file
        target_path = self.target_file

        # If files were moved, update paths to new locations
        if self.move_files_check.isChecked() and master_folder:
            # Update reference file path if it was moved
            if ref_path:
                ref_filename = os.path.basename(ref_path)
                new_ref_path = None

                if use_camera_folders:
                    # Check camera folders for the file
                    for folder_name, folder_path in status.camera_folders.items():
                        potential_path = os.path.join(folder_path, ref_filename)
                        if os.path.exists(potential_path):
                            new_ref_path = potential_path
                            logger.info(f"Found reference file at: {new_ref_path}")
                            break
                else:
                    # Check in master folder root
                    potential_path = os.path.join(master_folder, ref_filename)
                    if os.path.exists(potential_path):
                        new_ref_path = potential_path
                        logger.info(f"Found reference file at: {new_ref_path}")

                if new_ref_path:
                    ref_path = new_ref_path

            # Update target file path if it was moved
            if target_path:
                target_filename = os.path.basename(target_path)
                new_target_path = None

                if use_camera_folders:
                    # Check camera folders for the file
                    for folder_name, folder_path in status.camera_folders.items():
                        potential_path = os.path.join(folder_path, target_filename)
                        if os.path.exists(potential_path):
                            new_target_path = potential_path
                            logger.info(f"Found target file at: {new_target_path}")
                            break
                else:
                    # Check in master folder root
                    potential_path = os.path.join(master_folder, target_filename)
                    if os.path.exists(potential_path):
                        new_target_path = potential_path
                        logger.info(f"Found target file at: {new_target_path}")

                if new_target_path:
                    target_path = new_target_path

        # Clear UI
        self.ref_files_list.clear()
        self.target_files_list.clear()
        self.reference_group_files = []
        self.target_group_files = []

        # Reload files if they exist
        if ref_path and os.path.exists(ref_path):
            logger.info(f"Reloading reference file: {ref_path}")
            self.load_reference_photo(ref_path)
        else:
            logger.warning(f"Cannot reload reference file, not found: {ref_path}")
            self.reference_info.setText("No media loaded (file moved/deleted)")

        if target_path and os.path.exists(target_path):
            logger.info(f"Reloading target file: {target_path}")
            self.load_target_photo(target_path)
        else:
            logger.warning(f"Cannot reload target file, not found: {target_path}")
            self.target_info.setText("No media loaded (file moved/deleted)")

    def create_manual_offset_section(self, parent_layout):
        """Create the manual time offset input section"""
        # Container for manual offset
        manual_container = QWidget()
        manual_layout = QHBoxLayout(manual_container)
        manual_layout.setContentsMargins(10, 5, 10, 5)

        # Label
        manual_layout.addWidget(QLabel("Manual Time Offset:"))

        # Years input
        manual_layout.addWidget(QLabel("Years:"))
        self.manual_years = QSpinBox()
        self.manual_years.setRange(0, 100)
        self.manual_years.setMaximumWidth(60)
        self.manual_years.valueChanged.connect(self.update_apply_button_state)
        manual_layout.addWidget(self.manual_years)

        # Days input
        manual_layout.addWidget(QLabel("Days:"))
        self.manual_days = QSpinBox()
        self.manual_days.setRange(0, 365)
        self.manual_days.setMaximumWidth(60)
        self.manual_days.valueChanged.connect(self.update_apply_button_state)
        manual_layout.addWidget(self.manual_days)

        # Hours input
        manual_layout.addWidget(QLabel("Hours:"))
        self.manual_hours = QSpinBox()
        self.manual_hours.setRange(0, 23)
        self.manual_hours.setMaximumWidth(50)
        self.manual_hours.valueChanged.connect(self.update_apply_button_state)
        manual_layout.addWidget(self.manual_hours)

        # Minutes input
        manual_layout.addWidget(QLabel("Minutes:"))
        self.manual_minutes = QSpinBox()
        self.manual_minutes.setRange(0, 59)
        self.manual_minutes.setMaximumWidth(50)
        self.manual_minutes.valueChanged.connect(self.update_apply_button_state)
        manual_layout.addWidget(self.manual_minutes)

        # Seconds input
        manual_layout.addWidget(QLabel("Seconds:"))
        self.manual_seconds = QSpinBox()
        self.manual_seconds.setRange(0, 59)
        self.manual_seconds.setMaximumWidth(50)
        self.manual_seconds.valueChanged.connect(self.update_apply_button_state)
        manual_layout.addWidget(self.manual_seconds)

        # Direction radio buttons
        manual_layout.addWidget(QLabel("("))
        self.manual_add_radio = QRadioButton("Add")
        self.manual_add_radio.setChecked(True)
        manual_layout.addWidget(self.manual_add_radio)

        manual_layout.addWidget(QLabel("•"))

        self.manual_subtract_radio = QRadioButton("Subtract")
        manual_layout.addWidget(self.manual_subtract_radio)

        manual_layout.addWidget(QLabel(") time"))

        # Group the radio buttons
        self.manual_direction_group = QButtonGroup()
        self.manual_direction_group.addButton(self.manual_add_radio)
        self.manual_direction_group.addButton(self.manual_subtract_radio)

        manual_layout.addStretch()

        # Note label
        self.manual_note_label = QLabel("Note: Used when target photo is missing")
        self.manual_note_label.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        manual_layout.addWidget(self.manual_note_label)

        parent_layout.addWidget(manual_container)

        # Store reference to manual container for enabling/disabling
        self.manual_offset_container = manual_container

    def get_manual_offset_timedelta(self):
        """Get the manual offset as a timedelta object"""
        years = self.manual_years.value()
        days = self.manual_days.value()
        hours = self.manual_hours.value()
        minutes = self.manual_minutes.value()
        seconds = self.manual_seconds.value()

        # Convert years to days (approximate)
        total_days = days + (years * 365)

        offset = timedelta(
            days=total_days,
            hours=hours,
            minutes=minutes,
            seconds=seconds
        )

        # Apply direction
        if self.manual_subtract_radio.isChecked():
            offset = -offset

        return offset

    def is_manual_offset_set(self):
        """Check if any manual offset values are set"""
        return (self.manual_years.value() > 0 or
                self.manual_days.value() > 0 or
                self.manual_hours.value() > 0 or
                self.manual_minutes.value() > 0 or
                self.manual_seconds.value() > 0)

    def update_manual_offset_state(self):
        """Update the state of manual offset controls based on loaded photos"""
        has_target = self.target_file is not None

        # Disable manual controls when target is loaded
        if hasattr(self, 'manual_offset_container'):
            self.manual_offset_container.setEnabled(not has_target)

        # Update note text
        if has_target:
            self.manual_note_label.setText("Note: Disabled (using calculated offset)")
            self.manual_note_label.setStyleSheet("color: #999; font-style: italic; font-size: 11px;")
        else:
            self.manual_note_label.setText("Note: Used when target photo is missing")
            self.manual_note_label.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")

    def update_apply_button_state(self):
        """Update apply button state based on current conditions"""
        can_apply = False

        if not self.single_file_mode and self.reference_file:
            if self.target_file:
                # Both photos loaded - use calculated offset
                can_apply = self.time_offset is not None
            else:
                # Only reference loaded - can apply with or without manual offset
                can_apply = True

        self.apply_button.setEnabled(can_apply)

    def load_config(self):
        """Load saved configuration"""
        geometry = self.config_manager.get('window_geometry', {})
        if geometry:
            self.setGeometry(geometry.get('x', 100), geometry.get('y', 100),
                             geometry.get('width', 900), geometry.get('height', 700))

        last_master = self.config_manager.get('last_master_folder', '')
        self.master_folder_input.setText(last_master)

        move_files = self.config_manager.get('move_to_master', True)
        self.move_files_check.setChecked(move_files)

        # Load single file mode preference
        single_mode = self.config_manager.get('single_file_mode', False)
        self.single_file_mode_check.setChecked(single_mode)

        # Load corruption detection preference (default to True)
        corruption_detection = self.config_manager.get('corruption_detection_enabled', True)
        self.corruption_detection_check.setChecked(corruption_detection)

    def clear_loaded_files(self):
        """Clear both reference and target files and reset the UI"""
        logger.info("Clearing loaded files")

        # Stop any running file scanning threads
        self.stop_file_scanning()

        # Clear file references
        self.reference_file = None
        self.target_file = None
        self.reference_metadata = {}
        self.target_metadata = {}
        self.time_offset = None

        # Clear file lists
        self.clear_file_lists()

        # Reset drop zones
        self.reference_drop.setText("Drop Reference Photo/Video")
        self.reference_drop.file_path = None
        self.target_drop.setText("Drop Photo/Video to Align")
        self.target_drop.file_path = None

        # Reset info labels
        self.reference_info.setText("No media loaded")
        self.target_info.setText("No media loaded")

        # Clear time field radio buttons
        self.clear_time_field_radios()

        # Reset pattern labels
        self.ref_pattern_label.setText("Pattern: Not detected")
        self.target_pattern_label.setText("Pattern: Not detected")

        # Reset offset display
        self.offset_label.setText("Time Offset: Not calculated")

        # Update apply button state
        self.update_apply_button_state()

        # Update investigate button state
        self.update_investigate_button_state()

        # Update status
        self.statusBar().showMessage("Files cleared - Ready to load new files")

        logger.info("Files cleared successfully")

    def clear_time_field_radios(self):
        """Clear time field radio buttons for both reference and target"""
        # Clear reference time radios
        for radio in self.ref_time_radios.values():
            container = radio.parent()
            self.ref_time_container.removeWidget(container)
            container.deleteLater()
        self.ref_time_radios.clear()

        # Clear target time radios
        for radio in self.target_time_radios.values():
            container = radio.parent()
            self.target_time_container.removeWidget(container)
            container.deleteLater()
        self.target_time_radios.clear()

    def closeEvent(self, event):
        """Save configuration on close"""
        # Terminate any running threads
        if self.ref_scanner_thread and self.ref_scanner_thread.isRunning():
            self.ref_scanner_thread.stop()
            self.ref_scanner_thread.wait()

        if self.target_scanner_thread and self.target_scanner_thread.isRunning():
            self.target_scanner_thread.stop()
            self.target_scanner_thread.wait()

        # Save configuration
        self.config_manager.set('window_geometry', {
            'x': self.geometry().x(),
            'y': self.geometry().y(),
            'width': self.geometry().width(),
            'height': self.geometry().height()
        })
        self.config_manager.set('last_master_folder', self.master_folder_input.text())
        self.config_manager.set('move_to_master', self.move_files_check.isChecked())
        self.config_manager.set('single_file_mode', self.single_file_mode_check.isChecked())
        # Save corruption detection preference
        self.config_manager.set('corruption_detection_enabled', self.corruption_detection_check.isChecked())
        self.config_manager.save()
        event.accept()