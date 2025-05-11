# test_video_metadata.py
import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import ExifHandler
from src.core.time_calculator import TimeCalculator


def analyze_video_metadata(file_path):
    """Analyze metadata from a video file"""
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()

    print(f"\n{'=' * 60}")
    print(f"Analyzing: {file_name}")
    print(f"Format: {file_ext}")
    print(f"Size: {os.path.getsize(file_path) / (1024 * 1024):.2f} MB")
    print('=' * 60)

    exif_handler = ExifHandler()

    try:
        # Get all metadata
        metadata = exif_handler.read_metadata(file_path)
        print(f"\nTotal metadata fields: {len(metadata)}")

        # Filter for time-related fields
        time_fields = {}
        all_time_keywords = [
            'date', 'time', 'create', 'modify', 'record',
            'timestamp', 'duration', 'start', 'end', 'year'
        ]

        for key, value in metadata.items():
            if any(keyword in key.lower() for keyword in all_time_keywords):
                time_fields[key] = value

        print(f"Time-related fields found: {len(time_fields)}")
        print("\nRaw Time Fields:")
        print("-" * 40)
        for field, value in sorted(time_fields.items()):
            print(f"{field:<30} = {value}")

        # Get parsed datetime fields
        datetime_fields = exif_handler.get_datetime_fields(file_path)

        print("\nParsed DateTime Fields:")
        print("-" * 40)
        for field, value in sorted(datetime_fields.items()):
            if value:
                raw_value = metadata.get(field, "N/A")
                print(f"{field:<30} = {value.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  Raw: {raw_value}")
            else:
                print(f"{field:<30} = Failed to parse")

        # Identify camera/device info
        camera_info = exif_handler.get_camera_info(file_path)
        print("\nCamera/Device Info:")
        print("-" * 40)
        print(f"Make: {camera_info.get('make', 'N/A')}")
        print(f"Model: {camera_info.get('model', 'N/A')}")

        # Check for video-specific metadata
        video_fields = ['VideoCodec', 'AudioCodec', 'Width', 'Height',
                        'FrameRate', 'Duration', 'VideoStreamType', 'Encoder',
                        'CompressorName', 'HandlerDescription', 'HandlerType',
                        'MediaDataSize']

        print("\nVideo-Specific Metadata:")
        print("-" * 40)
        for field in video_fields:
            value = metadata.get(field, 'Not found')
            if value != 'Not found':
                print(f"{field:<20} = {value}")

        # Additional metadata that might be relevant
        print("\nAll Metadata Fields:")
        print("-" * 40)
        for key, value in sorted(metadata.items()):
            print(f"{key:<30} = {value}")

        return metadata

    except Exception as e:
        print(f"Error analyzing metadata: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_time_parsing_edge_cases():
    """Test parsing of various video timestamp formats"""
    print("\nTesting Time Parsing Edge Cases:")
    print("-" * 40)

    test_timestamps = [
        # Standard formats
        "2023:12:25 14:30:22",
        "2023-12-25 14:30:22",
        "2023-12-25T14:30:22",
        "2023-12-25T14:30:22Z",
        "2023-12-25T14:30:22+01:00",

        # Video-specific formats
        "2023-12-25T14:30:22.123",
        "2023-12-25T14:30:22.123456",
        "20231225143022",
        "2023.12.25 14:30:22",
        "25/12/2023 14:30:22",
        "12/25/2023 14:30:22",
        "2023-12-25 14:30:22 UTC",
        "2023-12-25 14:30:22 GMT",

        # Your specific format
        "2022:07:27 16:33:19",
        "2022:08:13 20:00:08+02:00",

        # Problematic formats
        "2023-12-25 14:30:22.123456789",  # Too many milliseconds
        "2023-12-25T14:30:22.123+01:00",  # Milliseconds with timezone
    ]

    for timestamp in test_timestamps:
        parsed = TimeCalculator.parse_datetime_naive(timestamp)
        if parsed:
            print(f"✓ '{timestamp}' -> {parsed.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"✗ '{timestamp}' -> Failed to parse")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        analyze_video_metadata(sys.argv[1])
    else:
        print("Usage: python test_video_metadata.py <video_file>")

    # Always run edge case testing
    test_time_parsing_edge_cases()