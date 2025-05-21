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
        self.metadata_errors = []  # List of (file_path, error_msg)
        self.metadata_skipped = []  # List of (file_path, reason)
        self.files_moved = 0
        self.move_skipped = []  # List of (file_path, reason)
        self.move_errors = []  # List of (file_path, error_msg)

        # Track camera folders created
        self.camera_folders = {}  # camera_id -> folder_path


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
        logger.info("AlignmentProcessor.process_files called")
        logger.info(f"Parameters: ref_files={len(reference_files)}, target_files={len(target_files)}")
        logger.info(f"Fields: ref_field={reference_field}, target_field={target_field}")
        logger.info(f"Offset: {time_offset}, master_folder={master_folder}")
        logger.info(f"Move files: {move_files}, use camera folders: {use_camera_folders}")

        self.status = ProcessingStatus()
        all_files = reference_files + target_files
        self.status.total_files = len(all_files)

        # Create groups with their respective fields
        groups = [
            (reference_files, reference_field, "Reference Group"),
            (target_files, target_field, "Target Group")
        ]

        # Phase 1: Update metadata
        logger.info("Starting metadata updates...")
        for files, selected_field, group_name in groups:
            logger.info(f"Processing {group_name} with {len(files)} files")
            self._update_metadata_batch(files, selected_field, time_offset, group_name)

        # Phase 2: Move files if requested
        if move_files and master_folder:
            logger.info("Starting file move operations...")
            self._move_files_batch(all_files, master_folder, use_camera_folders)

        logger.info("AlignmentProcessor.process_files completed")
        return self.status

    def _update_metadata_batch(self, files: List[str], selected_field: str,
                               offset: timedelta, group_name: str):
        """Update metadata for a batch of files"""
        for file_path in files:
            try:
                # Check if file has the selected field
                datetime_fields = self.exif_handler.get_datetime_fields(file_path)

                if selected_field not in datetime_fields or datetime_fields[selected_field] is None:
                    self.status.metadata_skipped.append(
                        (file_path, f"Selected field '{selected_field}' not found")
                    )
                    continue

                # Apply offset to the selected field
                original_time = datetime_fields[selected_field]
                new_time = original_time + offset

                # Prepare updates for all existing fields
                fields_to_update = {}
                for field_name, value in datetime_fields.items():
                    if value is not None:  # Only update existing fields
                        fields_to_update[field_name] = new_time

                # Apply updates
                success = self.exif_handler.update_all_datetime_fields(file_path, fields_to_update)

                if success:
                    self.status.metadata_updated += 1
                    logger.info(f"Updated {len(fields_to_update)} fields in {os.path.basename(file_path)}")
                else:
                    self.status.metadata_errors.append(
                        (file_path, "Failed to update metadata")
                    )

            except Exception as e:
                self.status.metadata_errors.append(
                    (file_path, f"Error: {str(e)}")
                )
                logger.error(f"Error processing {file_path}: {str(e)}")

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