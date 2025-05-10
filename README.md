# Photo Time Aligner

A Windows application for synchronizing timestamps across photos from different cameras.

## Features
- Drag and drop interface for photo comparison
- Automatic detection of photos from the same camera
- Batch time adjustment for all matching photos
- Optional master folder organization

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