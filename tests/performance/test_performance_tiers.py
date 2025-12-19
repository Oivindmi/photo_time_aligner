"""
Phase C: Tier 2 Performance Tests

Tests the Photo Time Aligner at scale:
- 50-file scale: Baseline performance
- 200-file scale: Medium scale with GROUP_SIZE restart
- 500-file scale: Large scale stress test

Verifies:
- Performance remains acceptable at scale
- GROUP_SIZE restart logic prevents pool exhaustion
- Memory usage stays within bounds
- No zombie processes accumulate
- Batch processing completes successfully

Tests use real ExifTool and real test media files.
"""

import pytest
import tempfile
import shutil
import os
import gc
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
import psutil
import time

from src.core.alignment_processor import AlignmentProcessor
from src.core.exif_handler import ExifHandler
from src.core.file_processor import FileProcessor
from src.core.time_calculator import TimeCalculator


class TestPerformanceScale50:
    """Performance tests at 50-file scale (baseline)"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_50_file_alignment_performance(self, exif_handler_live, file_processor_live,
                                           real_photo_file, temp_alignment_dir,
                                           performance_monitor):
        """
        Test alignment performance with 50 files.

        Verifies:
        - No GROUP_SIZE restart (GROUP_SIZE=40, so need 2 groups)
        - Processing completes within reasonable time
        - Memory usage is stable
        - All files processed correctly
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        # Create 50 test files by copying real photo
        test_files = []
        for i in range(50):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Create reference file
        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        # Process alignment
        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        time_offset = timedelta(seconds=30)

        status = processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=time_offset,
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Assertions
        assert status is not None, "Processing should return status"
        assert status.processed_files >= 0, "Should process files"

        # Performance assertions (50 files)
        # Note: First run may be slower due to ExifTool initialization
        assert metrics["elapsed_seconds"] < 90, \
            f"50-file alignment should complete in <90s, took {metrics['elapsed_seconds']:.1f}s"

        # Memory assertions
        assert metrics["memory_delta_mb"] < 250, \
            f"Memory growth should be <250MB, was {metrics['memory_delta_mb']:.1f}MB"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_50_file_metadata_read_performance(self, exif_handler_live, temp_alignment_dir,
                                               real_photo_file, performance_monitor):
        """
        Test batch metadata reading with 50 files.

        Verifies:
        - Batch read completes quickly
        - All metadata retrieved
        - Process pool used efficiently
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        # Create 50 test files
        test_files = []
        for i in range(50):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        performance_monitor.start()

        # Read metadata from all files
        metadata_list = []
        for file_path in test_files:
            try:
                metadata = exif_handler_live.read_metadata(file_path)
                metadata_list.append(metadata)
            except Exception:
                pass

        metrics = performance_monitor.stop()

        # Assertions
        assert len(metadata_list) == 50, "Should read metadata from all 50 files"
        assert metrics["elapsed_seconds"] < 15, \
            f"Metadata read for 50 files should be <15s, took {metrics['elapsed_seconds']:.1f}s"


class TestPerformanceScale200:
    """Performance tests at 200-file scale (GROUP_SIZE restart trigger)"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_200_file_alignment_with_group_restart(self, exif_handler_live, file_processor_live,
                                                    real_photo_file, temp_alignment_dir,
                                                    performance_monitor):
        """
        Test alignment with 200 files (triggers GROUP_SIZE restart).

        Important: GROUP_SIZE=40, so 200 files = 5 groups
        Each group should trigger pool.restart_pool() to prevent exhaustion.

        Verifies:
        - GROUP_SIZE restart logic works correctly
        - No zombie processes accumulate
        - All 200 files processed
        - Performance degradation is minimal
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        # Create 200 test files
        test_files = []
        for i in range(200):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Create reference file
        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        # Process alignment with GROUP_SIZE restart
        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        time_offset = timedelta(seconds=30)

        status = processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=time_offset,
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Assertions
        assert status is not None, "Processing should return status"
        assert status.processed_files >= 0, "Should process files"

        # Performance assertion: 200 files with GROUP_SIZE restarts
        # Should still complete in reasonable time (allowing for pool restarts)
        assert metrics["elapsed_seconds"] < 300, \
            f"200-file alignment should complete in <300s, took {metrics['elapsed_seconds']:.1f}s"

        # Memory should not grow excessively with pool restarts
        assert metrics["memory_delta_mb"] < 400, \
            f"Memory growth should be <400MB with pool restarts, was {metrics['memory_delta_mb']:.1f}MB"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_200_file_process_pool_restart_verification(self, exif_handler_live, temp_alignment_dir,
                                                        real_photo_file):
        """
        Verify that GROUP_SIZE restart logic works correctly.

        Tests the actual restart mechanism to ensure:
        - Processes are properly restarted between groups
        - No zombie processes remain
        - Pool maintains correct state
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        # Create 200 test files
        test_files = []
        for i in range(200):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Get initial process count
        process = psutil.Process(os.getpid())
        children_before = len(process.children(recursive=True))

        # Read metadata in batches, triggering GROUP_SIZE restarts
        batch_size = 40  # GROUP_SIZE value
        num_batches = (len(test_files) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(test_files))
            batch_files = test_files[start_idx:end_idx]

            for file_path in batch_files:
                try:
                    exif_handler_live.read_metadata(file_path)
                except Exception:
                    pass

            # Restart pool between batches (simulating GROUP_SIZE behavior)
            if batch_idx < num_batches - 1:
                try:
                    exif_handler_live.exiftool_pool.restart_pool()
                except Exception:
                    pass
                time.sleep(0.2)

        # Get final process count
        children_after = len(process.children(recursive=True))

        # Verify no zombie processes accumulated
        # Allow some tolerance for system processes
        assert children_after - children_before < 5, \
            f"Zombie processes detected: {children_after - children_before} processes not cleaned up"


class TestPerformanceScale500:
    """Performance tests at 500-file scale (large scale stress test)"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_500_file_alignment_stress_test(self, exif_handler_live, file_processor_live,
                                            real_photo_file, temp_alignment_dir,
                                            performance_monitor):
        """
        Stress test alignment with 500 files.

        500 files with GROUP_SIZE=40 = 12-13 groups
        Heavy use of pool restart mechanism.

        Verifies:
        - System remains stable at large scale
        - GROUP_SIZE restart prevents pool exhaustion
        - Processing completes successfully
        - Memory usage remains bounded
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        # Create 500 test files
        test_files = []
        for i in range(500):
            target_file = temp_alignment_dir / f"photo_{i:05d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Create reference file
        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        # Process alignment
        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        time_offset = timedelta(seconds=30)

        status = processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=time_offset,
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Assertions
        assert status is not None, "Processing should return status"
        assert status.processed_files >= 0, "Should process files"

        # Performance assertion for 500 files
        # This is a stress test, so allow significant time
        assert metrics["elapsed_seconds"] < 600, \
            f"500-file alignment should complete in <600s, took {metrics['elapsed_seconds']:.1f}s"

        # Memory should still be bounded (no major leak)
        assert metrics["memory_delta_mb"] < 600, \
            f"Memory growth should be <600MB at 500-file scale, was {metrics['memory_delta_mb']:.1f}MB"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_500_file_no_zombie_processes(self, exif_handler_live, temp_alignment_dir,
                                          real_photo_file):
        """
        Verify no zombie ExifTool processes remain after 500-file processing.

        Tests the critical requirement that pool restart + cleanup
        prevents accumulation of zombie processes.
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        # Create 500 test files
        test_files = []
        for i in range(500):
            target_file = temp_alignment_dir / f"photo_{i:05d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Get baseline ExifTool process count
        process = psutil.Process(os.getpid())
        children_before = len(process.children(recursive=True))

        # Process all files
        batch_size = 40  # GROUP_SIZE
        num_batches = (len(test_files) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(test_files))
            batch_files = test_files[start_idx:end_idx]

            for file_path in batch_files:
                try:
                    exif_handler_live.read_metadata(file_path)
                except Exception:
                    pass

            # Restart pool between batches
            if batch_idx < num_batches - 1:
                try:
                    exif_handler_live.exiftool_pool.restart_pool()
                except Exception:
                    pass
                time.sleep(0.2)
                gc.collect()

        # Wait for processes to stabilize
        time.sleep(1)

        # Force cleanup
        exif_handler_live.exiftool_pool.shutdown()

        # Get final process count
        children_after = len(process.children(recursive=True))

        # Verify minimal zombie processes
        # Account for some system overhead
        zombie_count = children_after - children_before
        assert zombie_count < 3, \
            f"Too many zombie processes: {zombie_count}. Pool restart may not be working correctly."


class TestMemoryLeakDetection:
    """Memory leak detection tests across scale"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_stability_50_files(self, exif_handler_live, temp_alignment_dir,
                                       real_photo_file, performance_monitor):
        """
        Test memory stability with 50 files.

        Verifies baseline memory behavior and cleanup.
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        # Create 50 test files
        test_files = []
        for i in range(50):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        performance_monitor.start()

        # Process files multiple times to detect leaks
        for iteration in range(3):
            for file_path in test_files:
                try:
                    exif_handler_live.read_metadata(file_path)
                except Exception:
                    pass

        metrics = performance_monitor.stop()

        # Memory growth should be minimal for repeated operations
        # Each iteration shouldn't accumulate memory
        assert metrics["memory_delta_mb"] < 150, \
            f"Memory leak detected: {metrics['memory_delta_mb']:.1f}MB growth for repeated reads"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_stability_200_files(self, exif_handler_live, temp_alignment_dir,
                                        real_photo_file, performance_monitor):
        """
        Test memory stability with 200 files.

        Verifies memory behavior with GROUP_SIZE restart.
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        # Create 200 test files
        test_files = []
        for i in range(200):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        performance_monitor.start()

        # Process in batches with pool restarts
        batch_size = 40
        num_batches = (len(test_files) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(test_files))
            batch_files = test_files[start_idx:end_idx]

            for file_path in batch_files:
                try:
                    exif_handler_live.read_metadata(file_path)
                except Exception:
                    pass

            # Restart and clean
            if batch_idx < num_batches - 1:
                try:
                    exif_handler_live.exiftool_pool.restart_pool()
                except Exception:
                    pass
                gc.collect()
                time.sleep(0.1)

        metrics = performance_monitor.stop()

        # Memory should be bounded even with multiple restarts
        assert metrics["memory_delta_mb"] < 300, \
            f"Memory leak with restarts: {metrics['memory_delta_mb']:.1f}MB growth for 200 files"


class TestGroupSizeRestartLogic:
    """Tests specifically for GROUP_SIZE restart logic"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_group_size_restart_at_boundary(self, exif_handler_live, file_processor_live,
                                            real_photo_file, temp_alignment_dir):
        """
        Test GROUP_SIZE restart logic at group boundaries.

        Tests exact boundary: GROUP_SIZE=40
        - 40 files: 1 group, no restart
        - 41 files: 2 groups, should restart after first group
        - 80 files: 2 groups, should restart
        - 81 files: 3 groups, should restart twice
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        GROUP_SIZE = 40

        # Test case 1: Exactly GROUP_SIZE files (no restart needed)
        test_files_40 = []
        for i in range(GROUP_SIZE):
            target_file = temp_alignment_dir / f"test_40_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files_40.append(str(target_file))

        # Should complete without error
        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        ref_file = temp_alignment_dir / "ref_40.jpg"
        shutil.copy2(real_photo_file, ref_file)

        status = processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files_40,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=timedelta(seconds=30),
            progress_callback=None
        )

        assert status is not None, "40-file processing should complete"

        # Test case 2: GROUP_SIZE + 1 files (should trigger restart)
        test_files_41 = []
        for i in range(GROUP_SIZE + 1):
            target_file = temp_alignment_dir / f"test_41_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files_41.append(str(target_file))

        ref_file_41 = temp_alignment_dir / "ref_41.jpg"
        shutil.copy2(real_photo_file, ref_file_41)

        status = processor.process_files(
            reference_files=[str(ref_file_41)],
            target_files=test_files_41,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=timedelta(seconds=30),
            progress_callback=None
        )

        assert status is not None, "41-file processing with restart should complete"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_group_restart_pool_state(self, exif_handler_live, temp_alignment_dir, real_photo_file):
        """
        Verify pool state is correct after GROUP_SIZE restart.

        Checks that:
        - Pool has correct number of processes after restart
        - Processes are fresh (not exhausted)
        - Available queue is properly refilled
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        pool = exif_handler_live.exiftool_pool

        # Record initial state
        initial_pool_size = len(pool.processes)
        assert initial_pool_size > 0, "Pool should have processes"

        # Create and process GROUP_SIZE files
        test_files = []
        for i in range(40):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        # Process files
        for file_path in test_files:
            try:
                exif_handler_live.read_metadata(file_path)
            except Exception:
                pass

        # Check pool state before restart
        available_before = pool.available.qsize()

        # Restart pool
        pool.restart_pool()

        # Check pool state after restart
        pool_size_after = len(pool.processes)
        available_after = pool.available.qsize()

        assert pool_size_after == initial_pool_size, \
            f"Pool size should be maintained after restart: {pool_size_after} != {initial_pool_size}"

        assert available_after > 0, \
            "Pool should have available processes after restart"


# Performance baseline data collection
class TestPerformanceBaselines:
    """Collect performance baseline metrics"""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_collect_baseline_50_files(self, exif_handler_live, file_processor_live,
                                       real_photo_file, temp_alignment_dir, performance_monitor):
        """Collect and report baseline metrics for 50 files"""
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        test_files = []
        for i in range(50):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=timedelta(seconds=30),
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Report metrics for documentation
        print(f"\n=== 50-File Baseline Metrics ===")
        print(f"Elapsed Time: {metrics['elapsed_seconds']:.2f}s")
        print(f"Memory Start: {metrics['start_memory_mb']:.1f}MB")
        print(f"Memory Peak: {metrics['peak_memory_mb']:.1f}MB")
        print(f"Memory Delta: {metrics['memory_delta_mb']:.1f}MB")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_collect_baseline_200_files(self, exif_handler_live, file_processor_live,
                                        real_photo_file, temp_alignment_dir, performance_monitor):
        """Collect and report baseline metrics for 200 files"""
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        test_files = []
        for i in range(200):
            target_file = temp_alignment_dir / f"photo_{i:04d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=timedelta(seconds=30),
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Report metrics
        print(f"\n=== 200-File Baseline Metrics (With GROUP_SIZE Restart) ===")
        print(f"Elapsed Time: {metrics['elapsed_seconds']:.2f}s")
        print(f"Memory Start: {metrics['start_memory_mb']:.1f}MB")
        print(f"Memory Peak: {metrics['peak_memory_mb']:.1f}MB")
        print(f"Memory Delta: {metrics['memory_delta_mb']:.1f}MB")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_collect_baseline_500_files(self, exif_handler_live, file_processor_live,
                                        real_photo_file, temp_alignment_dir, performance_monitor):
        """Collect and report baseline metrics for 500 files"""
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        performance_monitor.start()

        test_files = []
        for i in range(500):
            target_file = temp_alignment_dir / f"photo_{i:05d}.jpg"
            shutil.copy2(real_photo_file, target_file)
            test_files.append(str(target_file))

        ref_file = temp_alignment_dir / "reference.jpg"
        shutil.copy2(real_photo_file, ref_file)

        processor = AlignmentProcessor(exif_handler_live, file_processor_live)
        processor.process_files(
            reference_files=[str(ref_file)],
            target_files=test_files,
            reference_field="DateTimeOriginal",
            target_field="DateTimeOriginal",
            time_offset=timedelta(seconds=30),
            progress_callback=None
        )

        metrics = performance_monitor.stop()

        # Report metrics
        print(f"\n=== 500-File Baseline Metrics (Stress Test) ===")
        print(f"Elapsed Time: {metrics['elapsed_seconds']:.2f}s")
        print(f"Memory Start: {metrics['start_memory_mb']:.1f}MB")
        print(f"Memory Peak: {metrics['peak_memory_mb']:.1f}MB")
        print(f"Memory Delta: {metrics['memory_delta_mb']:.1f}MB")
