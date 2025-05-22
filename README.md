# Photo & Video Time Aligner

A Windows application for synchronizing timestamps across photos and videos from different cameras.

## Features
- Drag and drop interface for photo and video comparison
- Automatic detection of media from the same camera/device
- Batch time adjustment for all matching media files
- Support for 50+ photo and video formats
- Optional master folder organization

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

This will install:
- PyQt5: For the GUI interface
- python-dateutil: For parsing various date formats
- ijson: For efficient streaming JSON parsing

2. Ensure ExifTool is properly installed and available (see ExifTool Installation section)

## Architecture Overview

### Performance Optimizations

The application uses a hybrid ExifTool integration approach that combines:

- **Persistent Process**: Maintains a single ExifTool process to eliminate startup overhead
- **Argument Files**: Uses temporary files with the `-@` flag for reliable file path handling
- **Incremental Processing**: Processes files in batches while updating UI incrementally
- **Thread Safety**: All ExifTool operations are synchronized to prevent conflicts

This approach provides 5-10x performance improvement while maintaining reliability across different file types and quantities.

### Key Design Decisions

1. **Stack Overflow Resolution**: Changed from bulk list returns to incremental signal emission
2. **Windows Compatibility**: Uses argument files instead of command-line arguments
3. **Error Recovery**: Implements automatic ExifTool process restart on failures
4. **Scalability**: Tested with 100+ files without memory or performance issues

For detailed technical documentation, see:
- [Design Decisions](docs/DESIGN_DECISIONS.md)
- [ExifTool Implementation Guide](docs/EXIFTOOL_IMPLEMENTATION.md)
- [Architecture Decision Records](docs/adr/)