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

import os
import logging
import gc
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..utils.exceptions import FileProcessingError
from .time_calculator import TimeCalculator

import gc
from .supported_formats import ALL_SUPPORTED_EXTENSIONS
from .concurrent_file_processor import ConcurrentFileProcessor

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file scanning and grouping logic with async operations"""

    def __init__(self, exif_handler):
        self.exif_handler = exif_handler
        self.supported_extensions = ALL_SUPPORTED_EXTENSIONS
        self.concurrent_processor = ConcurrentFileProcessor(exif_handler)
        logger.info(f"FileProcessor initialized with {len(self.supported_extensions)} supported formats")

        # Group processing settings
        self.GROUP_SIZE = 80
        self.progress_callback = None

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
        """Apply time offset to files using group-based processing with pool restart"""
        results = {}
        total_files = len(files)

        if total_files == 0:
            return results

        logger.info(f"Starting group-based processing of {total_files} files with offset {offset_seconds} seconds")

        # Calculate number of groups
        num_groups = (total_files + self.GROUP_SIZE - 1) // self.GROUP_SIZE  # Ceiling division
        logger.info(f"Processing {total_files} files in {num_groups} groups of {self.GROUP_SIZE} files each")

        processed_files = 0

        # Process files in groups
        for group_index in range(num_groups):
            start_idx = group_index * self.GROUP_SIZE
            end_idx = min(start_idx + self.GROUP_SIZE, total_files)
            group_files = files[start_idx:end_idx]

            group_num = group_index + 1
            logger.info(f"Processing group {group_num}/{num_groups} ({len(group_files)} files)")

            # Update progress
            if self.progress_callback:
                status = f"Processing group {group_num} of {num_groups}"
                self.progress_callback(processed_files, total_files, status)

            # Process the group (with retry logic)
            group_results = self._process_group_with_retry(
                group_files, selected_field, offset_seconds, group_num, num_groups
            )

            # Add group results to overall results
            results.update(group_results)
            processed_files += len(group_files)

            # Update progress after group completion
            if self.progress_callback:
                status = f"Completed group {group_num} of {num_groups}"
                self.progress_callback(processed_files, total_files, status)

            # Restart process pool between groups (except for the last group)
            if group_index < num_groups - 1:
                logger.info(f"Restarting process pool before group {group_num + 1}")
                if self.progress_callback:
                    self.progress_callback(processed_files, total_files, "Restarting processes...")

                try:
                    self.exif_handler.exiftool_pool.restart_pool()
                    # Small delay to ensure processes are ready
                    import time
                    time.sleep(0.2)
                except Exception as e:
                    logger.error(f"Error restarting process pool: {str(e)}")
                    # Continue anyway - the pool might still work

            # Force garbage collection after each group
            gc.collect()

        # Final progress update
        if self.progress_callback:
            self.progress_callback(total_files, total_files, "Processing complete")

        successful = sum(1 for success in results.values() if success)
        logger.info(f"Group-based processing complete: {successful}/{total_files} files processed successfully")

        return results

    def _process_group_with_retry(self, group_files: List[str], selected_field: str,
                                  offset_seconds: float, group_num: int, total_groups: int) -> Dict[str, bool]:
        """Process a group of files with retry logic"""
        max_attempts = 2

        for attempt in range(max_attempts):
            attempt_num = attempt + 1

            try:
                if attempt > 0:
                    logger.warning(f"Retrying group {group_num}/{total_groups} (attempt {attempt_num}/{max_attempts})")
                    if self.progress_callback:
                        status = f"Retrying group {group_num} of {total_groups} (attempt {attempt_num})"
                        # We don't update the file count during retry, just the status
                        processed_so_far = (group_num - 1) * self.GROUP_SIZE
                        total_files = total_groups * self.GROUP_SIZE
                        self.progress_callback(processed_so_far, total_files, status)

                # Process the group
                group_results = self._process_single_group(group_files, selected_field, offset_seconds)

                # Check if the group was processed successfully
                successful_files = sum(1 for success in group_results.values() if success)
                logger.info(
                    f"Group {group_num}/{total_groups} attempt {attempt_num}: {successful_files}/{len(group_files)} files successful")

                return group_results

            except Exception as e:
                logger.error(f"Error processing group {group_num}/{total_groups} attempt {attempt_num}: {str(e)}")

                if attempt < max_attempts - 1:
                    # Not the last attempt, try restarting the pool
                    logger.info(f"Restarting process pool before retry...")
                    try:
                        self.exif_handler.exiftool_pool.restart_pool()
                        import time
                        time.sleep(0.5)
                    except Exception as restart_error:
                        logger.error(f"Error restarting pool for retry: {str(restart_error)}")
                else:
                    # Last attempt failed, return failure for all files in group
                    logger.error(f"Group {group_num}/{total_groups} failed after {max_attempts} attempts")
                    return {file_path: False for file_path in group_files}

        # Shouldn't reach here, but just in case
        return {file_path: False for file_path in group_files}

    def _process_single_group(self, group_files: List[str], selected_field: str,
                              offset_seconds: float) -> Dict[str, bool]:
        """Process a single group of files with batch metadata reading"""
        results = {}

        logger.debug(f"Reading metadata for entire group of {len(group_files)} files at once")

        # Read metadata for ALL files in the group at once (instead of in small batches)
        try:
            metadata_list = self.exif_handler.read_metadata_batch(group_files)
            logger.debug(f"Successfully read metadata for {len(metadata_list)} files in group")
        except Exception as e:
            logger.error(f"Error reading batch metadata for group: {str(e)}")
            # Fallback to individual file processing
            return self._process_group_individual_fallback(group_files, selected_field, offset_seconds)

        # Process each file with its metadata
        for file_path, metadata in zip(group_files, metadata_list):
            try:
                result = self._process_single_file(file_path, metadata, selected_field, offset_seconds)
                results[file_path] = result
            except Exception as e:
                logger.error(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                results[file_path] = False

        return results

    def _process_group_individual_fallback(self, group_files: List[str], selected_field: str,
                                           offset_seconds: float) -> Dict[str, bool]:
        """Fallback to individual file processing if batch fails"""
        logger.warning("Falling back to individual file processing for this group")
        results = {}

        for file_path in group_files:
            try:
                # Read metadata for single file
                metadata = self.exif_handler.read_metadata(file_path)
                result = self._process_single_file(file_path, metadata, selected_field, offset_seconds)
                results[file_path] = result
            except Exception as e:
                logger.error(f"Error processing {os.path.basename(file_path)}: {str(e)}")
                results[file_path] = False

        return results

    def _process_single_file(self, file_path: str, metadata: dict,
                             selected_field: str, offset_seconds: float) -> bool:
        """Process a single file"""
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
                return False

            # Apply offset
            original_timestamp = datetime_fields[selected_field]
            if offset_seconds != 0:
                adjusted_timestamp = original_timestamp + timedelta(seconds=offset_seconds)
            else:
                adjusted_timestamp = original_timestamp

            # Update all populated fields
            fields_to_update = {}
            for field_name, value in datetime_fields.items():
                if value is not None:
                    fields_to_update[field_name] = adjusted_timestamp

            # Apply updates
            success = self.exif_handler.update_all_datetime_fields(file_path, fields_to_update)

            if success:
                logger.debug(f"Updated {len(fields_to_update)} fields in {os.path.basename(file_path)}")
            else:
                logger.warning(f"Failed to update fields in {os.path.basename(file_path)}")

            return success

        except Exception as e:
            logger.error(f"Error processing single file {os.path.basename(file_path)}: {str(e)}")
            return False