import subprocess
import json
import shutil
import os
import logging
import tempfile
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
        """Read all metadata from a file using argument file approach"""
        try:
            # Create a temporary argument file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path)
                arg_file_path = arg_file.name

            try:
                cmd = [
                    self.exiftool_path,
                    '-json',
                    '-charset', 'filename=utf8',
                    '-time:all',
                    '-make',
                    '-model',
                    '-@', arg_file_path
                ]

                logger.debug(f"ExifTool command: {' '.join(cmd)}")
                logger.debug(f"Processing file: {file_path}")

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)

                logger.debug(f"ExifTool stdout length: {len(result.stdout)}")
                logger.debug(f"ExifTool stderr: {result.stderr}")

                if not result.stdout.strip():
                    raise ExifToolError("ExifTool returned empty output")

                metadata = json.loads(result.stdout)[0]
                logger.debug(f"Parsed metadata keys: {list(metadata.keys())}")

                return metadata
            finally:
                # Clean up the argument file
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)
                    logger.debug(f"Cleaned up argument file: {arg_file_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"ExifTool error: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise ExifToolError(f"Error reading metadata: {e.stderr}")
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Error parsing metadata: {e}")
            logger.error(f"stdout was: {result.stdout if 'result' in locals() else 'Not available'}")
            raise ExifToolError(f"Error parsing metadata: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in read_metadata: {e}")
            raise

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
        """Update a specific datetime field using argument file approach"""
        try:
            # Create a temporary argument file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path)
                arg_file_path = arg_file.name

            try:
                # Format datetime for ExifTool
                formatted_value = value.strftime("%Y:%m:%d %H:%M:%S")
                cmd = [
                    self.exiftool_path,
                    f'-{field_name}={formatted_value}',
                    '-overwrite_original',
                    '-charset', 'filename=utf8',
                    '-@', arg_file_path
                ]

                logger.debug(f"Updating {field_name} to {formatted_value} in {file_path}")
                logger.debug(f"ExifTool command: {' '.join(cmd)}")

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.debug(f"Update successful for {field_name}")
                return True
            finally:
                # Clean up the argument file
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)
                    logger.debug(f"Cleaned up argument file: {arg_file_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error updating {field_name}: {e.stderr}")
            raise ExifToolError(f"Error updating {field_name}: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error in update_datetime_field: {e}")
            raise

    def update_all_datetime_fields(self, file_path: str, fields: Dict[str, datetime]) -> bool:
        """Update multiple datetime fields at once using argument file approach"""
        try:
            # Create a temporary argument file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path)
                arg_file_path = arg_file.name

            try:
                cmd = [self.exiftool_path, '-overwrite_original', '-charset', 'filename=utf8']

                for field_name, value in fields.items():
                    formatted_value = value.strftime("%Y:%m:%d %H:%M:%S")
                    cmd.append(f'-{field_name}={formatted_value}')
                    logger.debug(f"Queuing update for {field_name}: {formatted_value}")

                cmd.extend(['-@', arg_file_path])

                logger.debug(f"Batch update command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.info(f"Successfully updated {len(fields)} datetime fields in {file_path}")
                return True
            finally:
                # Clean up the argument file
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)
                    logger.debug(f"Cleaned up argument file: {arg_file_path}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Error updating datetime fields: {e.stderr}")
            raise ExifToolError(f"Error updating datetime fields: {e.stderr}")
        except Exception as e:
            logger.error(f"Unexpected error in update_all_datetime_fields: {e}")
            raise

    def get_camera_info(self, file_path: str) -> Dict[str, str]:
        """Get camera make and model"""
        metadata = self.read_metadata(file_path)
        return {
            'make': metadata.get('Make', '').strip(),
            'model': metadata.get('Model', '').strip()
        }