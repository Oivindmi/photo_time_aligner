from PyQt5.QtCore import QThread, pyqtSignal
from typing import List
import logging
import os

logger = logging.getLogger(__name__)


class FileScannerThread(QThread):
    """Worker thread for file scanning"""

    files_found = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    pattern_detected = pyqtSignal(str)  # New signal for pattern display

    def __init__(self, file_processor, reference_file: str,
                 use_camera: bool, use_extension: bool, use_pattern: bool):
        super().__init__()
        self.file_processor = file_processor
        self.reference_file = reference_file
        self.use_camera = use_camera
        self.use_extension = use_extension
        self.use_pattern = use_pattern

    def run(self):
        """Run the file scanning in a separate thread"""
        try:
            # If pattern matching is enabled, detect and emit the pattern
            if self.use_pattern:
                from ..core import FilenamePatternMatcher
                pattern = FilenamePatternMatcher.extract_pattern(
                    os.path.basename(self.reference_file)
                )
                self.pattern_detected.emit(pattern['display'])

            # Call the batch processing method
            matching_files = self.file_processor.find_matching_files_batch(
                self.reference_file, self.use_camera, self.use_extension, self.use_pattern
            )
            self.files_found.emit(matching_files)
        except Exception as e:
            logger.error(f"Error in file scanner thread: {str(e)}")
            self.error.emit(str(e))