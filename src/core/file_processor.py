import os
import json
import subprocess
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from ..utils.exceptions import FileProcessingError


class FileProcessor:
    """Handles file scanning and grouping logic"""

    def __init__(self, exif_handler):
        self.exif_handler = exif_handler
        self.supported_extensions = {
            '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.raw',
            '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2'
        }

    def find_matching_files_batch(self, reference_file: str, use_camera_match: bool = True,
                                  use_extension_match: bool = True) -> List[str]:
        """Find files using batch ExifTool processing for better performance"""
        try:
            folder = os.path.dirname(reference_file)
            ref_extension = os.path.splitext(reference_file)[1].lower()

            # Get reference camera info
            ref_camera_info = None
            if use_camera_match:
                ref_camera_info = self.exif_handler.get_camera_info(reference_file)

            # First, collect all potential files
            potential_files = []
            for file_name in os.listdir(folder):
                file_path = os.path.join(folder, file_name)

                if not os.path.isfile(file_path):
                    continue

                file_extension = os.path.splitext(file_name)[1].lower()

                # Quick filters before ExifTool
                if file_extension not in self.supported_extensions:
                    continue

                if use_extension_match and file_extension != ref_extension:
                    continue

                potential_files.append(file_path)

            # If no camera matching needed, return all files
            if not use_camera_match or not ref_camera_info:
                return sorted(potential_files)

            # Batch process all files for camera info
            return self._batch_filter_by_camera(potential_files, ref_camera_info)

        except Exception as e:
            raise FileProcessingError(f"Error scanning files: {str(e)}")

    def _batch_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str]) -> List[str]:
        """Filter files by camera info using batch processing"""
        if not file_paths:
            return []

        try:
            # Use ExifTool in batch mode
            cmd = [self.exif_handler.exiftool_path, '-json', '-Make', '-Model'] + file_paths
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                # Fallback to individual processing
                return self._individual_filter_by_camera(file_paths, ref_camera_info)

            metadata_list = json.loads(result.stdout)
            matching_files = []

            for metadata in metadata_list:
                file_path = metadata.get('SourceFile')
                if not file_path:
                    continue

                make = metadata.get('Make', '').strip()
                model = metadata.get('Model', '').strip()

                if (make == ref_camera_info['make'] and
                        model == ref_camera_info['model']):
                    matching_files.append(file_path)

            return sorted(matching_files)

        except Exception:
            # Fallback to individual processing if batch fails
            return self._individual_filter_by_camera(file_paths, ref_camera_info)

    def _individual_filter_by_camera(self, file_paths: List[str], ref_camera_info: Dict[str, str]) -> List[str]:
        """Filter files by camera info using individual file processing"""
        matching_files = []
        for file_path in file_paths:
            try:
                file_camera_info = self.exif_handler.get_camera_info(file_path)
                if (file_camera_info['make'] == ref_camera_info['make'] and
                        file_camera_info['model'] == ref_camera_info['model']):
                    matching_files.append(file_path)
            except Exception:
                continue
        return sorted(matching_files)

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