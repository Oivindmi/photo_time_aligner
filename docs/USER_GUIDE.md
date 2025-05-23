# Photo Time Aligner - User Guide

## Quick Start

### Step 1: Install ExifTool
1. Download from https://exiftool.org
2. Extract and rename `exiftool(-k).exe` to `exiftool.exe`
3. Place in `C:\ExifTool\` or add to PATH

### Step 2: Launch Application
Run `PhotoTimeAligner.exe` or `python main.py`

### Step 3: Load Reference Photo
Drag and drop a photo from your reference camera (the one with correct time)

### Step 4: Load Target Photo
Drag and drop a photo from the camera that needs time adjustment

### Step 5: Configure Matching Rules
- **Camera Model**: Enable to match only photos from same camera
- **File Extension**: Enable to match only same file types
- **Filename Pattern**: Enable for files without camera metadata

### Step 6: Select Time Fields
Choose which EXIF field contains the time you want to use for alignment

### Step 7: Apply Alignment
Review the calculated offset and click "Apply Alignment"

## Understanding Time Synchronization

### How It Works
1. The app calculates the time difference between your two photos
2. It finds all similar photos in each folder
3. It applies the time adjustment to sync the cameras

### What Gets Updated
- **Reference Camera Files**: Time fields are synchronized but not shifted
- **Target Camera Files**: Time fields are shifted by the offset AND synchronized

### Example
If your Canon photo is 2 hours ahead of your Nikon photo:
- All Canon photos will have 2 hours subtracted
- All time fields within each photo will match

## Advanced Features

### Master Folder Organization
Enable "Move processed files to master folder" to:
- Collect all processed photos in one location
- Maintain original folder structure
- Handle naming conflicts automatically

### Filename Pattern Matching
Useful for:
- Screenshots without camera metadata
- Phones that don't write camera model
- Scanned photos with consistent naming

### Combining Filters
All three filters work together:
- Camera + Extension: "All Canon CR2 files"
- Camera + Pattern: "All Nikon files starting with DSC_"
- All three: Maximum precision

## Troubleshooting

### No Files Found
- Check that camera model filter isn't too restrictive
- Try disabling camera filter for files without EXIF
- Enable pattern matching for screenshots

### Time Offset Seems Wrong
- Verify you've selected the correct time fields
- Check for timezone issues (app strips timezones)
- Ensure reference photo has correct time

### Performance Issues
- Large folders may take time to scan
- Progress shown in status bar
- App remains responsive during scanning

### ExifTool Not Found
- Verify ExifTool is installed correctly
- Check it's in PATH or standard location
- Restart app after installing

## Tips and Best Practices

1. **Test First**: Try with a few photos before processing hundreds
2. **Same Event**: Use photos from the same event for alignment
3. **Check Results**: Verify a few photos after processing
4. **Original Files**: Keep backups - the app modifies originals
5. **Consistent Selection**: Use same time fields across cameras when possible

## Common Scenarios

### Wedding Photography
- Multiple photographers with different cameras
- Align all cameras to primary photographer's time
- Move all photos to master folder for editing

### Travel Photos
- Phone and camera with different time zones
- Align to local time of destination
- Group by camera model for easy sorting

### Family Events
- Multiple family members' phones/cameras
- Pick one device as reference
- Process each device against reference

## Keyboard Shortcuts
- `Ctrl+Q`: Quit application
- `Tab`: Navigate between controls
- `Space`: Toggle checkboxes
- `Enter`: Apply alignment (when button focused)