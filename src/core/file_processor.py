import os
import json
import subprocess
import logging
import tempfile
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from ..utils.exceptions import FileProcessingError
from .filename_pattern import FilenamePatternMatcher
from .supported_formats import ALL_SUPPORTED_EXTENSIONS

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
        """Find files using batch ExifTool processing for better performance"""
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

    def _batch_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str]) -> List[str]:
        """Filter files by camera info using batch processing with argument file"""
        if not file_paths:
            return []

        try:
            logger.info(f"Attempting batch ExifTool processing for {len(file_paths)} files")

            matching_files = []
            excluded_by_camera = []

            # Create a temporary argument file with all file paths
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
                logger.info(f"Processing {len(file_paths)} files in a single batch")

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

                if result.returncode != 0:
                    logger.warning(f"Batch ExifTool failed with return code {result.returncode}")
                    logger.warning(f"Error message: {result.stderr}")
                    logger.info("Falling back to individual file processing")
                    # Process files individually
                    return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

                try:
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
                                excluded_by_camera.append({
                                    'file': os.path.basename(file_path),
                                    'camera': f"{make} {model}" if (make or model) else "empty",
                                    'expected': "empty"
                                })
                        else:
                            # Reference has camera info - match files with same camera info
                            if (make == ref_camera_info['make'] and
                                    model == ref_camera_info['model']):
                                matching_files.append(file_path)
                            else:
                                excluded_by_camera.append({
                                    'file': os.path.basename(file_path),
                                    'camera': f"{make} {model}" if (make or model) else "empty",
                                    'expected': f"{ref_camera_info['make']} {ref_camera_info['model']}"
                                })

                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing JSON: {str(e)}")
                    logger.info("Falling back to individual file processing")
                    return self._individual_filter_by_camera(file_paths, ref_camera_info, notify_fallback=True)

            finally:
                # Clean up the argument file
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)
                    logger.debug(f"Cleaned up argument file: {arg_file_path}")

            # Log camera exclusions
            if excluded_by_camera:
                logger.info(f"Excluded {len(excluded_by_camera)} files due to camera mismatch")
                # Show first 10 camera mismatches
                for exc in excluded_by_camera[:10]:
                    logger.debug(f"  {exc['file']}: found '{exc['camera']}', expected '{exc['expected']}'")
                if len(excluded_by_camera) > 10:
                    logger.debug(f"  ... and {len(excluded_by_camera) - 10} more")

            logger.info(f"Batch processing found {len(matching_files)} matching files")
            return sorted(matching_files)

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            logger.info("Falling back to individual file processing (this may take longer)")
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
        """Apply time offset to all files and sync other time fields"""
        results = {}

        for file_path in files:
            try:
                # Get all datetime fields
                datetime_fields = self.exif_handler.get_datetime_fields(file_path)

                # Get the selected field value
                if selected_field not in datetime_fields or datetime_fields[selected_field] is None:
                    results[file_path] = False
                    continue

                # Calculate new time for selected field
                selected_value = datetime_fields[selected_field]
                if offset_seconds != 0:
                    selected_value = selected_value + timedelta(seconds=offset_seconds)

                # Update all populated time fields to match the selected field value
                fields_to_update = {}
                for field_name, value in datetime_fields.items():
                    if value is not None:  # Only update fields that have values
                        fields_to_update[field_name] = selected_value

                # Apply updates
                success = self.exif_handler.update_all_datetime_fields(file_path, fields_to_update)
                results[file_path] = success

            except Exception as e:
                results[file_path] = False

        return results