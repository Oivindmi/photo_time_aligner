import os
import asyncio
import logging
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from ..utils.exceptions import FileProcessingError
from .filename_pattern import FilenamePatternMatcher
from .supported_formats import ALL_SUPPORTED_EXTENSIONS
from .concurrent_file_processor import ConcurrentFileProcessor
from .time_calculator import TimeCalculator

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file scanning and grouping logic with async operations"""

    def __init__(self, exif_handler):
        self.exif_handler = exif_handler
        self.supported_extensions = ALL_SUPPORTED_EXTENSIONS
        self.concurrent_processor = ConcurrentFileProcessor(exif_handler)
        logger.info(f"FileProcessor initialized with {len(self.supported_extensions)} supported formats")

    def find_matching_files_incremental(self, reference_file: str, use_camera_match: bool = True,
                                        use_extension_match: bool = True, use_pattern_match: bool = False,
                                        file_found_signal=None) -> None:
        """Find files incrementally using async operations"""
        # Run async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                self._find_matching_files_async(
                    reference_file, use_camera_match, use_extension_match,
                    use_pattern_match, file_found_signal
                )
            )
        finally:
            loop.close()

    async def _find_matching_files_async(self, reference_file: str, use_camera_match: bool,
                                         use_extension_match: bool, use_pattern_match: bool,
                                         file_found_signal) -> None:
        """Async implementation of find_matching_files"""
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

            # Determine extensions to scan
            extensions = {ref_extension} if use_extension_match else self.supported_extensions

            # Fast async directory scan
            all_files = await self.concurrent_processor.scan_directory_async(folder, extensions)

            logger.info(f"Found {len(all_files)} potential files after extension filtering")

            # Quick pattern filtering if enabled
            if use_pattern_match and ref_pattern:
                pattern_filtered = []
                for file_path in all_files:
                    if FilenamePatternMatcher.matches_pattern(os.path.basename(file_path), ref_pattern):
                        pattern_filtered.append(file_path)
                all_files = pattern_filtered
                logger.info(f"Pattern filtering reduced to {len(all_files)} files")

            # If no camera matching needed, emit all files
            if not use_camera_match or not ref_camera_info:
                logger.info("No camera matching needed, emitting all files")
                for file_path in sorted(all_files):
                    if file_found_signal:
                        file_found_signal.emit(file_path)
                return

            # Process files for camera matching in parallel batches
            await self._process_camera_matching_async(
                all_files, ref_camera_info, file_found_signal
            )

        except Exception as e:
            logger.error(f"Error in find_matching_files: {str(e)}")
            raise FileProcessingError(f"Error scanning files: {str(e)}")

    async def _process_camera_matching_async(self, files: List[str], ref_camera_info: Dict[str, str],
                                             file_found_signal) -> None:
        """Process camera matching asynchronously"""
        # Process in batches for efficiency
        batch_size = 20

        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]

            # Get metadata for batch in parallel
            metadata_list = self.exif_handler.read_metadata_batch(batch)

            # Check each file in batch
            for file_path, metadata in zip(batch, metadata_list):
                make = metadata.get('Make', '').strip()
                model = metadata.get('Model', '').strip()

                # Check if camera matches
                matches = False
                if not ref_camera_info.get('make') and not ref_camera_info.get('model'):
                    # Reference has empty camera info - match files with empty camera info
                    if not make and not model:
                        matches = True
                else:
                    # Reference has camera info - match files with same camera info
                    if (make == ref_camera_info.get('make', '') and
                            model == ref_camera_info.get('model', '')):
                        matches = True

                if matches and file_found_signal:
                    file_found_signal.emit(file_path)

    def apply_time_offset(self, files: List[str], selected_field: str,
                          offset_seconds: float = 0) -> Dict[str, bool]:
        """Apply time offset to files using parallel processing"""
        results = {}

        logger.info(f"Applying offset of {offset_seconds} seconds to {len(files)} files using field {selected_field}")

        # Process files in parallel batches
        batch_size = 10

        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]

            # Get metadata for batch
            metadata_list = self.exif_handler.read_metadata_batch(batch)

            # Process each file in batch
            for file_path, metadata in zip(batch, metadata_list):
                try:
                    # Parse datetime fields from metadata
                    datetime_fields = {}
                    for key, value in metadata.items():
                        if any(date_key in key.lower() for date_key in ['date', 'time']) and value:
                            parsed_date = TimeCalculator.parse_datetime_naive(str(value))
                            if parsed_date:
                                datetime_fields[key] = parsed_date

                    # Check if selected field exists
                    if selected_field not in datetime_fields or datetime_fields[selected_field] is None:
                        logger.warning(f"Selected field {selected_field} not found in {os.path.basename(file_path)}")
                        results[file_path] = False
                        continue

                    # Apply offset
                    original_timestamp = datetime_fields[selected_field]
                    adjusted_timestamp = original_timestamp
                    if offset_seconds != 0:
                        adjusted_timestamp = original_timestamp + timedelta(seconds=offset_seconds)

                    # Update all populated fields
                    fields_to_update = {}
                    for field_name, value in datetime_fields.items():
                        if value is not None:
                            fields_to_update[field_name] = adjusted_timestamp

                    # Apply updates
                    success = self.exif_handler.update_all_datetime_fields(file_path, fields_to_update)

                    if success:
                        logger.info(f"Updated {len(fields_to_update)} fields in {os.path.basename(file_path)}")
                    else:
                        logger.error(f"Failed to update fields in {os.path.basename(file_path)}")

                    results[file_path] = success

                except Exception as e:
                    logger.error(f"Error updating timestamps for {os.path.basename(file_path)}: {str(e)}")
                    results[file_path] = False

        return results