from PyQt5.QtCore import QThread, pyqtSignal
from typing import List
import logging
import os

logger = logging.getLogger(__name__)


class FileScannerThread(QThread):
    """Worker thread for file scanning"""

    # Original signals (kept for backward compatibility)
    files_found = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    pattern_detected = pyqtSignal(str)

    # New signals for incremental file discovery
    file_found = pyqtSignal(str)  # Emits one file at a time
    scanning_complete = pyqtSignal()  # Signals when scanning is complete

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

            # Use the new incremental method instead of batch method
            # This emits files one by one instead of returning a large list
            self.file_processor.find_matching_files_incremental(
                self.reference_file,
                self.use_camera,
                self.use_extension,
                self.use_pattern,
                self.file_found  # Pass the signal to emit files
            )

            # Signal completion when all files have been processed
            self.scanning_complete.emit()

        except Exception as e:
            logger.error(f"Error in file scanner thread: {str(e)}")
            self.error.emit(str(e))