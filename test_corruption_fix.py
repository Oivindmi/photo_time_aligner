# test_corruption_fix.py - Test the enhanced corruption handling

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime


def test_corruption_strategies(file_path):
    """Test all three strategies on a corrupted file"""

    print(f"\n{'=' * 70}")
    print(f"TESTING CORRUPTION HANDLING: {os.path.basename(file_path)}")
    print(f"{'=' * 70}")

    # Create backup
    backup_path = file_path + ".corruption_test_backup"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ Created backup for testing")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return

    exiftool_path = "exiftool"
    test_date = "2020:01:01 12:00:00"

    strategies = [
        {
            "name": "Strategy 1: Standard with error handling",
            "flags": ["-overwrite_original", "-ignoreMinorErrors", "-m"]
        },
        {
            "name": "Strategy 2: Force update",
            "flags": ["-overwrite_original", "-ignoreMinorErrors", "-m", "-f", "-G"]
        },
        {
            "name": "Strategy 3: Filesystem only",
            "flags": ["-overwrite_original", "-ignoreMinorErrors", "-m", "-f"],
            "fields_only": ["FileCreateDate", "FileModifyDate"]
        }
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"\n{i}. TESTING {strategy['name'].upper()}:")
        print("-" * 50)

        # Restore backup for each test
        shutil.copy2(backup_path, file_path)

        try:
            # Build command
            cmd = [exiftool_path] + strategy["flags"]

            # Add fields to update
            if "fields_only" in strategy:
                # Only filesystem fields
                for field in strategy["fields_only"]:
                    cmd.append(f"-{field}={test_date}")
            else:
                # All datetime fields
                datetime_fields = [
                    "DateTimeOriginal", "CreateDate", "ModifyDate",
                    "FileCreateDate", "FileModifyDate"
                ]
                for field in datetime_fields:
                    cmd.append(f"-{field}={test_date}")

            cmd.append(file_path)

            print(f"Command flags: {' '.join(strategy['flags'])}")

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            print(f"Output: {result.stdout}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")

            # Check success
            if "1 image files updated" in result.stdout or "1 files updated" in result.stdout:
                print(f"✅ {strategy['name']} SUCCEEDED!")

                # Verify filesystem dates changed
                try:
                    stat_info = os.stat(file_path)
                    new_create_time = datetime.fromtimestamp(stat_info.st_ctime)
                    new_modify_time = datetime.fromtimestamp(stat_info.st_mtime)

                    target_datetime = datetime(2020, 1, 1, 12, 0, 0)
                    create_diff = abs((new_create_time - target_datetime).total_seconds())
                    modify_diff = abs((new_modify_time - target_datetime).total_seconds())

                    if create_diff < 3600:  # Within 1 hour
                        print(f"✅ FileCreateDate updated: {new_create_time}")
                    else:
                        print(f"⚠️ FileCreateDate may not have updated: {new_create_time}")

                    if modify_diff < 3600:  # Within 1 hour
                        print(f"✅ FileModifyDate updated: {new_modify_time}")
                    else:
                        print(f"⚠️ FileModifyDate may not have updated: {new_modify_time}")

                except Exception as e:
                    print(f"⚠️ Could not verify filesystem dates: {e}")

                print(f"🎉 Found working strategy: {strategy['name']}")
                break

            else:
                print(f"❌ {strategy['name']} failed")

        except Exception as e:
            print(f"❌ {strategy['name']} exception: {e}")

    else:
        print(f"\n❌ All strategies failed for this file")
        print(f"⚠️ This file may be severely corrupted")

    # Always restore original
    try:
        shutil.move(backup_path, file_path)
        print(f"\n✅ Restored original file")
    except Exception as e:
        print(f"❌ Error restoring backup: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_corruption_fix.py <file_path>")
        print("\nThis tests multiple strategies for handling corrupted EXIF files.")
        return

    file_path = sys.argv[1]
    if os.path.exists(file_path):
        test_corruption_strategies(file_path)
    else:
        print(f"❌ File not found: {file_path}")


if __name__ == "__main__":
    main()