# debug_filesystem_dates.py - Debug why FileCreateDate isn't updating

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime


def test_filesystem_date_update(file_path):
    """Test if ExifTool can update filesystem dates on this file"""

    print(f"\n{'=' * 60}")
    print(f"TESTING FILESYSTEM DATE UPDATE: {os.path.basename(file_path)}")
    print(f"{'=' * 60}")

    # Get current filesystem dates
    print("1. CURRENT FILESYSTEM DATES:")
    print("-" * 30)
    try:
        stat_info = os.stat(file_path)
        print(f"Current Create Time: {datetime.fromtimestamp(stat_info.st_ctime)}")
        print(f"Current Modify Time: {datetime.fromtimestamp(stat_info.st_mtime)}")
        print(f"Current Access Time: {datetime.fromtimestamp(stat_info.st_atime)}")
    except Exception as e:
        print(f"Error getting filesystem dates: {e}")
        return

    # Create backup for testing
    backup_path = file_path + ".filesystem_test_backup"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ Created backup for testing")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return

    try:
        exiftool_path = "exiftool"

        print("\n2. TESTING FILESYSTEM DATE UPDATE:")
        print("-" * 30)

        # Test updating FileCreateDate and FileModifyDate
        test_date = "2020:01:01 12:00:00"
        cmd = [
            exiftool_path,
            '-overwrite_original',  # Use your current settings
            '-ignoreMinorErrors',
            '-m',
            f'-FileCreateDate={test_date}',
            f'-FileModifyDate={test_date}',
            file_path
        ]

        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        print(f"ExifTool output: {result.stdout}")
        if result.stderr:
            print(f"ExifTool stderr: {result.stderr}")

        print("\n3. CHECKING RESULTS:")
        print("-" * 30)

        # Check if filesystem dates changed
        try:
            new_stat_info = os.stat(file_path)
            new_create_time = datetime.fromtimestamp(new_stat_info.st_ctime)
            new_modify_time = datetime.fromtimestamp(new_stat_info.st_mtime)

            print(f"New Create Time: {new_create_time}")
            print(f"New Modify Time: {new_modify_time}")

            # Check if they match our target date (allowing for some time drift)
            target_datetime = datetime(2020, 1, 1, 12, 0, 0)

            create_diff = abs((new_create_time - target_datetime).total_seconds())
            modify_diff = abs((new_modify_time - target_datetime).total_seconds())

            if create_diff < 60:  # Within 1 minute
                print("✅ FileCreateDate was updated successfully!")
            else:
                print(f"❌ FileCreateDate was NOT updated (diff: {create_diff} seconds)")

            if modify_diff < 60:  # Within 1 minute
                print("✅ FileModifyDate was updated successfully!")
            else:
                print(f"❌ FileModifyDate was NOT updated (diff: {modify_diff} seconds)")

        except Exception as e:
            print(f"❌ Error checking results: {e}")

        print("\n4. CHECKING EXIFTOOL'S VIEW OF FILESYSTEM DATES:")
        print("-" * 30)

        # Check what ExifTool thinks the filesystem dates are
        cmd_check = [exiftool_path, '-FileCreateDate', '-FileModifyDate', '-s', file_path]
        result_check = subprocess.run(cmd_check, capture_output=True, text=True, timeout=30)

        if result_check.returncode == 0:
            print("ExifTool reports:")
            for line in result_check.stdout.strip().split('\n'):
                if line.strip():
                    print(f"  {line}")
        else:
            print(f"Error checking ExifTool view: {result_check.stderr}")

        print("\n5. TESTING ALTERNATIVE APPROACHES:")
        print("-" * 30)

        # Try alternative command formats
        # Restore backup first
        shutil.copy2(backup_path, file_path)

        # Try with argument file (like your app uses)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            cmd_alt = [
                exiftool_path,
                '-overwrite_original',
                '-ignoreMinorErrors',
                '-m',
                f'-FileCreateDate={test_date}',
                f'-FileModifyDate={test_date}',
                '-@', arg_file_path
            ]

            print(f"Alternative command (with arg file): exiftool [options] -@ {os.path.basename(arg_file_path)}")
            result_alt = subprocess.run(cmd_alt, capture_output=True, text=True, timeout=30)

            print(f"Alternative output: {result_alt.stdout}")
            if result_alt.stderr:
                print(f"Alternative stderr: {result_alt.stderr}")

            # Check results again
            alt_stat_info = os.stat(file_path)
            alt_create_time = datetime.fromtimestamp(alt_stat_info.st_ctime)
            print(f"After alternative method - Create Time: {alt_create_time}")

        finally:
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    except Exception as e:
        print(f"❌ Error during testing: {e}")

    finally:
        # Restore original file
        try:
            shutil.move(backup_path, file_path)
            print(f"\n✅ Restored original file")
        except Exception as e:
            print(f"❌ Error restoring backup: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_filesystem_dates.py <file_path>")
        print("\nThis will test if ExifTool can update filesystem dates on your file.")
        return

    file_path = sys.argv[1]
    if os.path.exists(file_path):
        test_filesystem_date_update(file_path)
    else:
        print(f"❌ File not found: {file_path}")


if __name__ == "__main__":
    main()