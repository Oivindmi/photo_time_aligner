from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QLineEdit, QListWidget,
                             QRadioButton, QCheckBox, QFileDialog, QButtonGroup,
                             QGroupBox, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QPixmap
import os
from datetime import datetime
from typing import List
from ..core import ExifHandler, ConfigManager, FileProcessor, TimeCalculator
from ..utils import FileProcessingError
from .file_scanner_thread import FileScannerThread
from ..core.supported_formats import is_supported_format
from datetime import datetime
from .progress_dialog import ProgressDialog

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

        # Thread references
        self.ref_scanner_thread = None
        self.target_scanner_thread = None

        self.init_ui()
        self.load_config()

    def init_ui(self):
        self.setWindowTitle("Photo & Video Time Aligner")
        self.setMinimumSize(900, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create top section with drop zones
        drop_section = QHBoxLayout()

        # Reference photo section
        reference_section = QVBoxLayout()
        reference_section.addWidget(QLabel("Reference Media"))  # Updated label
        self.reference_drop = PhotoDropZone("Drop Reference Photo/Video", parent=self)  # Pass self as parent
        self.reference_drop.file_dropped.connect(self.load_reference_photo)
        reference_section.addWidget(self.reference_drop)
        self.reference_info = QLabel("No media loaded")
        reference_section.addWidget(self.reference_info)

        # Target photo section
        target_section = QVBoxLayout()
        target_section.addWidget(QLabel("Media to Align"))  # Updated label
        self.target_drop = PhotoDropZone("Drop Photo/Video to Align", parent=self)  # Pass self as parent
        self.target_drop.file_dropped.connect(self.load_target_photo)
        target_section.addWidget(self.target_drop)
        self.target_info = QLabel("No media loaded")
        target_section.addWidget(self.target_info)

        drop_section.addLayout(reference_section)
        drop_section.addLayout(target_section)
        main_layout.addLayout(drop_section)

        # Create middle section with group rules and time fields
        middle_section = QHBoxLayout()

        # Reference group settings
        ref_group = QGroupBox("Reference Group Settings")
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

        ref_group.setLayout(ref_layout)

        # Target group settings
        target_group = QGroupBox("Target Group Settings")
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

        target_group.setLayout(target_layout)

        middle_section.addWidget(ref_group)
        middle_section.addWidget(target_group)
        main_layout.addLayout(middle_section)

        # File lists section
        file_lists_section = QHBoxLayout()

        # Reference files list
        ref_files_group = QGroupBox("Reference Files")
        ref_files_layout = QVBoxLayout()
        self.ref_files_list = QListWidget()
        ref_files_layout.addWidget(self.ref_files_list)
        ref_files_group.setLayout(ref_files_layout)

        # Target files list
        target_files_group = QGroupBox("Target Files")
        target_files_layout = QVBoxLayout()
        self.target_files_list = QListWidget()
        target_files_layout.addWidget(self.target_files_list)
        target_files_group.setLayout(target_files_layout)

        file_lists_section.addWidget(ref_files_group)
        file_lists_section.addWidget(target_files_group)
        main_layout.addLayout(file_lists_section)

        # Time offset display
        offset_layout = QHBoxLayout()
        self.offset_label = QLabel("Time Offset: Not calculated")
        self.offset_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        offset_layout.addWidget(self.offset_label)
        main_layout.addLayout(offset_layout)

        # Master folder section
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

        # Add folder organization options
        folder_org_group = QGroupBox("Master Folder Organization")
        folder_org_layout = QVBoxLayout()

        self.folder_org_group = QButtonGroup()
        self.org_root_radio = QRadioButton("Move to root folder")
        self.org_root_radio.setChecked(True)  # Default option
        self.org_camera_radio = QRadioButton("Create camera-specific subfolders")

        self.folder_org_group.addButton(self.org_root_radio)
        self.folder_org_group.addButton(self.org_camera_radio)

        folder_org_layout.addWidget(self.org_root_radio)
        folder_org_layout.addWidget(self.org_camera_radio)

        folder_org_group.setLayout(folder_org_layout)

        # Only show organization options when move files is checked
        folder_org_group.setEnabled(self.move_files_check.isChecked())
        self.move_files_check.stateChanged.connect(
            lambda state: folder_org_group.setEnabled(state == Qt.Checked)
        )

        main_layout.addWidget(folder_org_group)

        # Apply button
        self.apply_button = QPushButton("Apply Alignment")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_alignment)
        self.apply_button.setStyleSheet("font-size: 16px; padding: 10px;")
        main_layout.addWidget(self.apply_button)

        # Status bar
        self.statusBar().showMessage("Ready")

    def load_reference_photo(self, file_path: str):
        """Load reference photo and scan for matching files"""
        try:
            self.reference_file = file_path
            self.reference_metadata = self.exif_handler.read_metadata(file_path)
            camera_info = self.exif_handler.get_camera_info(file_path)

            # Update UI
            camera_str = f"{camera_info['make']} {camera_info['model']}".strip() or "Unknown Camera"
            self.reference_info.setText(camera_str)

            # Load time fields
            self.load_time_fields_for_reference()

            # Find matching files
            self.update_reference_files()

            # Calculate offset if both files are loaded
            self.calculate_time_offset()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading reference photo: {str(e)}")

    def load_target_photo(self, file_path: str):
        """Load target photo and scan for matching files"""
        try:
            self.target_file = file_path
            self.target_metadata = self.exif_handler.read_metadata(file_path)
            camera_info = self.exif_handler.get_camera_info(file_path)

            # Update UI
            camera_str = f"{camera_info['make']} {camera_info['model']}".strip() or "Unknown Camera"
            self.target_info.setText(camera_str)

            # Load time fields
            self.load_time_fields_for_target()

            # Find matching files
            self.update_target_files()

            # Calculate offset if both files are loaded
            self.calculate_time_offset()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading target photo: {str(e)}")

    def load_time_fields_for_reference(self):
        """Load available time fields for reference photo"""
        # Clear existing radio buttons
        for radio in self.ref_time_radios.values():
            # Get the parent widget (container) and remove it
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
            if parsed_value:  # Only show fields with values
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
            # Get the parent widget (container) and remove it
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
            if parsed_value:  # Only show fields with values
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
        """Update list of files matching reference photo criteria"""
        if not self.reference_file:
            return

        # Cancel previous scan if running
        if self.ref_scanner_thread and self.ref_scanner_thread.isRunning():
            self.ref_scanner_thread.terminate()
            self.ref_scanner_thread.wait()

        # Update UI to show scanning
        self.ref_file_count.setText("Scanning...")
        self.ref_files_list.clear()

        # Reset pattern label if pattern matching is disabled
        if not self.ref_pattern_check.isChecked():
            self.ref_pattern_label.setText("Pattern: Not detected")

        # Create and start scanner thread
        self.ref_scanner_thread = FileScannerThread(
            self.file_processor,
            self.reference_file,
            self.ref_camera_check.isChecked(),
            self.ref_extension_check.isChecked(),
            self.ref_pattern_check.isChecked()  # NEW: Pass pattern matching flag
        )

        self.ref_scanner_thread.files_found.connect(self._on_reference_files_found)
        self.ref_scanner_thread.error.connect(self._on_reference_scan_error)
        self.ref_scanner_thread.status_update.connect(
            lambda msg: self.statusBar().showMessage(msg)
        )
        self.ref_scanner_thread.pattern_detected.connect(  # NEW: Connect pattern detection signal
            lambda pattern: self.ref_pattern_label.setText(f"Pattern: {pattern}")
        )
        self.ref_scanner_thread.start()

    def update_target_files(self):
        """Update list of files matching target photo criteria"""
        if not self.target_file:
            return

        # Cancel previous scan if running
        if self.target_scanner_thread and self.target_scanner_thread.isRunning():
            self.target_scanner_thread.terminate()
            self.target_scanner_thread.wait()

        # Update UI to show scanning
        self.target_file_count.setText("Scanning...")
        self.target_files_list.clear()

        # Reset pattern label if pattern matching is disabled
        if not self.target_pattern_check.isChecked():
            self.target_pattern_label.setText("Pattern: Not detected")

        # Create and start scanner thread
        self.target_scanner_thread = FileScannerThread(
            self.file_processor,
            self.target_file,
            self.target_camera_check.isChecked(),
            self.target_extension_check.isChecked(),
            self.target_pattern_check.isChecked()  # NEW: Pass pattern matching flag
        )

        self.target_scanner_thread.files_found.connect(self._on_target_files_found)
        self.target_scanner_thread.error.connect(self._on_target_scan_error)
        self.target_scanner_thread.status_update.connect(
            lambda msg: self.statusBar().showMessage(msg)
        )
        self.target_scanner_thread.pattern_detected.connect(  # NEW: Connect pattern detection signal
            lambda pattern: self.target_pattern_label.setText(f"Pattern: {pattern}")
        )
        self.target_scanner_thread.start()

    def _on_reference_files_found(self, files: List[str]):
        """Handle files found by scanner thread"""
        self.reference_group_files = files
        self.ref_files_list.clear()
        for file_path in files:
            self.ref_files_list.addItem(os.path.basename(file_path))
        self.ref_file_count.setText(f"Matching files: {len(files)}")

    def _on_reference_scan_error(self, error_msg: str):
        """Handle scanning errors"""
        self.statusBar().showMessage(f"Error scanning reference files: {error_msg}")
        self.ref_file_count.setText("Error scanning files")

    def _on_target_files_found(self, files: List[str]):
        """Handle files found by scanner thread"""
        self.target_group_files = files
        self.target_files_list.clear()
        for file_path in files:
            self.target_files_list.addItem(os.path.basename(file_path))
        self.target_file_count.setText(f"Matching files: {len(files)}")

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

                # Debug information
                debug_info = (
                    f"Reference: {ref_field} = {ref_datetime}, "
                    f"Target: {target_field} = {target_datetime}, "
                    f"Offset: {self.time_offset} ({self.time_offset.total_seconds()} seconds)"
                )
                print(debug_info)  # Print to console
                self.statusBar().showMessage(debug_info)

                # Format offset display
                offset_str, direction = TimeCalculator.format_offset(self.time_offset)

                display_text = f"Time Offset: {offset_str}\n"
                display_text += f"Target photo is {direction} reference photo"

                self.offset_label.setText(display_text)
                self.apply_button.setEnabled(True)
        except Exception as e:
            error_msg = f"Error calculating offset: {str(e)}"
            print(error_msg)  # Print to console
            self.statusBar().showMessage(error_msg)

    def browse_master_folder(self):
        """Browse for master folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Master Folder")
        if folder:
            self.master_folder_input.setText(folder)

    def apply_alignment(self):
        """Apply time alignment to all matching files"""
        logger.info("=== Starting apply_alignment method ===")

        try:
            # Validate inputs
            logger.info("Validating inputs...")

            if not self.time_offset:
                logger.warning("No time offset calculated")
                QMessageBox.warning(self, "Warning", "No time offset calculated.")
                return

            logger.info(f"Time offset: {self.time_offset}")

            # Get selected time fields
            ref_field = None
            target_field = None

            logger.info("Getting selected time fields...")

            for radio in self.ref_time_radios.values():
                if radio.isChecked():
                    ref_field = radio.property("field_name")
                    logger.info(f"Reference field selected: {ref_field}")
                    break

            for radio in self.target_time_radios.values():
                if radio.isChecked():
                    target_field = radio.property("field_name")
                    logger.info(f"Target field selected: {target_field}")
                    break

            if not (ref_field and target_field):
                logger.warning("Time fields not selected for both groups")
                QMessageBox.warning(self, "Warning", "Please select time fields for both groups.")
                return

            # Check if we have files to process
            logger.info(
                f"Reference files count: {len(self.reference_group_files) if self.reference_group_files else 0}")
            logger.info(f"Target files count: {len(self.target_group_files) if self.target_group_files else 0}")

            if not (self.reference_group_files or self.target_group_files):
                logger.warning("No files to process")
                QMessageBox.warning(self, "Warning", "No files to process.")
                return

            # Get master folder settings
            logger.info("Getting master folder settings...")
            master_folder = self.master_folder_input.text() if self.move_files_check.isChecked() else None
            use_camera_folders = self.org_camera_radio.isChecked() if self.move_files_check.isChecked() else False

            logger.info(f"Master folder: {master_folder}")
            logger.info(f"Move files: {self.move_files_check.isChecked()}")
            logger.info(f"Use camera folders: {use_camera_folders}")

            if self.move_files_check.isChecked() and not master_folder:
                logger.warning("Master folder not specified")
                QMessageBox.warning(self, "Warning", "Please specify a master folder.")
                return

            # Show progress dialog
            logger.info("Creating progress dialog...")
            progress_dialog = ProgressDialog(self)
            logger.info("Progress dialog created successfully")

            logger.info("Showing progress dialog...")
            progress_dialog.show()
            logger.info("Progress dialog shown")

            logger.info("Updating progress dialog status...")
            progress_dialog.update_status("Processing files...")
            logger.info("Progress dialog status updated")

            # Record start time
            start_time = datetime.now()
            logger.info(f"Start time: {start_time}")

            # Create processor and run
            logger.info("Importing AlignmentProcessor and AlignmentReport...")
            try:
                from ..core import AlignmentProcessor, AlignmentReport
                logger.info("Import successful")
            except Exception as e:
                logger.error(f"Import error: {str(e)}")
                raise

            logger.info("Creating AlignmentProcessor...")
            processor = AlignmentProcessor(self.exif_handler, self.file_processor)
            logger.info("AlignmentProcessor created successfully")

            # Process files
            logger.info("Starting file processing...")
            logger.info(f"Reference files: {[os.path.basename(f) for f in self.reference_group_files]}")
            logger.info(f"Target files: {[os.path.basename(f) for f in self.target_group_files]}")

            status = processor.process_files(
                reference_files=self.reference_group_files,
                target_files=self.target_group_files,
                reference_field=ref_field,
                target_field=target_field,
                time_offset=self.time_offset,
                master_folder=master_folder,
                move_files=self.move_files_check.isChecked(),
                use_camera_folders=use_camera_folders
            )

            logger.info("File processing completed")

            # Record end time
            end_time = datetime.now()
            logger.info(f"End time: {end_time}")

            # Hide progress dialog
            logger.info("Closing progress dialog...")
            progress_dialog.close()
            logger.info("Progress dialog closed")

            # Generate report
            logger.info("Creating AlignmentReport...")
            report_generator = AlignmentReport(self.config_manager)
            logger.info("AlignmentReport created")

            logger.info("Generating console report...")
            report_text = report_generator.generate_console_report(
                status=status,
                time_offset=self.time_offset,
                start_time=start_time,
                end_time=end_time,
                master_folder_org="Camera-specific subfolders" if use_camera_folders else "Root folder"
            )
            logger.info("Console report generated")

            # Print to console
            print("\n" + report_text)

            # Save log file
            logger.info("Saving log file...")
            log_path = report_generator.save_log_file(report_text, status)
            if log_path:
                logger.info(f"Log file saved to: {log_path}")
                report_text += f"\n\nLog saved to: {log_path}"
            else:
                logger.warning("Failed to save log file")

            # Show summary dialog
            logger.info("Showing results dialog...")
            self.show_results_dialog(status, report_text)
            logger.info("Results dialog shown")

            # Update UI if files were moved
            if status.files_moved > 0 and self.reference_file:
                logger.info("Updating UI for moved files...")
                # Find the new path of the reference file
                ref_filename = os.path.basename(self.reference_file)
                new_ref_path = None

                # Search in the camera folders or root
                if use_camera_folders:
                    for folder_path in status.camera_folders.values():
                        potential_path = os.path.join(folder_path, ref_filename)
                        if os.path.exists(potential_path):
                            new_ref_path = potential_path
                            logger.info(f"Found reference file at: {new_ref_path}")
                            break
                else:
                    potential_path = os.path.join(master_folder, ref_filename)
                    if os.path.exists(potential_path):
                        new_ref_path = potential_path
                        logger.info(f"Found reference file at: {new_ref_path}")

                # Reload reference file from new location
                if new_ref_path:
                    logger.info("Reloading reference file from new location...")
                    self.load_reference_photo(new_ref_path)
                    logger.info("Reference file reloaded")

            logger.info("=== apply_alignment method completed successfully ===")

        except Exception as e:
            import traceback
            logger.error(f"Error during alignment: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"An error occurred during alignment:\n{str(e)}")

    def show_results_dialog(self, status, report_text):
        """Show results dialog with summary"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("Alignment Results")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        # Text area with report
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(report_text)
        text_edit.setFontFamily("Courier New")
        layout.addWidget(text_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.setLayout(layout)
        dialog.exec_()

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

    def closeEvent(self, event):
        """Save configuration on close"""
        # Terminate any running threads
        if self.ref_scanner_thread and self.ref_scanner_thread.isRunning():
            self.ref_scanner_thread.terminate()
            self.ref_scanner_thread.wait()

        if self.target_scanner_thread and self.target_scanner_thread.isRunning():
            self.target_scanner_thread.terminate()
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
        self.config_manager.save()
        event.accept()