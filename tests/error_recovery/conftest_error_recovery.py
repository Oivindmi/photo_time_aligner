"""
Pytest configuration and fixtures for Phase D - Error Recovery Tests.

This module extends conftest.py with Phase D-specific fixtures for:
- Scaled corruption batches (50/200/500 files)
- Permission error simulation (Windows/POSIX)
- Backup and restore verification
- Partial failure recovery tracking
- Group restart behavior verification
"""

import os
import sys
import pytest
import tempfile
import shutil
import time
import psutil
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import timedelta
import subprocess
import hashlib

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import project modules
try:
    from src.core.exif_handler import ExifHandler
    from src.core.file_processor import FileProcessor
    from src.core.corruption_detector import CorruptionDetector, CorruptionType, CorruptionInfo
    from src.core.repair_strategies import FileRepairer, RepairResult
    from src.core.alignment_processor import AlignmentProcessor
    from tests.fixtures.helpers.media_generator import MediaGenerator
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")


# ============================================================================
# CONSTANTS
# ============================================================================

GROUP_SIZE = 60  # Matches file_processor.py GROUP_SIZE
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_MEDIA_DIR = FIXTURES_DIR / "sample_media"
CLEAN_MEDIA_DIR = SAMPLE_MEDIA_DIR / "clean"
CORRUPTED_MEDIA_DIR = SAMPLE_MEDIA_DIR / "corrupted"


# ============================================================================
# SCALE PARAMETRIZATION
# ============================================================================

@pytest.fixture(params=[50, 200, 500])
def scale_level(request):
    """
    Parametrized fixture for scale testing.

    Yields:
        int: File scale level (50, 200, or 500)
    """
    return request.param


@pytest.fixture
def batch_size(scale_level):
    """
    Batch size for current scale level.

    Returns:
        int: Number of files in batch
    """
    return scale_level


# ============================================================================
# CORRUPTION FILE FACTORY
# ============================================================================

class CorruptionFileFactory:
    """Factory for creating corrupted files at scale for testing."""

    def __init__(self, base_dir: Path, real_photo_file: Optional[Path] = None):
        """
        Initialize corruption factory.

        Args:
            base_dir: Base directory for creating test files
            real_photo_file: Path to real photo to use as template
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.real_photo_file = real_photo_file
        self.media_gen = MediaGenerator(self.base_dir)

    def create_mixed_corruption_batch(self, scale: int) -> Dict:
        """
        Create mixed batch with all 5 corruption types at specified scale.

        Distribution for scale=200:
        - 160 HEALTHY (80%)
        - 20 EXIF_STRUCTURE (10%)
        - 10 MAKERNOTES (5%)
        - 5 SEVERE_CORRUPTION (2.5%)
        - 5 FILESYSTEM_ONLY (2.5%)

        Args:
            scale: Total number of files to create

        Returns:
            Dict: {
                'healthy': [file_paths],
                'exif_structure': [file_paths],
                'makernotes': [file_paths],
                'severe_corruption': [file_paths],
                'filesystem_only': [file_paths],
                'all': [all_file_paths],
                'metadata': {file_path: CorruptionType}
            }
        """
        batch = {
            CorruptionType.HEALTHY: [],
            CorruptionType.EXIF_STRUCTURE: [],
            CorruptionType.MAKERNOTES: [],
            CorruptionType.SEVERE_CORRUPTION: [],
            CorruptionType.FILESYSTEM_ONLY: [],
        }

        # Calculate distribution
        healthy_count = int(scale * 0.80)
        exif_count = int(scale * 0.10)
        makernotes_count = int(scale * 0.05)
        severe_count = int(scale * 0.025)
        filesystem_count = scale - healthy_count - exif_count - makernotes_count - severe_count

        # Create HEALTHY files
        for i in range(healthy_count):
            file_path = self._create_file(f"mixed_{i:04d}_healthy.jpg", CorruptionType.HEALTHY)
            batch[CorruptionType.HEALTHY].append(file_path)

        # Create EXIF_STRUCTURE corruption
        for i in range(exif_count):
            file_path = self._create_file(f"mixed_{healthy_count+i:04d}_exif.jpg",
                                         CorruptionType.EXIF_STRUCTURE)
            batch[CorruptionType.EXIF_STRUCTURE].append(file_path)

        # Create MAKERNOTES corruption
        for i in range(makernotes_count):
            file_path = self._create_file(f"mixed_{healthy_count+exif_count+i:04d}_makernotes.jpg",
                                         CorruptionType.MAKERNOTES)
            batch[CorruptionType.MAKERNOTES].append(file_path)

        # Create SEVERE_CORRUPTION
        for i in range(severe_count):
            file_path = self._create_file(f"mixed_{healthy_count+exif_count+makernotes_count+i:04d}_severe.jpg",
                                         CorruptionType.SEVERE_CORRUPTION)
            batch[CorruptionType.SEVERE_CORRUPTION].append(file_path)

        # Create FILESYSTEM_ONLY
        for i in range(filesystem_count):
            file_path = self._create_file(f"mixed_{healthy_count+exif_count+makernotes_count+severe_count+i:04d}_fsonly.jpg",
                                         CorruptionType.FILESYSTEM_ONLY)
            batch[CorruptionType.FILESYSTEM_ONLY].append(file_path)

        # Flatten all files
        all_files = []
        for corruption_type in batch:
            all_files.extend(batch[corruption_type])

        # Create metadata dict
        metadata = {}
        for corruption_type in batch:
            for file_path in batch[corruption_type]:
                metadata[file_path] = corruption_type

        return {
            'healthy': batch[CorruptionType.HEALTHY],
            'exif_structure': batch[CorruptionType.EXIF_STRUCTURE],
            'makernotes': batch[CorruptionType.MAKERNOTES],
            'severe_corruption': batch[CorruptionType.SEVERE_CORRUPTION],
            'filesystem_only': batch[CorruptionType.FILESYSTEM_ONLY],
            'all': all_files,
            'metadata': metadata,
            'scale': scale,
            'corruption_counts': {
                'healthy': healthy_count,
                'exif_structure': exif_count,
                'makernotes': makernotes_count,
                'severe_corruption': severe_count,
                'filesystem_only': filesystem_count
            }
        }

    def create_per_type_batches(self, count: int = 50) -> Dict:
        """
        Create dedicated batch for each corruption type (count files each).

        Args:
            count: Number of files per type

        Returns:
            Dict: {CorruptionType.X: [file_paths], ...}
        """
        batches = {}

        for corruption_type in CorruptionType:
            files = []
            for i in range(count):
                file_path = self._create_file(
                    f"{corruption_type.name.lower()}_{i:03d}.jpg",
                    corruption_type
                )
                files.append(file_path)
            batches[corruption_type] = files

        return batches

    def create_group_boundary_batch(self, group_size: int = 60, num_groups: int = 3) -> Dict:
        """
        Create batch structured to test GROUP_SIZE boundaries.

        With GROUP_SIZE=60:
        - Group 1: 60 files (mixed health/corruption)
        - Group 2: 60 files (partial corruption)
        - Group 3: 40 files (all healthy)

        Args:
            group_size: GROUP_SIZE constant
            num_groups: Number of groups to create

        Returns:
            Dict: {'files': [...], 'group_structure': {...}}
        """
        all_files = []
        group_structure = {}

        for group_idx in range(num_groups):
            files_in_group = group_size if group_idx < num_groups - 1 else group_size // 1.5
            files_in_group = int(files_in_group)

            group_files = []
            for file_idx in range(files_in_group):
                # Mix corruption types per group
                if file_idx % 10 == 0:
                    corruption_type = CorruptionType.EXIF_STRUCTURE
                elif file_idx % 10 == 1:
                    corruption_type = CorruptionType.MAKERNOTES
                else:
                    corruption_type = CorruptionType.HEALTHY

                file_path = self._create_file(
                    f"group_{group_idx}_file_{file_idx:04d}.jpg",
                    corruption_type
                )
                group_files.append(file_path)
                all_files.append(file_path)

            group_structure[group_idx] = {
                'files': group_files,
                'count': files_in_group,
                'should_restart_before': group_idx > 0
            }

        return {
            'files': all_files,
            'group_structure': group_structure,
            'total_groups': num_groups,
            'group_size': group_size
        }

    def _create_file(self, filename: str, corruption_type: CorruptionType) -> Path:
        """
        Create a file with specified corruption type.

        Args:
            filename: Name of file to create
            corruption_type: Type of corruption to inject

        Returns:
            Path: Path to created file
        """
        file_path = self.base_dir / filename

        if corruption_type == CorruptionType.HEALTHY:
            self._create_healthy_file(file_path)
        elif corruption_type == CorruptionType.EXIF_STRUCTURE:
            self._create_exif_corruption(file_path)
        elif corruption_type == CorruptionType.MAKERNOTES:
            self._create_makernotes_corruption(file_path)
        elif corruption_type == CorruptionType.SEVERE_CORRUPTION:
            self._create_severe_corruption(file_path)
        elif corruption_type == CorruptionType.FILESYSTEM_ONLY:
            self._create_filesystem_only_file(file_path)

        return file_path

    def _create_healthy_file(self, file_path: Path):
        """Create a healthy, uncorrupted file."""
        if self.real_photo_file and self.real_photo_file.exists():
            shutil.copy2(self.real_photo_file, file_path)
        else:
            self.media_gen.create_minimal_jpeg(file_path)

    def _create_exif_corruption(self, file_path: Path):
        """Create file with EXIF structure corruption."""
        # Start with healthy file
        self._create_healthy_file(file_path)

        # Corrupt EXIF via exiftool by injecting bad StripOffsets
        try:
            subprocess.run(
                ["exiftool", "-overwrite_original", "-StripOffsets=bad_value", str(file_path)],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass  # If fails, file remains as-is

    def _create_makernotes_corruption(self, file_path: Path):
        """Create file with MakerNotes corruption."""
        # Start with healthy file
        self._create_healthy_file(file_path)

        # Create MakerNotes corruption by injecting invalid MakerNote offset
        try:
            subprocess.run(
                ["exiftool", "-overwrite_original", "-MakerNote=<invalid>", str(file_path)],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass

    def _create_severe_corruption(self, file_path: Path):
        """Create file with severe/unreadable corruption."""
        # Create file with binary garbage that looks like JPEG header but isn't valid
        with open(file_path, 'wb') as f:
            # JPEG header
            f.write(b'\xFF\xD8\xFF\xE0')
            # Invalid/garbage data
            f.write(os.urandom(1024))
            # Truncated/invalid JPEG footer
            f.write(b'\xFF\xD9')

    def _create_filesystem_only_file(self, file_path: Path):
        """Create file with no EXIF metadata (filesystem-only timestamps)."""
        # Create healthy JPEG but strip all EXIF
        if self.real_photo_file and self.real_photo_file.exists():
            shutil.copy2(self.real_photo_file, file_path)
        else:
            self.media_gen.create_minimal_jpeg(file_path)

        # Strip all EXIF data
        try:
            subprocess.run(
                ["exiftool", "-overwrite_original", "-all=", str(file_path)],
                capture_output=True,
                timeout=5
            )
        except Exception:
            pass


@pytest.fixture
def corruption_factory(temp_alignment_dir, real_photo_file):
    """
    Factory for creating corrupted files at scale.

    Args:
        temp_alignment_dir: Temporary directory for test files
        real_photo_file: Real photo file to use as template

    Yields:
        CorruptionFileFactory: Factory instance
    """
    factory = CorruptionFileFactory(temp_alignment_dir, real_photo_file)
    yield factory


@pytest.fixture
def scaled_corruption_batch(corruption_factory, scale_level):
    """
    Create mixed corruption batch at specified scale.

    Args:
        corruption_factory: Factory fixture
        scale_level: Scale parametrization (50, 200, 500)

    Yields:
        Dict: Mixed corruption batch metadata
    """
    return corruption_factory.create_mixed_corruption_batch(scale_level)


@pytest.fixture
def per_corruption_batches(corruption_factory):
    """
    Create dedicated batch for each corruption type.

    Args:
        corruption_factory: Factory fixture

    Yields:
        Dict: Corruption type -> [file_paths]
    """
    return corruption_factory.create_per_type_batches(count=50)


@pytest.fixture
def group_boundary_batch(corruption_factory):
    """
    Create batch structured to test GROUP_SIZE boundaries.

    Args:
        corruption_factory: Factory fixture

    Yields:
        Dict: Group boundary batch metadata
    """
    return corruption_factory.create_group_boundary_batch(GROUP_SIZE, num_groups=3)


# ============================================================================
# PERMISSION SIMULATOR
# ============================================================================

class PermissionSimulator:
    """Simulate file permission errors for testing."""

    def __init__(self):
        """Initialize permission simulator."""
        self.original_permissions = {}
        self.platform = sys.platform

    def make_read_only(self, file_path: Path) -> bool:
        """
        Make file read-only.

        Args:
            file_path: Path to file

        Returns:
            bool: True if successful
        """
        file_path = Path(file_path)
        try:
            # Store original permissions
            self.original_permissions[file_path] = os.stat(file_path).st_mode

            if self.platform == 'win32':
                # Windows: use attrib command or os.chmod
                os.chmod(file_path, 0o444)  # Read-only
            else:
                # POSIX: remove write permissions
                os.chmod(file_path, 0o444)

            return True
        except Exception as e:
            print(f"Error making file read-only: {e}")
            return False

    def make_write_protected(self, file_path: Path) -> bool:
        """
        Make file write-protected (remove write permissions).

        Args:
            file_path: Path to file

        Returns:
            bool: True if successful
        """
        return self.make_read_only(file_path)

    def restore_permissions(self, file_path: Path) -> bool:
        """
        Restore original file permissions.

        Args:
            file_path: Path to file

        Returns:
            bool: True if successful
        """
        file_path = Path(file_path)
        try:
            if file_path in self.original_permissions:
                mode = self.original_permissions[file_path]
                os.chmod(file_path, mode)
                del self.original_permissions[file_path]
                return True
            else:
                # If not tracked, restore normal permissions
                os.chmod(file_path, 0o644)
                return True
        except Exception as e:
            print(f"Error restoring permissions: {e}")
            return False

    def create_readonly_batch(self, real_photo_file: Path, temp_dir: Path) -> List[Tuple[Path, bool]]:
        """
        Create batch of read-only files.

        Args:
            real_photo_file: Template photo file
            temp_dir: Directory to create files in

        Returns:
            List[(file_path, recovery_possible)]: List of read-only files
        """
        files = []
        for i in range(10):
            f = temp_dir / f"readonly_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            self.make_read_only(f)
            files.append((f, True))  # Recovery possible
        return files

    def cleanup(self):
        """Restore all tracked permissions."""
        for file_path in list(self.original_permissions.keys()):
            self.restore_permissions(file_path)


@pytest.fixture
def permission_simulator():
    """
    Permission simulator for Windows/POSIX permission handling.

    Yields:
        PermissionSimulator: Simulator instance
    """
    sim = PermissionSimulator()
    yield sim
    # Cleanup: restore all permissions
    sim.cleanup()


@pytest.fixture
def read_only_file_batch(real_photo_file, temp_alignment_dir, permission_simulator):
    """
    Create batch of read-only files.

    Args:
        real_photo_file: Real photo file to use
        temp_alignment_dir: Temp directory
        permission_simulator: Permission simulator fixture

    Yields:
        List[(file_path, recovery_possible)]: Read-only file paths
    """
    return permission_simulator.create_readonly_batch(real_photo_file, temp_alignment_dir)


# ============================================================================
# BACKUP AND RECOVERY HELPERS
# ============================================================================

class BackupIntegrityVerifier:
    """Verify backup creation and integrity."""

    @staticmethod
    def verify_backup_exists(backup_path: Path) -> bool:
        """
        Check if backup file exists and is readable.

        Args:
            backup_path: Path to backup file

        Returns:
            bool: True if exists and readable
        """
        if not backup_path.exists():
            return False
        if not backup_path.stat().st_size > 0:
            return False
        return True

    @staticmethod
    def verify_content_identical(original_path: Path, backup_path: Path) -> bool:
        """
        Verify backup content is identical to original via SHA256.

        Args:
            original_path: Path to original file
            backup_path: Path to backup file

        Returns:
            bool: True if checksums match
        """
        def get_sha256(file_path):
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()

        try:
            return get_sha256(original_path) == get_sha256(backup_path)
        except Exception:
            return False

    @staticmethod
    def verify_naming_convention(backup_path: Path) -> bool:
        """
        Verify backup filename follows convention: photo_backup.jpg (not photo.jpg_backup).

        Args:
            backup_path: Path to backup file

        Returns:
            bool: True if naming is correct
        """
        name = backup_path.name

        # Should have _backup before extension
        if "_backup" not in name:
            return False

        # Should not have double extension (photo.jpg_backup)
        parts = name.split('_backup')
        if len(parts) != 2:
            return False

        # Should have extension after _backup
        if not parts[1].startswith('.'):
            return False

        return True


@pytest.fixture
def backup_integrity_verifier():
    """
    Backup integrity verifier fixture.

    Yields:
        BackupIntegrityVerifier: Verifier instance
    """
    return BackupIntegrityVerifier()


# ============================================================================
# ERROR TRACKING
# ============================================================================

class ErrorTracker:
    """Track and validate error tracking during processing."""

    def __init__(self):
        """Initialize error tracker."""
        self.errors_by_file = {}
        self.errors_by_type = {}

    def track_error(self, file_path: str, error_type: str, error_message: str):
        """
        Track an error.

        Args:
            file_path: Path to file that errored
            error_type: Type of error (permission, corruption, etc)
            error_message: Error message
        """
        self.errors_by_file[file_path] = (error_type, error_message)

        if error_type not in self.errors_by_type:
            self.errors_by_type[error_type] = []
        self.errors_by_type[error_type].append(file_path)

    def get_errors_by_category(self) -> Dict[str, List[str]]:
        """
        Get all errors grouped by category.

        Returns:
            Dict: {error_type: [file_paths]}
        """
        return self.errors_by_type.copy()

    def verify_error_in_list(self, metadata_errors: List[Tuple], file_path: str) -> bool:
        """
        Verify error appears in status.metadata_errors.

        Args:
            metadata_errors: List of (file_path, error_msg) tuples from ProcessingStatus
            file_path: File path to look for

        Returns:
            bool: True if error found for this file
        """
        for error_entry in metadata_errors:
            if error_entry[0] == file_path:
                return True
        return False


@pytest.fixture
def error_tracker():
    """
    Error tracking fixture.

    Yields:
        ErrorTracker: Error tracker instance
    """
    return ErrorTracker()


# ============================================================================
# MIXED FAILURE SCENARIOS
# ============================================================================

@pytest.fixture
def mixed_success_batch(corruption_factory, scale_level):
    """
    Create batch with controlled success/failure rates.

    For scale=200: 100 healthy + 50 repairable + 50 unrepairable

    Args:
        corruption_factory: Factory fixture
        scale_level: Scale parametrization

    Yields:
        Dict: Batch metadata with expected outcomes
    """
    # 50% healthy, 25% repairable, 25% unrepairable
    healthy_count = int(scale_level * 0.50)
    repairable_count = int(scale_level * 0.25)
    unrepairable_count = scale_level - healthy_count - repairable_count

    batch = {
        'healthy': [],
        'repairable': [],
        'unrepairable': [],
    }

    # Create healthy files
    for i in range(healthy_count):
        file_path = corruption_factory._create_file(f"mixed_success_{i:04d}_healthy.jpg",
                                                    CorruptionType.HEALTHY)
        batch['healthy'].append(file_path)

    # Create repairable (EXIF_STRUCTURE) files
    for i in range(repairable_count):
        file_path = corruption_factory._create_file(f"mixed_success_{healthy_count+i:04d}_repairable.jpg",
                                                    CorruptionType.EXIF_STRUCTURE)
        batch['repairable'].append(file_path)

    # Create unrepairable (SEVERE_CORRUPTION) files
    for i in range(unrepairable_count):
        file_path = corruption_factory._create_file(f"mixed_success_{healthy_count+repairable_count+i:04d}_unrepairable.jpg",
                                                    CorruptionType.SEVERE_CORRUPTION)
        batch['unrepairable'].append(file_path)

    all_files = batch['healthy'] + batch['repairable'] + batch['unrepairable']

    expected_outcomes = {}
    for f in batch['healthy']:
        expected_outcomes[f] = 'success'
    for f in batch['repairable']:
        expected_outcomes[f] = 'repairable'
    for f in batch['unrepairable']:
        expected_outcomes[f] = 'unrepairable'

    return {
        'files': all_files,
        'healthy': batch['healthy'],
        'repairable': batch['repairable'],
        'unrepairable': batch['unrepairable'],
        'expected_outcomes': expected_outcomes,
        'repair_progress': [],
        'scale': scale_level
    }
