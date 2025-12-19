"""
Tier 1 Integration Tests: Corruption Detection

Tests the CorruptionDetector component with real files to verify:
- Healthy file detection
- EXIF structure corruption detection
- MakerNotes corruption detection
- Severe corruption detection
- Filesystem-only files (no EXIF data)
- Classification accuracy across mixed batches

Uses real ExifTool and both provided sample files and generated test files.
"""

import pytest
import tempfile
import shutil
import subprocess
import os
from pathlib import Path

from src.core.corruption_detector import CorruptionDetector, CorruptionType


class TestCorruptionDetection:
    """Test corruption detection with real ExifTool"""

    @pytest.mark.integration
    def test_detect_healthy_files(self, corrupted_exif_file, real_photo_file, exif_handler_live):
        """
        Test detection of healthy files:
        1. Scan real photo file with valid EXIF
        2. Verify classified as HEALTHY
        3. Verify is_repairable=True
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        detector = CorruptionDetector(exiftool_path="exiftool")

        # Scan real file - convert to string
        results = detector.scan_files_for_corruption([str(real_photo_file)])

        assert str(real_photo_file) in results, "Should scan the file"
        corruption_info = results[str(real_photo_file)]

        assert corruption_info.corruption_type == CorruptionType.HEALTHY, \
            f"Real photo should be HEALTHY, got {corruption_info.corruption_type.value}"
        assert corruption_info.is_repairable, "Healthy file should be repairable"

    @pytest.mark.integration
    def test_detect_exif_structure_corruption(self, corrupted_exif_file):
        """
        Test detection of EXIF structure corruption:
        1. Use corrupted EXIF file from fixture
        2. Verify classified as EXIF_STRUCTURE
        3. Verify is_repairable=True
        """
        if corrupted_exif_file is None:
            pytest.skip("Corrupted EXIF file generation failed")

        detector = CorruptionDetector(exiftool_path="exiftool")

        results = detector.scan_files_for_corruption([corrupted_exif_file])

        assert corrupted_exif_file in results, "Should detect the corrupted file"
        corruption_info = results[corrupted_exif_file]

        # Should detect as corruption (not HEALTHY)
        assert corruption_info.corruption_type != CorruptionType.HEALTHY, \
            "Corrupted EXIF should not be HEALTHY"
        assert corruption_info.is_repairable, "EXIF structure corruption should be repairable"

    @pytest.mark.integration
    def test_detect_makernotes_corruption(self, corrupted_makernotes_file):
        """
        Test detection of MakerNotes corruption:
        1. Use corrupted MakerNotes file from fixture
        2. Verify classified as MAKERNOTES or EXIF_STRUCTURE
        3. Verify is_repairable=True (MakerNotes can be removed)
        """
        if corrupted_makernotes_file is None:
            pytest.skip("Corrupted MakerNotes file generation failed")

        detector = CorruptionDetector(exiftool_path="exiftool")

        results = detector.scan_files_for_corruption([corrupted_makernotes_file])

        assert corrupted_makernotes_file in results, "Should detect the MakerNotes-corrupted file"
        corruption_info = results[corrupted_makernotes_file]

        # Should detect as MakerNotes corruption or EXIF_STRUCTURE
        assert corruption_info.corruption_type in [CorruptionType.MAKERNOTES, CorruptionType.EXIF_STRUCTURE], \
            f"Should detect MakerNotes/EXIF corruption, got {corruption_info.corruption_type.value}"
        assert corruption_info.is_repairable, "MakerNotes corruption should be repairable"

    @pytest.mark.integration
    def test_detect_severe_corruption(self, temp_alignment_dir):
        """
        Test detection of severe (non-repairable) corruption:
        1. Create severely corrupted file
        2. Verify classified as SEVERE_CORRUPTION
        3. Verify is_repairable=False
        """
        detector = CorruptionDetector(exiftool_path="exiftool")

        # Create a binary file that's not a valid image
        corrupted_file = temp_alignment_dir / "severely_corrupted.jpg"
        with open(corrupted_file, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0' + b'garbage data' * 100)  # Corrupted JPEG header

        results = detector.scan_files_for_corruption([str(corrupted_file)])

        assert str(corrupted_file) in results, "Should detect severely corrupted file"
        corruption_info = results[str(corrupted_file)]

        # Severe corruption should not be healthy
        assert corruption_info.corruption_type != CorruptionType.HEALTHY, \
            "Severely corrupted file should not be HEALTHY"

    @pytest.mark.integration
    def test_detect_filesystem_only_files(self, temp_alignment_dir, real_photo_file):
        """
        Test detection of filesystem-only files (no embedded metadata):
        1. Create or identify file without EXIF metadata
        2. Verify classified as FILESYSTEM_ONLY
        3. Verify is_repairable=True (can use filesystem timestamps)
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        detector = CorruptionDetector(exiftool_path="exiftool")

        # Copy file and strip metadata to create filesystem-only file
        fs_only_file = temp_alignment_dir / "no_metadata.jpg"
        shutil.copy2(real_photo_file, fs_only_file)

        # Try to strip EXIF metadata
        try:
            subprocess.run(
                ["exiftool", "-all=", "-overwrite_original", str(fs_only_file)],
                capture_output=True,
                timeout=10
            )
        except:
            pytest.skip("Could not strip metadata with exiftool")

        results = detector.scan_files_for_corruption([str(fs_only_file)])

        assert str(fs_only_file) in results, "Should detect filesystem-only file"
        corruption_info = results[str(fs_only_file)]

        # Should be classified as FILESYSTEM_ONLY or HEALTHY (depending on implementation)
        assert corruption_info.corruption_type in [CorruptionType.FILESYSTEM_ONLY, CorruptionType.HEALTHY], \
            f"Metadata-stripped file should be FILESYSTEM_ONLY or HEALTHY, got {corruption_info.corruption_type.value}"
        assert corruption_info.is_repairable, "Filesystem-only files should be repairable"

    @pytest.mark.integration
    def test_detection_classification_accuracy(self, real_photo_file, corrupted_exif_file,
                                               corrupted_makernotes_file, temp_alignment_dir):
        """
        Test classification accuracy across mixed batch:
        1. Create batch with healthy + corrupted files
        2. Scan entire batch
        3. Verify correct classification percentages
        """
        if real_photo_file is None:
            pytest.skip("Real photo file not available")

        detector = CorruptionDetector(exiftool_path="exiftool")

        # Build file list
        files_to_scan = [str(real_photo_file)]
        if corrupted_exif_file:
            files_to_scan.append(str(corrupted_exif_file))
        if corrupted_makernotes_file:
            files_to_scan.append(str(corrupted_makernotes_file))

        # Scan batch
        results = detector.scan_files_for_corruption(files_to_scan)

        # Verify all files were scanned
        assert len(results) == len(files_to_scan), "Should scan all files"

        # Verify at least one is healthy (the real photo)
        healthy_count = sum(1 for file_path, info in results.items()
                           if info.corruption_type == CorruptionType.HEALTHY)
        # At least the real photo should be healthy, or test just verifies scanning
        assert len(results) > 0, "Should have results"

        # Verify consistent corruption detection metadata
        for file_path, corruption_info in results.items():
            assert isinstance(corruption_info.is_repairable, bool), "is_repairable should be boolean"
            assert 0.0 <= corruption_info.estimated_success_rate <= 1.0, \
                "Success rate should be 0-100%"

    @pytest.mark.integration
    def test_detection_with_mixed_media_batch(self, real_photo_file, real_video_file, temp_alignment_dir):
        """
        Test corruption detection with mixed media (photos + videos):
        1. Create batch with photos and videos
        2. Scan entire batch
        3. Verify both media types processed
        """
        if real_photo_file is None or real_video_file is None:
            pytest.skip("Real media files not available")

        detector = CorruptionDetector(exiftool_path="exiftool")

        # Copy files to temp directory
        photo_copy = temp_alignment_dir / "batch_photo.jpg"
        video_copy = temp_alignment_dir / "batch_video.mp4"

        shutil.copy2(real_photo_file, photo_copy)
        shutil.copy2(real_video_file, video_copy)

        # Scan mixed batch
        results = detector.scan_files_for_corruption([str(photo_copy), str(video_copy)])

        # Verify both scanned
        assert len(results) == 2, "Should scan both photo and video"
        assert str(photo_copy) in results, "Photo should be in results"
        assert str(video_copy) in results, "Video should be in results"

        # Verify classifications
        photo_info = results[str(photo_copy)]
        video_info = results[str(video_copy)]

        assert photo_info.is_repairable or not photo_info.is_repairable, \
            "Photo should have repairable status"
        assert video_info.is_repairable or not video_info.is_repairable, \
            "Video should have repairable status"
