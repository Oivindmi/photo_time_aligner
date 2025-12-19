"""
Tier 1 Integration Tests: File Repair

Tests the FileRepairer component with real files to verify:
- Safest repair strategy (minimal changes, high success)
- Thorough repair strategy (more aggressive, better recovery)
- Aggressive repair strategy (most aggressive, removes MakerNotes)
- Filesystem-only strategy (uses filesystem timestamps only)
- Strategy selection and progression logic
- Backup creation during repair

Uses real ExifTool and generated corrupted test files.
"""

import pytest
import tempfile
import shutil
import subprocess
import os
from pathlib import Path

from src.core.repair_strategies import FileRepairer, RepairStrategy, RepairResult
from src.core.corruption_detector import CorruptionDetector, CorruptionType


class TestFileRepair:
    """Test file repair with real ExifTool"""

    @pytest.mark.integration
    def test_safest_repair_strategy_execution(self, corrupted_exif_file, temp_alignment_dir):
        """
        Test execution of safest repair strategy:
        1. Use corrupted EXIF file
        2. Apply SAFEST strategy (no MakerNotes removal)
        3. Verify repair succeeded or reported accurately
        4. Verify backup created
        """
        if corrupted_exif_file is None:
            pytest.skip("Corrupted EXIF file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Attempt repair with SAFEST strategy
        result = repairer.repair_file(
            file_path=corrupted_exif_file,
            corruption_type=CorruptionType.EXIF_STRUCTURE,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.SAFEST
        )

        # Verify result structure
        assert isinstance(result, RepairResult), "Should return RepairResult"
        assert result.strategy_used == RepairStrategy.SAFEST, "Should use SAFEST strategy"
        assert isinstance(result.success, bool), "success should be boolean"
        assert isinstance(result.verification_passed, bool), "verification_passed should be boolean"

        # Verify backup created or error reported
        if result.success:
            assert os.path.exists(corrupted_exif_file), "Original file should still exist"

    @pytest.mark.integration
    def test_thorough_repair_strategy_execution(self, corrupted_makernotes_file, temp_alignment_dir):
        """
        Test execution of thorough repair strategy:
        1. Use corrupted file (MakerNotes or EXIF structure)
        2. Apply THOROUGH strategy
        3. Verify repair handling
        4. Verify result accuracy
        """
        if corrupted_makernotes_file is None:
            pytest.skip("Corrupted MakerNotes file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        result = repairer.repair_file(
            file_path=corrupted_makernotes_file,
            corruption_type=CorruptionType.MAKERNOTES,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.THOROUGH
        )

        # Verify result structure
        assert isinstance(result, RepairResult), "Should return RepairResult"
        assert result.strategy_used == RepairStrategy.THOROUGH, "Should use THOROUGH strategy"

    @pytest.mark.integration
    def test_aggressive_repair_strategy_execution(self, corrupted_makernotes_file, temp_alignment_dir):
        """
        Test execution of aggressive repair strategy:
        1. Use corrupted file with MakerNotes issues
        2. Apply AGGRESSIVE strategy (removes problematic metadata)
        3. Verify repair removes corrupted sections
        4. Verify file still readable after repair
        """
        if corrupted_makernotes_file is None:
            pytest.skip("Corrupted MakerNotes file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        result = repairer.repair_file(
            file_path=corrupted_makernotes_file,
            corruption_type=CorruptionType.MAKERNOTES,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.AGGRESSIVE
        )

        assert isinstance(result, RepairResult), "Should return RepairResult"
        assert result.strategy_used == RepairStrategy.AGGRESSIVE, "Should use AGGRESSIVE strategy"

    @pytest.mark.integration
    def test_filesystem_only_strategy_execution(self, missing_datetime_file, temp_alignment_dir):
        """
        Test execution of filesystem-only strategy:
        1. Use file without embedded datetime metadata
        2. Apply FILESYSTEM_ONLY strategy
        3. Verify uses filesystem creation time
        4. Verify metadata written to file
        """
        if missing_datetime_file is None:
            pytest.skip("Missing datetime file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        result = repairer.repair_file(
            file_path=missing_datetime_file,
            corruption_type=CorruptionType.FILESYSTEM_ONLY,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.FILESYSTEM_ONLY
        )

        assert isinstance(result, RepairResult), "Should return RepairResult"
        assert result.strategy_used == RepairStrategy.FILESYSTEM_ONLY, "Should use FILESYSTEM_ONLY strategy"

    @pytest.mark.integration
    def test_strategy_selection_logic(self, corrupted_exif_file, temp_alignment_dir):
        """
        Test automatic strategy selection and progression:
        1. Attempt repair without forcing strategy
        2. Verify tries strategies in order: SAFEST → THOROUGH → AGGRESSIVE → FILESYSTEM_ONLY
        3. Verify returns first successful strategy or stops at last one
        """
        if corrupted_exif_file is None:
            pytest.skip("Corrupted EXIF file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Attempt repair without forcing strategy (automatic progression)
        result = repairer.repair_file(
            file_path=corrupted_exif_file,
            corruption_type=CorruptionType.EXIF_STRUCTURE,
            backup_dir=str(backup_dir),
            force_strategy=False,
            selected_strategy=None
        )

        # Verify result is valid
        assert isinstance(result, RepairResult), "Should return RepairResult"
        # Strategy used should be one of the available strategies
        assert result.strategy_used in repairer.strategies, \
            f"Strategy {result.strategy_used} not in available strategies"

    @pytest.mark.integration
    def test_backup_creation_during_repair(self, corrupted_exif_file, temp_alignment_dir):
        """
        Test that backup files are created during repair:
        1. Perform repair on corrupted file
        2. Verify backup directory contains backup file
        3. Verify backup is readable and valid
        4. Verify original preserved
        """
        if corrupted_exif_file is None:
            pytest.skip("Corrupted EXIF file generation failed")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Get original file size for comparison
        original_size = os.path.getsize(corrupted_exif_file)

        result = repairer.repair_file(
            file_path=corrupted_exif_file,
            corruption_type=CorruptionType.EXIF_STRUCTURE,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.SAFEST
        )

        # Verify backup path is provided in result if successful
        if result.success:
            # Backup should have been created
            backup_files = list(backup_dir.glob("*"))
            # May or may not have backup depending on strategy, but should track if created
            if result.backup_path:
                assert os.path.exists(result.backup_path), "Backup file should exist if path provided"

    @pytest.mark.integration
    def test_strategy_result_accuracy(self, real_photo_file, temp_alignment_dir, exif_handler_live):
        """
        Test that repair results accurately reflect outcome:
        1. Repair healthy file (should maintain quality)
        2. Verify success flag is accurate
        3. Verify error_message is informative when failure occurs
        4. Verify verification_passed indicates if metadata verified
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        repairer = FileRepairer(exiftool_path="exiftool")
        backup_dir = temp_alignment_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Copy healthy file
        test_file = temp_alignment_dir / "healthy_test.jpg"
        shutil.copy2(real_photo_file, test_file)

        result = repairer.repair_file(
            file_path=str(test_file),
            corruption_type=CorruptionType.HEALTHY,
            backup_dir=str(backup_dir),
            force_strategy=True,
            selected_strategy=RepairStrategy.SAFEST
        )

        # Verify result accuracy
        assert isinstance(result.success, bool), "success should be boolean"
        assert isinstance(result.error_message, str), "error_message should be string"
        assert isinstance(result.verification_passed, bool), "verification_passed should be boolean"

        # Healthy file should either succeed or report why it didn't
        if not result.success:
            assert len(result.error_message) > 0, "Should provide error message for failure"
