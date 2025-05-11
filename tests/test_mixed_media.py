# test_mixed_media.py - Test mixed photo and video processing
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import ExifHandler, FileProcessor


def test_mixed_media_directory():
    """Test processing a directory with both photos and videos"""
    exif_handler = ExifHandler()
    file_processor = FileProcessor(exif_handler)

    # Test directory path
    test_dir = r"C:\TEST FOLDER FOR PHOTO APP\TEST OF photo_time_aligner\test"

    if not os.path.exists(test_dir):
        print(f"Test directory not found: {test_dir}")
        return

    print(f"Scanning directory: {test_dir}")

    # Get all supported files
    all_files = []
    photo_files = []
    video_files = []

    for file in os.listdir(test_dir):
        file_path = os.path.join(test_dir, file)
        ext = os.path.splitext(file)[1].lower()

        if ext in file_processor.supported_extensions:
            all_files.append(file_path)

            # Categorize by type (for analysis only)
            if ext in {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm'}:
                video_files.append(file_path)
            else:
                photo_files.append(file_path)

    print(f"\nFound {len(all_files)} supported files:")
    print(f"  - {len(photo_files)} photos")
    print(f"  - {len(video_files)} videos")

    # Test time field extraction from each file
    print("\nExtracting time fields from all files...")

    success_count = 0
    failed_files = []

    for file_path in all_files:
        file_name = os.path.basename(file_path)
        try:
            datetime_fields = exif_handler.get_datetime_fields(file_path)
            if datetime_fields:
                success_count += 1
                print(f"✓ {file_name}: {len(datetime_fields)} time fields")
            else:
                print(f"⚠ {file_name}: No time fields found")
        except Exception as e:
            failed_files.append((file_name, str(e)))
            print(f"✗ {file_name}: Error - {e}")

    print(f"\nSummary:")
    print(f"  Successfully processed: {success_count}/{len(all_files)}")
    print(f"  Failed: {len(failed_files)}")

    if failed_files:
        print("\nFailed files:")
        for file_name, error in failed_files:
            print(f"  - {file_name}: {error}")


if __name__ == "__main__":
    test_mixed_media_directory()