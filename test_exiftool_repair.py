# test_exiftool_repair.py - Test ExifTool repair strategies on corrupted files

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime


def test_repair_strategies(file_path):
    """Test various ExifTool repair strategies on a corrupted file"""

    print(f"\n{'=' * 80}")
    print(f"TESTING EXIFTOOL REPAIR STRATEGIES: {os.path.basename(file_path)}")
    print(f"{'=' * 80}")

    # Create working directory for repair tests
    temp_dir = tempfile.mkdtemp(prefix="exiftool_repair_test_")
    print(f"✅ Created test directory: {temp_dir}")

    exiftool_path = "exiftool"

    repair_strategies = [
        {
            "name": "Strategy 1: Basic Metadata Rebuild",
            "description": "Remove all metadata and rebuild from remaining data",
            "steps": [
                {
                    "desc": "Remove all metadata",
                    "cmd": [exiftool_path, "-all=", "-overwrite_original", "{file}"]
                },
                {
                    "desc": "Try to restore from backup data",
                    "cmd": [exiftool_path, "-tagsfromfile", "{file}", "-all:all", "-unsafe", "-overwrite_original",
                            "{file}"]
                }
            ]
        },
        {
            "name": "Strategy 2: EXIF Structure Repair",
            "description": "Attempt to repair EXIF structure while preserving data",
            "steps": [
                {
                    "desc": "Repair EXIF structure",
                    "cmd": [exiftool_path, "-all=", "-tagsfromfile", "{file}", "-exif:all", "-unsafe",
                            "-overwrite_original", "{file}"]
                }
            ]
        },
        {
            "name": "Strategy 3: Safe Metadata Extraction and Rebuild",
            "description": "Extract safe metadata and rebuild file structure",
            "steps": [
                {
                    "desc": "Extract all safe metadata to text",
                    "cmd": [exiftool_path, "-a", "-u", "-g1", "{file}"],
                    "capture_output": True
                },
                {
                    "desc": "Clear all metadata",
                    "cmd": [exiftool_path, "-all=", "-overwrite_original", "{file}"]
                },
                {
                    "desc": "Restore essential EXIF structure",
                    "cmd": [exiftool_path, "-tagsfromfile", "{original}", "-EXIF:all", "-overwrite_original", "{file}"]
                }
            ]
        },
        {
            "name": "Strategy 4: Conservative Repair",
            "description": "Only repair specific corrupted sections",
            "steps": [
                {
                    "desc": "Remove problematic IFD0 data",
                    "cmd": [exiftool_path, "-IFD0:all=", "-overwrite_original", "{file}"]
                },
                {
                    "desc": "Restore from backup data",
                    "cmd": [exiftool_path, "-tagsfromfile", "{original}", "-IFD0:all", "-unsafe", "-overwrite_original",
                            "{file}"]
                }
            ]
        },
        {
            "name": "Strategy 5: JPEG Structure Repair",
            "description": "Repair JPEG file structure and rebuild metadata",
            "steps": [
                {
                    "desc": "Extract image data only",
                    "cmd": [exiftool_path, "-all=", "-overwrite_original", "{file}"]
                },
                {
                    "desc": "Add minimal EXIF structure",
                    "cmd": [exiftool_path, "-EXIF:ColorSpace=1", "-EXIF:ExifVersion=0232", "-overwrite_original",
                            "{file}"]
                }
            ]
        }
    ]

    successful_strategies = []

    for i, strategy in enumerate(repair_strategies, 1):
        print(f"\n{i}. TESTING {strategy['name'].upper()}")
        print(f"   {strategy['description']}")
        print("=" * 60)

        # Create a copy for this test
        test_file = os.path.join(temp_dir, f"test_{i}_{os.path.basename(file_path)}")
        original_backup = os.path.join(temp_dir, f"original_{i}_{os.path.basename(file_path)}")

        try:
            shutil.copy2(file_path, test_file)
            shutil.copy2(file_path, original_backup)
            print(f"✅ Created test copy: {os.path.basename(test_file)}")

            # Execute repair steps
            strategy_success = True
            extracted_metadata = None

            for step_num, step in enumerate(strategy["steps"], 1):
                print(f"\n   Step {step_num}: {step['desc']}")

                # Replace placeholders in command
                cmd = []
                for arg in step["cmd"]:
                    if arg == "{file}":
                        cmd.append(test_file)
                    elif arg == "{original}":
                        cmd.append(original_backup)
                    else:
                        cmd.append(arg)

                try:
                    if step.get("capture_output"):
                        # Capture metadata extraction
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        extracted_metadata = result.stdout
                        print(f"      Extracted {len(result.stdout)} characters of metadata")
                        if result.stderr:
                            print(f"      Warnings: {result.stderr[:200]}...")
                    else:
                        # Normal command execution
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        print(f"      Output: {result.stdout.strip()}")
                        if result.stderr:
                            print(f"      Stderr: {result.stderr[:200]}...")

                        # Check if command succeeded
                        if result.returncode != 0:
                            print(f"      ❌ Step failed with return code {result.returncode}")
                            strategy_success = False
                            break

                except subprocess.TimeoutExpired:
                    print(f"      ❌ Step timed out")
                    strategy_success = False
                    break
                except Exception as e:
                    print(f"      ❌ Step exception: {e}")
                    strategy_success = False
                    break

            if strategy_success:
                # Test if the repaired file can now be updated
                print(f"\n   Testing if repair was successful...")
                success = test_datetime_update_after_repair(test_file, exiftool_path)

                if success:
                    print(f"   ✅ {strategy['name']} SUCCEEDED!")
                    print(f"   🎉 File can now be updated with datetime fields!")
                    successful_strategies.append({
                        'name': strategy['name'],
                        'file': test_file,
                        'metadata': extracted_metadata
                    })
                else:
                    print(f"   ❌ Repair appeared to work but datetime update still fails")
            else:
                print(f"   ❌ {strategy['name']} failed during repair steps")

        except Exception as e:
            print(f"   ❌ Exception during {strategy['name']}: {e}")

    # Summary
    print(f"\n{'=' * 80}")
    print("REPAIR TEST SUMMARY")
    print("=" * 80)

    if successful_strategies:
        print(f"✅ Found {len(successful_strategies)} working repair strategies:")
        for i, strategy in enumerate(successful_strategies, 1):
            print(f"   {i}. {strategy['name']}")

        # Show details of the first successful strategy
        best_strategy = successful_strategies[0]
        print(f"\n🎯 RECOMMENDED STRATEGY: {best_strategy['name']}")
        print(f"   Repaired file location: {best_strategy['file']}")

        if best_strategy['metadata']:
            print(f"   Extracted metadata preview:")
            lines = best_strategy['metadata'].split('\n')[:10]
            for line in lines:
                if line.strip():
                    print(f"      {line}")
            if len(best_strategy['metadata'].split('\n')) > 10:
                print(f"      ... and more")

    else:
        print("❌ No repair strategies succeeded")
        print("⚠️ This file may be too severely corrupted to repair")
        print("💡 Recommendation: Use filesystem-only updates for this file")

    # Cleanup option
    print(f"\n📁 Test files preserved in: {temp_dir}")
    cleanup = input("\nDelete test files? (y/n): ").lower().strip()
    if cleanup == 'y':
        try:
            shutil.rmtree(temp_dir)
            print("✅ Test files deleted")
        except Exception as e:
            print(f"⚠️ Could not delete test directory: {e}")
    else:
        print(f"📁 Test files kept in: {temp_dir}")


def test_datetime_update_after_repair(file_path, exiftool_path):
    """Test if a repaired file can now accept datetime updates"""
    try:
        test_date = "2021:06:15 14:30:00"
        cmd = [
            exiftool_path,
            "-overwrite_original",
            "-ignoreMinorErrors",
            "-m",
            f"-DateTimeOriginal={test_date}",
            f"-CreateDate={test_date}",
            file_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if "1 image files updated" in result.stdout or "1 files updated" in result.stdout:
            return True
        else:
            return False

    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_exiftool_repair.py <corrupted_file_path>")
        print("\nThis will test various ExifTool repair strategies on a corrupted file.")
        print("⚠️  WARNING: This creates test copies but does NOT modify your original file.")
        return

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    print("⚠️  IMPORTANT:")
    print("   - This test creates copies of your file for testing")
    print("   - Your original file will NOT be modified")
    print("   - Some repair strategies are aggressive and may lose metadata")
    print("   - This is for testing purposes only")

    proceed = input("\nProceed with repair testing? (y/n): ").lower().strip()
    if proceed != 'y':
        print("Test cancelled.")
        return

    test_repair_strategies(file_path)


if __name__ == "__main__":
    main()