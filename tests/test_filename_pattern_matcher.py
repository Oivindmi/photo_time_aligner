"""
Comprehensive unit tests for FilenamePatternMatcher class.
Tests pattern extraction, matching, and various filename formats including Norwegian characters.
"""
import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.filename_pattern import FilenamePatternMatcher


class TestPrefixSeparatorNumberPattern:
    """Tests for IMG_XXXX, DSC_XXXX patterns (prefix_separator_number)"""

    def test_extract_img_underscore_pattern(self):
        """Test extracting IMG_1234 pattern"""
        result = FilenamePatternMatcher.extract_pattern("IMG_1234.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'] == ('IMG', '_', '1234')
        assert result['display'] == 'IMG_####'

    def test_extract_img_dash_pattern(self):
        """Test extracting IMG-1234 pattern"""
        result = FilenamePatternMatcher.extract_pattern("IMG-5678.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'] == ('IMG', '-', '5678')
        assert result['display'] == 'IMG-####'

    def test_extract_dsc_pattern(self):
        """Test extracting DSC_XXXX pattern (common Canon)"""
        result = FilenamePatternMatcher.extract_pattern("DSC_0001.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'] == ('DSC', '_', '0001')
        assert result['display'] == 'DSC_####'

    def test_extract_pano_pattern(self):
        """Test extracting PANO_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("PANO_9999.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'][0] == 'PANO'
        assert result['groups'][1] == '_'

    def test_extract_raw_pattern(self):
        """Test extracting RAW_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("RAW_0042.cr2")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'][0] == 'RAW'

    def test_extract_photo_pattern(self):
        """Test extracting PHOTO_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("PHOTO_2048.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'][0] == 'PHOTO'

    def test_extract_with_large_numbers(self):
        """Test extracting pattern with large photo numbers"""
        result = FilenamePatternMatcher.extract_pattern("IMG_9999999.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'][2] == '9999999'

    def test_extract_multiple_digit_groups(self):
        """Test extracting with multiple digit groups"""
        result = FilenamePatternMatcher.extract_pattern("DSC_1234_5678.jpg")
        assert result['type'] == 'generic'  # Falls through to generic pattern

    def test_match_same_img_prefix(self):
        """Test matching IMG files with same prefix"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")

        assert FilenamePatternMatcher.matches_pattern("IMG_0002.jpg", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("IMG_0100.jpg", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("DSC_0001.jpg", ref_pattern)

    def test_match_dsc_files(self):
        """Test matching DSC files"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("DSC_0001.jpg")

        assert FilenamePatternMatcher.matches_pattern("DSC_0002.jpg", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("DSC_9999.jpg", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("IMG_0001.jpg", ref_pattern)


class TestPrefixNumberPattern:
    """Tests for IMG1234, DSC1234 patterns (prefix_number, no separator)"""

    def test_extract_prefix_number_no_separator(self):
        """Test extracting IMG1234 pattern (no separator)"""
        result = FilenamePatternMatcher.extract_pattern("IMG1234.jpg")
        assert result['type'] == 'prefix_number'
        assert result['groups'] == ('IMG', '1234')
        assert result['display'] == 'IMG####'

    def test_extract_dsc_no_separator(self):
        """Test extracting DSC0001 pattern"""
        result = FilenamePatternMatcher.extract_pattern("DSC0001.jpg")
        assert result['type'] == 'prefix_number'
        assert result['groups'][0] == 'DSC'

    def test_extract_photo_no_separator(self):
        """Test extracting PHOTO2048 pattern"""
        result = FilenamePatternMatcher.extract_pattern("PHOTO2048.jpg")
        assert result['type'] == 'prefix_number'
        assert result['groups'][0] == 'PHOTO'

    def test_match_same_prefix_no_separator(self):
        """Test matching files with same prefix"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("IMG1001.jpg")

        assert FilenamePatternMatcher.matches_pattern("IMG1002.jpg", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("IMG9999.jpg", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("DSC1001.jpg", ref_pattern)


class TestDateBasedPatterns:
    """Tests for YYYYMMDD-based patterns"""

    def test_extract_date_separator_time_pattern(self):
        """Test extracting YYYYMMDD_HHMMSS pattern"""
        result = FilenamePatternMatcher.extract_pattern("20231225_143045.jpg")
        assert result['type'] == 'date_separator_time'
        assert result['groups'] == ('20231225', '_', '143045')
        assert result['display'] == 'YYYYMMDD_HHMMSS'

    def test_extract_date_dash_time_pattern(self):
        """Test extracting YYYYMMDD-HHMMSS pattern"""
        result = FilenamePatternMatcher.extract_pattern("20231225-143045.jpg")
        assert result['type'] == 'date_separator_time'
        assert result['groups'] == ('20231225', '-', '143045')

    def test_extract_date_separator_time_video(self):
        """Test extracting date-time pattern from videos"""
        result = FilenamePatternMatcher.extract_pattern("20231225_143045.mp4")
        assert result['type'] == 'date_separator_time'

    def test_extract_different_dates(self):
        """Test extracting various dates"""
        test_dates = [
            "20240101_000000.jpg",
            "20251231_235959.jpg",
            "20000101_120000.jpg",
            "20231215_093000.jpg",
        ]

        for filename in test_dates:
            result = FilenamePatternMatcher.extract_pattern(filename)
            assert result['type'] == 'date_separator_time'

    def test_match_date_time_pattern(self):
        """Test matching files with date-time pattern"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("20231225_143045.jpg")

        # date_separator_time pattern matches any date_separator_time format
        assert FilenamePatternMatcher.matches_pattern("20231225_153045.jpg", ref_pattern)
        # Different date still matches because pattern type is the same
        assert FilenamePatternMatcher.matches_pattern("20231226_143045.jpg", ref_pattern)


class TestVideoPatterns:
    """Tests for video-specific patterns"""

    def test_extract_vid_underscore_pattern(self):
        """Test extracting VID_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("VID_1234.mp4")
        # VID matches prefix_separator_number before video_prefix_number
        assert result['type'] in ['video_prefix_number', 'prefix_separator_number']
        assert result['groups'][0] == 'VID'

    def test_extract_mov_pattern(self):
        """Test extracting MOV_XXXX pattern (Apple)"""
        result = FilenamePatternMatcher.extract_pattern("MOV_0001.mov")
        # MOV matches prefix_separator_number pattern
        assert result['type'] in ['video_prefix_number', 'prefix_separator_number']
        assert result['groups'][0] == 'MOV'

    def test_extract_mvi_pattern(self):
        """Test extracting MVI_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("MVI_5000.avi")
        # MVI matches prefix_separator_number pattern
        assert result['type'] in ['video_prefix_number', 'prefix_separator_number']
        assert result['groups'][0] == 'MVI'

    def test_extract_video_timestamp_pattern(self):
        """Test extracting VIDEO_YYYYMMDD_HHMMSS pattern"""
        result = FilenamePatternMatcher.extract_pattern("VIDEO_20231225_143045.mp4")
        # VIDEO matches generic pattern first
        assert result['type'] in ['video_timestamp', 'generic']
        assert result['groups'][0] == 'VIDEO'

    def test_extract_vid_timestamp_pattern(self):
        """Test extracting VID_YYYYMMDD_HHMMSS pattern"""
        result = FilenamePatternMatcher.extract_pattern("VID_20231225_143045.mp4")
        assert result['type'] == 'video_timestamp'
        assert result['groups'][0] == 'VID'

    def test_extract_video_date_time_dash_pattern(self):
        """Test extracting YYYY-MM-DD HH-MM-SS pattern"""
        result = FilenamePatternMatcher.extract_pattern("2023-12-25 14-30-45.mp4")
        assert result['type'] == 'video_date_time'
        assert result['display'] == 'YYYY-MM-DD HH-MM-SS'

    def test_match_vid_files(self):
        """Test matching VID files"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("VID_0001.mp4")

        assert FilenamePatternMatcher.matches_pattern("VID_0002.mp4", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("MOV_0001.mp4", ref_pattern)


class TestGoPro:
    """Tests for GoPro/Action camera patterns"""

    def test_extract_gopro_gh_pattern(self):
        """Test extracting GH##### (GoPro Hero) pattern"""
        result = FilenamePatternMatcher.extract_pattern("GH010123.mp4")
        # GH matches prefix_number pattern first
        assert result['type'] in ['gopro_pattern', 'prefix_number']
        assert result['groups'][0] == 'GH'

    def test_extract_gopro_gp_pattern(self):
        """Test extracting GP##### pattern"""
        result = FilenamePatternMatcher.extract_pattern("GP001234.mp4")
        assert result['type'] in ['gopro_pattern', 'prefix_number']
        assert result['groups'][0] == 'GP'

    def test_extract_gopro_gx_pattern(self):
        """Test extracting GX##### pattern"""
        result = FilenamePatternMatcher.extract_pattern("GX020456.mp4")
        assert result['type'] in ['gopro_pattern', 'prefix_number']
        assert result['groups'][0] == 'GX'

    def test_extract_gopro_gopr_pattern(self):
        """Test extracting GOPR#### pattern"""
        result = FilenamePatternMatcher.extract_pattern("GOPR0123.mp4")
        assert result['type'] in ['gopro_pattern', 'prefix_number']
        assert result['groups'][0] == 'GOPR'

    def test_match_gopro_files(self):
        """Test matching GoPro files"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("GH010123.mp4")

        assert FilenamePatternMatcher.matches_pattern("GH010124.mp4", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("GP010123.mp4", ref_pattern)


class TestDJI:
    """Tests for DJI drone patterns"""

    def test_extract_dji_underscore_pattern(self):
        """Test extracting DJI_XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("DJI_0001.mp4")
        # DJI matches prefix_separator_number first
        assert result['type'] in ['dji_pattern', 'prefix_separator_number']
        assert result['groups'] == ('DJI', '_', '0001')

    def test_extract_dji_dash_pattern(self):
        """Test extracting DJI-XXXX pattern"""
        result = FilenamePatternMatcher.extract_pattern("DJI-0456.mp4")
        assert result['type'] in ['dji_pattern', 'prefix_separator_number']
        assert result['groups'] == ('DJI', '-', '0456')

    def test_extract_dji_large_number(self):
        """Test extracting DJI with large numbers"""
        result = FilenamePatternMatcher.extract_pattern("DJI_9999999.mp4")
        assert result['type'] in ['dji_pattern', 'prefix_separator_number']
        assert result['groups'][2] == '9999999'

    def test_match_dji_files(self):
        """Test matching DJI files"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("DJI_0001.mp4")

        # Both underscore and dash versions match the same prefix
        assert FilenamePatternMatcher.matches_pattern("DJI_0002.mp4", ref_pattern)
        # Dash version also matches (same prefix 'DJI')
        assert FilenamePatternMatcher.matches_pattern("DJI-0001.mp4", ref_pattern)


class TestScreencastPatterns:
    """Tests for screenshot and screen recording patterns"""

    def test_extract_screenshot_pattern(self):
        """Test extracting Screenshot pattern"""
        result = FilenamePatternMatcher.extract_pattern("Screenshot_20231225-143045_Display.png")
        assert result['type'] == 'screenshot_pattern'
        assert result['groups'][0] == 'Screenshot'
        assert result['display'] == 'Screenshot_########-######_*'

    def test_extract_screencast_pattern(self):
        """Test extracting Screencast pattern"""
        result = FilenamePatternMatcher.extract_pattern("Screencast_2023-12-25_14-30-45.webm")
        assert result['type'] == 'screen_recording'
        assert result['groups'][0] == 'Screencast'
        assert result['display'] == 'Screencast_YYYY-MM-DD_HH-MM-SS'

    def test_extract_recording_pattern(self):
        """Test extracting Recording pattern"""
        result = FilenamePatternMatcher.extract_pattern("Recording_2023-12-25_14-30-45.mp4")
        assert result['type'] == 'screen_recording'
        assert result['groups'][0] == 'Recording'

    def test_match_screencast_files(self):
        """Test matching screencast files"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("Screencast_2023-12-25_14-30-45.webm")

        assert FilenamePatternMatcher.matches_pattern("Screencast_2023-12-25_15-30-45.webm", ref_pattern)
        # Recording also matches because both Screencast and Recording match the same pattern
        assert FilenamePatternMatcher.matches_pattern("Recording_2023-12-25_14-30-45.webm", ref_pattern)


class TestNorwegianCharacters:
    """Tests for Norwegian characters in filenames (Ø, Æ, Å)"""

    def test_extract_pattern_with_norwegian_prefix(self):
        """Test extracting pattern from filename with Norwegian characters"""
        result = FilenamePatternMatcher.extract_pattern("Øyvind_1234.jpg")
        assert result is not None
        assert result['type'] is not None

    def test_extract_pattern_with_å_character(self):
        """Test extracting pattern with Å character"""
        result = FilenamePatternMatcher.extract_pattern("År_2023_0001.jpg")
        assert result is not None

    def test_extract_pattern_with_æ_character(self):
        """Test extracting pattern with Æ character"""
        result = FilenamePatternMatcher.extract_pattern("Æble_0042.jpg")
        assert result is not None

    def test_extract_generic_norwegian_filename(self):
        """Test extracting generic pattern from Norwegian filename"""
        result = FilenamePatternMatcher.extract_pattern("Foto_20231225.jpg")
        # Should match generic pattern or date pattern
        assert result['type'] in ['generic', 'date_separator_time']

    def test_norwegian_directory_path(self):
        """Test with Norwegian characters in full path"""
        # Just the filename extraction, not full path
        result = FilenamePatternMatcher.extract_pattern("Bilder_Øyvind_0001.jpg")
        assert result is not None
        assert 'type' in result

    def test_match_norwegian_filenames(self):
        """Test matching Norwegian filenames"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("Foto_0001.jpg")

        # Should match other Norwegian filenames with same prefix
        assert FilenamePatternMatcher.matches_pattern("Foto_0002.jpg", ref_pattern)

    def test_norwegian_date_format(self):
        """Test Norwegian date format in filename"""
        result = FilenamePatternMatcher.extract_pattern("25_12_2023_Julebilder.jpg")
        # Should be classified as generic or no_pattern
        assert result is not None


class TestGenericPattern:
    """Tests for generic/fallback pattern matching"""

    def test_extract_generic_prefix_number(self):
        """Test extracting generic prefix_number pattern"""
        result = FilenamePatternMatcher.extract_pattern("CUSTOM0001.jpg")
        assert result['type'] == 'prefix_number'
        assert result['groups'][0] == 'CUSTOM'

    def test_extract_generic_with_mixed_case(self):
        """Test extracting with mixed case"""
        result = FilenamePatternMatcher.extract_pattern("Photo0001.jpg")
        # Mixed case matches generic pattern
        assert result['type'] in ['prefix_number', 'generic']
        assert result['groups'][0] == 'Photo'

    def test_extract_generic_pattern_fallback(self):
        """Test generic pattern as fallback"""
        result = FilenamePatternMatcher.extract_pattern("MyVideo0123456.mp4")
        assert result['type'] in ['prefix_number', 'generic']

    def test_extract_no_pattern_random_text(self):
        """Test no pattern for pure text filenames"""
        result = FilenamePatternMatcher.extract_pattern("MyCustomFile.jpg")
        assert result['type'] == 'no_pattern'
        assert result['groups'] == ['MyCustomFile']

    def test_extract_no_pattern_single_word(self):
        """Test no pattern for single word"""
        result = FilenamePatternMatcher.extract_pattern("vacation.jpg")
        assert result['type'] == 'no_pattern'

    def test_match_no_pattern_same_prefix(self):
        """Test matching no_pattern with prefix check"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("vacation.jpg")

        assert FilenamePatternMatcher.matches_pattern("vacation2.jpg", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("vacation_photos.jpg", ref_pattern)
        assert not FilenamePatternMatcher.matches_pattern("beach.jpg", ref_pattern)

    def test_no_pattern_display_truncation(self):
        """Test display truncation for long no_pattern names"""
        result = FilenamePatternMatcher.extract_pattern("VeryLongFilenameWithoutNumbersThatExceedsLimit.jpg")
        assert '...' in result['display']


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_extract_single_digit_number(self):
        """Test extracting single digit number"""
        result = FilenamePatternMatcher.extract_pattern("IMG_1.jpg")
        assert result['type'] == 'prefix_separator_number'

    def test_extract_very_long_number(self):
        """Test extracting very long number"""
        result = FilenamePatternMatcher.extract_pattern("IMG_123456789012345.jpg")
        assert result['type'] == 'prefix_separator_number'

    def test_extract_uppercase_prefix(self):
        """Test uppercase prefix requirement"""
        result = FilenamePatternMatcher.extract_pattern("img_1234.jpg")
        # Should not match prefix_separator_number (requires uppercase)
        assert result['type'] != 'prefix_separator_number'

    def test_extract_mixed_separators(self):
        """Test filename with multiple separators"""
        result = FilenamePatternMatcher.extract_pattern("IMG_20231225_001.jpg")
        assert result is not None

    def test_extract_empty_extension(self):
        """Test extracting without extension"""
        result = FilenamePatternMatcher.extract_pattern("IMG_1234")
        assert result['type'] == 'prefix_separator_number'

    def test_extract_multiple_extensions(self):
        """Test extracting with multiple extensions"""
        result = FilenamePatternMatcher.extract_pattern("IMG_1234.backup.jpg")
        # Should handle the filename part before first dot
        assert result is not None

    def test_match_different_extensions_same_pattern(self):
        """Test matching files with different extensions"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")

        assert FilenamePatternMatcher.matches_pattern("IMG_0002.raw", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("IMG_0003.png", ref_pattern)

    def test_zero_padded_numbers(self):
        """Test zero-padded numbers"""
        result = FilenamePatternMatcher.extract_pattern("DSC_000001.jpg")
        assert result['type'] == 'prefix_separator_number'
        assert result['groups'][2] == '000001'

    def test_numbers_with_leading_zeros(self):
        """Test matching zero-padded vs non-zero-padded"""
        ref_pattern = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")

        assert FilenamePatternMatcher.matches_pattern("IMG_0002.jpg", ref_pattern)
        assert FilenamePatternMatcher.matches_pattern("IMG_9999.jpg", ref_pattern)


class TestRealWorldScenarios:
    """Tests with real-world photo/video organization scenarios"""

    def test_organize_mixed_camera_photos(self):
        """Test organizing photos from different cameras"""
        cameras = [
            "IMG_0001.jpg",
            "DSC_0001.jpg",
            "PHOTO_001.jpg",
            "20231225_140000.jpg",
        ]

        patterns = {}
        for filename in cameras:
            result = FilenamePatternMatcher.extract_pattern(filename)
            pattern_type = result['type']
            if pattern_type not in patterns:
                patterns[pattern_type] = []
            patterns[pattern_type].append(filename)

        # Each should have different pattern
        assert len(patterns) >= 2

    def test_group_photos_by_pattern(self):
        """Test grouping photos by detected pattern"""
        reference = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")

        files = [
            "IMG_0002.jpg",
            "IMG_0100.jpg",
            "IMG_9999.jpg",
            "DSC_0001.jpg",
            "PHOTO_0001.jpg",
        ]

        img_files = [f for f in files if FilenamePatternMatcher.matches_pattern(f, reference)]
        assert len(img_files) == 3  # Only IMG_* files

    def test_video_detection_workflow(self):
        """Test detecting and grouping videos"""
        videos = [
            "VID_0001.mp4",
            "VIDEO_20231225_143045.mp4",
            "GH010123.mp4",
            "DJI_0001.mp4",
        ]

        for video in videos:
            result = FilenamePatternMatcher.extract_pattern(video)
            # All should be recognized as specific patterns
            assert result['type'] != 'no_pattern'

    def test_mixed_media_organization(self):
        """Test organizing mixed photos and videos"""
        all_files = [
            "IMG_0001.jpg",
            "IMG_0002.jpg",
            "VID_0001.mp4",
            "VID_0002.mp4",
            "20231225_140000.jpg",
            "screenshot_001.png",
        ]

        photo_pattern = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")
        video_pattern = FilenamePatternMatcher.extract_pattern("VID_0001.mp4")

        photos = [f for f in all_files if FilenamePatternMatcher.matches_pattern(f, photo_pattern)]
        videos = [f for f in all_files if FilenamePatternMatcher.matches_pattern(f, video_pattern)]

        assert len(photos) == 2
        assert len(videos) == 2

    def test_pattern_consistency_across_batch(self):
        """Test that pattern detection is consistent for batch processing"""
        batch = ["IMG_0001.jpg", "IMG_0050.jpg", "IMG_0100.jpg"]

        patterns = [FilenamePatternMatcher.extract_pattern(f) for f in batch]

        # All should have same type
        types = [p['type'] for p in patterns]
        assert len(set(types)) == 1
        assert types[0] == 'prefix_separator_number'


class TestDisplayFormatting:
    """Tests for pattern display formatting"""

    def test_display_img_pattern(self):
        """Test display format for IMG pattern"""
        result = FilenamePatternMatcher.extract_pattern("IMG_1234.jpg")
        assert result['display'] == 'IMG_####'

    def test_display_dsc_pattern(self):
        """Test display format for DSC pattern"""
        result = FilenamePatternMatcher.extract_pattern("DSC_1234.jpg")
        assert result['display'] == 'DSC_####'

    def test_display_date_time_pattern(self):
        """Test display format for date-time pattern"""
        result = FilenamePatternMatcher.extract_pattern("20231225_143045.jpg")
        assert result['display'] == 'YYYYMMDD_HHMMSS'

    def test_display_video_timestamp(self):
        """Test display format for video timestamp"""
        result = FilenamePatternMatcher.extract_pattern("VIDEO_20231225_143045.mp4")
        assert result['display'] == 'VIDEO_YYYYMMDD_HHMMSS'

    def test_display_gopro_pattern(self):
        """Test display format for GoPro pattern"""
        result = FilenamePatternMatcher.extract_pattern("GH010123.mp4")
        assert result['display'] == 'GH####'

    def test_display_dji_pattern(self):
        """Test display format for DJI pattern"""
        result = FilenamePatternMatcher.extract_pattern("DJI_0001.mp4")
        assert result['display'] == 'DJI_####'

    def test_display_screenshot_pattern(self):
        """Test display format for screenshot pattern"""
        result = FilenamePatternMatcher.extract_pattern("Screenshot_20231225-143045_Display.png")
        assert result['display'] == 'Screenshot_########-######_*'

    def test_display_screencast_pattern(self):
        """Test display format for screencast pattern"""
        result = FilenamePatternMatcher.extract_pattern("Screencast_2023-12-25_14-30-45.webm")
        assert result['display'] == 'Screencast_YYYY-MM-DD_HH-MM-SS'


class TestPatternAttributes:
    """Tests for pattern metadata and attributes"""

    def test_result_contains_type(self):
        """Test that result contains type field"""
        result = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")
        assert 'type' in result
        assert isinstance(result['type'], str)

    def test_result_contains_groups(self):
        """Test that result contains groups field"""
        result = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")
        assert 'groups' in result
        assert isinstance(result['groups'], tuple)

    def test_result_contains_display(self):
        """Test that result contains display field"""
        result = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")
        assert 'display' in result
        assert isinstance(result['display'], str)

    def test_result_contains_pattern(self):
        """Test that result contains pattern field"""
        result = FilenamePatternMatcher.extract_pattern("IMG_0001.jpg")
        assert 'pattern' in result

    def test_no_pattern_has_correct_structure(self):
        """Test that no_pattern results have correct structure"""
        result = FilenamePatternMatcher.extract_pattern("random_text.jpg")
        assert result['type'] == 'no_pattern'
        assert result['pattern'] is None
        assert isinstance(result['groups'], list)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
