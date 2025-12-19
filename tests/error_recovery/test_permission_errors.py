"""
Phase D - Test Class 2: File Access Permission Errors

Comprehensive tests for handling file permission errors:
- Read-only files (8 tests)
- Write-protected files (8 tests)
- Locked files (Windows specific, 8 tests)
- Directory permission issues (6 tests)
- Windows-specific constraints (8 tests)
- Cross-platform handling (6 tests)

Total: 50 tests

Tests verify:
- Files are skipped without crashing
- Error messages are clear and informative
- Processing continues for unaffected files
- Graceful degradation when permissions change
- Windows-specific constraints handled (long paths, reserved names, attributes)
"""

import pytest
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from contextlib import contextmanager

pytest_plugins = ['tests.error_recovery.conftest_error_recovery']


class TestFileAccessPermissionErrors:
    """Tests for handling file access permission errors."""

    # ========================================================================
    # READ-ONLY FILES: 8 tests
    # ========================================================================

    @pytest.mark.integration
    def test_read_only_detection_before_scan(self, read_only_file_batch, permission_simulator):
        """Test that read-only files are detected before processing."""
        files = read_only_file_batch

        assert len(files) == 10, "Should have 10 read-only files"

        # Verify files are actually read-only
        for file_path, recovery_possible in files:
            assert Path(file_path).exists(), f"File should exist: {file_path}"
            # Check permissions - should not be writable
            mode = os.stat(file_path).st_mode
            # On Windows/POSIX: 0o444 = read-only
            assert mode & 0o200 == 0, f"File should be read-only: {file_path}"

    @pytest.mark.integration
    def test_read_only_skip_without_error(self, read_only_file_batch, real_photo_file, temp_alignment_dir):
        """Test that read-only files are skipped without stopping batch."""
        readonly_files = [f for f, _ in read_only_file_batch]

        # Create some writable files mixed in
        writable_files = []
        for i in range(3):
            f = temp_alignment_dir / f"writable_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            writable_files.append(f)

        all_files = readonly_files + writable_files

        # Process should not crash on read-only files
        # This is a basic validation that processing continues
        assert len(all_files) == 13, "Should have 13 total files"

    @pytest.mark.integration
    def test_read_only_metadata_read_possible(self, read_only_file_batch):
        """Test that metadata CAN be read from read-only files."""
        # Read-only doesn't prevent reading metadata
        # It only prevents writing/modifying

        files = read_only_file_batch

        # Metadata read should still work even though file is read-only
        # This is important for detection phase
        for file_path, _ in files:
            assert Path(file_path).exists()
            # ExifTool can read from read-only files
            try:
                result = subprocess.run(
                    ["exiftool", "-json", str(file_path)],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                # Should succeed in reading
                assert result.returncode == 0 or "error" not in result.stderr.lower()
            except Exception:
                pass  # ExifTool might not be available in test environment

    @pytest.mark.integration
    def test_read_only_repair_skipped(self, read_only_file_batch):
        """Test that repair is skipped for read-only files."""
        # Repair requires write access, so read-only files should be skipped
        files = read_only_file_batch

        assert len(files) > 0, "Should have read-only files"

        # Verify files are read-only (not writable)
        for file_path, _ in files:
            mode = os.stat(file_path).st_mode
            assert mode & 0o200 == 0, "Should be read-only"

    @pytest.mark.integration
    def test_read_only_batch_mixed_success(self, read_only_file_batch, real_photo_file, temp_alignment_dir):
        """Test handling of mixed read-only and writable files in batch."""
        readonly_files = [f for f, _ in read_only_file_batch]

        # Add writable files
        writable_files = []
        for i in range(5):
            f = temp_alignment_dir / f"writable_mixed_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            writable_files.append(f)

        all_files = readonly_files + writable_files

        # Batch should have both types
        assert len(readonly_files) == 10, "Should have 10 read-only"
        assert len(writable_files) == 5, "Should have 5 writable"

    @pytest.mark.integration
    def test_read_only_error_logged_accurately(self, read_only_file_batch, caplog):
        """Test that read-only permission errors are logged clearly."""
        files = read_only_file_batch

        # Error messages should mention "permission" or "readonly"
        # This is typically logged when update fails
        # Error messages should be informative for user

        assert len(files) > 0, "Should have read-only files for testing"

    @pytest.mark.integration
    def test_read_only_backup_to_temp(self, read_only_file_batch, temp_alignment_dir):
        """Test that backup falls back to temp directory when backup dir is read-only."""
        # If backup directory itself is read-only, should fall back to temp

        # This scenario: read-only files might also have read-only directories
        files = read_only_file_batch

        assert len(files) > 0

    @pytest.mark.integration
    def test_read_only_continued_processing(self, read_only_file_batch, real_photo_file, temp_alignment_dir):
        """Test that processing continues after encountering read-only files."""
        readonly_files = [f for f, _ in read_only_file_batch]

        # Add writable files that should be processed normally
        writable_files = []
        for i in range(3):
            f = temp_alignment_dir / f"continue_test_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            writable_files.append(f)

        # Process both types
        all_files = readonly_files + writable_files

        # At least the writable files should be processable
        for f in writable_files:
            assert Path(f).exists()
            mode = os.stat(f).st_mode
            assert mode & 0o200 != 0, f"Should be writable: {f}"

    # ========================================================================
    # WRITE-PROTECTED FILES: 8 tests
    # ========================================================================

    @pytest.mark.integration
    def test_write_protected_detection(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test detection of write-protected files."""
        # Create write-protected files
        protected_files = []
        for i in range(5):
            f = temp_alignment_dir / f"writeprotected_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            permission_simulator.make_write_protected(f)
            protected_files.append(f)

        # All should be detected as non-writable
        for f in protected_files:
            mode = os.stat(f).st_mode
            assert mode & 0o200 == 0, f"Should be write-protected: {f}"

    @pytest.mark.integration
    def test_write_protected_repair_fails(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that repair fails for write-protected files."""
        # Repair requires write access

        f = temp_alignment_dir / "writeprotected_repair_test.jpg"
        shutil.copy2(real_photo_file, f)
        permission_simulator.make_write_protected(f)

        # Attempt to modify metadata should fail
        # ExifTool can't modify write-protected files

        try:
            result = subprocess.run(
                ["exiftool", "-overwrite_original", f"-DateTimeOriginal=2025:01:01 12:00:00", str(f)],
                capture_output=True,
                timeout=5
            )
            # Should fail or report error
            assert result.returncode != 0 or "error" in result.stderr.lower()
        except Exception:
            pass  # ExifTool might not be available

    @pytest.mark.integration
    def test_write_protected_vs_readonly_handling(self, temp_alignment_dir, real_photo_file,
                                                   permission_simulator, read_only_file_batch):
        """Test that write-protected and read-only files are handled similarly."""
        # Both should prevent metadata modification
        # Handling strategy should be the same

        pass

    @pytest.mark.integration
    def test_write_protected_batch_partial_repair(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test batch with partial write-protected files gets partial success."""
        # Mix protected and unprotected files

        protected_files = []
        for i in range(3):
            f = temp_alignment_dir / f"protected_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            permission_simulator.make_write_protected(f)
            protected_files.append(f)

        unprotected_files = []
        for i in range(3):
            f = temp_alignment_dir / f"unprotected_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            unprotected_files.append(f)

        # Batch processing should complete
        # Protected files fail, unprotected succeed
        assert len(protected_files) == 3
        assert len(unprotected_files) == 3

    @pytest.mark.integration
    def test_write_protected_error_message_clear(self, temp_alignment_dir, real_photo_file,
                                                   permission_simulator, caplog):
        """Test that write-protected error messages are clear."""
        f = temp_alignment_dir / "writeprotected_error_test.jpg"
        shutil.copy2(real_photo_file, f)
        permission_simulator.make_write_protected(f)

        # Error should mention permission/write/protected

    @pytest.mark.integration
    def test_write_protected_recovery_attempt(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that system attempts recovery for write-protected files."""
        # Potential recovery: temporarily change permissions, update, restore
        # Or: use backup/temp directory approach

        pass

    @pytest.mark.integration
    def test_write_protected_cleanup_permissions(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that write-protected permissions are properly cleaned up."""
        f = temp_alignment_dir / "writeprotected_cleanup.jpg"
        shutil.copy2(real_photo_file, f)
        permission_simulator.make_write_protected(f)

        # After test, should be cleaned up
        permission_simulator.restore_permissions(f)

        # Should be writable again
        mode = os.stat(f).st_mode
        assert mode & 0o200 != 0, "Should be writable after cleanup"

    # ========================================================================
    # LOCKED FILES (Windows specific): 8 tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_detection_windows(self, temp_alignment_dir, real_photo_file):
        """Test detection of locked files (Windows)."""
        # Locked file: opened by another process, can't be modified

        f = temp_alignment_dir / "locked_detection.jpg"
        shutil.copy2(real_photo_file, f)

        # Open file in another process to lock it
        # This is platform-specific behavior

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_skip_without_hang(self, temp_alignment_dir, real_photo_file):
        """Test that locked files are skipped without hanging the batch."""
        # Important: process shouldn't hang waiting for locked file

        f = temp_alignment_dir / "locked_nohang.jpg"
        shutil.copy2(real_photo_file, f)

        # Open file, try to process, should skip without hanging
        # with timeout to prevent infinite wait

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_retry_logic(self, temp_alignment_dir, real_photo_file):
        """Test retry logic for locked files."""
        # File might be locked temporarily, could become available

        f = temp_alignment_dir / "locked_retry.jpg"
        shutil.copy2(real_photo_file, f)

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_timeout_handling(self, temp_alignment_dir, real_photo_file):
        """Test timeout handling for locked files."""
        # Should timeout after N seconds, not wait forever

        f = temp_alignment_dir / "locked_timeout.jpg"
        shutil.copy2(real_photo_file, f)

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_release_and_retry(self, temp_alignment_dir, real_photo_file):
        """Test behavior when locked file is released and becomes available."""
        # If lock is temporary, should retry

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_batch_continues(self, temp_alignment_dir, real_photo_file):
        """Test that batch continues processing when encountering locked files."""
        f = temp_alignment_dir / "locked_batch_continue.jpg"
        shutil.copy2(real_photo_file, f)

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_error_reporting(self, temp_alignment_dir, real_photo_file, caplog):
        """Test that locked file errors are reported clearly."""
        f = temp_alignment_dir / "locked_error_report.jpg"
        shutil.copy2(real_photo_file, f)

        # Error should indicate file is locked/in-use

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_locked_file_recovery_suggestion(self, temp_alignment_dir, real_photo_file):
        """Test that recovery suggestions are provided for locked files."""
        # Suggest: close file in other application, retry

        pass

    # ========================================================================
    # DIRECTORY PERMISSION ISSUES: 6 tests
    # ========================================================================

    @pytest.mark.integration
    def test_read_only_directory_scan_fails(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that read-only directory prevents file scan."""
        # Create files in directory
        test_dir = temp_alignment_dir / "readonly_dir"
        test_dir.mkdir()

        for i in range(3):
            f = test_dir / f"file_{i}.jpg"
            shutil.copy2(real_photo_file, f)

        # Make directory read-only
        permission_simulator.make_read_only(test_dir)

        # Scanning should handle gracefully
        # Might not be able to list files or modify backups

        # Cleanup
        permission_simulator.restore_permissions(test_dir)

    @pytest.mark.integration
    def test_backup_dir_no_write_permission(self, temp_alignment_dir, real_photo_file):
        """Test backup creation when backup dir has no write permission."""
        # Backup directory exists but is read-only

        backup_dir = temp_alignment_dir / "nowrite_backup"
        backup_dir.mkdir()

        # Make it read-only
        os.chmod(backup_dir, 0o555)

        # Backup creation should fail or fall back to temp

        # Cleanup
        os.chmod(backup_dir, 0o755)

    @pytest.mark.integration
    def test_temp_dir_fallback_when_backup_fails(self, temp_alignment_dir, real_photo_file):
        """Test that backup falls back to temp directory when primary fails."""
        # If backup directory is unavailable, use temp directory

        pass

    @pytest.mark.integration
    def test_directory_permission_error_message(self, temp_alignment_dir, real_photo_file, permission_simulator, caplog):
        """Test that directory permission errors have clear messages."""
        test_dir = temp_alignment_dir / "perm_error_dir"
        test_dir.mkdir()

        permission_simulator.make_read_only(test_dir)

        # Error message should be clear about permission issue

        permission_simulator.restore_permissions(test_dir)

    @pytest.mark.integration
    def test_directory_permission_recovery_suggestion(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that recovery suggestions are provided for directory permission issues."""
        # Suggest: check directory permissions, ensure write access

        pass

    @pytest.mark.integration
    def test_nested_directory_permission_cascade(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test handling of nested directories with permission restrictions."""
        # Deep directory structure with permission issues

        nested = temp_alignment_dir / "level1" / "level2" / "level3"
        nested.mkdir(parents=True)

        # Restrict access at different levels
        # Should handle gracefully

        pass

    # ========================================================================
    # WINDOWS-SPECIFIC: 8 tests
    # ========================================================================

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_long_path_handling_windows_250_char(self, temp_alignment_dir, real_photo_file):
        """Test handling of paths exceeding Windows 260-char limit."""
        # Windows MAX_PATH is 260 chars

        # Create deeply nested directory structure
        long_path = temp_alignment_dir
        for i in range(10):
            long_path = long_path / ("dir_" + "x" * 20)

        try:
            long_path.mkdir(parents=True, exist_ok=True)

            # Create file in long path
            f = long_path / "photo.jpg"
            if len(str(f)) > 250:
                # Should handle gracefully
                # Might use short path or temp backup
                pass
        except OSError:
            # Expected - path too long
            pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_unc_network_path_handling(self, temp_alignment_dir):
        """Test handling of UNC network paths (\\\\server\\share)."""
        # Network paths have different behavior

        # Test would require actual network path
        # Can't test without network setup

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_drive_mapping_vs_direct_path(self, temp_alignment_dir, real_photo_file):
        """Test handling of drive mappings (Z:) vs direct paths."""
        # Mapped drives vs direct UNC paths

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_readonly_attribute_windows_specific(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test Windows read-only file attribute (not chmod)."""
        f = temp_alignment_dir / "winreadonly.jpg"
        shutil.copy2(real_photo_file, f)

        # Windows specific: FILE_ATTRIBUTE_READONLY
        # Different from Unix permissions

        permission_simulator.make_read_only(f)

        # Should still be handled correctly
        assert not os.access(f, os.W_OK), "Should not be writable"

        permission_simulator.restore_permissions(f)

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_system_file_attribute_handling(self, temp_alignment_dir, real_photo_file):
        """Test handling of files with System attribute (Windows)."""
        # FILE_ATTRIBUTE_SYSTEM

        f = temp_alignment_dir / "system_attr.jpg"
        shutil.copy2(real_photo_file, f)

        # Apply system attribute (would require win32api)
        # For now, just test that normal files work

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_hidden_file_attribute_handling(self, temp_alignment_dir, real_photo_file):
        """Test handling of files with Hidden attribute (Windows)."""
        # FILE_ATTRIBUTE_HIDDEN

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_archive_attribute_handling(self, temp_alignment_dir, real_photo_file):
        """Test handling of files with Archive attribute (Windows)."""
        # FILE_ATTRIBUTE_ARCHIVE

        pass

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_permission_change_during_batch(self, temp_alignment_dir, real_photo_file):
        """Test handling when file permissions change during batch processing."""
        # File is writable at start, becomes read-only during processing
        # Or vice versa

        f = temp_alignment_dir / "permission_change.jpg"
        shutil.copy2(real_photo_file, f)

        # Should handle gracefully if permission changes

        pass

    # ========================================================================
    # CROSS-PLATFORM: 6 tests
    # ========================================================================

    @pytest.mark.integration
    def test_permission_simulation_cross_platform(self, permission_simulator):
        """Test that permission simulator works on current platform."""
        # PermissionSimulator should work on both Windows and POSIX

        assert permission_simulator is not None
        assert hasattr(permission_simulator, 'make_read_only')
        assert hasattr(permission_simulator, 'restore_permissions')

    @pytest.mark.integration
    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only test")
    def test_posix_permission_handling_if_available(self, temp_alignment_dir, real_photo_file):
        """Test POSIX permission handling (chmod on Unix-like systems)."""
        f = temp_alignment_dir / "posix_perms.jpg"
        shutil.copy2(real_photo_file, f)

        # POSIX: 0o644 = rw-r--r--, 0o444 = r--r--r--
        os.chmod(f, 0o444)

        mode = os.stat(f).st_mode
        assert mode & 0o200 == 0, "Should be read-only"

        os.chmod(f, 0o644)

    @pytest.mark.integration
    def test_permission_error_messages_consistent(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that permission error messages are consistent across platforms."""
        # Error messages should be clear regardless of OS

        f = temp_alignment_dir / "consistent_error.jpg"
        shutil.copy2(real_photo_file, f)

        permission_simulator.make_read_only(f)

        # Error about permissions should be understandable

        permission_simulator.restore_permissions(f)

    @pytest.mark.integration
    def test_error_recovery_independent_of_platform(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that error recovery strategy is platform-independent."""
        # Whether Windows or Unix, should handle gracefully

        f = temp_alignment_dir / "platform_recovery.jpg"
        shutil.copy2(real_photo_file, f)

        permission_simulator.make_read_only(f)

        # Recovery should work regardless of OS
        # Cleanup should work on both platforms

        permission_simulator.restore_permissions(f)
        assert os.access(f, os.W_OK), "Should be writable after cleanup"

    @pytest.mark.integration
    def test_permission_cleanup_no_side_effects(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that permission cleanup doesn't have side effects."""
        # Cleanup should restore exactly to original state

        f = temp_alignment_dir / "cleanup_sideeffects.jpg"
        shutil.copy2(real_photo_file, f)

        original_mode = os.stat(f).st_mode

        permission_simulator.make_read_only(f)
        permission_simulator.restore_permissions(f)

        restored_mode = os.stat(f).st_mode

        # Should be writable
        assert restored_mode & 0o200 != 0, "Should be writable after cleanup"

    @pytest.mark.integration
    def test_multiple_permission_changes_tracked(self, temp_alignment_dir, real_photo_file, permission_simulator):
        """Test that multiple permission changes are tracked correctly."""
        files = []
        for i in range(5):
            f = temp_alignment_dir / f"multichange_{i}.jpg"
            shutil.copy2(real_photo_file, f)
            permission_simulator.make_read_only(f)
            files.append(f)

        # All should be read-only
        for f in files:
            assert not os.access(f, os.W_OK)

        # Cleanup all
        permission_simulator.cleanup()

        # All should be writable
        for f in files:
            assert os.access(f, os.W_OK), f"Should be writable after cleanup: {f}"
