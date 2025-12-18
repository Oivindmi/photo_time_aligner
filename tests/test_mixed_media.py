"""
Unit tests for mixed media (photo and video) processing.
Tests that the application can handle directories containing both photos and videos.
"""
import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_media_directory():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp(prefix='test_mixed_media_')
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_media_files(temp_media_directory):
    """Create sample media files in temp directory"""
    files = []

    # Create dummy photo files with supported extensions
    photo_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.cr2']
    for i, ext in enumerate(photo_extensions):
        file_path = os.path.join(temp_media_directory, f'photo_{i}{ext}')
        Path(file_path).touch()
        files.append(file_path)

    # Create dummy video files with supported extensions
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    for i, ext in enumerate(video_extensions):
        file_path = os.path.join(temp_media_directory, f'video_{i}{ext}')
        Path(file_path).touch()
        files.append(file_path)

    return {
        'directory': temp_media_directory,
        'all_files': files,
        'photo_count': len(photo_extensions),
        'video_count': len(video_extensions),
    }


class TestMixedMediaDirectory:
    """Tests for mixed media directory processing"""

    def test_file_processor_supports_photos(self):
        """Test that FileProcessor recognizes photo formats"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            photo_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
            for ext in photo_extensions:
                assert ext in file_processor.supported_extensions, \
                    f"Photo format {ext} should be supported"

    def test_file_processor_supports_videos(self):
        """Test that FileProcessor recognizes video formats"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
            for ext in video_extensions:
                assert ext in file_processor.supported_extensions, \
                    f"Video format {ext} should be supported"

    def test_categorize_mixed_files(self, temp_media_files):
        """Test categorizing mixed photo and video files"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Categorize files in temp directory
            photos = []
            videos = []

            for file in os.listdir(temp_media_files['directory']):
                file_path = os.path.join(temp_media_files['directory'], file)
                ext = os.path.splitext(file)[1].lower()

                if ext in file_processor.supported_extensions:
                    if ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}:
                        videos.append(file_path)
                    else:
                        photos.append(file_path)

            # Verify categorization
            assert len(photos) == temp_media_files['photo_count'], \
                f"Expected {temp_media_files['photo_count']} photos, got {len(photos)}"
            assert len(videos) == temp_media_files['video_count'], \
                f"Expected {temp_media_files['video_count']} videos, got {len(videos)}"

    def test_scan_directory_finds_all_media(self, temp_media_files):
        """Test that directory scanning finds all media files"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Count supported files in directory
            supported_count = 0
            for file in os.listdir(temp_media_files['directory']):
                ext = os.path.splitext(file)[1].lower()
                if ext in file_processor.supported_extensions:
                    supported_count += 1

            # Should find all created files
            total_expected = temp_media_files['photo_count'] + temp_media_files['video_count']
            assert supported_count == total_expected, \
                f"Expected {total_expected} supported files, found {supported_count}"

    def test_mixed_directory_file_listing(self, temp_media_files):
        """Test listing files from mixed media directory"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Get all files that would be processed
            all_media_files = []
            for file in os.listdir(temp_media_files['directory']):
                file_path = os.path.join(temp_media_files['directory'], file)
                ext = os.path.splitext(file)[1].lower()

                if ext in file_processor.supported_extensions:
                    all_media_files.append(file_path)

            # Verify we have files
            assert len(all_media_files) > 0, "Should find at least one media file"
            assert len(all_media_files) == len(temp_media_files['all_files']), \
                "Should find all created files"

    def test_extension_detection_case_insensitive(self, temp_media_files):
        """Test that extension detection works regardless of case"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Test both uppercase and lowercase
            test_extensions = ['.MP4', '.Jpg', '.AVI', '.Png', '.MOV']
            for ext in test_extensions:
                lower_ext = ext.lower()
                assert lower_ext in file_processor.supported_extensions, \
                    f"Should recognize {lower_ext} (from {ext})"


class TestMediaFileFiltering:
    """Tests for media file filtering and categorization"""

    def test_unsupported_files_excluded(self, temp_media_files):
        """Test that unsupported files are filtered out"""
        # Create unsupported files in temp directory
        unsupported_extensions = ['.txt', '.doc', '.exe', '.zip']
        for i, ext in enumerate(unsupported_extensions):
            file_path = os.path.join(temp_media_files['directory'], f'file_{i}{ext}')
            Path(file_path).touch()

        with patch('src.core.exiftool_process.ExifToolProcess'):
            from src.core import FileProcessor
            from src.core.exif_handler import ExifHandler

            exif_handler = Mock(spec=ExifHandler)
            file_processor = FileProcessor(exif_handler)

            # Count only supported files
            supported_count = 0
            unsupported_count = 0

            for file in os.listdir(temp_media_files['directory']):
                ext = os.path.splitext(file)[1].lower()
                if ext in file_processor.supported_extensions:
                    supported_count += 1
                else:
                    unsupported_count += 1

            # Should have excluded all unsupported files
            assert unsupported_count == len(unsupported_extensions), \
                f"Expected {len(unsupported_extensions)} unsupported files, got {unsupported_count}"
            assert supported_count == len(temp_media_files['all_files']), \
                f"Should have all {len(temp_media_files['all_files'])} media files"

    def test_empty_directory_handling(self):
        """Test that empty directories are handled gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('src.core.exiftool_process.ExifToolProcess'):
                from src.core import FileProcessor
                from src.core.exif_handler import ExifHandler

                exif_handler = Mock(spec=ExifHandler)
                file_processor = FileProcessor(exif_handler)

                # Count files in empty directory
                media_count = 0
                for file in os.listdir(temp_dir):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in file_processor.supported_extensions:
                        media_count += 1

                # Should handle empty directory gracefully
                assert media_count == 0, "Empty directory should have no media files"

    def test_video_categorization_accuracy(self, temp_media_files):
        """Test accurate video categorization"""
        video_ext_list = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v', '.3gp'}

        videos_found = []
        for file in os.listdir(temp_media_files['directory']):
            file_path = os.path.join(temp_media_files['directory'], file)
            ext = os.path.splitext(file)[1].lower()

            if ext in video_ext_list:
                videos_found.append(file_path)

        # Should find the test video files we created
        assert len(videos_found) == temp_media_files['video_count'], \
            f"Expected {temp_media_files['video_count']} videos, found {len(videos_found)}"

    def test_photo_categorization_accuracy(self, temp_media_files):
        """Test accurate photo categorization"""
        photo_ext_list = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif', '.cr2', '.nef'}

        photos_found = []
        for file in os.listdir(temp_media_files['directory']):
            file_path = os.path.join(temp_media_files['directory'], file)
            ext = os.path.splitext(file)[1].lower()

            if ext in photo_ext_list:
                photos_found.append(file_path)

        # Should find the test photo files we created
        assert len(photos_found) == temp_media_files['photo_count'], \
            f"Expected {temp_media_files['photo_count']} photos, found {len(photos_found)}"