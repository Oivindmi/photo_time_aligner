# troubleshoot_files.py - Utility script to diagnose problematic files

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path


def diagnose_file(file_path):
    """Comprehensive diagnosis of a problematic file"""
    print(f"\n{'=' * 60}")
    print(f"DIAGNOSING: {os.path.basename(file_path)}")
    print(f"Full path: {file_path}")
    print(f"{'=' * 60}")

    # Basic file checks
    print("\n1. BASIC FILE INFORMATION:")
    print("-" * 30)

    if not os.path.exists(file_path):
        print("❌ File does not exist!")
        return

    print(f"✅ File exists")
    print(f"📁 Directory: {os.path.dirname(file_path)}")
    print(f"📄 Filename: {os.path.basename(file_path)}")

    # File size and permissions
    try:
        stat_info = os.stat(file_path)
        print(f"📏 Size: {stat_info.st_size:,} bytes")
        print(f"🔐 Permissions: {oct(stat_info.st_mode)[-3:]}")
        print(f"👁️ Readable: {'✅' if os.access(file_path, os.R_OK) else '❌'}")
        print(f"✏️ Writable: {'✅' if os.access(file_path, os.W_OK) else '❌'}")

        # Check read-only attribute
        import stat
        if not (stat_info.st_mode & stat.S_IWRITE):
            print("⚠️ File has READ-ONLY attribute!")

    except Exception as e:
        print(f"❌ Error getting file info: {e}")
        return

    # ExifTool availability
    print("\n2. EXIFTOOL AVAILABILITY:")
    print("-" * 30)

    exiftool_path = find_exiftool()
    if exiftool_path:
        print(f"✅ ExifTool found: {exiftool_path}")

        # Test ExifTool version
        try:
            result = subprocess.run([exiftool_path, '-ver'],
                                    capture_output=True, text=True, timeout=10)
            print(f"📋 Version: {result.stdout.strip()}")
        except Exception as e:
            print(f"⚠️ Error checking ExifTool version: {e}")
    else:
        print("❌ ExifTool not found!")
        return

    # Test metadata reading
    print("\n3. METADATA READING TEST:")
    print("-" * 30)

    try:
        metadata = read_metadata_with_exiftool(file_path, exiftool_path)
        if metadata:
            print(f"✅ Successfully read {len(metadata)} metadata fields")

            # Show datetime fields
            datetime_fields = [k for k in metadata.keys()
                               if any(dt in k.lower() for dt in ['date', 'time'])]
            print(f"📅 Found {len(datetime_fields)} datetime fields:")
            for field in datetime_fields[:5]:  # Show first 5
                print(f"    {field}: {metadata[field]}")
            if len(datetime_fields) > 5:
                print(f"    ... and {len(datetime_fields) - 5} more")
        else:
            print("⚠️ No metadata could be read")

    except Exception as e:
        print(f"❌ Error reading metadata: {e}")

    # Test simple metadata update
    print("\n4. METADATA UPDATE TEST:")
    print("-" * 30)

    try:
        # Create backup first
        backup_path = file_path + ".backup_for_test"
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"📋 Created backup: {os.path.basename(backup_path)}")

        # Try a simple comment update
        success = test_simple_update(file_path, exiftool_path)
        if success:
            print("✅ Simple metadata update succeeded")
        else:
            print("❌ Simple metadata update failed")

        # Try datetime update
        success = test_datetime_update(file_path, exiftool_path)
        if success:
            print("✅ DateTime metadata update succeeded")
        else:
            print("❌ DateTime metadata update failed")

        # Restore from backup
        shutil.move(backup_path, file_path)
        print("📋 Restored from backup")

    except Exception as e:
        print(f"❌ Error during update test: {e}")

        # Try to restore backup if it exists
        backup_path = file_path + ".backup_for_test"
        if os.path.exists(backup_path):
            try:
                shutil.move(backup_path, file_path)
                print("📋 Restored from backup after error")
            except:
                print("⚠️ Could not restore backup!")

    # File format analysis
    print("\n5. FILE FORMAT ANALYSIS:")
    print("-" * 30)

    try:
        format_info = analyze_file_format(file_path, exiftool_path)
        for key, value in format_info.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"❌ Error analyzing file format: {e}")


def find_exiftool():
    """Find ExifTool executable"""
    # Check if in PATH
    if shutil.which("exiftool"):
        return "exiftool"

    # Check common Windows locations
    common_paths = [
        r"C:\Program Files\ExifTool\exiftool.exe",
        r"C:\ExifTool\exiftool.exe",
        r"C:\Windows\exiftool.exe"
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def read_metadata_with_exiftool(file_path, exiftool_path):
    """Read metadata using ExifTool directly"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
        arg_file.write(file_path + '\n')
        arg_file_path = arg_file.name

    try:
        cmd = [exiftool_path, '-json', '-charset', 'filename=utf8', '-@', arg_file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            metadata_list = json.loads(result.stdout)
            return metadata_list[0] if metadata_list else {}
        else:
            print(f"ExifTool stderr: {result.stderr}")
            return {}

    finally:
        if os.path.exists(arg_file_path):
            os.remove(arg_file_path)


def test_simple_update(file_path, exiftool_path):
    """Test simple metadata update"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
        arg_file.write(file_path + '\n')
        arg_file_path = arg_file.name

    try:
        cmd = [exiftool_path, '-overwrite_original', '-Comment=Test Update',
               '-charset', 'filename=utf8', '-@', arg_file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        print(f"Update command output: {result.stdout}")
        if result.stderr:
            print(f"Update command stderr: {result.stderr}")

        return "1 image files updated" in result.stdout or "1 files updated" in result.stdout

    finally:
        if os.path.exists(arg_file_path):
            os.remove(arg_file_path)


def test_datetime_update(file_path, exiftool_path):
    """Test datetime metadata update"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
        arg_file.write(file_path + '\n')
        arg_file_path = arg_file.name

    try:
        cmd = [exiftool_path, '-overwrite_original', '-CreateDate=2025:01:01 12:00:00',
               '-charset', 'filename=utf8', '-@', arg_file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        print(f"DateTime update output: {result.stdout}")
        if result.stderr:
            print(f"DateTime update stderr: {result.stderr}")

        return "1 image files updated" in result.stdout or "1 files updated" in result.stdout

    finally:
        if os.path.exists(arg_file_path):
            os.remove(arg_file_path)


def analyze_file_format(file_path, exiftool_path):
    """Analyze file format details"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
        arg_file.write(file_path + '\n')
        arg_file_path = arg_file.name

    try:
        cmd = [exiftool_path, '-FileType', '-MIMEType', '-ImageWidth', '-ImageHeight',
               '-Make', '-Model', '-Software', '-charset', 'filename=utf8', '-@', arg_file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        format_info = {}
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    format_info[key.strip()] = value.strip()

        return format_info

    finally:
        if os.path.exists(arg_file_path):
            os.remove(arg_file_path)


def main():
    """Main function to run diagnostics"""
    if len(sys.argv) < 2:
        print("Usage: python troubleshoot_files.py <file_path> [file_path2] ...")
        print("\nThis script will diagnose why files might be failing to update.")
        return

    print("FILE TROUBLESHOOTING UTILITY")
    print("=" * 60)
    print("This utility will help diagnose why certain files fail to update.")

    for file_path in sys.argv[1:]:
        diagnose_file(file_path)

    print(f"\n{'=' * 60}")
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()