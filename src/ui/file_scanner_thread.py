from PyQt5.QtCore import QThread, pyqtSignal
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


class FileScannerThread(QThread):
    """Worker thread for async file scanning"""

    # Signals
    file_found = pyqtSignal(str)
    scanning_complete = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    pattern_detected = pyqtSignal(str)

    def __init__(self, file_processor, reference_file: str,
                 use_camera: bool, use_extension: bool, use_pattern: bool):
        super().__init__()
        self.file_processor = file_processor
        self.reference_file = reference_file
        self.use_camera = use_camera
        self.use_extension = use_extension
        self.use_pattern = use_pattern
        self._stop_requested = False

    def run(self):
        """Run the file scanning in a separate thread"""
        try:
            # Detect pattern if needed
            if self.use_pattern:
                from ..core import FilenamePatternMatcher
                pattern = FilenamePatternMatcher.extract_pattern(
                    os.path.basename(self.reference_file)
                )
                self.pattern_detected.emit(pattern['display'])

            # Use async scanning
            self.file_processor.find_matching_files_incremental(
                self.reference_file,
                self.use_camera,
                self.use_extension,
                self.use_pattern,
                self.file_found
            )

            self.scanning_complete.emit()

        except Exception as e:
            logger.error(f"Error in file scanner thread: {str(e)}")
            self.error.emit(str(e))

    def stop(self):
        """Request thread to stop"""
        self._stop_requested = True