# test_makernotes_fix.py - Test the MakerNotes fix

import os
import sys
import subprocess
import tempfile
import shutil


def test_makernotes_fix(file_path):
    """Test the MakerNotes fix on a problematic file"""
    print(f"\n{'=' * 60}")
    print(f"TESTING MAKERNOTES FIX ON: {os.path.basename(file_path)}")
    print(f"{'=' * 60}")

    # Find ExifTool
    exiftool_path = "exiftool"  # Assuming it's in PATH based on previous test

    # Create backup
    backup_path = file_path + ".makernotes_test_backup"
    try:
        shutil.copy2(file_path, backup_path)
        print(f"✅ Created backup: {os.path.basename(backup_path)}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return

    try:
        print("\n1. TESTING STANDARD DATETIME UPDATE (should fail):")
        print("-" * 50)

        # Test 1: Standard update (should fail)
        cmd1 = [exiftool_path, '-overwrite_original', '-CreateDate=2025:01:01 12:00:00', file_path]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=30)

        print(f"Standard update output: {result1.stdout}")
        if result1.stderr:
            print(f"Standard update stderr: {result1.stderr}")

        if "0 image files updated" in result1.stdout:
            print("❌ Standard update failed as expected")
        else:
            print("✅ Standard update unexpectedly succeeded")

        # Restore backup for next test
        shutil.copy2(backup_path, file_path)

        print("\n2. TESTING MAKERNOTES-SAFE UPDATE (should succeed):")
        print("-" * 50)

        # Test 2: MakerNotes-safe update
        cmd2 = [
            exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',  # Ignore minor errors
            '-m',  # Ignore minor warnings
            '-CreateDate=2025:01:01 12:00:00',
            file_path
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=30)

        print(f"MakerNotes-safe update output: {result2.stdout}")
        if result2.stderr:
            print(f"MakerNotes-safe update stderr: {result2.stderr}")

        if "1 image files updated" in result2.stdout or "1 files updated" in result2.stdout:
            print("✅ MakerNotes-safe update SUCCEEDED!")
            print("🎉 This fix will work for your files!")
        else:
            print("❌ MakerNotes-safe update still failed")
            print("⚠️ This file may have deeper issues")

        print("\n3. TESTING MULTIPLE DATETIME FIELDS:")
        print("-" * 50)

        # Restore backup for comprehensive test
        shutil.copy2(backup_path, file_path)

        # Test 3: Multiple datetime fields (like your app does)
        cmd3 = [
            exiftool_path,
            '-overwrite_original',
            '-ignoreMinorErrors',
            '-m',
            '-CreateDate=2025:01:01 12:00:00',
            '-ModifyDate=2025:01:01 12:00:00',
            '-DateTimeOriginal=2025:01:01 12:00:00',
            file_path
        ]
        result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=30)

        print(f"Multiple fields update output: {result3.stdout}")
        if result3.stderr:
            print(f"Multiple fields update stderr: {result3.stderr}")

        if "1 image files updated" in result3.stdout or "1 files updated" in result3.stdout:
            print("✅ Multiple datetime fields update SUCCEEDED!")
        else:
            print("❌ Multiple datetime fields update failed")

    except Exception as e:
        print(f"❌ Error during testing: {e}")

    finally:
        # Always restore the original file
        try:
            shutil.move(backup_path, file_path)
            print(f"\n✅ Restored original file from backup")
        except Exception as e:
            print(f"❌ Error restoring backup: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_makernotes_fix.py <file_path>")
        print("\nThis will test if the MakerNotes fix works for your problematic files.")
        return

    file_path = sys.argv[1]
    if os.path.exists(file_path):
        test_makernotes_fix(file_path)
    else:
        print(f"❌ File not found: {file_path}")


if __name__ == "__main__":
    main()