"""
Assertion helpers for test validation.

Provides utilities for verifying metadata changes, file integrity, and test outcomes.
"""

from pathlib import Path
from datetime import datetime
import json
import subprocess
from typing import Dict, Any, Optional


class AssertionHelper:
    """Helper class for common test assertions."""

    @staticmethod
    def assert_file_exists(file_path: Path, message: str = None):
        """Assert that a file exists."""
        assert file_path.exists(), message or f"File not found: {file_path}"

    @staticmethod
    def assert_file_readable(file_path: Path):
        """Assert that a file is readable."""
        assert file_path.is_file(), f"Not a file: {file_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {file_path}"

    @staticmethod
    def assert_exif_datetime(file_path: Path, expected_datetime: datetime = None):
        """
        Assert that a file has valid EXIF datetime.

        Args:
            file_path: Path to media file
            expected_datetime: Expected datetime value (optional)
        """
        try:
            result = subprocess.run(
                ["exiftool", "-json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise AssertionError(f"ExifTool failed: {result.stderr}")

            data = json.loads(result.stdout)
            if not data or len(data) == 0:
                raise AssertionError(f"No EXIF data found in {file_path}")

            exif_data = data[0]

            # Check for datetime fields
            datetime_fields = [
                "CreateDate", "DateTimeOriginal", "ModifyDate",
                "CreationDate", "MediaCreateDate"
            ]

            found_datetime = None
            for field in datetime_fields:
                if field in exif_data and exif_data[field]:
                    found_datetime = exif_data[field]
                    break

            assert found_datetime, f"No datetime field found in {file_path}"

            if expected_datetime:
                # Parse and compare datetime strings
                assert expected_datetime.isoformat() in str(found_datetime) or \
                       expected_datetime.strftime("%Y:%m:%d") in str(found_datetime), \
                       f"Datetime mismatch: expected {expected_datetime}, got {found_datetime}"

        except subprocess.TimeoutExpired:
            raise AssertionError(f"ExifTool timeout for {file_path}")
        except json.JSONDecodeError as e:
            raise AssertionError(f"Failed to parse EXIF data from {file_path}: {e}")

    @staticmethod
    def assert_metadata_updated(file_path: Path, field_name: str, expected_value: str):
        """
        Assert that a specific metadata field was updated.

        Args:
            file_path: Path to media file
            field_name: Name of EXIF field
            expected_value: Expected field value
        """
        try:
            result = subprocess.run(
                ["exiftool", "-json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise AssertionError(f"ExifTool failed: {result.stderr}")

            data = json.loads(result.stdout)
            if not data or len(data) == 0:
                raise AssertionError(f"No EXIF data found in {file_path}")

            exif_data = data[0]

            assert field_name in exif_data, \
                f"Field '{field_name}' not found in {file_path}. Available fields: {list(exif_data.keys())}"

            actual_value = exif_data[field_name]
            assert str(actual_value) == str(expected_value), \
                f"Field mismatch: expected '{expected_value}', got '{actual_value}'"

        except subprocess.TimeoutExpired:
            raise AssertionError(f"ExifTool timeout for {file_path}")
        except json.JSONDecodeError as e:
            raise AssertionError(f"Failed to parse EXIF data from {file_path}: {e}")

    @staticmethod
    def assert_backup_exists(file_path: Path) -> Path:
        """
        Assert that a backup file exists for the given file.

        Args:
            file_path: Original file path

        Returns:
            Path: Path to backup file

        Raises:
            AssertionError: If backup doesn't exist
        """
        name, ext = file_path.stem, file_path.suffix
        backup_path = file_path.parent / f"{name}_backup{ext}"

        assert backup_path.exists(), f"Backup not found: {backup_path}"
        assert backup_path.stat().st_size > 0, f"Backup is empty: {backup_path}"

        return backup_path

    @staticmethod
    def assert_files_identical(file1: Path, file2: Path):
        """
        Assert that two files have identical content.

        Args:
            file1: First file path
            file2: Second file path

        Raises:
            AssertionError: If files differ
        """
        assert file1.exists(), f"File not found: {file1}"
        assert file2.exists(), f"File not found: {file2}"

        size1 = file1.stat().st_size
        size2 = file2.stat().st_size

        assert size1 == size2, f"File sizes differ: {size1} vs {size2}"

        # Compare content
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            content1 = f1.read()
            content2 = f2.read()

        assert content1 == content2, f"File content differs: {file1} vs {file2}"

    @staticmethod
    def assert_corruption_detected(file_path: Path, corruption_type: str):
        """
        Assert that a file is detected as having a specific corruption type.

        Args:
            file_path: Path to potentially corrupted file
            corruption_type: Expected corruption type (EXIF_STRUCTURE, MAKERNOTES, etc.)

        Note:
            This is a placeholder that will use CorruptionDetector when available.
        """
        # Will be implemented when CorruptionDetector tests are written
        pass


class PerformanceAssertion:
    """Helper class for performance assertions."""

    @staticmethod
    def assert_within_time(elapsed_seconds: float, max_seconds: float, test_name: str = ""):
        """
        Assert that operation completed within time limit.

        Args:
            elapsed_seconds: Actual elapsed time
            max_seconds: Maximum acceptable time
            test_name: Name of test for error message

        Raises:
            AssertionError: If elapsed time exceeds maximum
        """
        assert elapsed_seconds < max_seconds, \
            f"{test_name} took {elapsed_seconds:.2f}s, exceeds limit of {max_seconds:.2f}s"

    @staticmethod
    def assert_memory_bounded(memory_mb: float, max_memory_mb: float, test_name: str = ""):
        """
        Assert that memory usage stayed within bounds.

        Args:
            memory_mb: Actual memory usage in MB
            max_memory_mb: Maximum acceptable memory in MB
            test_name: Name of test for error message

        Raises:
            AssertionError: If memory exceeds limit
        """
        assert memory_mb < max_memory_mb, \
            f"{test_name} used {memory_mb:.1f}MB, exceeds limit of {max_memory_mb:.1f}MB"
