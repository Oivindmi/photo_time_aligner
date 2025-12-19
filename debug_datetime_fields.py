#!/usr/bin/env python3
"""Debug script to check what datetime fields are changing"""

import sys
from pathlib import Path
from datetime import timedelta
import shutil
import tempfile

# Add project to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.exif_handler import ExifHandler
from src.core.file_processor import FileProcessor
from src.core.alignment_processor import AlignmentProcessor

# Find sample media
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
SAMPLE_MEDIA_DIR = FIXTURES_DIR / "sample_media"
CLEAN_MEDIA_DIR = SAMPLE_MEDIA_DIR / "clean"
PHOTO_FILE = CLEAN_MEDIA_DIR / "photo_clean.jpg"

if not PHOTO_FILE.exists():
    print(f"Photo file not found: {PHOTO_FILE}")
    sys.exit(1)

# Create temp copy
with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir = Path(tmpdir)
    ref_file = tmpdir / "reference_test.jpg"
    shutil.copy2(PHOTO_FILE, ref_file)

    # Initialize handlers
    exif_handler = ExifHandler()
    file_processor = FileProcessor(exif_handler)
    processor = AlignmentProcessor(exif_handler, file_processor)

    # Get BEFORE state
    print("=" * 80)
    print("BEFORE PROCESSING:")
    print("=" * 80)
    datetime_fields_before = exif_handler.get_datetime_fields(str(ref_file))
    if datetime_fields_before:
        for field, value in sorted(datetime_fields_before.items()):
            print(f"  {field:30s}: {value}")
    else:
        print("  (no datetime fields found)")

    # Process with 0 offset
    print("\n" + "=" * 80)
    print("PROCESSING WITH 0 OFFSET...")
    print("=" * 80)
    status = processor.process_files(
        reference_files=[str(ref_file)],
        target_files=[],
        reference_field="DateTimeOriginal",
        target_field="DateTimeOriginal",
        time_offset=timedelta(0),
        progress_callback=None
    )
    print(f"Status: {status.status_message if hasattr(status, 'status_message') else 'Done'}")

    # Get AFTER state
    print("\n" + "=" * 80)
    print("AFTER PROCESSING:")
    print("=" * 80)
    datetime_fields_after = exif_handler.get_datetime_fields(str(ref_file))
    if datetime_fields_after:
        for field, value in sorted(datetime_fields_after.items()):
            print(f"  {field:30s}: {value}")
    else:
        print("  (no datetime fields found)")

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON:")
    print("=" * 80)

    all_fields = set(list((datetime_fields_before or {}).keys()) + list((datetime_fields_after or {}).keys()))

    if not all_fields:
        print("No datetime fields found!")
    else:
        for field in sorted(all_fields):
            before_val = (datetime_fields_before or {}).get(field)
            after_val = (datetime_fields_after or {}).get(field)

            if before_val == after_val:
                print(f"  ✓ {field:30s}: UNCHANGED ({before_val})")
            else:
                print(f"  ✗ {field:30s}: CHANGED")
                print(f"      Before: {before_val}")
                print(f"      After:  {after_val}")

print("\nDone!")
