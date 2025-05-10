from PyQt5.QtCore import QThread, pyqtSignal
from typing import List


class FileScannerThread(QThread):
    """Worker thread for file scanning"""

    files_found = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, file_processor, reference_file: str,
                 use_camera: bool, use_extension: bool):
        super().__init__()
        self.file_processor = file_processor
        self.reference_file = reference_file
        self.use_camera = use_camera
        self.use_extension = use_extension

    def run(self):
        """Run the file scanning in a separate thread"""
        try:
            # Call the batch processing method directly
            matching_files = self.file_processor.find_matching_files_batch(
                self.reference_file, self.use_camera, self.use_extension
            )
            self.files_found.emit(matching_files)
        except Exception as e:
            self.error.emit(str(e))