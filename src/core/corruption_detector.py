# Detect and classify file corruption

import os
import tempfile
import subprocess
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CorruptionType(Enum):
    HEALTHY = "healthy"
    EXIF_STRUCTURE = "exif_structure"
    MAKERNOTES = "makernotes"
    SEVERE_CORRUPTION = "severe_corruption"
    FILESYSTEM_ONLY = "filesystem_only"


@dataclass
class CorruptionInfo:
    file_path: str
    corruption_type: CorruptionType
    error_message: str
    is_repairable: bool
    estimated_success_rate: float  # 0.0 to 1.0


class CorruptionDetector:
    """Detect and classify file corruption types"""

    def __init__(self, exiftool_path: str = "exiftool"):
        self.exiftool_path = exiftool_path

    def scan_files_for_corruption(self, file_paths: List[str]) -> Dict[str, CorruptionInfo]:
        """Scan multiple files for corruption and classify them"""
        results = {}

        logger.info(f"Scanning {len(file_paths)} files for corruption...")

        for file_path in file_paths:
            try:
                corruption_info = self._detect_single_file_corruption(file_path)
                results[file_path] = corruption_info

                if corruption_info.corruption_type != CorruptionType.HEALTHY:
                    logger.debug(
                        f"Corruption detected in {os.path.basename(file_path)}: {corruption_info.corruption_type.value}")

            except Exception as e:
                logger.error(f"Error scanning {os.path.basename(file_path)}: {e}")
                # Default to severe corruption if we can't even scan it
                results[file_path] = CorruptionInfo(
                    file_path=file_path,
                    corruption_type=CorruptionType.SEVERE_CORRUPTION,
                    error_message=f"Scanning error: {str(e)}",
                    is_repairable=False,
                    estimated_success_rate=0.0
                )

        return results

    def _detect_single_file_corruption(self, file_path: str) -> CorruptionInfo:
        """Detect corruption in a single file"""

        # Test 1: Try basic metadata read
        basic_read_success, basic_error = self._test_basic_metadata_read(file_path)

        if basic_read_success:
            # Test 2: Try datetime update (most sensitive test)
            update_success, update_error = self._test_datetime_update(file_path)

            if update_success:
                return CorruptionInfo(
                    file_path=file_path,
                    corruption_type=CorruptionType.HEALTHY,
                    error_message="",
                    is_repairable=True,
                    estimated_success_rate=1.0
                )
            else:
                # Can read but can't update - classify the update error
                return self._classify_update_error(file_path, update_error)
        else:
            # Can't even read metadata - severe corruption
            return CorruptionInfo(
                file_path=file_path,
                corruption_type=CorruptionType.SEVERE_CORRUPTION,
                error_message=basic_error,
                is_repairable=False,
                estimated_success_rate=0.1
            )

    def _test_basic_metadata_read(self, file_path: str) -> Tuple[bool, str]:
        """Test if we can read basic metadata from file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            cmd = [self.exiftool_path, '-json', '-charset', 'filename=utf8', '-@', arg_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout.strip():
                return True, ""
            else:
                return False, result.stderr or "No metadata readable"

        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    def _test_datetime_update(self, file_path: str) -> Tuple[bool, str]:
        """Test if we can update datetime fields (most sensitive corruption test)"""
        # Create a backup first
        backup_path = file_path + ".corruption_test_backup"

        try:
            import shutil
            shutil.copy2(file_path, backup_path)

            # Try a simple datetime update
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path + '\n')
                arg_file_path = arg_file.name

            try:
                cmd = [
                    self.exiftool_path,
                    '-overwrite_original',
                    '-ignoreMinorErrors',
                    '-m',
                    '-CreateDate=2020:01:01 12:00:00',
                    '-@', arg_file_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                success = "1 image files updated" in result.stdout or "1 files updated" in result.stdout
                error_msg = result.stderr if result.stderr else result.stdout

                return success, error_msg

            finally:
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)

        except Exception as e:
            return False, str(e)
        finally:
            # Always restore backup
            if os.path.exists(backup_path):
                try:
                    import shutil
                    shutil.move(backup_path, file_path)
                except Exception as restore_error:
                    logger.error(f"Failed to restore backup for {file_path}: {restore_error}")

    def _classify_update_error(self, file_path: str, error_message: str) -> CorruptionInfo:
        """Classify the type of corruption based on update error message"""

        error_lower = error_message.lower()

        # MakerNotes issues
        if "makernotes" in error_lower or "offsets may be incorrect" in error_lower:
            return CorruptionInfo(
                file_path=file_path,
                corruption_type=CorruptionType.MAKERNOTES,
                error_message=error_message,
                is_repairable=True,
                estimated_success_rate=0.9
            )

        # EXIF structure corruption
        elif any(term in error_lower for term in [
            "stripoffsets", "ifd0", "ifd1", "exif structure",
            "invalid exif", "bad exif", "corrupt exif"
        ]):
            return CorruptionInfo(
                file_path=file_path,
                corruption_type=CorruptionType.EXIF_STRUCTURE,
                error_message=error_message,
                is_repairable=True,
                estimated_success_rate=0.7
            )

        # Files with only filesystem dates (no EXIF)
        elif "no exif" in error_lower or "no metadata" in error_lower:
            return CorruptionInfo(
                file_path=file_path,
                corruption_type=CorruptionType.FILESYSTEM_ONLY,
                error_message=error_message,
                is_repairable=True,
                estimated_success_rate=0.3  # Can add basic EXIF structure
            )

        # Severe/unknown corruption
        else:
            return CorruptionInfo(
                file_path=file_path,
                corruption_type=CorruptionType.SEVERE_CORRUPTION,
                error_message=error_message,
                is_repairable=True,
                estimated_success_rate=0.2
            )

    def get_corruption_summary(self, corruption_results: Dict[str, CorruptionInfo]) -> Dict[str, any]:
        """Generate summary statistics for corruption scan results"""

        healthy_count = 0
        repairable_count = 0
        unrepairable_count = 0
        corruption_types = {}

        for corruption_info in corruption_results.values():
            if corruption_info.corruption_type == CorruptionType.HEALTHY:
                healthy_count += 1
            elif corruption_info.is_repairable:
                repairable_count += 1
            else:
                unrepairable_count += 1

            # Count by type
            type_name = corruption_info.corruption_type.value
            corruption_types[type_name] = corruption_types.get(type_name, 0) + 1

        return {
            'total_files': len(corruption_results),
            'healthy_files': healthy_count,
            'repairable_files': repairable_count,
            'unrepairable_files': unrepairable_count,
            'corruption_types': corruption_types,
            'has_corruption': (repairable_count + unrepairable_count) > 0
        }