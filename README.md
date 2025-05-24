# Photo & Video Time Aligner

A Windows application for synchronizing timestamps across photos and videos from different cameras, with manual time adjustment capabilities and comprehensive metadata investigation tools.

## Features
- Drag and drop interface for photo and video comparison
- Automatic detection of media from the same camera/device
- Batch time adjustment for all matching media files
- **Manual time offset** - adjust photos without needing a target photo
- **Comprehensive metadata investigation** - explore all EXIF data in your files
- Support for 50+ photo and video formats
- Optional master folder organization with camera-specific subfolders

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

### Two-Photo Workflow (Standard)
1. Launch the application
2. Drag and drop a reference photo from one camera
3. Drag and drop a photo to align from another camera
4. Select which time fields to use for synchronization
5. Configure group selection rules (camera model, file extension, filename pattern)
6. Review the calculated time offset
7. Optionally set a master folder for organized output
8. Click "Apply Alignment" to synchronize all matching photos

### Single-Photo Workflow (Manual Offset) - **NEW**
1. Launch the application
2. Drag and drop a reference photo (no target photo needed)
3. Configure group selection rules for matching files
4. Select the time field to use for synchronization
5. Set manual time offset using the input fields:
   - Years (0-100), Days (0-365), Hours (0-23), Minutes (0-59), Seconds (0-59)
   - Choose "Add" or "Subtract" time
6. Optionally set a master folder for organized output
7. Click "Apply Alignment" to apply the manual offset to all matching photos

### Metadata Investigation - **NEW**
- Click "Investigate Metadata" next to Apply Alignment
- Choose Reference or Target file using radio buttons
- Explore comprehensive metadata in a searchable table
- Time/date fields are highlighted in bold
- Right-click to copy field names, values, or both
- Use search box to filter fields by name or value

### Group Selection Rules
The application identifies which files belong together using configurable rules:
- **Camera Model**: Match files from the same camera make/model
- **File Extension**: Match files with the same file type
- **Filename Pattern**: Match files with similar naming conventions (e.g., DSC_####, IMG_####)

All rules can be combined for precise file selection.

### Time Field Synchronization
The application handles time synchronization as follows:
- **Reference Group**: Selected time field remains unchanged; all other populated fields sync to it
- **Target Group**: Selected time field is adjusted by the calculated offset; all other fields sync to the adjusted time
- **Single Photo Mode**: All fields are adjusted by the manual offset
- **Empty Fields**: Never populated - only existing time fields are updated

### Master Folder Organization
Choose between two organization methods:
- **Root Folder**: All processed files moved to the master folder root
- **Camera Subfolders**: Files organized into camera-specific subfolders (e.g., Canon_EOS_R5, Unknown_Camera_JPG_1)

## Use Cases

### Wedding Photography
- Multiple photographers with different cameras
- Align all cameras to primary photographer's time
- Move all photos to master folder for editing

### Travel Photos with Manual Adjustment
- Camera forgot to change timezone
- Use manual offset to add/subtract hours for correct local time
- Process without needing a reference photo

### Equipment Analysis
- Use metadata investigation to explore camera settings
- Compare EXIF data between different photos
- Identify missing or corrupted metadata fields

## Architecture Overview

### Performance Optimizations

#### Process Pool Architecture
The application uses a pool of ExifTool processes for concurrent operations, providing 5-10x performance improvement for batch operations:
- 3 concurrent ExifTool processes by default (configurable)
- Thread-safe process management with automatic recovery
- Parallel metadata reading for large file sets

#### Async File Operations
- Asynchronous directory scanning using `os.scandir`
- Concurrent file filtering with configurable batch sizes
- 2-3x faster directory traversal for large folders

#### Optimized Batch Processing
- Parallel metadata extraction in batches of 20 files
- Reduced ExifTool call overhead through batch operations
- Efficient memory usage through streaming operations

#### Performance Characteristics
- **File Discovery**: ~5-10x faster with process pool
- **Metadata Updates**: ~3-5x faster than sequential processing
- **Scalability**: Tested with 10,000+ files successfully
- **Memory Usage**: Constant regardless of file count

For detailed technical documentation, see:
- [Design Decisions](docs/DESIGN_DECISIONS.md)
- [ExifTool Implementation Guide](docs/EXIFTOOL_IMPLEMENTATION.md)
- [User Guide](docs/USER_GUIDE.md)
- [Architecture Decision Records](docs/adr/)

## License
MIT License