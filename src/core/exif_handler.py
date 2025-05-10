import subprocess
import json
import shutil
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dateutil import parser
from ..utils.exceptions import ExifToolNotFoundError, ExifToolError
from .time_calculator import TimeCalculator

class ExifHandler:
    """Handles all ExifTool operations"""

    def __init__(self):
        self.exiftool_path = self._find_exiftool()

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
        """Read all metadata from a file"""
        try:
            cmd = [self.exiftool_path, '-json', '-time:all', '-make', '-model', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)[0]
            return metadata
        except subprocess.CalledProcessError as e:
            raise ExifToolError(f"Error reading metadata: {e.stderr}")
        except (json.JSONDecodeError, IndexError) as e:
            raise ExifToolError(f"Error parsing metadata: {e}")

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
        """Update a specific datetime field"""
        try:
            # Format datetime for ExifTool
            formatted_value = value.strftime("%Y:%m:%d %H:%M:%S")
            cmd = [
                self.exiftool_path,
                f'-{field_name}={formatted_value}',
                '-overwrite_original',
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise ExifToolError(f"Error updating {field_name}: {e.stderr}")

    def update_all_datetime_fields(self, file_path: str, fields: Dict[str, datetime]) -> bool:
        """Update multiple datetime fields at once"""
        try:
            cmd = [self.exiftool_path, '-overwrite_original']

            for field_name, value in fields.items():
                formatted_value = value.strftime("%Y:%m:%d %H:%M:%S")
                cmd.append(f'-{field_name}={formatted_value}')

            cmd.append(file_path)
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            raise ExifToolError(f"Error updating datetime fields: {e.stderr}")

    def get_camera_info(self, file_path: str) -> Dict[str, str]:
        """Get camera make and model"""
        metadata = self.read_metadata(file_path)
        return {
            'make': metadata.get('Make', '').strip(),
            'model': metadata.get('Model', '').strip()
        }