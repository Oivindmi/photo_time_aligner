import os
import logging
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessingStatus:
    """Track the status of the alignment processing operation"""

    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.metadata_updated = 0
        self.metadata_errors = []
        self.metadata_skipped = []
        self.files_moved = 0
        self.move_skipped = []
        self.move_errors = []
        self.camera_folders = {}


class AlignmentProcessor:
    """Handles the batch alignment process for photos and videos"""

    def __init__(self, exif_handler, file_processor):
        logger.info("AlignmentProcessor.__init__ called")
        self.exif_handler = exif_handler
        self.file_processor = file_processor
        self.status = ProcessingStatus()
        logger.info("AlignmentProcessor initialization completed")

    def process_files(self,
                      reference_files: List[str],
                      target_files: List[str],
                      reference_field: str,
                      target_field: str,
                      time_offset: timedelta,
                      master_folder: Optional[str] = None,
                      move_files: bool = False,
                      use_camera_folders: bool = False) -> ProcessingStatus:
        """
        Process reference and target files with appropriate time adjustments.
        """
        logger.info("AlignmentProcessor.process_files called")
        logger.info(f"Parameters: ref_files={len(reference_files)}, target_files={len(target_files)}")
        logger.info(f"Fields: ref_field={reference_field}, target_field={target_field}")
        logger.info(f"Offset: {time_offset}, master_folder={master_folder}")
        logger.info(f"Move files: {move_files}, use camera folders: {use_camera_folders}")

        self.status = ProcessingStatus()
        all_files = reference_files + target_files
        self.status.total_files = len(all_files)

        # Phase 1: Update reference files (synchronize fields, no offset)
        logger.info("=== Updating reference files (synchronizing fields only, no offset) ===")
        reference_results = self.file_processor.apply_time_offset(
            reference_files,
            reference_field,
            0  # No offset for reference files
        )

        # Update status based on reference results
        for file_path, success in reference_results.items():
            self.status.processed_files += 1
            if success:
                self.status.metadata_updated += 1
            else:
                self.status.metadata_errors.append(
                    (file_path, "Failed to update metadata")
                )

        # Phase 2: Update target files (apply NEGATIVE offset to adjust them)
        offset_seconds = time_offset.total_seconds()
        logger.info(f"=== Updating target files (applying offset: {-offset_seconds} seconds) ===")
        target_results = self.file_processor.apply_time_offset(
            target_files,
            target_field,
            -offset_seconds  # NEGATIVE offset to make target match reference
        )

        # Update status based on target results
        for file_path, success in target_results.items():
            self.status.processed_files += 1
            if success:
                self.status.metadata_updated += 1
            else:
                self.status.metadata_errors.append(
                    (file_path, "Failed to update metadata")
                )

        # Phase 3: Move files if requested
        if move_files and master_folder:
            logger.info("Starting file move operations...")
            self._move_files_batch(all_files, master_folder, use_camera_folders)

        logger.info("AlignmentProcessor.process_files completed")
        return self.status

    def _move_files_batch(self, files: List[str], master_folder: str, use_camera_folders: bool):
        """Move files to master folder with optional camera-specific organization"""
        # Ensure master folder exists
        os.makedirs(master_folder, exist_ok=True)

        # Counter for unknown camera folders
        unknown_camera_counters = {}

        for file_path in files:
            try:
                # Skip files that had metadata errors
                if any(file_path == error[0] for error in self.status.metadata_errors):
                    continue

                # Determine destination folder
                if use_camera_folders:
                    dest_folder = self._get_camera_folder(file_path, master_folder, unknown_camera_counters)
                else:
                    dest_folder = master_folder

                # Create destination folder if needed
                os.makedirs(dest_folder, exist_ok=True)

                # Check if file already exists
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(dest_folder, file_name)

                if os.path.exists(dest_path):
                    self.status.move_skipped.append(
                        (file_path, "File already exists in destination")
                    )
                    continue

                # Move the file
                shutil.move(file_path, dest_path)
                self.status.files_moved += 1
                logger.info(f"Moved {file_name} to {dest_folder}")

            except Exception as e:
                self.status.move_errors.append(
                    (file_path, f"Error: {str(e)}")
                )
                logger.error(f"Error moving {file_path}: {str(e)}")

    def _get_camera_folder(self, file_path: str, master_folder: str,
                           unknown_counters: Dict[str, int]) -> str:
        """Get the appropriate camera folder for a file"""
        try:
            camera_info = self.exif_handler.get_camera_info(file_path)
            make = camera_info.get('make', '').strip()
            model = camera_info.get('model', '').strip()

            if make and model:
                # Use camera make and model
                camera_id = f"{make}_{model}".replace(' ', '_').replace('/', '_')
            else:
                # No camera info - use Unknown_Camera_EXT_N format
                ext = os.path.splitext(file_path)[1].lower().replace('.', '').upper()
                counter_key = f"Unknown_Camera_{ext}"

                if counter_key not in unknown_counters:
                    unknown_counters[counter_key] = 1
                else:
                    unknown_counters[counter_key] += 1

                camera_id = f"{counter_key}_{unknown_counters[counter_key]}"

            folder_path = os.path.join(master_folder, camera_id)

            # Track camera folders for reporting
            if camera_id not in self.status.camera_folders:
                self.status.camera_folders[camera_id] = folder_path

            return folder_path

        except Exception as e:
            logger.error(f"Error getting camera folder for {file_path}: {str(e)}")
            # Fallback to root folder
            return master_folder