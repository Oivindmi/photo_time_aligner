import shutil
from .exiftool_pool import ExifToolProcessPool
from .cached_exif_handler import CachedExifHandler
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dateutil import parser
from ..utils.exceptions import ExifToolNotFoundError, ExifToolError
from .time_calculator import TimeCalculator

logger = logging.getLogger(__name__)


class ExifHandler:
    """Handles all ExifTool operations with caching and pooling"""

    def __init__(self, pool_size: int = 3):
        self.exiftool_path = self._find_exiftool()
        # Use pool instead of single process
        self.exiftool_pool = ExifToolProcessPool(pool_size=pool_size)
        # Initialize cache as None first
        self._cache = None

    def _find_exiftool(self) -> str:
        """Find ExifTool executable"""
        if shutil.which("exiftool"):
            return "exiftool"

        # Common Windows installation locations
        common_paths = [
            r"C:\Program Files\ExifTool\exiftool.exe",
            r"C:\ExifTool\exiftool.exe",
            r"C:\Windows\exiftool.exe",
            os.path.expanduser(r"~\AppData\Local\ExifTool\exiftool.exe")
        ]

        for path in common_paths:
            if os.path.isfile(path):
                return path

        raise ExifToolNotFoundError(
            "ExifTool not found. Please install from https://exiftool.org\n"
            "and ensure it's in your PATH or installed in a standard location."
        )

    def read_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read all metadata from a file"""
        try:
            logger.debug(f"Reading metadata for {file_path}")
            with self.exiftool_pool.get_process() as process:
                metadata = process.read_metadata(file_path)
            logger.debug(f"Parsed metadata keys: {list(metadata.keys())}")
            return metadata
        except Exception as e:
            logger.error(f"Error reading metadata for {file_path}: {str(e)}")
            raise ExifToolError(f"Error reading metadata: {str(e)}")

    def get_datetime_fields(self, file_path: str) -> Dict[str, Optional[datetime]]:
        """Get all datetime fields from a file"""
        metadata = self.read_metadata(file_path)
        datetime_fields = {}

        for key, value in metadata.items():
            if any(date_key in key.lower() for date_key in ['date', 'time']) and value:
                parsed_date = TimeCalculator.parse_datetime_naive(str(value))
                datetime_fields[key] = parsed_date

        return datetime_fields

    def update_datetime_field(self, file_path: str, field_name: str, value: datetime) -> bool:
        """Update a specific datetime field"""
        fields = {field_name: value}
        return self.update_all_datetime_fields(file_path, fields)

    def update_all_datetime_fields(self, file_path: str, fields: Dict[str, datetime]) -> bool:
        """Update multiple datetime fields at once"""
        try:
            logger.info(f"Updating {len(fields)} datetime fields in {file_path}")
            with self.exiftool_pool.get_process() as process:
                success = process.update_datetime_fields(file_path, fields)
            return success
        except Exception as e:
            logger.error(f"Error updating datetime fields: {str(e)}")
            raise ExifToolError(f"Error updating datetime fields: {str(e)}")

    def get_camera_info(self, file_path: str) -> Dict[str, str]:
        """Get camera make and model"""
        metadata = self.read_metadata(file_path)
        return {
            'make': metadata.get('Make', '').strip(),
            'model': metadata.get('Model', '').strip()
        }

    def read_metadata_batch(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Read metadata from multiple files in parallel"""
        return self.exiftool_pool.read_metadata_batch_parallel(file_paths)

    def get_comprehensive_metadata(self, file_path: str) -> str:
        """Get comprehensive metadata from a file using all ExifTool flags"""
        try:
            logger.debug(f"Getting comprehensive metadata for {file_path}")
            with self.exiftool_pool.get_process() as process:
                metadata_text = process.get_comprehensive_metadata(file_path)
            return metadata_text
        except Exception as e:
            logger.error(f"Error getting comprehensive metadata for {file_path}: {str(e)}")
            raise ExifToolError(f"Error getting comprehensive metadata: {str(e)}")
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'exiftool_pool'):
            self.exiftool_pool.shutdown()