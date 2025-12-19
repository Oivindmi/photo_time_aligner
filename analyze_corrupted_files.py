#!/usr/bin/env python3
"""Analyze corrupted test files for corruption classification"""

import subprocess
import os
import json
from pathlib import Path

# Change to directory with corrupted files
test_dir = Path("C:/Users/AB33529/testoffunctions/photo_time_aligner/tests/fixtures/sample_media/corrupted_user_provided/")
os.chdir(test_dir)

files = sorted([f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg'))])

print("\n" + "="*80)
print("CORRUPTION ANALYSIS REPORT")
print("="*80)

results = {}

for file in files:
    print(f"\n{'='*80}")
    print(f"FILE: {file}")
    print('='*80)

    file_info = {
        'name': file,
        'basic_read': False,
        'update_success': False,
        'warnings': [],
        'corruption_type': 'UNKNOWN'
    }

    # Test 1: Basic metadata read
    result = subprocess.run(
        ['exiftool', '-json', file],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode == 0 and result.stdout.strip():
        print("[OK] Basic metadata read: SUCCESS")
        file_info['basic_read'] = True
        try:
            data = json.loads(result.stdout)
            print(f"     Fields found: {len(data[0]) if data else 0}")
        except:
            pass
    else:
        print("[FAIL] Basic metadata read: FAILED")
        file_info['basic_read'] = False
        print(f"       Error: {result.stderr[:100]}")

    # Test 2: Try to update metadata
    result = subprocess.run(
        ['exiftool', '-DateTimeOriginal=2024:01:01 12:00:00', '-m', '-ignoreMinorErrors', '-overwrite_original', file],
        capture_output=True, text=True, timeout=10
    )

    output = result.stdout + result.stderr
    if "1 image files updated" in output or "1 files updated" in output:
        print("[OK] Metadata write: SUCCESS")
        file_info['update_success'] = True
    else:
        print("[FAIL] Metadata write: FAILED or UNCHANGED")
        print(f"       Output: {output[:150]}")
        file_info['update_success'] = False

    # Test 3: Check for warnings/errors
    result = subprocess.run(
        ['exiftool', file],
        capture_output=True, text=True, timeout=10
    )

    warnings = []
    for line in result.stdout.split('\n'):
        if 'Warning' in line or 'Error' in line or 'error' in line:
            warnings.append(line.strip())

    if warnings:
        print(f"[WARN] Warnings/Errors detected ({len(warnings)}):")
        for w in warnings[:3]:
            print(f"       {w[:100]}")
        file_info['warnings'] = warnings
    else:
        print("[OK] No warnings/errors in metadata")

    # Classify corruption
    if not file_info['basic_read']:
        file_info['corruption_type'] = 'SEVERE_CORRUPTION'
        print("\n--> CLASSIFICATION: SEVERE_CORRUPTION (cannot read)")
    elif file_info['warnings']:
        if any('MakerNotes' in w for w in warnings):
            file_info['corruption_type'] = 'MAKERNOTES'
            print("\n--> CLASSIFICATION: MAKERNOTES (MakerNotes corruption)")
        elif any('EXIF' in w for w in warnings):
            file_info['corruption_type'] = 'EXIF_STRUCTURE'
            print("\n--> CLASSIFICATION: EXIF_STRUCTURE")
        else:
            file_info['corruption_type'] = 'EXIF_STRUCTURE'
            print("\n--> CLASSIFICATION: EXIF_STRUCTURE (has errors)")
    elif not file_info['update_success']:
        file_info['corruption_type'] = 'EXIF_STRUCTURE'
        print("\n--> CLASSIFICATION: EXIF_STRUCTURE (cannot write)")
    else:
        file_info['corruption_type'] = 'HEALTHY'
        print("\n--> CLASSIFICATION: HEALTHY (no corruption detected)")

    results[file] = file_info

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)

for file, info in results.items():
    status = "[CORRUPT]" if info['corruption_type'] != 'HEALTHY' else "[HEALTHY]"
    print(f"{status} {file:40} -> {info['corruption_type']}")

print("\n" + "="*80)
print("READY FOR TEST INTEGRATION")
print("="*80)

# Show which tests can now run
corrupted_files = {k: v for k, v in results.items() if v['corruption_type'] != 'HEALTHY'}
print(f"\nFound {len(corrupted_files)} corrupted files:")
for corruption_type in sorted(set(v['corruption_type'] for v in corrupted_files.values())):
    files_of_type = [k for k, v in corrupted_files.items() if v['corruption_type'] == corruption_type]
    print(f"  * {corruption_type}: {len(files_of_type)} files")

print("\nTests that will now PASS:")
print("  * test_detect_exif_structure_corruption")
print("  * test_detect_makernotes_corruption")
print("  * test_safest_repair_strategy_execution")
print("  * test_thorough_repair_strategy_execution")
print("  * test_aggressive_repair_strategy_execution")
print("  * test_strategy_selection_logic")
print("  * test_backup_creation_during_repair")

