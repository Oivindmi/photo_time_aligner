# src/core/alignment_processor.py - Enhanced with repair functionality

import os
import logging
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from .corruption_detector import CorruptionDetector, CorruptionType
from .repair_strategies import FileRepairer, RepairResult

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

        # New repair tracking
        self.corruption_detected = 0
        self.repair_attempted = 0
        self.repair_successful = 0
        self.repair_failed = 0
        self.repair_results = {}  # file_path -> RepairResult


class AlignmentProcessor:
    """Handles the batch alignment process for photos and videos with repair functionality"""

    def __init__(self, exif_handler, file_processor):
        logger.info("AlignmentProcessor.__init__ called")
        self.exif_handler = exif_handler
        self.file_processor = file_processor
        self.status = ProcessingStatus()

        # Initialize repair components
        self.corruption_detector = CorruptionDetector()
        self.file_repairer = FileRepairer()

        logger.info("AlignmentProcessor initialization completed")

    def process_files(self,
                      reference_files: List[str],
                      target_files: List[str],
                      reference_field: str,
                      target_field: str,
                      time_offset: timedelta,
                      master_folder: Optional[str] = None,
                      move_files: bool = False,
                      use_camera_folders: bool = False,
                      progress_callback: Optional[callable] = None) -> ProcessingStatus:
        """
        Process reference and target files with corruption detection and repair.
        """
        logger.info("AlignmentProcessor.process_files called with repair functionality")
        logger.info(f"Parameters: ref_files={len(reference_files)}, target_files={len(target_files)}")

        self.status = ProcessingStatus()
        all_files = reference_files + target_files
        self.status.total_files = len(all_files)

        # Phase 1: Corruption Detection
        if progress_callback:
            progress_callback(0, len(all_files), "Scanning files for corruption...")

        corruption_results = self.corruption_detector.scan_files_for_corruption(all_files)
        corruption_summary = self.corruption_detector.get_corruption_summary(corruption_results)

        # Check if we found any corruption
        if corruption_summary['has_corruption']:
            # Ask user if they want to attempt repairs
            repair_choice = self._get_user_repair_choice(corruption_summary, corruption_results)

            if repair_choice:
                # Phase 2: Repair corrupted files
                repaired_files = self._repair_corrupted_files(
                    corruption_results, all_files, progress_callback
                )

                # Update file lists with repaired files
                reference_files, target_files = self._update_file_lists_after_repair(
                    reference_files, target_files, repaired_files
                )

        # Phase 3: Normal processing (now with potentially repaired files)
        if progress_callback:
            progress_callback(0, len(all_files), "Processing files...")

        # Update reference files (synchronize fields, no offset)
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

        # Update target files (apply NEGATIVE offset to adjust them)
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

        # Phase 4: Move files if requested
        if move_files and master_folder:
            logger.info("Starting file move operations...")
            self._move_files_batch(all_files, master_folder, use_camera_folders)

        logger.info("AlignmentProcessor.process_files completed")
        return self.status

    def _get_user_repair_choice(self, corruption_summary: Dict,
                                corruption_results: Dict) -> bool:
        """Get user choice on whether to attempt repairs"""

        # This will be called by the UI to show the repair dialog
        # For now, we'll use a simple approach that can be overridden
        logger.info(f"Corruption detected in {corruption_summary['repairable_files']} files")

        # In the real implementation, this will be handled by the UI
        # For now, return True to attempt repairs (will be overridden by UI)
        return True

    def _repair_corrupted_files(self, corruption_results: Dict, all_files: List[str],
                                progress_callback: Optional[callable] = None) -> Dict[str, str]:
        """Repair corrupted files with progress reporting"""

        # Get files that need repair
        files_to_repair = [
            file_path for file_path, corruption_info in corruption_results.items()
            if corruption_info.corruption_type != CorruptionType.HEALTHY and corruption_info.is_repairable
        ]

        if not files_to_repair:
            return {}

        logger.info(f"Attempting to repair {len(files_to_repair)} corrupted files")

        # Create backup directory
        backup_dir = self._create_backup_directory(all_files[0])  # Use first file's directory

        repaired_files = {}

        for i, file_path in enumerate(files_to_repair):
            if progress_callback:
                progress_callback(i, len(files_to_repair),
                                  f"Repairing corrupted files... ({i + 1}/{len(files_to_repair)})")

            corruption_info = corruption_results[file_path]

            try:
                # Attempt repair
                repair_result = self.file_repairer.repair_file(
                    file_path,
                    corruption_info.corruption_type,
                    backup_dir
                )

                # Track repair attempt
                self.status.repair_attempted += 1
                self.status.repair_results[file_path] = repair_result

                if repair_result.success and repair_result.verification_passed:
                    self.status.repair_successful += 1
                    repaired_files[file_path] = file_path  # File repaired in place
                    logger.info(
                        f"✅ Successfully repaired {os.path.basename(file_path)} using {repair_result.strategy_used.value}")
                else:
                    self.status.repair_failed += 1
                    logger.warning(f"❌ Failed to repair {os.path.basename(file_path)}: {repair_result.error_message}")

            except Exception as e:
                self.status.repair_failed += 1
                logger.error(f"Exception during repair of {os.path.basename(file_path)}: {e}")
                self.status.repair_results[file_path] = RepairResult(
                    strategy_used=None,
                    success=False,
                    error_message=str(e),
                    verification_passed=False
                )

        if progress_callback:
            progress_callback(len(files_to_repair), len(files_to_repair),
                              f"Repair complete: {self.status.repair_successful}/{len(files_to_repair)} successful")

        logger.info(f"Repair summary: {self.status.repair_successful} successful, {self.status.repair_failed} failed")
        return repaired_files

    def _create_backup_directory(self, reference_file_path: str) -> str:
        """Create backup directory in the same location as the files being processed"""
        base_dir = os.path.dirname(reference_file_path)
        backup_dir = os.path.join(base_dir, "backup")

        try:
            os.makedirs(backup_dir, exist_ok=True)
            logger.info(f"Created backup directory: {backup_dir}")
            return backup_dir
        except Exception as e:
            # Fallback to temp directory
            import tempfile
            backup_dir = tempfile.mkdtemp(prefix="photo_aligner_backup_")
            logger.warning(f"Could not create backup in source directory, using temp: {backup_dir}")
            return backup_dir

    def _update_file_lists_after_repair(self, reference_files: List[str], target_files: List[str],
                                        repaired_files: Dict[str, str]) -> Tuple[List[str], List[str]]:
        """Update file lists after repair (in case file paths changed)"""
        # In our case, files are repaired in place, so no path changes needed
        # But this method allows for future scenarios where repair might create new files
        return reference_files, target_files

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