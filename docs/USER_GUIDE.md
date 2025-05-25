# Photo Time Aligner - User Guide

## Quick Start

### Step 1: Install ExifTool
1. Download from https://exiftool.org
2. Extract and rename `exiftool(-k).exe` to `exiftool.exe`
3. Place in `C:\ExifTool\` or add to PATH

### Step 2: Launch Application
Run `PhotoTimeAligner.exe` or `python main.py`

### Step 3: Choose Your Mode
The application offers two distinct modes for different use cases:

## Operation Modes

### Single File Mode (Investigation Only) - NEW
**When to use**: Quick examination of individual files without processing

#### Step 3A: Enable Single File Mode
1. Check "Single File Mode (Investigation Only)" at the top of the interface
2. Notice how processing controls are disabled and interface is simplified

#### Step 4A: Investigate File
1. Drag and drop any photo/video into the reference zone
2. **Examine Time Fields**: All available time/date fields are displayed with:
   - Field names (e.g., CreateDate, ModifyDate)
   - Raw values (as stored in file)
   - Parsed values (interpreted by application)
3. **Use Investigation**: Click "Investigate Metadata" for comprehensive metadata exploration

#### Benefits of Single File Mode:
- **Resource Efficient**: Uses only 1 ExifTool process (instead of 4)
- **Simplified Interface**: No distracting processing controls
- **Quick Investigation**: Perfect for understanding file metadata before processing
- **Educational**: Learn about different metadata standards and camera settings

### Full Processing Mode (Default)
**When to use**: Actual time synchronization and batch processing

## Full Processing Workflows

### Option A: Two-Photo Alignment (Standard)

#### Step 3A: Load Reference Photo
Drag and drop a photo from your reference camera (the one with correct time)

#### Step 4A: Load Target Photo
Drag and drop a photo from the camera that needs time adjustment

#### Step 5A: Configure and Apply
1. Configure matching rules and select time fields
2. Review calculated offset
3. Click "Apply Alignment"

### Option B: Single-Photo Manual Adjustment

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

## Mode Switching

### Switching Between Modes
- **Toggle Checkbox**: Check/uncheck "Single File Mode" at any time
- **Automatic Cleanup**: Mode switching automatically stops file scanning and clears lists
- **Resource Management**: ExifTool processes are optimized for each mode
- **Preference Saved**: Your last used mode is remembered between sessions

### Visual Indicators
- **Single File Mode**: 
  - Status: "Single File Mode - Investigation Only"
  - Processing controls are grayed out
  - Only reference section is active
- **Full Processing Mode**:
  - Status: "Normal Mode - Full Processing"
  - All controls are active
  - Both reference and target sections available

## Understanding Time Synchronization (Full Processing Mode Only)

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

## Metadata Investigation Feature (Available in Both Modes)

### Accessing Metadata Investigation
1. Load at least one photo (reference or target)
2. Click "Investigate Metadata" button
3. Select which file to investigate using radio buttons:
   - ○ Reference (always available)
   - ○ Target (disabled in Single File Mode)

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

## Advanced Features (Full Processing Mode Only)

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

## Workflow Recommendations

### Before Processing: Use Single File Mode
1. **Enable Single File Mode**
2. **Drop representative files** from each camera/device
3. **Examine time fields** to understand what's available
4. **Check for issues** like missing timestamps or wrong timezones
5. **Plan your approach** based on findings

### For Processing: Switch to Full Processing Mode
1. **Disable Single File Mode**
2. **Choose appropriate workflow** (two-photo or manual offset)
3. **Configure group rules** based on your investigation
4. **Process files** with confidence

### After Processing: Use Single File Mode Again
1. **Re-enable Single File Mode**
2. **Verify results** by examining processed files
3. **Confirm time synchronization** worked correctly

## Troubleshooting

### Mode-Related Issues

#### Single File Mode Not Working
- Ensure checkbox is checked at top of interface
- Verify processing controls are grayed out
- Check status bar shows "Single File Mode - Investigation Only"

#### Can't Process Files
- Ensure Single File Mode is **disabled** (unchecked)
- Check that Apply Alignment button is enabled
- Verify you have loaded appropriate files for your workflow

### Performance Issues

#### Slow in Full Processing Mode
- Large folders may take time to scan with 4 processes
- Progress shown in status bar
- Consider using pattern matching to reduce file count

#### High Resource Usage
- Switch to Single File Mode for investigation tasks
- Uses only 1 ExifTool process instead of 4
- Significantly reduces memory and CPU usage

### General Issues

#### No Files Found
- Check that camera model filter isn't too restrictive
- Try disabling camera filter for files without EXIF
- Enable pattern matching for screenshots/unknown files

#### Time Offset Seems Wrong
- Use Single File Mode to investigate time field values first
- Verify you've selected the correct time fields
- Check for timezone issues (app strips timezones automatically)
- Ensure reference photo has correct time

#### ExifTool Not Found
- Verify ExifTool is installed correctly
- Check it's in PATH or standard location (`C:\ExifTool\`)
- Restart app after installing

#### Metadata Investigation Empty
- File may have no metadata (some screenshots, edited images)
- Try a different photo to verify the feature works
- Check ExifTool installation

## Tips and Best Practices

### Mode Selection Strategy
1. **Start with Single File Mode**: Always investigate before processing
2. **Switch for Processing**: Use Full Processing Mode for actual work
3. **Return for Verification**: Check results with Single File Mode

### Before You Start
1. **Investigate First**: Use Single File Mode to understand your files
2. **Test Small**: Try with a few photos before processing hundreds
3. **Same Event**: Use photos from the same event for alignment
4. **Backup**: Keep backups - the app modifies original files

### Choosing Time Fields
1. **Investigate Available Fields**: Use Single File Mode to see all options
2. **Consistency**: Use same time fields across cameras when possible
3. **Reliability**: CreateDate and DateTimeOriginal are usually most reliable

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

### Investigation Workflow
- **Before Purchase**: Examine sample files from different cameras
- **Before Processing**: Understand available time fields and quality
- **Troubleshooting**: Investigate files with timestamp issues
- **Learning**: Understand metadata standards and camera differences

### Wedding Photography
- Use Single File Mode to examine samples from each photographer
- Switch to Full Processing Mode to align all cameras to primary photographer's time
- Enable camera subfolders for organized delivery

### Travel Photos
- Investigate timezone issues using Single File Mode
- Use manual offset to correct timezone without needing reference photo
- Group by camera model for easy sorting

### Family Events
- Examine time field quality across different devices
- Pick one device as reference after investigation
- Process each device against reference using two-photo mode

### Equipment Testing
- Use Single File Mode to compare camera settings and capabilities
- Analyze EXIF differences between shots in investigation dialog
- Identify camera capabilities and limitations

## Keyboard Shortcuts
- `Ctrl+Q`: Quit application
- `Tab`: Navigate between controls
- `Space`: Toggle checkboxes (including Single File Mode)
- `Enter`: Apply alignment (when button focused and enabled)
- `Ctrl+F`: Focus search box (in metadata investigation dialog)

## Performance Optimization

### Resource Management
- **Single File Mode**: 1 ExifTool process, minimal memory usage
- **Full Processing Mode**: 4 ExifTool processes, maximum performance
- **Automatic Switching**: Resources are optimized when switching modes

### Best Practices for Performance
- Use Single File Mode for investigation tasks to conserve resources
- Switch to Full Processing Mode only when ready to process files
- The application automatically manages ExifTool processes for optimal performance