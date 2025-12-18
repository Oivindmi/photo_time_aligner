"""
Unit tests for video support functionality.
Tests format recognition, pattern matching, and metadata extraction capabilities.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.filename_pattern import FilenamePatternMatcher


class TestVideoFormatSupport:
    """Tests for video format recognition and support"""

    def test_common_video_formats_recognized(self):
        """Test that common video formats are in supported list"""
        video_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv']

        # Import after mocking to avoid real process creation
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            for ext in video_formats:
                assert ext in file_processor.supported_extensions, \
                    f"Video format {ext} should be supported"

    def test_common_photo_formats_recognized(self):
        """Test that common photo formats are in supported list"""
        photo_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.cr2', '.nef']

        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            for ext in photo_formats:
                assert ext in file_processor.supported_extensions, \
                    f"Photo format {ext} should be supported"

    def test_unsupported_formats_not_recognized(self):
        """Test that unsupported formats are rejected"""
        unsupported_formats = ['.txt', '.doc', '.exe', '.zip', '.pdf']

        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            for ext in unsupported_formats:
                assert ext not in file_processor.supported_extensions, \
                    f"Format {ext} should not be supported"

    def test_supported_extensions_count_reasonable(self):
        """Test that we support a reasonable number of formats (should be ~54)"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Should support 50+ formats (photos + videos)
            assert len(file_processor.supported_extensions) >= 50, \
                f"Expected 50+ supported formats, got {len(file_processor.supported_extensions)}"


class TestFilenamePatternMatching:
    """Tests for video filename pattern matching"""

    def test_vid_pattern_recognition(self):
        """Test VID_YYYYMMDD_HHMMSS pattern recognition"""
        filename = "VID_20231225_143022.mp4"
        pattern = FilenamePatternMatcher.extract_pattern(filename)

        assert pattern is not None, "Should recognize VID pattern"
        assert pattern['type'] in ['video_timestamp', 'generic'], \
            f"Expected video_timestamp or generic pattern, got {pattern['type']}"

    def test_mov_pattern_recognition(self):
        """Test MOV_XXXX pattern recognition"""
        filename = "MOV_1234.mov"
        pattern = FilenamePatternMatcher.extract_pattern(filename)

        assert pattern is not None, "Should recognize MOV pattern"
        # MOV_1234 is recognized as prefix_separator_number (generic pattern for prefix_number format)
        assert pattern['type'] in ['prefix_separator_number', 'generic'], \
            f"Expected prefix_separator_number or generic pattern, got {pattern['type']}"

    def test_dji_pattern_recognition(self):
        """Test DJI_XXXX pattern recognition"""
        filename = "DJI_0456.mp4"
        pattern = FilenamePatternMatcher.extract_pattern(filename)

        assert pattern is not None, "Should recognize DJI pattern"
        assert pattern['type'] is not None, "Pattern should have a type"

    def test_timestamp_pattern_recognition(self):
        """Test date-timestamp pattern recognition"""
        filename = "2023-12-25 14-30-22.mp4"
        pattern = FilenamePatternMatcher.extract_pattern(filename)

        assert pattern is not None, "Should recognize timestamp pattern"
        assert pattern['type'] is not None, "Pattern should have a type"

    def test_generic_pattern_fallback(self):
        """Test that generic names still return a pattern"""
        filename = "movie.mp4"
        pattern = FilenamePatternMatcher.extract_pattern(filename)

        assert pattern is not None, "Should return pattern for generic filename"
        assert 'type' in pattern, "Pattern should have a type field"

    def test_pattern_has_required_fields(self):
        """Test that all patterns have required fields"""
        test_filenames = [
            "VID_20231225_143022.mp4",
            "MOV_1234.mov",
            "DSC_1234.jpg",
            "photo.png",
        ]

        for filename in test_filenames:
            pattern = FilenamePatternMatcher.extract_pattern(filename)
            assert 'type' in pattern, f"Pattern for {filename} missing 'type' field"
            assert 'display' in pattern, f"Pattern for {filename} missing 'display' field"


class TestVideoMetadataCapability:
    """Tests for video metadata extraction capabilities"""

    def test_exif_handler_can_read_metadata(self):
        """Test that ExifHandler has metadata reading capability"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core.exif_handler import ExifHandler

            exif_handler = ExifHandler()
            assert hasattr(exif_handler, 'read_metadata'), \
                "ExifHandler should have read_metadata method"

    def test_exif_handler_can_get_datetime_fields(self):
        """Test that ExifHandler can extract datetime fields"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core.exif_handler import ExifHandler

            exif_handler = ExifHandler()
            assert hasattr(exif_handler, 'get_datetime_fields'), \
                "ExifHandler should have get_datetime_fields method"

    def test_exif_handler_can_get_camera_info(self):
        """Test that ExifHandler can extract camera/device information"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core.exif_handler import ExifHandler

            exif_handler = ExifHandler()
            assert hasattr(exif_handler, 'get_camera_info'), \
                "ExifHandler should have get_camera_info method"

    @patch('src.core.exiftool_process.ExifToolProcess')
    def test_metadata_reading_handles_missing_file(self, mock_process):
        """Test that metadata reading gracefully handles missing files"""
        from src.core.exif_handler import ExifHandler

        exif_handler = ExifHandler()

        # Should not raise exception for missing file
        result = exif_handler.read_metadata("/nonexistent/file.mp4")
        assert result is not None, "Should return a result even for missing files"

    @patch('src.core.exiftool_process.ExifToolProcess')
    def test_datetime_extraction_handles_missing_file(self, mock_process):
        """Test that datetime field extraction gracefully handles missing files"""
        from src.core.exif_handler import ExifHandler

        exif_handler = ExifHandler()

        # Should not raise exception for missing file
        result = exif_handler.get_datetime_fields("/nonexistent/file.mp4")
        assert isinstance(result, dict), "Should return dict even for missing files"


class TestFileProcessorExtensions:
    """Tests for FileProcessor supported extensions"""

    def test_extension_list_is_not_empty(self):
        """Test that FileProcessor has extensions configured"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            assert len(file_processor.supported_extensions) > 0, \
                "FileProcessor should have supported extensions configured"

    def test_extensions_are_lowercase(self):
        """Test that all extensions are stored in lowercase"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            for ext in file_processor.supported_extensions:
                assert ext == ext.lower(), \
                    f"Extension {ext} should be lowercase"

    def test_extensions_have_dot_prefix(self):
        """Test that all extensions start with a dot"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            for ext in file_processor.supported_extensions:
                assert ext.startswith('.'), \
                    f"Extension {ext} should start with '.'"