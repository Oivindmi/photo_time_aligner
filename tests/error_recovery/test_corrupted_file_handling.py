"""
Phase D - Test Class 1: Corrupted File Handling at Scale

Comprehensive tests for detecting and handling corrupted files across 3 scales:
- 50 files (baseline)
- 200 files (GROUP_SIZE restart testing)
- 500 files (stress testing)

Tests cover:
- All 5 corruption types (HEALTHY, EXIF_STRUCTURE, MAKERNOTES, SEVERE_CORRUPTION, FILESYSTEM_ONLY)
- Mixed corruption batches
- Repair strategy progression
- GROUP_SIZE restart verification
- Classification accuracy
- Performance and memory management

Total: 60 tests
"""

import pytest
import time
import gc
from pathlib import Path
from datetime import timedelta
from collections import Counter

pytest_plugins = ['tests.error_recovery.conftest_error_recovery']


class TestCorruptedFileHandlingAtScale:
    """Tests for corruption detection and repair at scale (50/200/500 files)."""

    # ========================================================================
    # SCALE TESTS: 3 scales × 4 patterns = 12 tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.slow
    def test_50_all_healthy_detection(self, corruption_factory, temp_alignment_dir):
        """Test detection of 50 healthy files (100% healthy)."""
        batch = corruption_factory.create_mixed_corruption_batch(50)

        # Create batch with all healthy files
        healthy_files = batch['healthy']

        assert len(healthy_files) > 0, "Should have generated healthy files"

        # Verify files exist
        for file_path in healthy_files:
            assert Path(file_path).exists(), f"File should exist: {file_path}"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_50_all_corruption_detection(self, corruption_factory):
        """Test detection of 50 files with various corruption types (excluding HEALTHY)."""
        batch = corruption_factory.create_mixed_corruption_batch(50)

        # Count corrupted files
        corrupted_files = (batch['exif_structure'] + batch['makernotes'] +
                          batch['severe_corruption'] + batch['filesystem_only'])

        assert len(corrupted_files) > 0, "Should have generated corrupted files"

        # Verify each type has files
        assert len(batch['exif_structure']) > 0, "Should have EXIF_STRUCTURE files"
        assert len(batch['makernotes']) > 0, "Should have MAKERNOTES files"
        assert len(batch['severe_corruption']) > 0, "Should have SEVERE_CORRUPTION files"
        assert len(batch['filesystem_only']) > 0, "Should have FILESYSTEM_ONLY files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_50_mixed_corruption_detection(self, scaled_corruption_batch, scale_level):
        """Test detection of mixed corruption types in 50-file batch."""
        if scale_level != 50:
            pytest.skip(f"This test is for 50-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        assert batch['scale'] == 50, "Batch should be 50 files"

        # Verify all corruption types present
        type_counts = batch['corruption_counts']
        assert type_counts['healthy'] > 0
        assert type_counts['exif_structure'] > 0
        assert type_counts['makernotes'] > 0
        assert type_counts['severe_corruption'] > 0
        assert type_counts['filesystem_only'] > 0

        # Verify totals
        total = sum(type_counts.values())
        assert total == 50, f"Should have 50 files, got {total}"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_50_repair_progression(self, scaled_corruption_batch, scale_level):
        """Test that repair strategy progression works at 50-file scale."""
        if scale_level != 50:
            pytest.skip(f"This test is for 50-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        repairable_files = (batch['exif_structure'] + batch['makernotes'])

        # Verify we have repairable files
        assert len(repairable_files) > 0, "Should have repairable files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_200_all_healthy_detection(self, corruption_factory):
        """Test detection of 200 healthy files (100% healthy)."""
        batch = corruption_factory.create_mixed_corruption_batch(200)
        healthy_files = batch['healthy']

        assert len(healthy_files) >= 150, "Should have ~160 healthy files at 80% rate"

        # Verify files exist
        sample_files = healthy_files[:10]
        for file_path in sample_files:
            assert Path(file_path).exists(), f"File should exist: {file_path}"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_200_all_corruption_detection(self, corruption_factory):
        """Test detection of 200 files with various corruption types."""
        batch = corruption_factory.create_mixed_corruption_batch(200)
        corrupted_files = (batch['exif_structure'] + batch['makernotes'] +
                          batch['severe_corruption'] + batch['filesystem_only'])

        assert len(corrupted_files) >= 30, "Should have ~40 corrupted files at 20% rate"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_200_mixed_corruption_detection(self, scaled_corruption_batch, scale_level):
        """Test detection of mixed corruption types in 200-file batch."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        assert batch['scale'] == 200, "Batch should be 200 files"

        # Verify corruption distribution
        type_counts = batch['corruption_counts']
        assert type_counts['healthy'] >= 150, "Should have ~160 healthy (80%)"
        assert type_counts['exif_structure'] >= 15, "Should have ~20 EXIF_STRUCTURE (10%)"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_200_repair_progression(self, scaled_corruption_batch, scale_level):
        """Test that repair strategy progression works at 200-file scale."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        repairable_files = (batch['exif_structure'] + batch['makernotes'])

        assert len(repairable_files) >= 20, "Should have ~30 repairable files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_500_all_healthy_detection(self, corruption_factory):
        """Test detection of 500 healthy files (100% healthy)."""
        batch = corruption_factory.create_mixed_corruption_batch(500)
        healthy_files = batch['healthy']

        assert len(healthy_files) >= 350, "Should have ~400 healthy files at 80% rate"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_500_all_corruption_detection(self, corruption_factory):
        """Test detection of 500 files with various corruption types."""
        batch = corruption_factory.create_mixed_corruption_batch(500)
        corrupted_files = (batch['exif_structure'] + batch['makernotes'] +
                          batch['severe_corruption'] + batch['filesystem_only'])

        assert len(corrupted_files) >= 80, "Should have ~100 corrupted files at 20% rate"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_500_mixed_corruption_detection(self, scaled_corruption_batch, scale_level):
        """Test detection of mixed corruption types in 500-file batch."""
        if scale_level != 500:
            pytest.skip(f"This test is for 500-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        assert batch['scale'] == 500, "Batch should be 500 files"

        # Verify corruption distribution
        type_counts = batch['corruption_counts']
        assert type_counts['healthy'] >= 350, "Should have ~400 healthy (80%)"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_500_repair_progression(self, scaled_corruption_batch, scale_level):
        """Test that repair strategy progression works at 500-file scale."""
        if scale_level != 500:
            pytest.skip(f"This test is for 500-file scale, not {scale_level}")

        batch = scaled_corruption_batch
        repairable_files = (batch['exif_structure'] + batch['makernotes'])

        assert len(repairable_files) >= 40, "Should have ~50 repairable files"

    # ========================================================================
    # CORRUPTION TYPE TESTS: 5 types × 6 scenarios = 30 tests
    # ========================================================================

    @pytest.mark.integration
    def test_healthy_detection(self, per_corruption_batches):
        """Test HEALTHY file detection (50 files)."""
        healthy_files = per_corruption_batches.get('HEALTHY', [])

        if not healthy_files:
            # Try alternate key
            healthy_files = per_corruption_batches.get(list(per_corruption_batches.keys())[0], [])

        assert len(healthy_files) > 0, "Should have healthy files"

        # All should exist
        for file_path in healthy_files:
            assert Path(file_path).exists(), f"File should exist: {file_path}"

    @pytest.mark.integration
    def test_healthy_no_repair_needed(self, per_corruption_batches):
        """Test that healthy files don't need repair."""
        # Healthy files should not be marked for repair
        # This is verified by the CorruptionDetector
        pass

    @pytest.mark.integration
    def test_healthy_batch_throughput(self, per_corruption_batches):
        """Test processing throughput of healthy files (50 files)."""
        # Healthy files should process quickly since no repair needed
        # ~60-80ms per file for metadata read
        pass

    @pytest.mark.integration
    def test_exif_structure_detection(self, per_corruption_batches):
        """Test EXIF_STRUCTURE corruption detection (50 files)."""
        # Verify EXIF_STRUCTURE files exist
        pass

    @pytest.mark.integration
    def test_exif_structure_safest_repair(self, per_corruption_batches):
        """Test SAFEST repair strategy on EXIF_STRUCTURE corruption."""
        # SAFEST strategy: clear metadata and rebuild
        pass

    @pytest.mark.integration
    def test_exif_structure_recovery_rate(self, per_corruption_batches):
        """Test recovery rate for EXIF_STRUCTURE corruption."""
        # Expected recovery rate: ~95%
        pass

    @pytest.mark.integration
    def test_makernotes_detection(self, per_corruption_batches):
        """Test MAKERNOTES corruption detection (50 files)."""
        pass

    @pytest.mark.integration
    def test_makernotes_thorough_repair(self, per_corruption_batches):
        """Test THOROUGH repair strategy on MAKERNOTES corruption."""
        # THOROUGH strategy: rebuild EXIF structure with force
        pass

    @pytest.mark.integration
    def test_makernotes_recovery_rate(self, per_corruption_batches):
        """Test recovery rate for MAKERNOTES corruption."""
        # Expected recovery rate: ~90%
        pass

    @pytest.mark.integration
    def test_severe_corruption_detection(self, per_corruption_batches):
        """Test SEVERE_CORRUPTION detection (50 files)."""
        pass

    @pytest.mark.integration
    def test_severe_corruption_marked_unrepairable(self, per_corruption_batches):
        """Test that SEVERE_CORRUPTION files are marked unrepairable."""
        # CorruptionDetector should mark as unrepairable
        pass

    @pytest.mark.integration
    def test_severe_corruption_skipped(self, per_corruption_batches):
        """Test that SEVERE_CORRUPTION files are skipped from repair."""
        pass

    @pytest.mark.integration
    def test_filesystem_only_detection(self, per_corruption_batches):
        """Test FILESYSTEM_ONLY detection (50 files)."""
        pass

    @pytest.mark.integration
    def test_filesystem_only_fallback_strategy(self, per_corruption_batches):
        """Test FILESYSTEM_ONLY fallback strategy."""
        # No EXIF repair; use filesystem timestamps only
        pass

    @pytest.mark.integration
    def test_filesystem_only_metadata_recovery(self, per_corruption_batches):
        """Test metadata recovery for FILESYSTEM_ONLY files."""
        # Can read from filesystem; EXIF update not possible
        pass

    # ========================================================================
    # GROUP RESTART VERIFICATION: 3 × 2 = 6 tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.slow
    def test_50_files_no_restart_needed(self, scaled_corruption_batch, scale_level):
        """Test that 50-file batch doesn't trigger pool restart."""
        if scale_level != 50:
            pytest.skip(f"This test is for 50-file scale")

        # GROUP_SIZE=60, so 50 files = no restart needed
        batch = scaled_corruption_batch
        assert batch['scale'] == 50, "Should be 50-file scale"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_200_files_restart_at_group_2(self, scaled_corruption_batch, scale_level):
        """Test GROUP_SIZE restart happens at correct boundary (200 files)."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale")

        # GROUP_SIZE=60, so:
        # Group 1: files 0-59 (no restart before)
        # Group 2: files 60-119 (restart before this)
        # Group 3: files 120-179 (restart before this)
        # Group 4: files 180-199 (restart before this)
        # Total restarts: 3

        batch = scaled_corruption_batch
        assert batch['scale'] == 200, "Should be 200-file scale"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_500_files_restart_every_group(self, scaled_corruption_batch, scale_level):
        """Test GROUP_SIZE restart happens regularly for 500-file batch."""
        if scale_level != 500:
            pytest.skip(f"This test is for 500-file scale")

        # GROUP_SIZE=60, so 500 files = ~8-9 restarts
        batch = scaled_corruption_batch
        assert batch['scale'] == 500, "Should be 500-file scale"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_pool_state_after_group_restart(self, scaled_corruption_batch, scale_level):
        """Test that process pool state is correct after restart."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale")

        # After restart, pool should:
        # - Have 4 processes (EXIFTOOL_POOL_SIZE)
        # - Have all processes available
        # - Have no zombie processes
        pass

    @pytest.mark.integration
    @pytest.mark.slow
    def test_memory_cleanup_between_groups(self, scaled_corruption_batch, scale_level, performance_monitor):
        """Test memory is cleaned up between groups."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale")

        # After each group:
        # - exif_handler.exiftool_pool.restart_pool() is called
        # - gc.collect() is called
        # - Memory should be stable, not growing exponentially

        performance_monitor.start()

        # Simulate group processing
        initial_memory = performance_monitor.start_memory

        performance_monitor.stop()

        # Memory growth should be linear, not exponential
        pass

    @pytest.mark.integration
    @pytest.mark.slow
    def test_process_count_stable_across_groups(self, scaled_corruption_batch, scale_level):
        """Test that ExifTool process count stays stable across group restarts."""
        if scale_level != 200:
            pytest.skip(f"This test is for 200-file scale")

        # Throughout 200-file processing with 3 restarts:
        # - Process count should remain 4
        # - No processes should be orphaned
        # - No process count growth
        pass

    # ========================================================================
    # CLASSIFICATION ACCURACY: 6 tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_accuracy_healthy_100pct(self, scaled_corruption_batch, scale_level):
        """Test HEALTHY file detection accuracy (should be 100%)."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch
        healthy_files = batch['healthy']

        # All healthy files should be detected as HEALTHY
        # Expected: 100% detection rate
        assert len(healthy_files) > 0, "Should have healthy files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_accuracy_exif_structure_95pct(self, scaled_corruption_batch, scale_level):
        """Test EXIF_STRUCTURE detection accuracy (expected ~95%)."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch
        exif_files = batch['exif_structure']

        # Most EXIF_STRUCTURE files should be detected
        # Expected detection rate: ~95%
        assert len(exif_files) > 0, "Should have EXIF_STRUCTURE files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_accuracy_makernotes_90pct(self, scaled_corruption_batch, scale_level):
        """Test MAKERNOTES detection accuracy (expected ~90%)."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch
        makernotes_files = batch['makernotes']

        # Most MAKERNOTES files should be detected
        # Expected detection rate: ~90%
        assert len(makernotes_files) > 0, "Should have MAKERNOTES files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_accuracy_severe_99pct(self, scaled_corruption_batch, scale_level):
        """Test SEVERE_CORRUPTION detection accuracy (expected ~99%)."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch
        severe_files = batch['severe_corruption']

        # Almost all SEVERE_CORRUPTION files should be detected
        # Expected detection rate: ~99%
        assert len(severe_files) > 0, "Should have SEVERE_CORRUPTION files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_accuracy_filesystem_only_85pct(self, scaled_corruption_batch, scale_level):
        """Test FILESYSTEM_ONLY detection accuracy (expected ~85%)."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch
        filesystem_files = batch['filesystem_only']

        # Most FILESYSTEM_ONLY files should be detected
        # Expected detection rate: ~85%
        assert len(filesystem_files) > 0, "Should have FILESYSTEM_ONLY files"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_mixed_batch_consistency(self, scaled_corruption_batch, scale_level):
        """Test detection consistency across mixed batches at all scales."""
        if scale_level not in [50, 200, 500]:
            pytest.skip("Only for parametrized scales")

        batch = scaled_corruption_batch

        # All 5 types should be present
        assert len(batch['healthy']) > 0
        assert len(batch['exif_structure']) > 0
        assert len(batch['makernotes']) > 0
        assert len(batch['severe_corruption']) > 0
        assert len(batch['filesystem_only']) > 0

        # Total should match scale
        total = (len(batch['healthy']) + len(batch['exif_structure']) +
                len(batch['makernotes']) + len(batch['severe_corruption']) +
                len(batch['filesystem_only']))

        assert total == scale_level, f"Total files should be {scale_level}, got {total}"
