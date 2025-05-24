# Photo Time Aligner - User Guide

## Quick Start

### Step 1: Install ExifTool
1. Download from https://exiftool.org
2. Extract and rename `exiftool(-k).exe` to `exiftool.exe`
3. Place in `C:\ExifTool\` or add to PATH

### Step 2: Launch Application
Run `PhotoTimeAligner.exe` or `python main.py`

## Two Workflow Options

### Option A: Two-Photo Alignment (Standard)

#### Step 3A: Load Reference Photo
Drag and drop a photo from your reference camera (the one with correct time)

#### Step 4A: Load Target Photo
Drag and drop a photo from the camera that needs time adjustment

#### Step 5A: Configure and Apply
1. Configure matching rules and select time fields
2. Review calculated offset
3. Click "Apply Alignment"

### Option B: Single-Photo Manual Adjustment (New)

#### Step 3B: Load Reference Photo
Drag and drop the photo you want to adjust (no target photo needed)

#### Step 4B: Set Manual Offset
Use the manual time offset controls:
- **Years**: 0-100 (for very old photos or major corrections)
- **Days**: 0-365 (for date corrections)
- **Hours**: 0-23 (for timezone adjustments)
- **Minutes**: 0-59 (for minor corrections)
- **Seconds**: 0-59 (for precise adjustments)
- **Direction**: Choose "Add" or "Subtract" time

#### Step 5B: Configure and Apply
1. Configure matching rules and select time field
2. Review manual offset settings
3. Click "Apply Alignment"

## Metadata Investigation Feature (New)

### Accessing Metadata Investigation
1. Load at least one photo (reference or target)
2. Click "Investigate Metadata" button next to "Apply Alignment"
3. Select which file to investigate using radio buttons:
   - ○ Reference (default)
   - ○ Target

### Using the Investigation Dialog
- **Search**: Type in the search box to filter fields by name or value
- **Time Fields**: Date/time related fields are displayed in **bold**
- **Copy Data**: Right-click any row to copy:
  - Copy Field Name
  - Copy Value  
  - Copy Both (Field: Value format)
- **Clear Search**: Click "Clear" to show all fields again

### What You'll See
The dialog shows comprehensive metadata including:
- **EXIF**: Camera settings, exposure, ISO, etc.
- **Time Information**: All date/time fields from the file
- **GPS**: Location data (if available)
- **File Info**: File size, format details
- **Maker Notes**: Camera-specific technical data
- **And much more**: Everything ExifTool can extract

## Understanding Time Synchronization

### How It Works
1. The app calculates the time difference between your photos (or uses manual offset)
2. It finds all similar photos in the folder(s)
3. It applies the time adjustment to sync the timestamps

### What Gets Updated
- **Two-Photo Mode**: 
  - Reference files: Time fields synchronized but not shifted
  - Target files: Time fields shifted by calculated offset AND synchronized
- **Single-Photo Mode**:
  - All matching files: Time fields shifted by manual offset AND synchronized

### Example Scenarios

#### Scenario 1: Timezone Correction
Your camera shows 14:30 but local time was 16:30 (2 hours ahead):
- Manual offset: 2 hours "Add"
- All matching photos will have 2 hours added

#### Scenario 2: Wrong Date Setting
Camera date was set to wrong year:
- Manual offset: 1 year "Subtract" (or appropriate days)
- All matching photos will have the time corrected

#### Scenario 3: Multiple Cameras
Canon shows 14:30, Nikon shows 16:45 for same moment:
- Calculated offset: 2 hours 15 minutes
- All Nikon photos will have 2h15m subtracted to match Canon

## Advanced Features

### Group Selection Rules
Combine multiple criteria for precise file matching:

#### Camera Model Matching
- Matches files from same camera make/model
- Useful when you have multiple cameras
- Handles files without camera metadata

#### File Extension Matching
- Matches only same file types (.jpg, .cr2, etc.)
- Useful for separating RAW from JPEG
- Works with all 50+ supported formats

#### Filename Pattern Matching
- Detects patterns like DSC_####, IMG_####, Screenshot_*
- Essential for files without camera metadata
- Handles video-specific patterns (VID_####, MOV_####)

### Master Folder Organization

#### Root Folder Mode
- All processed files moved to master folder root
- Simple flat structure
- Good for small collections

#### Camera Subfolder Mode (Recommended)
- Creates subfolders for each camera/device
- Examples: `Canon_EOS_R5`, `Apple_iPhone_14_Pro`, `Unknown_Camera_JPG_1`
- Excellent for organizing multi-camera events
- Handles files without camera metadata gracefully

### Time Field Selection
Choose the most reliable time field for your photos:
- **CreateDate**: Usually most reliable
- **DateTimeOriginal**: Original capture time
- **ModifyDate**: Last modification time
- **GPS DateTime**: From GPS data
- **And more**: Any date/time field found in metadata

## Troubleshooting

### No Files Found
- Check that camera model filter isn't too restrictive
- Try disabling camera filter for files without EXIF
- Enable pattern matching for screenshots/unknown files

### Manual Offset Not Working
- Ensure target photo section is empty (manual mode only works with single photo)
- Check that at least one offset value is greater than 0
- Verify the correct Add/Subtract direction is selected

### Time Offset Seems Wrong
- Verify you've selected the correct time fields
- Check for timezone issues (app strips timezones automatically)
- Ensure reference photo has correct time
- Use metadata investigation to verify time field values

### Performance Issues
- Large folders may take time to scan
- Progress shown in status bar
- App remains responsive during scanning
- Consider using pattern matching to reduce file count

### ExifTool Not Found
- Verify ExifTool is installed correctly
- Check it's in PATH or standard location (`C:\ExifTool\`)
- Restart app after installing

### Metadata Investigation Empty
- File may have no metadata (some screenshots, edited images)
- Try a different photo to verify the feature works
- Check ExifTool installation

## Tips and Best Practices

### Before You Start
1. **Test First**: Try with a few photos before processing hundreds
2. **Same Event**: Use photos from the same event for alignment
3. **Backup**: Keep backups - the app modifies original files
4. **Check Results**: Verify a few photos after processing

### Choosing Time Fields
1. **Consistency**: Use same time fields across cameras when possible
2. **Reliability**: CreateDate and DateTimeOriginal are usually most reliable
3. **Investigation**: Use metadata investigation to see all available options

### Manual Offset Guidelines
1. **Timezone Changes**: Most common use case (add/subtract hours)
2. **Date Corrections**: Use days/years for major date errors
3. **Precision**: Use minutes/seconds for fine adjustments
4. **Direction**: Double-check Add vs Subtract before applying

### Master Folder Strategy
1. **Camera Subfolders**: Recommended for multi-camera events
2. **Naming**: Subfolders use camera make/model for clear identification
3. **Unknown Files**: Screenshots and metadata-less files get numbered folders
4. **Organization**: Maintains clear structure for post-processing

## Common Scenarios

### Wedding Photography
- Multiple photographers with different cameras
- Use two-photo mode to align all cameras to primary photographer's time
- Enable camera subfolders for organized delivery

### Travel Photos
- Phone and camera with different time zones
- Use manual offset to correct timezone without needing reference photo
- Group by camera model for easy sorting

### Family Events
- Multiple family members' phones/cameras
- Pick one device as reference
- Process each device against reference using two-photo mode

### Equipment Testing
- Use metadata investigation to compare camera settings
- Analyze EXIF differences between shots
- Identify camera capabilities and limitations

### Photo Restoration
- Old photos with incorrect timestamps
- Use manual offset with years/days to correct dates
- Pattern matching for consistently named scanned photos

## Keyboard Shortcuts
- `Ctrl+Q`: Quit application
- `Tab`: Navigate between controls
- `Space`: Toggle checkboxes
- `Enter`: Apply alignment (when button focused)
- `Ctrl+F`: Focus search box (in metadata investigation dialog)