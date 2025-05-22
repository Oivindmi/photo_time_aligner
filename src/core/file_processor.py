import os
import json
import subprocess
import logging
import tempfile
import select  # Add this import
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from ..utils.exceptions import FileProcessingError
from .filename_pattern import FilenamePatternMatcher
from .supported_formats import ALL_SUPPORTED_EXTENSIONS
from PyQt5.QtCore import QThread

# Set up logger
logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file scanning and grouping logic"""

    def __init__(self, exif_handler):
        self.exif_handler = exif_handler
        # Use the centralized format definition
        self.supported_extensions = ALL_SUPPORTED_EXTENSIONS
        logger.info(f"FileProcessor initialized with {len(self.supported_extensions)} supported formats")

    def find_matching_files_batch(self, reference_file: str, use_camera_match: bool = True,
                                  use_extension_match: bool = True,
                                  use_pattern_match: bool = False) -> List[str]:
        """Find files using batch ExifTool processing for better performance

        Note: This method is kept for backward compatibility but is no longer recommended.
        Use find_matching_files_incremental instead to avoid stack overflow errors.
        """
        try:
            folder = os.path.dirname(reference_file)
            ref_filename = os.path.basename(reference_file)
            ref_extension = os.path.splitext(reference_file)[1].lower()

            logger.info(f"Scanning folder: {folder}")
            logger.info(f"Reference file: {ref_filename}")
            logger.info(
                f"Camera match: {use_camera_match}, Extension match: {use_extension_match}, Pattern match: {use_pattern_match}")

            # Get reference pattern if needed
            ref_pattern = None
            if use_pattern_match:
                ref_pattern = FilenamePatternMatcher.extract_pattern(ref_filename)
                logger.info(f"Reference pattern: {ref_pattern['display']}")

            # Get reference camera info
            ref_camera_info = None
            if use_camera_match:
                ref_camera_info = self.exif_handler.get_camera_info(reference_file)
                logger.info(f"Reference camera: {ref_camera_info}")

            # First, collect all potential files
            potential_files = []
            excluded_files = {
                'not_file': [],
                'wrong_extension': [],
                'extension_mismatch': [],
                'pattern_mismatch': []
            }

            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)

                if not os.path.isfile(file_path):
                    excluded_files['not_file'].append(file_name)
                    continue

                file_extension = os.path.splitext(file_name)[1].lower()

                # Quick filters before ExifTool
                if file_extension not in self.supported_extensions:
                    excluded_files['wrong_extension'].append(f"{file_name} (ext: {file_extension})")
                    continue

                if use_extension_match and file_extension != ref_extension:
                    excluded_files['extension_mismatch'].append(
                        f"{file_name} (ext: {file_extension} != {ref_extension})")
                    continue

                # Pattern matching
                if use_pattern_match and ref_pattern:
                    if not FilenamePatternMatcher.matches_pattern(file_name, ref_pattern):
                        excluded_files['pattern_mismatch'].append(
                            f"{file_name} (doesn't match {ref_pattern['display']})")
                        continue

                potential_files.append(file_path)

            # Log excluded files
            if excluded_files['not_file']:
                logger.info(f"Excluded {len(excluded_files['not_file'])} directories/non-files")
            if excluded_files['wrong_extension']:
                logger.info(f"Excluded {len(excluded_files['wrong_extension'])} files with unsupported extensions")
                logger.debug(f"Unsupported extensions: {excluded_files['wrong_extension'][:10]}...")
            if excluded_files['extension_mismatch']:
                logger.info(f"Excluded {len(excluded_files['extension_mismatch'])} files with mismatched extensions")
                logger.debug(f"Extension mismatches: {excluded_files['extension_mismatch'][:10]}...")
            if excluded_files['pattern_mismatch']:
                logger.info(
                    f"Excluded {len(excluded_files['pattern_mismatch'])} files with mismatched filename patterns")
                logger.debug(f"Pattern mismatches: {excluded_files['pattern_mismatch'][:10]}...")

            logger.info(f"Found {len(potential_files)} potential files after initial filtering")

            # If no camera matching needed, return all files
            if not use_camera_match or not ref_camera_info:
                logger.info("No camera matching needed, returning all files")
                return sorted(potential_files)

            # Batch process all files for camera info
            return self._batch_filter_by_camera(potential_files, ref_camera_info)

        except Exception as e:
            logger.error(f"Error in find_matching_files_batch: {str(e)}")
            raise FileProcessingError(f"Error scanning files: {str(e)}")

    def find_matching_files_incremental(self, reference_file: str, use_camera_match: bool = True,
                                        use_extension_match: bool = True, use_pattern_match: bool = False,
                                        file_found_signal=None) -> None:
        """Find files incrementally, emitting each match through a signal

        This method avoids returning large lists across thread boundaries by emitting
        files one at a time through the provided signal.
        """
        try:
            folder = os.path.dirname(reference_file)
            ref_filename = os.path.basename(reference_file)
            ref_extension = os.path.splitext(reference_file)[1].lower()

            logger.info(f"Scanning folder: {folder}")
            logger.info(f"Reference file: {ref_filename}")
            logger.info(
                f"Camera match: {use_camera_match}, Extension match: {use_extension_match}, Pattern match: {use_pattern_match}")

            # Get reference pattern if needed
            ref_pattern = None
            if use_pattern_match:
                ref_pattern = FilenamePatternMatcher.extract_pattern(ref_filename)
                logger.info(f"Reference pattern: {ref_pattern['display']}")

            # Get reference camera info
            ref_camera_info = None
            if use_camera_match:
                ref_camera_info = self.exif_handler.get_camera_info(reference_file)
                logger.info(f"Reference camera: {ref_camera_info}")

            # First, collect all potential files
            potential_files = []
            excluded_files = {
                'not_file': [],
                'wrong_extension': [],
                'extension_mismatch': [],
                'pattern_mismatch': []
            }

            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)

                if not os.path.isfile(file_path):
                    excluded_files['not_file'].append(file_name)
                    continue

                file_extension = os.path.splitext(file_name)[1].lower()

                # Quick filters before ExifTool
                if file_extension not in self.supported_extensions:
                    excluded_files['wrong_extension'].append(f"{file_name} (ext: {file_extension})")
                    continue

                if use_extension_match and file_extension != ref_extension:
                    excluded_files['extension_mismatch'].append(
                        f"{file_name} (ext: {file_extension} != {ref_extension})")
                    continue

                # Pattern matching
                if use_pattern_match and ref_pattern:
                    if not FilenamePatternMatcher.matches_pattern(file_name, ref_pattern):
                        excluded_files['pattern_mismatch'].append(
                            f"{file_name} (doesn't match {ref_pattern['display']})")
                        continue

                potential_files.append(file_path)

            # Log excluded files
            if excluded_files['not_file']:
                logger.info(f"Excluded {len(excluded_files['not_file'])} directories/non-files")
            if excluded_files['wrong_extension']:
                logger.info(f"Excluded {len(excluded_files['wrong_extension'])} files with unsupported extensions")
                logger.debug(f"Unsupported extensions: {excluded_files['wrong_extension'][:10]}...")
            if excluded_files['extension_mismatch']:
                logger.info(f"Excluded {len(excluded_files['extension_mismatch'])} files with mismatched extensions")
                logger.debug(f"Extension mismatches: {excluded_files['extension_mismatch'][:10]}...")
            if excluded_files['pattern_mismatch']:
                logger.info(
                    f"Excluded {len(excluded_files['pattern_mismatch'])} files with mismatched filename patterns")
                logger.debug(f"Pattern mismatches: {excluded_files['pattern_mismatch'][:10]}...")

            logger.info(f"Found {len(potential_files)} potential files after initial filtering")

            # If no camera matching needed, emit all files immediately
            if not use_camera_match or not ref_camera_info:
                logger.info("No camera matching needed, emitting all files")
                # Sort files for consistent order
                for file_path in sorted(potential_files):
                    if file_found_signal:
                        file_found_signal.emit(file_path)
                return

            # Process files incrementally for camera matching
            self._incremental_filter_by_camera(potential_files, ref_camera_info, file_found_signal)

        except Exception as e:
            logger.error(f"Error in find_matching_files_incremental: {str(e)}")
            raise FileProcessingError(f"Error scanning files: {str(e)}")

    def _batch_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str]) -> List[str]:
        """Filter files by camera info using batch processing with argument file

        Note: This method is kept for backward compatibility but may cause stack overflow
        with large numbers of files. Use _incremental_filter_by_camera instead.
        """
        if not file_paths:
            return []

        try:
            logger.info(f"Batch processing {len(file_paths)} files for camera matching")

            # Define batch size
            BATCH_SIZE = 5  # Use a small batch size to reduce the risk of stack overflow

            matching_files = []
            # Process files in batches to avoid stack overflow
            for batch_start in range(0, len(file_paths), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(file_paths))
                batch = file_paths[batch_start:batch_end]

                logger.info(f"Processing batch {batch_start // BATCH_SIZE + 1} ({len(batch)} files)")

                # Process this batch
                batch_matches = self._process_batch(batch, ref_camera_info)
                if batch_matches:
                    matching_files.extend(batch_matches)

            logger.info(f"All batches processed, found {len(matching_files)} matching files")
            return sorted(matching_files)

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            logger.info("Falling back to individual file processing (this may take longer)")
            return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

    def _incremental_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str],
                                      file_found_signal) -> None:
        """Process files in larger batches, emitting matches incrementally"""
        if not file_paths:
            return

        try:
            logger.info(f"Incremental processing {len(file_paths)} files for camera matching")

            # Sort files for consistent order
            sorted_files = sorted(file_paths)

            # Use larger batches for better performance
            BATCH_SIZE = 20  # Increased from 2 to 20

            # Process files in batches
            for batch_start in range(0, len(sorted_files), BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, len(sorted_files))
                batch = sorted_files[batch_start:batch_end]

                logger.info(f"Processing batch {batch_start // BATCH_SIZE + 1} ({len(batch)} files)")

                # Get metadata for entire batch at once
                try:
                    batch_metadata = []
                    for file_path in batch:
                        try:
                            file_camera_info = self.exif_handler.get_camera_info(file_path)
                            batch_metadata.append((file_path, file_camera_info))
                        except Exception as e:
                            logger.debug(f"Error getting camera info for {os.path.basename(file_path)}: {str(e)}")

                    # Process metadata and emit matching files
                    for file_path, file_camera_info in batch_metadata:
                        # Check if this file matches the reference camera
                        matches = False

                        if (not ref_camera_info.get('make') and not ref_camera_info.get('model')):
                            # Reference has empty camera info - match files with empty camera info
                            if not file_camera_info.get('make') and not file_camera_info.get('model'):
                                matches = True
                        else:
                            # Reference has camera info - match files with same camera info
                            if (file_camera_info.get('make', '') == ref_camera_info.get('make', '') and
                                    file_camera_info.get('model', '') == ref_camera_info.get('model', '')):
                                matches = True

                        # Emit the file immediately if it matches
                        if matches and file_found_signal:
                            file_found_signal.emit(file_path)

                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    # Fall back to individual processing for this batch
                    for file_path in batch:
                        try:
                            file_camera_info = self.exif_handler.get_camera_info(file_path)

                            # Check if this file matches the reference camera
                            matches = False

                            if (not ref_camera_info.get('make') and not ref_camera_info.get('model')):
                                if not file_camera_info.get('make') and not file_camera_info.get('model'):
                                    matches = True
                            else:
                                if (file_camera_info.get('make', '') == ref_camera_info.get('make', '') and
                                        file_camera_info.get('model', '') == ref_camera_info.get('model', '')):
                                    matches = True

                            # Emit the file immediately if it matches
                            if matches and file_found_signal:
                                file_found_signal.emit(file_path)

                        except Exception as e:
                            logger.debug(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                            continue

                # Short sleep to allow UI to process signals (optional)
                # QThread.msleep(1)

            logger.info("Incremental file processing complete")

        except Exception as e:
            logger.error(f"Error in incremental processing: {str(e)}")

    def _process_batch(self, file_paths: List[str], ref_camera_info: Dict[str, str]) -> List[str]:
        """Process a batch of files using ExifTool and streaming JSON parsing"""
        try:
            matching_files = []

            # Create a temporary argument file with all file paths in this batch
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                for file_path in file_paths:
                    arg_file.write(file_path + '\n')
                arg_file_path = arg_file.name

            try:
                # Use ExifTool with argument file for all files at once
                cmd = [
                    self.exif_handler.exiftool_path,
                    '-json',
                    '-Make',
                    '-Model',
                    '-charset', 'filename=utf8',
                    '-@', arg_file_path
                ]

                logger.debug(f"Batch ExifTool command: {' '.join(cmd)}")

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

                if result.returncode != 0:
                    logger.warning(f"Batch ExifTool failed with return code {result.returncode}")
                    logger.warning(f"Error message: {result.stderr}")
                    logger.info("Falling back to individual file processing")
                    return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

                # Process the JSON output manually to avoid stack overflow
                try:
                    # Standard JSON parsing with small batches should be safe
                    metadata_list = json.loads(result.stdout)

                    for metadata in metadata_list:
                        file_path = metadata.get('SourceFile')
                        if not file_path:
                            continue

                        make = metadata.get('Make', '').strip()
                        model = metadata.get('Model', '').strip()

                        # Empty camera info should match empty camera info
                        if (not ref_camera_info.get('make') and not ref_camera_info.get('model')):
                            # Reference has empty camera info - match files with empty camera info
                            if not make and not model:
                                matching_files.append(file_path)
                        else:
                            # Reference has camera info - match files with same camera info
                            if (make == ref_camera_info['make'] and
                                    model == ref_camera_info['model']):
                                matching_files.append(file_path)

                    logger.info(f"JSON parsing found {len(matching_files)} matching files")

                except (json.JSONDecodeError, RecursionError) as e:
                    logger.error(f"Error in JSON parsing: {str(e)}")
                    # Fall back to individual processing
                    return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

            finally:
                # Clean up the argument file
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)
                    logger.debug(f"Cleaned up argument file: {arg_file_path}")

            return matching_files

        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
            # Fall back to individual processing
            return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

    def _individual_filter_by_camera_with_logging(self, file_paths: List[str], ref_camera_info: Dict[str, str],
                                                  notify_fallback: bool = False) -> Tuple[List[str], List[Dict]]:
        """Filter files by camera info using individual file processing, with exclusion logging"""
        if notify_fallback:
            logger.warning("Using fallback method - processing files individually. This may take longer.")

        matching_files = []
        excluded_files = []
        total_files = len(file_paths)

        for idx, file_path in enumerate(file_paths):
            if idx % 10 == 0:  # Log progress every 10 files
                logger.info(f"Processing file {idx + 1}/{total_files}")

            try:
                file_camera_info = self.exif_handler.get_camera_info(file_path)

                # Empty camera info should match empty camera info
                if (not ref_camera_info.get('make') and not ref_camera_info.get('model')):
                    # Reference has empty camera info - match files with empty camera info
                    if not file_camera_info.get('make') and not file_camera_info.get('model'):
                        matching_files.append(file_path)
                    else:
                        excluded_files.append({
                            'file': os.path.basename(file_path),
                            'camera': f"{file_camera_info['make']} {file_camera_info['model']}".strip() or "empty",
                            'expected': "empty"
                        })
                else:
                    # Reference has camera info - match files with same camera info
                    if (file_camera_info['make'] == ref_camera_info['make'] and
                            file_camera_info['model'] == ref_camera_info['model']):
                        matching_files.append(file_path)
                    else:
                        excluded_files.append({
                            'file': os.path.basename(file_path),
                            'camera': f"{file_camera_info['make']} {file_camera_info['model']}".strip() or "empty",
                            'expected': f"{ref_camera_info['make']} {ref_camera_info['model']}"
                        })

            except Exception as e:
                logger.debug(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                excluded_files.append({
                    'file': os.path.basename(file_path),
                    'camera': 'Error reading metadata',
                    'expected': f"{ref_camera_info['make']} {ref_camera_info['model']}".strip() or "empty"
                })
                continue

        # Log exclusions
        if excluded_files:
            logger.info(f"Individual processing excluded {len(excluded_files)} files due to camera mismatch")
            for exc in excluded_files[:10]:
                logger.debug(f"  {exc['file']}: found '{exc['camera']}', expected '{exc['expected']}'")
            if len(excluded_files) > 10:
                logger.debug(f"  ... and {len(excluded_files) - 10} more")

        logger.info(f"Individual processing complete. Found {len(matching_files)} matching files")
        return sorted(matching_files), excluded_files

    def _individual_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str],
                                     notify_fallback: bool = False) -> List[str]:
        """Filter files by camera info using individual file processing"""
        matches, _ = self._individual_filter_by_camera_with_logging(file_paths, ref_camera_info, notify_fallback)
        return matches

    def apply_time_offset(self, files: List[str], selected_field: str,
                          offset_seconds: float = 0) -> Dict[str, bool]:
        """
        Apply time offset to all files and sync other time fields.

        For each file:
        1. Get the selected field's original timestamp
        2. Apply the offset to create an adjusted timestamp (if offset is not 0)
        3. Update all datetime fields to match the adjusted timestamp

        This preserves relative time differences between files.
        """
        results = {}

        logger.info(f"Applying offset of {offset_seconds} seconds to {len(files)} files using field {selected_field}")

        for file_path in files:
            try:
                # Get all datetime fields
                datetime_fields = self.exif_handler.get_datetime_fields(file_path)

                # Get the selected field value
                if selected_field not in datetime_fields or datetime_fields[selected_field] is None:
                    logger.warning(f"Selected field {selected_field} not found in {os.path.basename(file_path)}")
                    results[file_path] = False
                    continue

                # Get the original timestamp for the selected field
                original_timestamp = datetime_fields[selected_field]

                # Apply offset to create adjusted timestamp
                adjusted_timestamp = original_timestamp
                if offset_seconds != 0:
                    adjusted_timestamp = original_timestamp + timedelta(seconds=offset_seconds)
                    logger.debug(
                        f"Adjusting {os.path.basename(file_path)} from {original_timestamp} to {adjusted_timestamp}")

                # Update all populated time fields to match the adjusted timestamp
                fields_to_update = {}
                for field_name, value in datetime_fields.items():
                    if value is not None:  # Only update fields that have values
                        fields_to_update[field_name] = adjusted_timestamp

                # Apply updates
                success = self.exif_handler.update_all_datetime_fields(file_path, fields_to_update)

                if success:
                    logger.info(f"Updated {len(fields_to_update)} fields in {os.path.basename(file_path)} " +
                                f"{'(no change)' if offset_seconds == 0 else f'(offset: {offset_seconds} seconds)'}")
                else:
                    logger.error(f"Failed to update fields in {os.path.basename(file_path)}")

                results[file_path] = success

            except Exception as e:
                logger.error(f"Error updating timestamps for {os.path.basename(file_path)}: {str(e)}")
                results[file_path] = False

        return results