# src/core/repair_strategies.py - Robust repair strategies without caching

import os
import tempfile
import subprocess
import shutil
import logging
from typing import List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .corruption_detector import CorruptionType

logger = logging.getLogger(__name__)


class RepairStrategy(Enum):
    SAFEST = "safest"
    THOROUGH = "thorough"
    AGGRESSIVE = "aggressive"
    FILESYSTEM_ONLY = "filesystem_only"


@dataclass
class RepairResult:
    strategy_used: RepairStrategy
    success: bool
    error_message: str
    verification_passed: bool


class FileRepairer:
    """Repair corrupted files using robust single-step strategies"""

    def __init__(self, exiftool_path: str = "exiftool"):
        self.exiftool_path = exiftool_path

        # Define repair strategies in order of preference
        self.strategies = [
            RepairStrategy.SAFEST,
            RepairStrategy.THOROUGH,
            RepairStrategy.AGGRESSIVE,
            RepairStrategy.FILESYSTEM_ONLY
        ]

    def repair_file(self, file_path: str, corruption_type: CorruptionType,
                    backup_dir: str) -> RepairResult:
        """Repair a single file using best available strategy"""

        logger.info(f"Attempting repair of {os.path.basename(file_path)} (type: {corruption_type.value})")

        # Create backup
        backup_path = self._create_backup(file_path, backup_dir)
        if not backup_path:
            return RepairResult(
                strategy_used=RepairStrategy.SAFEST,
                success=False,
                error_message="Failed to create backup",
                verification_passed=False
            )

        # Try each strategy in order until one works
        for strategy in self.strategies:
            logger.debug(f"Trying {strategy.value} repair on {os.path.basename(file_path)}")

            try:
                # Restore from backup before each attempt
                shutil.copy2(backup_path, file_path)

                # Apply repair strategy (single-step, robust approach)
                repair_success, repair_error = self._apply_single_step_repair(file_path, strategy)

                if repair_success:
                    # Verify the repair worked
                    verification_success = self._verify_repair(file_path)

                    if verification_success:
                        logger.info(f"Successfully repaired {os.path.basename(file_path)} using {strategy.value}")

                        return RepairResult(
                            strategy_used=strategy,
                            success=True,
                            error_message="",
                            verification_passed=True
                        )
                    else:
                        logger.debug(f"{strategy.value} repair completed but verification failed")
                        continue
                else:
                    logger.debug(f"{strategy.value} repair failed: {repair_error}")
                    continue

            except Exception as e:
                logger.debug(f"Exception during {strategy.value} repair: {e}")
                continue

        # All strategies failed - restore backup and return failure
        try:
            shutil.copy2(backup_path, file_path)
        except Exception as e:
            logger.error(f"Failed to restore backup for {file_path}: {e}")

        return RepairResult(
            strategy_used=RepairStrategy.FILESYSTEM_ONLY,
            success=False,
            error_message="All repair strategies failed",
            verification_passed=False
        )

    def _create_backup(self, file_path: str, backup_dir: str) -> Optional[str]:
        """Create backup of file before repair with Windows path handling"""
        import tempfile  # Import at the top to avoid scoping issues

        try:
            # Normalize the path separators
            file_path = os.path.normpath(file_path)
            backup_dir = os.path.normpath(backup_dir)

            # Ensure backup directory exists
            os.makedirs(backup_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)

            # Truncate name if too long (Windows has 255 char limit for filename)
            max_name_length = 200  # Leave room for _backup and extension
            if len(name) > max_name_length:
                name = name[:max_name_length]
                logger.debug(f"Truncated long filename: {filename} -> {name}{ext}")

            backup_filename = f"{name}_backup{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)

            # Check if backup path is too long (Windows MAX_PATH is typically 260)
            if len(backup_path) > 250:  # Leave some margin
                # Create shorter backup filename
                short_name = name[:50]  # Very short name
                backup_filename = f"{short_name}_backup{ext}"
                backup_path = os.path.join(backup_dir, backup_filename)
                logger.debug(f"Using shortened backup path: {backup_path}")

            # Handle file already exists case
            counter = 1
            original_backup_path = backup_path
            while os.path.exists(backup_path):
                name_part, ext_part = os.path.splitext(original_backup_path)
                backup_path = f"{name_part}_{counter}{ext_part}"
                counter += 1
                if counter > 100:  # Prevent infinite loop
                    raise Exception("Too many backup files exist")

            # Use shutil.copy2 which handles Unicode and metadata better
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {os.path.basename(backup_path)}")

            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup for {os.path.basename(file_path)}: {e}")

            # Try alternative backup location if original fails
            try:
                temp_backup_dir = tempfile.mkdtemp(prefix="photo_repair_backup_")

                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)

                # Use simple name for temp backup
                backup_filename = f"backup_{hash(file_path) % 10000}{ext}"
                backup_path = os.path.join(temp_backup_dir, backup_filename)

                shutil.copy2(file_path, backup_path)
                logger.warning(f"Created backup in temp directory: {temp_backup_dir}")

                return backup_path

            except Exception as e2:
                logger.error(f"Failed to create temp backup: {e2}")
                return None

    def _apply_single_step_repair(self, file_path: str, strategy: RepairStrategy) -> Tuple[bool, str]:
        """Apply repair strategy using single, robust command"""

        # Create argument file for Unicode safety (like your existing code)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            if strategy == RepairStrategy.SAFEST:
                return self._safest_single_step(arg_file_path)
            elif strategy == RepairStrategy.THOROUGH:
                return self._thorough_single_step(arg_file_path)
            elif strategy == RepairStrategy.AGGRESSIVE:
                return self._aggressive_single_step(arg_file_path)
            elif strategy == RepairStrategy.FILESYSTEM_ONLY:
                return True, "Filesystem-only (no repair needed)"
            else:
                return False, f"Unknown strategy: {strategy}"

        finally:
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    def _safest_single_step(self, arg_file_path: str) -> Tuple[bool, str]:
        """Safest repair - single command, minimal changes"""
        # Just try to read and rewrite the file with error handling
        cmd = [
            self.exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',
            '-m',
            '-charset', 'filename=utf8',
            '-all=',  # Clear problematic metadata
            '-@', arg_file_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            success = result.returncode == 0 and (
                        "1 image files updated" in result.stdout or "updated" in result.stdout.lower())
            return success, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def _thorough_single_step(self, arg_file_path: str) -> Tuple[bool, str]:
        """Thorough repair - single command to rebuild structure"""
        # Clear all metadata in one robust operation
        cmd = [
            self.exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',
            '-m',
            '-f',  # Force operation
            '-charset', 'filename=utf8',
            '-all=',  # Remove all metadata
            '-@', arg_file_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            success = result.returncode == 0
            return success, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)

    def _aggressive_single_step(self, arg_file_path: str) -> Tuple[bool, str]:
        """Aggressive repair - force clear everything and add minimal structure"""
        # First clear everything forcefully
        cmd1 = [
            self.exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',
            '-m',
            '-f',  # Force
            '-G',  # Ignore structure errors
            '-charset', 'filename=utf8',
            '-all=',  # Clear all metadata
            '-@', arg_file_path
        ]

        try:
            result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=60)
            if result1.returncode != 0:
                return False, f"Clear step failed: {result1.stderr}"

            # Then add minimal EXIF structure
            cmd2 = [
                self.exiftool_path,
                '-overwrite_original',
                '-charset', 'filename=utf8',
                '-EXIF:ExifVersion=0232',  # Add minimal EXIF
                '-@', arg_file_path
            ]

            result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
            success = result2.returncode == 0
            return success, result2.stderr or result2.stdout

        except Exception as e:
            return False, str(e)

    def _verify_repair(self, file_path: str) -> bool:
        """Verify repair by testing datetime update with path handling"""
        import tempfile  # Import at the top to avoid scoping issues

        # Create backup path with better handling
        try:
            # Use a simpler backup name to avoid path issues
            backup_dir = os.path.dirname(file_path)
            backup_filename = f"verify_temp_{hash(file_path) % 10000}.bak"
            backup_path = os.path.join(backup_dir, backup_filename)

            # If backup path is still too long, use temp directory
            if len(backup_path) > 250:
                temp_dir = tempfile.gettempdir()
                backup_path = os.path.join(temp_dir, backup_filename)

        except Exception:
            # Fallback to simple temp file
            backup_path = tempfile.mktemp(suffix=".bak", prefix="verify_")

        try:
            # Create backup for verification test
            shutil.copy2(file_path, backup_path)

            # Try updating a datetime field using same approach as main app
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path + '\n')
                arg_file_path = arg_file.name

            try:
                cmd = [
                    self.exiftool_path,
                    '-overwrite_original',
                    '-ignoreMinorErrors',
                    '-m',
                    '-charset', 'filename=utf8',
                    '-CreateDate=2021:06:15 14:30:00',
                    '-@', arg_file_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                success = "1 image files updated" in result.stdout or "1 files updated" in result.stdout

                logger.debug(f"Verification result: {success}, output: {result.stdout}")
                return success

            finally:
                if os.path.exists(arg_file_path):
                    os.remove(arg_file_path)

        except Exception as e:
            logger.debug(f"Verification test failed: {e}")
            return False
        finally:
            # Restore from backup after verification test
            if os.path.exists(backup_path):
                try:
                    shutil.move(backup_path, file_path)
                except Exception as e:
                    logger.error(f"Failed to restore after verification: {e}")
                    # Try copying instead of moving
                    try:
                        shutil.copy2(backup_path, file_path)
                        os.remove(backup_path)
                    except Exception as e2:
                        logger.error(f"Failed to copy restore: {e2}")