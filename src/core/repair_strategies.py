# - Repair strategies with caching

import os
import json
import tempfile
import subprocess
import shutil
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
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


class RepairStrategyCache:
    """Cache successful repair strategies for different corruption types"""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        """Load cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load repair cache: {e}")
        return {}

    def save_cache(self):
        """Save cache to file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save repair cache: {e}")

    def get_best_strategy(self, corruption_type: CorruptionType) -> Optional[RepairStrategy]:
        """Get the best known strategy for a corruption type"""
        type_key = corruption_type.value
        if type_key in self.cache:
            strategy_name = self.cache[type_key].get('best_strategy')
            if strategy_name:
                try:
                    return RepairStrategy(strategy_name)
                except ValueError:
                    pass
        return None

    def record_success(self, corruption_type: CorruptionType, strategy: RepairStrategy):
        """Record a successful repair strategy"""
        type_key = corruption_type.value
        if type_key not in self.cache:
            self.cache[type_key] = {'best_strategy': None, 'success_count': {}}

        strategy_name = strategy.value
        success_counts = self.cache[type_key]['success_count']
        success_counts[strategy_name] = success_counts.get(strategy_name, 0) + 1

        # Update best strategy based on success count
        best_strategy = max(success_counts.items(), key=lambda x: x[1])[0]
        self.cache[type_key]['best_strategy'] = best_strategy

        self.save_cache()


class FileRepairer:
    """Repair corrupted files using multiple strategies"""

    def __init__(self, exiftool_path: str = "exiftool", cache_file: str = None):
        self.exiftool_path = exiftool_path
        self.cache = RepairStrategyCache(cache_file or self._get_default_cache_file())

        # Define repair strategies in order of preference
        self.strategies = [
            RepairStrategy.SAFEST,
            RepairStrategy.THOROUGH,
            RepairStrategy.AGGRESSIVE,
            RepairStrategy.FILESYSTEM_ONLY
        ]

    def _get_default_cache_file(self) -> str:
        """Get default cache file location"""
        from pathlib import Path
        config_dir = Path(os.environ.get('APPDATA', '')) / 'PhotoTimeAligner'
        return str(config_dir / 'repair_cache.json')

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

        # Get strategy order (cached strategy first if available)
        strategy_order = self._get_strategy_order(corruption_type)

        # Try each strategy until one works
        for strategy in strategy_order:
            logger.debug(f"Trying {strategy.value} repair on {os.path.basename(file_path)}")

            try:
                # Restore from backup before each attempt
                shutil.copy2(backup_path, file_path)

                # Apply repair strategy
                repair_success, repair_error = self._apply_repair_strategy(file_path, strategy)

                if repair_success:
                    # Verify the repair worked
                    verification_success = self._verify_repair(file_path)

                    if verification_success:
                        logger.info(f"Successfully repaired {os.path.basename(file_path)} using {strategy.value}")

                        # Cache this success
                        self.cache.record_success(corruption_type, strategy)

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
        """Create backup of file before repair"""
        try:
            os.makedirs(backup_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            backup_path = os.path.join(backup_dir, f"{filename}_backup")

            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")

            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup for {file_path}: {e}")
            return None

    def _get_strategy_order(self, corruption_type: CorruptionType) -> List[RepairStrategy]:
        """Get strategy order with cached strategy first"""
        cached_strategy = self.cache.get_best_strategy(corruption_type)

        if cached_strategy and cached_strategy in self.strategies:
            # Put cached strategy first, then others
            strategy_order = [cached_strategy]
            strategy_order.extend([s for s in self.strategies if s != cached_strategy])
            logger.debug(f"Using cached strategy {cached_strategy.value} first for {corruption_type.value}")
            return strategy_order
        else:
            return self.strategies.copy()

    def _apply_repair_strategy(self, file_path: str, strategy: RepairStrategy) -> Tuple[bool, str]:
        """Apply a specific repair strategy"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            if strategy == RepairStrategy.SAFEST:
                return self._safest_repair(file_path, arg_file_path)
            elif strategy == RepairStrategy.THOROUGH:
                return self._thorough_repair(file_path, arg_file_path)
            elif strategy == RepairStrategy.AGGRESSIVE:
                return self._aggressive_repair(file_path, arg_file_path)
            elif strategy == RepairStrategy.FILESYSTEM_ONLY:
                return True, "Filesystem-only (no repair needed)"  # Always "succeeds"
            else:
                return False, f"Unknown strategy: {strategy}"

        finally:
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    def _safest_repair(self, file_path: str, arg_file_path: str) -> Tuple[bool, str]:
        """Safest repair - minimal changes"""
        cmd = [
            self.exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',
            '-m',
            '-@', arg_file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        success = result.returncode == 0 and ("1 image files updated" in result.stdout or result.stdout.strip() == "")
        return success, result.stderr or result.stdout

    def _thorough_repair(self, file_path: str, arg_file_path: str) -> Tuple[bool, str]:
        """Thorough repair - rebuild metadata structure"""
        # Step 1: Clear all metadata
        cmd1 = [
            self.exiftool_path,
            '-all=',
            '-overwrite_original',
            '-@', arg_file_path
        ]

        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=60)
        if result1.returncode != 0:
            return False, f"Clear metadata failed: {result1.stderr}"

        # Step 2: Restore from backup data
        cmd2 = [
            self.exiftool_path,
            '-tagsfromfile', file_path,
            '-all:all',
            '-unsafe',
            '-overwrite_original',
            '-@', arg_file_path
        ]

        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        success = result2.returncode == 0
        return success, result2.stderr or result2.stdout

    def _aggressive_repair(self, file_path: str, arg_file_path: str) -> Tuple[bool, str]:
        """Aggressive repair - force rebuild with structure fixes"""
        # Step 1: Force clear all metadata
        cmd1 = [
            self.exiftool_path,
            '-all=',
            '-f',  # Force
            '-overwrite_original',
            '-@', arg_file_path
        ]

        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=60)

        # Step 2: Add minimal EXIF structure
        cmd2 = [
            self.exiftool_path,
            '-EXIF:ColorSpace=1',
            '-EXIF:ExifVersion=0232',
            '-overwrite_original',
            '-@', arg_file_path
        ]

        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=60)
        success = result2.returncode == 0
        return success, result2.stderr or result2.stdout

    def _verify_repair(self, file_path: str) -> bool:
        """Verify that repair was successful by testing datetime update"""
        backup_path = file_path + ".verify_backup"

        try:
            # Create backup for verification test
            shutil.copy2(file_path, backup_path)

            # Try updating a datetime field
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
                arg_file.write(file_path + '\n')
                arg_file_path = arg_file.name

            try:
                cmd = [
                    self.exiftool_path,
                    '-overwrite_original',
                    '-ignoreMinorErrors',
                    '-m',
                    '-CreateDate=2021:06:15 14:30:00',
                    '-@', arg_file_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                success = "1 image files updated" in result.stdout or "1 files updated" in result.stdout

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