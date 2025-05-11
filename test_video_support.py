# test_video_support.py - Test script to verify video support
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import ExifHandler, FileProcessor
from src.core.filename_pattern import FilenamePatternMatcher


def test_format_support():
    """Test that video formats are recognized"""
    print("Testing format support...")

    exif_handler = ExifHandler()
    file_processor = FileProcessor(exif_handler)

    # Test extensions
    test_files = [
        "video.mp4", "movie.mov", "clip.avi", "recording.mkv",
        "photo.jpg", "image.png", "raw.cr2", "video.webm"
    ]

    for filename in test_files:
        ext = os.path.splitext(filename)[1].lower()
        is_supported = ext in file_processor.supported_extensions
        print(f"{filename}: {'✓ Supported' if is_supported else '✗ Not supported'}")

    print(f"\nTotal supported formats: {len(file_processor.supported_extensions)}")


def test_pattern_matching():
    """Test video filename pattern matching"""
    print("\nTesting pattern matching...")

    test_filenames = [
        "VID_20231225_143022.mp4",
        "MOV_1234.mov",
        "GH010123.mp4",
        "DJI_0456.mp4",
        "Screencast_2023-12-25_14-30-22.webm",
        "2023-12-25 14-30-22.mp4",
        "DSC_1234.jpg",  # Traditional photo pattern
    ]

    for filename in test_filenames:
        pattern = FilenamePatternMatcher.extract_pattern(filename)
        print(f"{filename}: {pattern['type']} - {pattern['display']}")


def test_metadata_extraction(file_path):
    """Test metadata extraction from a video file"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"\nTesting metadata extraction for: {file_path}")

    exif_handler = ExifHandler()
    try:
        metadata = exif_handler.read_metadata(file_path)
        print(f"Metadata fields found: {len(metadata)}")

        # Show time-related fields
        datetime_fields = exif_handler.get_datetime_fields(file_path)
        print("\nDate/Time fields:")
        for field, value in datetime_fields.items():
            raw_value = metadata.get(field, "N/A")
            print(f"  {field}: {raw_value} -> {value}")

    except Exception as e:
        print(f"Error extracting metadata: {e}")


if __name__ == "__main__":
    test_format_support()
    test_pattern_matching()

    # Test with an actual video file if provided
    if len(sys.argv) > 1:
        test_metadata_extraction(sys.argv[1])
    else:
        print("\nTo test metadata extraction, run with a video file path as argument")