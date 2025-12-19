#!/usr/bin/env python3
"""Analyze new batch of corrupted test files"""

import subprocess
import os
import json
from pathlib import Path

# Change to directory with corrupted files
test_dir = Path("C:/Users/AB33529/testoffunctions/photo_time_aligner/tests/fixtures/sample_media/corrupted_user_provided/")
os.chdir(test_dir)

# Include both image and video formats
files = sorted([f for f in os.listdir('.') if f.lower().endswith(('.jpg', '.jpeg', '.mpg', '.mp4', '.avi', '.mov', '.mts'))])

print("\n" + "="*80)
print("CORRUPTION ANALYSIS REPORT - NEW BATCH")
print("="*80)

results = {}

for file in files:
    print(f"\n{'='*80}")
    print(f"FILE: {file}")
    print('='*80)

    file_info = {
        'name': file,
        'size_mb': os.path.getsize(file) / (1024 * 1024),
        'basic_read': False,
        'update_success': False,
        'warnings': [],
        'corruption_type': 'UNKNOWN'
    }

    print(f"File size: {file_info['size_mb']:.1f} MB")

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
        if result.stderr:
            print(f"       Error: {result.stderr[:150]}")

    # Test 2: Try to update metadata (use appropriate field for video)
    if file.lower().endswith(('.mpg', '.mp4', '.avi', '.mov', '.mts')):
        update_field = 'MediaCreateDate'  # Standard video field
    else:
        update_field = 'DateTimeOriginal'  # Standard photo field

    result = subprocess.run(
        ['exiftool', f'-{update_field}=2024:01:01 12:00:00', '-m', '-ignoreMinorErrors', '-overwrite_original', file],
        capture_output=True, text=True, timeout=10
    )

    output = result.stdout + result.stderr
    if "1 image files updated" in output or "1 files updated" in output:
        print("[OK] Metadata write: SUCCESS")
        file_info['update_success'] = True
    else:
        print("[FAIL] Metadata write: FAILED or UNCHANGED")
        if output:
            print(f"       Output: {output[:200]}")
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
        elif any('EXIF' in w or 'Error' in w for w in warnings):
            file_info['corruption_type'] = 'EXIF_STRUCTURE'
            print("\n--> CLASSIFICATION: EXIF_STRUCTURE (has errors)")
        else:
            file_info['corruption_type'] = 'EXIF_STRUCTURE'
            print("\n--> CLASSIFICATION: EXIF_STRUCTURE (has warnings)")
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

healthy_count = 0
corrupt_count = 0

for file, info in results.items():
    status = "[CORRUPT]" if info['corruption_type'] != 'HEALTHY' else "[HEALTHY]"
    print(f"{status} {file:30} -> {info['corruption_type']:20} ({info['size_mb']:6.1f} MB)")
    if info['corruption_type'] == 'HEALTHY':
        healthy_count += 1
    else:
        corrupt_count += 1

print("\n" + "="*80)
print("BATCH STATISTICS")
print("="*80)
print(f"Total files analyzed: {len(results)}")
print(f"  Healthy files:      {healthy_count}")
print(f"  Corrupted files:    {corrupt_count}")

# Breakdown by corruption type
corruption_breakdown = {}
for file, info in results.items():
    ct = info['corruption_type']
    if ct not in corruption_breakdown:
        corruption_breakdown[ct] = []
    corruption_breakdown[ct].append(file)

print("\nBreakdown by corruption type:")
for ct in sorted(corruption_breakdown.keys()):
    print(f"  {ct:20} : {len(corruption_breakdown[ct]):2} files")
    for f in corruption_breakdown[ct]:
        print(f"    - {f}")

print("\n" + "="*80)
print("DETECTION ASSESSMENT")
print("="*80)
if corrupt_count > 0:
    print(f"Detection rate: {corrupt_count}/{len(results)} files detected as corrupt")
    print("Our CorruptionDetector should now handle these files.")
else:
    print("All files appear healthy to basic tests.")
    print("May need to investigate further with verbose ExifTool output.")
