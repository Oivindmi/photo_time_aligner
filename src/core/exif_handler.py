import shutil  # Make sure this is imported at the top
from .exiftool_process import ExifToolProcess
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
    """Handles all ExifTool operations"""

    def __init__(self):
        self.exiftool_path = self._find_exiftool()
        # Create the process with the path (which may be None)
        # The process will find exiftool if path is None
        self.exiftool_process = ExifToolProcess(self.exiftool_path)
        # Start the process during initialization
        self.exiftool_process.start()

    def _find_exiftool(self) -> str:
        """Find ExifTool executable"""
        # Check if exiftool is in PATH
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
        """Read all metadata from a file using persistent ExifTool process"""
        try:
            logger.debug(f"Reading metadata for {file_path}")
            metadata = self.exiftool_process.read_metadata(file_path)
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
                # Use TimeCalculator to parse naive datetime
                parsed_date = TimeCalculator.parse_datetime_naive(str(value))
                datetime_fields[key] = parsed_date

        return datetime_fields

    def update_datetime_field(self, file_path: str, field_name: str, value: datetime) -> bool:
        """Update a specific datetime field using persistent ExifTool process"""
        try:
            logger.debug(f"Updating {field_name} to {value} in {file_path}")
            fields = {field_name: value}
            return self.exiftool_process.update_datetime_fields(file_path, fields)
        except Exception as e:
            logger.error(f"Error updating {field_name}: {str(e)}")
            raise ExifToolError(f"Error updating {field_name}: {str(e)}")

    def update_all_datetime_fields(self, file_path: str, fields: Dict[str, datetime]) -> bool:
        """Update multiple datetime fields at once using persistent ExifTool process"""
        try:
            logger.info(f"Updating {len(fields)} datetime fields in {file_path}")
            return self.exiftool_process.update_datetime_fields(file_path, fields)
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

    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'exiftool_process') and self.exiftool_process:
            self.exiftool_process.stop()