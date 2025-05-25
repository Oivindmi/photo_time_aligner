# Photo & Video Time Aligner

A Windows application for synchronizing timestamps across photos and videos from different cameras, with manual time adjustment capabilities, comprehensive metadata investigation tools, single file investigation mode, and **automatic corruption detection and repair**.

## Features
- **Dual Operation Modes**: Full processing mode and single file investigation mode
- Drag and drop interface for photo and video comparison
- Automatic detection of media from the same camera/device
- Batch time adjustment for all matching media files
- **Manual time offset** - adjust photos without needing a target photo
- **Single File Mode** - investigate individual files without processing groups
- **Comprehensive metadata investigation** - explore all EXIF data in your files
- **NEW: Automatic Corruption Detection** - identifies and repairs corrupted EXIF data
- **NEW: Intelligent Repair System** - multiple repair strategies with caching
- **NEW: Mandatory Timestamp Fields** - ensures all processed files get proper datetime metadata
- Support for 50+ photo and video formats
- Optional master folder organization with camera-specific subfolders

## NEW: Corruption Detection & Repair System

### **Automatic Corruption Detection**
The application now automatically scans files for corruption before processing and can repair most types of EXIF corruption:

- **EXIF Structure Errors** (e.g., "Error reading StripOffsets data in IFD0")
- **MakerNotes Issues** (e.g., "MakerNotes offsets may be incorrect")
- **Missing EXIF Metadata** (files with only filesystem dates)
- **Severe Corruption** (various structural problems)

### **Intelligent Repair System**
When corruption is detected, the application offers to repair files using multiple strategies:

1. **Safest Repair**: Minimal changes to preserve existing metadata
2. **Thorough Repair**: Rebuild metadata structure with force flags
3. **Aggressive Repair**: Complete metadata rebuild with minimal EXIF structure
4. **Filesystem-Only Fallback**: Updates filesystem dates when EXIF repair fails

### **Smart Caching**
The system learns which repair strategies work best for different corruption types and tries the most successful approach first in future repairs.

### **Automatic Backups**
Before any repair attempt, the application automatically creates backups in a `backup` folder, ensuring your original files are always safe.

## Operation Modes

### Full Processing Mode (Default)
- Two-photo alignment workflow for synchronizing different cameras
- Single-photo manual adjustment workflow for timezone corrections
- **NEW: Corruption detection and repair** before processing
- Batch processing of matching files
- Master folder organization
- Uses 4 parallel ExifTool processes for optimal performance

### Single File Mode (Investigation Only)
- **Purpose**: Quick investigation of individual file metadata without processing
- **Resource Efficient**: Uses single ExifTool process instead of 4
- **UI Simplified**: Processing controls disabled, focus on investigation
- **Perfect For**: Examining time fields, camera settings, and metadata before processing
- **Toggle**: Checkbox at top of interface for easy switching

## Enhanced Processing Features

### **Mandatory Timestamp Fields**
All processed files now receive these essential timestamp fields:
- **DateTimeOriginal** - When photo/video was taken
- **CreateDate** - When image was created
- **ModifyDate** - When image was modified
- **FileCreateDate** - Windows filesystem creation date
- **FileModifyDate** - Windows filesystem modification date

This ensures every processed file has proper timestamps in both EXIF metadata AND Windows filesystem, making them compatible with all photo management software.

### **Corruption Repair Workflow**
1. **Automatic Detection**: Files are scanned for corruption before processing
2. **User Choice**: If corruption is found, user can choose to attempt repairs
3. **Multiple Strategies**: System tries different repair approaches automatically
4. **Verification**: Each repair is tested to ensure it actually worked
5. **Graceful Fallback**: Failed repairs fall back to filesystem-only updates
6. **Progress Feedback**: Real-time progress and detailed final reports

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
2. **Drop File**: Drag and drop any photo/video into the reference zone
3. **Examine Time Fields**: View all available time/date fields with raw and parsed values
4. **Investigate Metadata**: Click "Investigate Metadata" for comprehensive metadata exploration
5. **Resource Efficient**: Uses only one ExifTool process for optimal performance
6. **Quick Toggle**: Uncheck to return to full processing mode

### Full Processing Mode Workflows

#### Option A: Two-Photo Alignment (Standard)
1. **Disable Single File Mode** (if enabled)
2. Launch the application and load reference photo
3. Load target photo to align
4. **NEW**: If corruption is detected, choose whether to attempt repairs
5. Configure matching rules and select time fields
6. Review calculated offset and apply alignment

#### Option B: Single-Photo Manual Adjustment
1. **Disable Single File Mode** (if enabled)
2. Load reference photo (no target needed)
3. **NEW**: If corruption is detected, choose whether to attempt repairs
4. Set manual time offset using input fields
5. Configure matching rules and apply alignment

### NEW: Corruption Repair Process

When corruption is detected, you'll see:
```
Corruption Analysis Complete:
• 42 files are healthy
• 3 files have repairable corruption
  - 2 files: EXIF structure errors (~70% repair success rate)
  - 1 file: MakerNotes issues (~90% repair success rate)
• 2 files have severe corruption

⏱️ Estimated repair time: 1-2 minutes

[Attempt Repair] [Skip Repair]
```

**Repair Process:**
1. **Automatic Backups**: Created in `backup` folder before any changes
2. **Multiple Strategies**: System tries safest → thorough → aggressive approaches
3. **Real-time Progress**: See which files are being repaired and results
4. **Verification**: Each repair is tested to ensure it actually works
5. **Fallback**: Failed repairs still get filesystem date updates
6. **Caching**: Successful strategies are remembered for future similar files

### Enhanced Results

After processing, you'll see comprehensive reports including:
```
=== Enhanced Photo Time Alignment Report ===

File Repair Operations:
✓ Repair attempted: 5 files
✓ Successfully repaired: 3 files
✗ Repair failed: 2 files

Repair Details:
✓ IMG001.jpg: Repaired using thorough
✓ IMG002.jpg: Repaired using safest
✗ IMG003.jpg: All repair strategies failed

Metadata Updates:
✓ Successfully updated: 47 files
✓ Mandatory fields added: 23 files

📁 Backups saved to: /path/to/backup/folder
```

## Advanced Features

### Metadata Investigation (Available in Both Modes)
- **Enhanced Search**: Filter by field name or value
- **Comprehensive Data**: Shows all metadata ExifTool can extract
- **Time Field Highlighting**: Date/time fields displayed in bold
- **Copy Functions**: Right-click to copy field names, values, or both
- **Works with all formats**: Photos and videos

### Group Selection Rules
- **Camera Model**: Match files from same camera make/model
- **File Extension**: Match files with same file type
- **Filename Pattern**: Match files with similar naming conventions
- **Smart Combination**: All rules work together for precise selection

### Master Folder Organization
- **Root Folder**: All files in master folder root
- **Camera Subfolders**: Organized by camera (e.g., Canon_EOS_R5, Apple_iPhone_14_Pro)

### Performance Optimizations
- **Adaptive Process Management**: 1 process for Single File Mode, 4 for Full Processing
- **Process Pool Architecture**: Concurrent operations for maximum throughput
- **Group-Based Processing**: Files processed in optimized batches
- **Async File Operations**: Non-blocking directory scanning

## Architecture & Design

### Core Components
- **Corruption Detection**: Automatic identification of EXIF issues
- **Repair Strategies**: Multiple approaches for different corruption types
- **Mandatory Fields**: Ensures consistent timestamp structure
- **Process Pool**: Concurrent ExifTool operations
- **Intelligent Caching**: Performance optimization and learning

### Technical Features
- **Unicode Support**: Handles international characters in file paths
- **Error Recovery**: Automatic fallback strategies
- **Resource Management**: Adaptive based on operation mode
- **Comprehensive Logging**: Detailed operation tracking
- **Backup System**: Automatic file protection

## Troubleshooting

### Corruption-Related Issues
- **Backup Files**: Created in `backup` folder with original extensions
- **Log Files**: Detailed repair logs saved automatically
- **Strategy Selection**: System learns optimal approaches over time

### Performance
- **Large Collections**: Tested with 3000+ files
- **Memory Management**: Optimized resource usage
- **Process Optimization**: Automatic pool sizing

## Use Cases

### Professional Photography
- **Multi-camera Events**: Sync all cameras to primary photographer
- **Corruption Recovery**: Repair damaged EXIF from various sources
- **Batch Organization**: Master folder with camera-specific subfolders

### Personal Photo Management
- **Timezone Corrections**: Manual offset for travel photos
- **Legacy Photo Repair**: Fix corruption from old software/scanners
- **Metadata Investigation**: Understand photo origins and settings

### Digital Asset Management
- **Metadata Standardization**: Ensure consistent timestamp fields
- **Quality Control**: Identify and repair corrupted files
- **Batch Processing**: Handle large collections efficiently

## Version History

### Version 2.0.0 (Current)
- ✅ **NEW**: Automatic corruption detection and repair system
- ✅ **NEW**: Mandatory timestamp fields for all processed files
- ✅ **NEW**: Automatic backup system
- ✅ **NEW**: Enhanced progress reporting and error handling
- ✅ **IMPROVED**: Unicode path handling for international characters
- ✅ **IMPROVED**: Filesystem date updates (FileCreateDate, FileModifyDate)

### Version 1.0.0
- Initial release with dual-mode operation
- Single file investigation mode
- Two-photo and manual offset workflows
- Comprehensive metadata investigation
- Support for 50+ media formats

## License
MIT License