# Photo & Video Time Aligner

[![Test Pipeline](https://github.com/OivindHoem/photo_time_aligner/actions/workflows/test-pipeline.yml/badge.svg)](https://github.com/OivindHoem/photo_time_aligner/actions/workflows/test-pipeline.yml)
[![Nightly Performance Tests](https://github.com/OivindHoem/photo_time_aligner/actions/workflows/nightly-performance.yml/badge.svg)](https://github.com/OivindHoem/photo_time_aligner/actions/workflows/nightly-performance.yml)

A Windows application for synchronizing timestamps across photos and videos from different cameras, with manual time adjustment capabilities, comprehensive metadata investigation tools, single file investigation mode, and **advanced corruption detection and repair with user-controlled strategy selection**.

## Features
- **Dual Operation Modes**: Full processing mode and single file investigation mode
- **Optional Corruption Detection**: Toggle corruption scanning for faster processing when not needed
- **Advanced Repair System**: User-selectable repair strategies with automatic backups
- Drag and drop interface for photo and video comparison
- Automatic detection of media from the same camera/device
- Batch time adjustment for all matching media files
- **Manual time offset** - adjust photos without needing a target photo
- **Single File Mode** - investigate individual files without processing groups
- **Comprehensive metadata investigation** - explore all EXIF data in your files
- **NEW: User-Controlled Repair Strategies** - Choose between automatic progression or force specific repair methods
- **NEW: Enhanced Backup Management** - Easy access to backup files with click-to-copy paths
- **NEW: Performance Optimization** - Optional corruption detection for faster processing
- Support for 50+ photo and video formats
- Optional master folder organization with camera-specific subfolders

## NEW: Enhanced Corruption Detection & Repair System

### **Optional Corruption Detection**
The application now includes a toggle for corruption detection, allowing users to choose between:

- **Enabled (Default)**: Full corruption scanning and repair capabilities
- **Disabled**: Skip corruption analysis for faster processing of known-good files

### **User-Controlled Repair Strategies**
When corruption is detected, users can choose their repair approach:

#### **Automatic Mode (Recommended)**
- Tries repair strategies in order: Safest → Thorough → Aggressive → Filesystem-only
- Automatically progresses until a strategy works
- Best balance of safety and success rate

#### **Force Specific Strategy**
- **Force Safest**: Minimal changes, preserve existing metadata (~90% success rate)
- **Force Thorough**: Rebuild metadata structure with force flags (~70% success rate)
- **Force Aggressive**: Complete metadata rebuild with minimal EXIF structure (~50% success rate)
- **Force Filesystem-Only**: Update filesystem dates only, skip EXIF repair (~30% success rate)

### **Enhanced Corruption Analysis**
- **Detailed Classification**: Files grouped by corruption type (EXIF Structure, MakerNotes, etc.)
- **Success Rate Estimates**: Shows expected repair success rates for each corruption type
- **Clean Error Messages**: User-friendly error descriptions without technical file paths
- **Repairability Assessment**: Clear indication of which files can be repaired

### **Advanced Backup Management**
- **Automatic Backups**: Created before any repair attempt with proper file extensions
- **Interactive Backup Browser**: Click any backup path to copy to clipboard
- **Color-Coded Results**: Green for successful repairs, yellow for failed attempts
- **Backup Path Export**: Copy all backup paths at once for external management
- **Detailed Backup Information**: Shows original file, backup location, repair strategy used

### **Smart Caching and Learning**
The system learns which repair strategies work best for different corruption types and optimizes future repairs accordingly.

## Operation Modes

### Single File Mode (Investigation Only)
- **Purpose**: Quick investigation of individual file metadata without processing
- **Resource Efficient**: Uses single ExifTool process instead of 4
- **UI Simplified**: Processing controls disabled, focus on investigation
- **Perfect For**: Examining time fields, camera settings, and metadata before processing
- **Toggle**: Checkbox at top of interface for easy switching

### Full Processing Mode (Default)
- Two-photo alignment workflow for synchronizing different cameras
- Single-photo manual adjustment workflow for timezone corrections
- **Optional Corruption Detection**: Toggle for performance optimization
- **User-Controlled Repair**: Choose repair strategy when corruption is found
- Batch processing of matching files
- Master folder organization
- Uses 4 parallel ExifTool processes for optimal performance

## Enhanced Processing Features

### **Mandatory Timestamp Fields**
All processed files now receive these essential timestamp fields:
- **DateTimeOriginal** - When photo/video was taken
- **CreateDate** - When image was created
- **ModifyDate** - When image was modified
- **FileCreateDate** - Windows filesystem creation date
- **FileModifyDate** - Windows filesystem modification date

### **Advanced Corruption Repair Workflow**
1. **Optional Detection**: Choose whether to scan for corruption (toggle at top of interface)
2. **Detailed Analysis**: View corruption details grouped by type with success rates
3. **Strategy Selection**: Choose automatic progression or force specific repair method
4. **Automatic Backups**: Files backed up with accessible paths before any changes
5. **Real-time Progress**: See repair progress with strategy information
6. **Interactive Results**: Browse backup files with click-to-copy functionality
7. **Comprehensive Reporting**: Detailed logs with backup locations and repair outcomes

## Performance Optimization

### **Optional Corruption Detection**
- **Toggle Control**: Checkbox next to Single File Mode for easy access
- **Default**: Enabled for maximum data safety
- **When to Disable**: For known-good files or when speed is priority
- **Performance Impact**: Can reduce processing time significantly for large batches

### **Adaptive Resource Management**
- **Single File Mode**: 1 ExifTool process for minimal resource usage
- **Full Processing Mode**: 4 ExifTool processes for maximum throughput
- **Optional Corruption Scan**: Skip resource-intensive corruption analysis when not needed

## Supported Media Formats

The application supports a comprehensive range of photo and video formats:

### Photo Formats
- **Common**: JPG, JPEG, PNG, BMP, TIFF, TIF, GIF
- **RAW**: CR2, NEF, ARW, DNG, ORF, RW2, RAF, RWL, DCR, SRW, X3F
- **Modern**: HEIC, HEIF, WebP, AVIF, JXL
- **Professional**: PSD, EXR, HDR, TGA
- **Other**: SVG, PBM, PGM, PPM

### Video Formats
- **Common**: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, MPG, MPEG
- **Professional**: MXF, R3D, BRAW, ARI, ProRes
- **Mobile**: 3GP, 3G2, MTS, M2TS
- **Other**: TS, VOB, OGV, RM, RMVB, ASF, M2V, F4V, MOD, TOD

## Requirements
- Windows 10 or later
- Python 3.8+ (if running from source)
- ExifTool (see installation instructions below)

## ExifTool Installation
1. Download ExifTool for Windows from https://exiftool.org
2. Extract the zip file
3. Rename `exiftool(-k).exe` to `exiftool.exe`
4. Either:
   - Place `exiftool.exe` in `C:\Windows\` or `C:\ExifTool\`
   - OR add the ExifTool directory to your system PATH

## Installation
1. Install required Python packages:
```
pip install -r requirements.txt
```

2. Ensure ExifTool is properly installed and available (see ExifTool Installation section)

## Usage

### Single File Mode (Investigation Only) - Enhanced
1. **Enable Single File Mode**: Check "Single File Mode (Investigation Only)" at the top
2. **Optional**: Disable "Enable Corruption Detection & Repair" for faster investigation
3. **Drop File**: Drag and drop any photo/video into the reference zone
4. **Examine Time Fields**: View all available time/date fields with raw and parsed values
5. **Investigate Metadata**: Click "Investigate Metadata" for comprehensive metadata exploration
6. **Resource Efficient**: Uses only one ExifTool process for optimal performance

### Full Processing Mode Workflows

#### Option A: Two-Photo Alignment (Standard)
1. **Disable Single File Mode** (if enabled)
2. **Choose Corruption Detection**: Enable for unknown files, disable for speed
3. Launch the application and load reference photo
4. Load target photo to align
5. **NEW**: If corruption is detected (and enabled), choose repair strategy
6. Configure matching rules and select time fields
7. Review calculated offset and apply alignment

#### Option B: Single-Photo Manual Adjustment
1. **Disable Single File Mode** (if enabled)
2. **Choose Corruption Detection**: Enable for safety, disable for speed
3. Load reference photo (no target needed)
4. **NEW**: If corruption is detected (and enabled), choose repair strategy
5. Set manual time offset using input fields
6. Configure matching rules and apply alignment

### NEW: Corruption Detection and Repair Process

#### When Corruption Detection is Enabled:
```
Corruption Analysis Complete:
• 42 files are healthy
• 3 files have repairable corruption
  - 2 files: EXIF Structure (~70% repair success rate)
  - 1 file: MakerNotes Issues (~90% repair success rate)
• 2 files have severe corruption

Choose repair approach:
○ Automatic (Recommended) - Try strategies in order
○ Force Safest - Minimal changes (~90% success)
○ Force Thorough - Rebuild structure (~70% success)
○ Force Aggressive - Complete rebuild (~50% success)
○ Force Filesystem-Only - Skip EXIF repair (~30% success)

⏱️ Time: 1-2 minutes    📁 Backups will be created automatically

[Skip Repair] [Attempt Repair]
```

#### Enhanced Results with Backup Management:
```
=== Enhanced Photo Time Alignment Report ===

File Repair Operations:
✓ Repair attempted: 5 files
✓ Successfully repaired: 3 files
✗ Repair failed: 2 files

Repair Details:
✓ IMG001.jpg: Repaired using thorough
  📁 Backup: C:\backup\IMG001_backup.jpg
✓ IMG002.jpg: Repaired using safest
  📁 Backup: C:\backup\IMG002_backup.jpg
✗ IMG003.jpg: All repair strategies failed
  📁 Backup preserved: C:\backup\IMG003_backup.jpg

Interactive Backup Browser:
• Click any backup path to copy to clipboard
• Color-coded entries (green=success, yellow=failed)
• "Copy All Paths" button for batch operations

Metadata Updates:
✓ Successfully updated: 47 files
✓ Mandatory fields added: 23 files

📁 Backups saved to accessible locations with full path information
```

## Advanced Features

### Enhanced Metadata Investigation (Available in Both Modes)
- **Comprehensive Search**: Filter by field name or value
- **Corruption-Aware**: Shows metadata quality and potential issues
- **Time Field Highlighting**: Date/time fields displayed in bold
- **Copy Functions**: Right-click to copy field names, values, or both
- **Works with all formats**: Photos and videos

### Performance Controls
- **Corruption Detection Toggle**: Enable/disable corruption scanning
- **Single File Mode**: Resource-efficient investigation
- **Adaptive Processing**: Automatic resource allocation based on mode

### Group Selection Rules
- **Camera Model**: Match files from same camera make/model
- **File Extension**: Match files with same file type
- **Filename Pattern**: Match files with similar naming conventions
- **Smart Combination**: All rules work together for precise selection

### Master Folder Organization
- **Root Folder**: All files in master folder root
- **Camera Subfolders**: Organized by camera (e.g., Canon_EOS_R5, Apple_iPhone_14_Pro)

## Use Cases

### Professional Photography
- **Multi-camera Events**: Sync all cameras with user-controlled repair strategies
- **Corruption Recovery**: Advanced repair with backup management
- **Batch Organization**: Master folder with camera-specific subfolders
- **Performance Optimization**: Toggle corruption detection based on file source

### Personal Photo Management
- **Timezone Corrections**: Manual offset for travel photos
- **Legacy Photo Repair**: Fix corruption from old software/scanners with strategy selection
- **Metadata Investigation**: Understand photo origins and settings
- **Fast Processing**: Disable corruption detection for known-good files

### Digital Asset Management
- **Metadata Standardization**: Ensure consistent timestamp fields
- **Quality Control**: User-controlled corruption detection and repair
- **Backup Management**: Easy access to backup files with click-to-copy paths
- **Batch Processing**: Handle large collections efficiently with performance controls

## Version History

### Version 3.0.0 (Current)
- ✅ **NEW**: Optional corruption detection toggle for performance optimization
- ✅ **NEW**: User-selectable repair strategies (Automatic, Force Safest, Force Thorough, etc.)
- ✅ **NEW**: Enhanced backup management with click-to-copy paths
- ✅ **NEW**: Interactive results browser with color-coded backup files
- ✅ **NEW**: Detailed corruption analysis with success rate estimates
- ✅ **NEW**: Clean error message display without technical file paths
- ✅ **IMPROVED**: Advanced Windows path handling for Norwegian characters and long paths
- ✅ **IMPROVED**: Performance controls for different use cases

### Version 2.0.0 (Previous)
- ✅ **NEW**: Automatic corruption detection and repair system
- ✅ **NEW**: Mandatory timestamp fields for all processed files
- ✅ **NEW**: Automatic backup system
- ✅ **IMPROVED**: Unicode path handling for international characters

### Version 1.0.0
- Initial release with dual-mode operation
- Single file investigation mode
- Two-photo and manual offset workflows
- Comprehensive metadata investigation
- Support for 50+ media formats

## License
MIT License