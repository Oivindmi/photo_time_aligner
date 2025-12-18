"""
Pytest configuration and fixtures for Photo Time Aligner test suite.

This module provides:
- Pytest fixtures for test data and cleanup
- Shared test utilities
- Performance monitoring
- Sample media file handling
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
import time
import psutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import project modules (will be available after project setup)
try:
    from src.core.exif_handler import ExifHandler
    from src.core.file_processor import FileProcessor
except ImportError:
    pass  # Will fail later if actually needed


# ============================================================================
# SAMPLE MEDIA PATHS
# ============================================================================

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_MEDIA_DIR = FIXTURES_DIR / "sample_media"
CLEAN_MEDIA_DIR = SAMPLE_MEDIA_DIR / "clean"
CORRUPTED_MEDIA_DIR = SAMPLE_MEDIA_DIR / "corrupted"
BATCH_TEST_BASE_DIR = SAMPLE_MEDIA_DIR / "batch_test_base"


# ============================================================================
# PYTEST HOOKS - Session and collection helpers
# ============================================================================

def pytest_configure(config):
    """Configure pytest - runs before tests are collected."""
    # Ensure sample media directory exists
    SAMPLE_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    CORRUPTED_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    BATCH_TEST_BASE_DIR.mkdir(parents=True, exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add skip markers for missing prerequisites."""
    # Check if ExifTool is available
    import shutil as sh
    exiftool_available = sh.which("exiftool") is not None

    # Check if sample media exists
    sample_media_available = any(CLEAN_MEDIA_DIR.glob("*"))

    for item in items:
        # Add markers based on test location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "error_recovery" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
        elif "ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)
        else:
            item.add_marker(pytest.mark.unit)

        # Skip tests if prerequisites missing
        if item.get_closest_marker("skip_without_exiftool") and not exiftool_available:
            item.add_marker(pytest.mark.skip(reason="ExifTool not found in PATH"))

        if item.get_closest_marker("skip_without_media") and not sample_media_available:
            item.add_marker(pytest.mark.skip(reason="Sample media files not available"))


# ============================================================================
# BASIC FIXTURES
# ============================================================================

@pytest.fixture
def temp_alignment_dir():
    """
    Create a temporary directory for alignment tests.

    Yields:
        Path: Temporary directory path
    """
    temp_dir = tempfile.mkdtemp(prefix="test_alignment_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_project_dir():
    """
    Create a temporary directory structure mimicking a project directory.

    Yields:
        Path: Root temp directory with subdirectories for photos, videos, backups
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="test_project_"))
    (temp_dir / "photos").mkdir()
    (temp_dir / "videos").mkdir()
    (temp_dir / "backups").mkdir()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================================
# REAL FILE FIXTURES
# ============================================================================

@pytest.fixture
def real_photo_file():
    """
    Provide access to a real photo file from sample media.

    Returns:
        Path: Path to real JPEG photo, or None if not available

    Marks:
        skip_without_media: Skips test if file not available
    """
    photo_file = CLEAN_MEDIA_DIR / "photo_clean.jpg"

    if not photo_file.exists():
        return None

    return photo_file


@pytest.fixture
def real_video_file():
    """
    Provide access to a real video file from sample media.

    Returns:
        Path: Path to real video file, or None if not available

    Marks:
        skip_without_media: Skips test if file not available
    """
    video_file = CLEAN_MEDIA_DIR / "video_clean_mp4.mp4"

    if not video_file.exists():
        return None

    return video_file


@pytest.fixture
def real_raw_file():
    """
    Provide access to a real RAW file from sample media.

    Returns:
        Path: Path to real CR2/NEF file, or None if not available

    Marks:
        skip_without_media: Skips test if file not available
    """
    # Try common RAW formats
    for ext in [".cr2", ".nef", ".dng"]:
        raw_file = CLEAN_MEDIA_DIR / f"photo_clean{ext}"
        if raw_file.exists():
            return raw_file

    return None


@pytest.fixture
def norwegian_filename_file():
    """
    Provide access to a file with Norwegian characters in filename.

    Returns:
        Path: Path to file with Norwegian filename, or None if not available
    """
    norwegian_file = CLEAN_MEDIA_DIR / "Øivind_test.jpg"

    if not norwegian_file.exists():
        return None

    return norwegian_file


# ============================================================================
# GENERATED FILE FIXTURES
# ============================================================================

@pytest.fixture
def corrupted_exif_file(temp_alignment_dir):
    """
    Provide access to a corrupted EXIF file.

    This fixture will use media_generator to create a file with corrupted EXIF
    if it doesn't exist in the fixtures directory.

    Yields:
        Path: Path to corrupted EXIF file
    """
    # First check if pre-generated file exists
    corrupted_file = CORRUPTED_MEDIA_DIR / "corrupted_exif.jpg"

    if corrupted_file.exists():
        return corrupted_file

    # Otherwise generate it (will be implemented in media_generator.py)
    # For now, return None and tests will be skipped
    return None


@pytest.fixture
def corrupted_makernotes_file(temp_alignment_dir):
    """
    Provide access to a file with corrupted MakerNotes.

    Yields:
        Path: Path to corrupted MakerNotes file
    """
    corrupted_file = CORRUPTED_MEDIA_DIR / "corrupted_makernotes.jpg"

    if corrupted_file.exists():
        return corrupted_file

    return None


@pytest.fixture
def missing_datetime_file(temp_alignment_dir):
    """
    Provide access to a file missing datetime metadata.

    Yields:
        Path: Path to file without datetime
    """
    missing_file = CORRUPTED_MEDIA_DIR / "missing_datetime.jpg"

    if missing_file.exists():
        return missing_file

    return None


# ============================================================================
# BATCH PROCESSING FIXTURES
# ============================================================================

@pytest.fixture(params=[50, 200, 500])
def batch_size(request):
    """
    Parametrized fixture for batch processing tests.

    Yields:
        int: Number of files (50, 200, or 500)
    """
    return request.param


@pytest.fixture
def batch_photo_files(batch_size, temp_alignment_dir):
    """
    Create a batch of photo files for performance testing.

    Args:
        batch_size: Number of files to create (50, 200, or 500)
        temp_alignment_dir: Temporary directory for files

    Returns:
        List[Path]: List of created photo file paths
    """
    files = []
    for i in range(batch_size):
        file_path = temp_alignment_dir / f"photo_{i:04d}.jpg"
        file_path.touch()  # Create empty placeholder
        files.append(file_path)

    return files


# ============================================================================
# SYSTEM STATE FIXTURES
# ============================================================================

@pytest.fixture
def exif_handler_live():
    """
    Provide a real ExifHandler instance (not mocked).

    This fixture creates a real ExifHandler that uses actual ExifTool processes.
    Use this for integration tests that verify real ExifTool operations.

    Returns:
        ExifHandler: Real instance with live ExifTool processes

    Marks:
        skip_without_exiftool: Skips if ExifTool not in PATH
    """
    import shutil as sh
    if sh.which("exiftool") is None:
        pytest.skip("ExifTool not found in PATH")

    return ExifHandler()


@pytest.fixture
def file_processor_live(exif_handler_live):
    """
    Provide a real FileProcessor instance.

    Args:
        exif_handler_live: Real ExifHandler fixture

    Returns:
        FileProcessor: Real instance
    """
    return FileProcessor(exif_handler_live)


# ============================================================================
# PERFORMANCE MONITORING FIXTURES
# ============================================================================

class PerformanceMonitor:
    """Monitor performance metrics during test execution."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = None
        self.start_memory = None
        self.measurements = {}

    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

    def stop(self):
        """Stop performance monitoring and return metrics."""
        elapsed = time.time() - self.start_time
        peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = peak_memory - self.start_memory

        return {
            "elapsed_seconds": elapsed,
            "start_memory_mb": self.start_memory,
            "peak_memory_mb": peak_memory,
            "memory_delta_mb": memory_delta
        }

    def check_memory_growth(self, max_growth_mb=100):
        """
        Check if memory growth exceeded threshold.

        Args:
            max_growth_mb: Maximum acceptable memory growth in MB

        Raises:
            AssertionError: If memory growth exceeds threshold
        """
        peak_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = peak_memory - self.start_memory

        assert memory_delta < max_growth_mb, \
            f"Memory growth ({memory_delta:.1f}MB) exceeded limit ({max_growth_mb}MB)"


@pytest.fixture
def performance_monitor():
    """
    Provide a performance monitoring helper.

    Usage:
        def test_performance(performance_monitor):
            performance_monitor.start()
            # ... run code ...
            metrics = performance_monitor.stop()
            assert metrics['elapsed_seconds'] < 5.0

    Returns:
        PerformanceMonitor: Instance for tracking metrics
    """
    return PerformanceMonitor()


# ============================================================================
# ASSERTION HELPER FIXTURES
# ============================================================================

@pytest.fixture
def assert_metadata_helper():
    """
    Provide metadata assertion helpers.

    Returns:
        AssertionHelper: Instance for metadata validation
    """
    from tests.fixtures.helpers.assertion_helpers import AssertionHelper
    return AssertionHelper()


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

@contextmanager
def temp_copy_file(source_file, dest_dir):
    """
    Context manager to temporarily copy a file.

    Args:
        source_file: Path to source file
        dest_dir: Destination directory

    Yields:
        Path: Path to copied file
    """
    dest_file = Path(dest_dir) / source_file.name
    shutil.copy2(source_file, dest_file)

    try:
        yield dest_file
    finally:
        if dest_file.exists():
            dest_file.unlink()


@pytest.fixture
def temp_copy_file_fixture(temp_alignment_dir):
    """
    Provide context manager for temporary file copying.

    Usage:
        def test_something(temp_copy_file_fixture, real_photo_file):
            with temp_copy_file_fixture(real_photo_file) as temp_copy:
                # Use temp_copy for testing

    Returns:
        callable: Context manager function
    """
    return lambda source: temp_copy_file(source, temp_alignment_dir)
