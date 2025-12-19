# Photo Time Aligner - Claude Code Context

## Project Overview
**Photo Time Aligner** is a Windows desktop application for synchronizing timestamps across photos and videos from different cameras. Built with Python 3.11 and PyQt5, it uses ExifTool for metadata manipulation.

**Developer**: Øivind Hoem  
**Version**: 3.0.0  
**License**: MIT

## Quick Start Commands
```bash
# Run the application
python main.py

# Run tests
python -m pytest tests/
python tests/test_video_support.py
python tests/test_mixed_media.py

# Troubleshoot a file
python troubleshoot_files.py <file_path>

# Test corruption repair
python test_corruption_fix.py <file_path>
python test_exiftool_repair.py <file_path>
```

## Architecture Overview

### Directory Structure
```
photo_time_aligner/
├── main.py                 # Application entry point
├── src/
│   ├── core/               # Business logic
│   │   ├── exif_handler.py         # High-level ExifTool interface
│   │   ├── exiftool_process.py     # Persistent ExifTool process
│   │   ├── exiftool_pool.py        # Process pool management
│   │   ├── file_processor.py       # Batch file operations
│   │   ├── corruption_detector.py  # Corruption classification
│   │   ├── repair_strategies.py    # Repair strategy implementations
│   │   ├── alignment_processor.py  # Main alignment workflow
│   │   ├── time_calculator.py      # DateTime parsing/calculation
│   │   ├── filename_pattern.py     # Filename pattern matching
│   │   └── supported_formats.py    # 54 supported media formats
│   ├── ui/                 # PyQt5 GUI
│   │   ├── main_window.py          # Main application window
│   │   ├── repair_dialog.py        # Corruption repair UI
│   │   ├── metadata_dialog.py      # Metadata investigation UI
│   │   ├── progress_dialog.py      # Progress feedback
│   │   └── file_scanner_thread.py  # Async file scanning
│   └── utils/              # Utilities
│       └── exceptions.py           # Custom exceptions
├── docs/                   # Documentation
│   ├── adr/                        # Architecture Decision Records
│   ├── DESIGN_DECISIONS.md
│   ├── EXIFTOOL_IMPLEMENTATION.md
│   └── PERFORMANCE_OPTIMIZATION.md
└── tests/                  # Test scripts
```

### Core Components Flow
```
MainWindow (UI)
    ↓
AlignmentProcessor (orchestrates workflow)
    ↓
┌─────────────────┬──────────────────┬─────────────────┐
↓                 ↓                  ↓                 ↓
CorruptionDetector → FileRepairer → FileProcessor → ExifHandler
                                         ↓
                                   ExifToolProcessPool
                                         ↓
                                   ExifToolProcess (persistent)
```

## ⚠️ CRITICAL PATTERNS - MUST FOLLOW

### 1. Unicode/Norwegian Character Handling
**ALWAYS use argument files for ExifTool commands with file paths:**
```python
# ✅ CORRECT - Use argument file approach
with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
    arg_file.write(file_path + '\n')
    arg_file_path = arg_file.name

cmd = [
    self.exiftool_path,
    '-charset', 'filename=utf8',  # REQUIRED for Norwegian chars
    '-@', arg_file_path
]

# ❌ WRONG - Direct file path in command
cmd = [self.exiftool_path, '-json', file_path]  # Fails with Ø, Æ, Å
```

### 2. Windows Path Length Handling
**Check and handle paths > 250 characters:**
```python
# Truncate long filenames
if len(backup_path) > 250:
    # Use temp directory or truncate name
    backup_path = self._create_temp_backup(file_path)

# Normalize paths
file_path = os.path.normpath(file_path)
```

### 3. ExifTool Process Management
**Restart pool between groups to prevent zombie processes:**
```python
# Process files in groups of 60-80
GROUP_SIZE = 60

for group_index in range(num_groups):
    # Process group...
    
    # CRITICAL: Restart pool between groups
    if group_index < num_groups - 1:
        self.exif_handler.exiftool_pool.restart_pool()
        time.sleep(0.2)  # Allow processes to stabilize
    
    gc.collect()  # Force garbage collection
```

### 4. MakerNotes Corruption Handling
**Always use error-tolerant flags for metadata updates:**
```python
cmd = [
    exiftool_path,
    '-overwrite_original',
    '-ignoreMinorErrors',  # CRITICAL for MakerNotes issues
    '-m',                   # Ignore minor warnings
    '-charset', 'filename=utf8',
    f'-{field}={value}',
    '-@', arg_file_path
]
```

### 5. Backup Creation Pattern
**Create backups with proper extensions (not .jpg_backup):**
```python
# ✅ CORRECT
filename = "photo.jpg"
name, ext = os.path.splitext(filename)
backup_filename = f"{name}_backup{ext}"  # "photo_backup.jpg"

# ❌ WRONG
backup_filename = f"{filename}_backup"  # "photo.jpg_backup" - can't open!
```

### 6. Single File Mode Resource Management
**Switch between single process and pool based on mode:**
```python
if self.single_file_mode:
    # Use single process for investigation
    self.exif_handler.exiftool_pool.shutdown()
    self.exif_handler._single_process = ExifToolProcess()
    self.exif_handler._single_process.start()
else:
    # Use pool for batch processing
    if hasattr(self.exif_handler, '_single_process'):
        self.exif_handler._single_process.stop()
    self.exif_handler.exiftool_pool = ExifToolProcessPool(pool_size=4)
```

## Key Configuration Values
```python
# Process pool settings
EXIFTOOL_POOL_SIZE = 4          # Concurrent ExifTool processes
GROUP_SIZE = 60                  # Files per group before pool restart
METADATA_BATCH_SIZE = 80         # Files per metadata batch read

# Timeouts
COMMAND_TIMEOUT = 30.0           # ExifTool command timeout (seconds)
REPAIR_TIMEOUT = 60              # Repair operation timeout

# Repair strategies (in order of preference)
STRATEGIES = [SAFEST, THOROUGH, AGGRESSIVE, FILESYSTEM_ONLY]
```

## Resource Cleanup Strategy

### Process Lifecycle
1. **Startup**: ExifHandler creates ExifToolProcessPool (4 processes) with atexit handler registered
2. **Operation**: Processes reused via context manager from pool
3. **Shutdown**: Explicit cleanup OR atexit fallback

### Cleanup Paths (in order of preference)
1. **Primary** (Normal app): `app.aboutToQuit` signal → `cleanup()` → `pool.shutdown()`
2. **Secondary** (Threads): `ExifHandler.closeEvent()` handles scanner threads
3. **Fallback** (Crash/Force-kill): Python atexit handler → `pool._atexit_cleanup()` → `process._atexit_cleanup()`

### atexit Safety Net
- Registered in `ExifToolProcessPool.__init__()` and `ExifToolProcess.__init__()`
- Triggers automatically if normal shutdown path fails (crash, force-close, etc.)
- Prevents zombie processes that would otherwise consume resources
- **Idempotent**: Safe to call multiple times via `_shutdown` flag check

**When to see atexit warnings:**
- ✅ User force-closes app: `⚠️ atexit cleanup triggered` warning is EXPECTED
- ✅ Normal exit: NO warning (means normal cleanup worked)
- ✅ Uncaught crash: `⚠️ atexit cleanup triggered` warning is EXPECTED

**Benefits:**
- Eliminates zombie ExifTool processes after crashes/force-kills
- Works in non-PyQt5 contexts (CLI, tests, other frameworks)
- Catches edge cases where pool shutdown is interrupted
- Zero performance impact (only runs during exit)

## Supported Formats (54 total)
**Photos**: JPG, JPEG, PNG, BMP, TIFF, TIF, GIF, CR2, NEF, ARW, DNG, ORF, RW2, RAF, RAW, RWL, DCR, SRW, X3F, HEIC, HEIF, WebP, AVIF, JXL, PSD, EXR, HDR, TGA, SVG, PBM, PGM, PPM

**Videos**: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, MPG, MPEG, MXF, R3D, BRAW, ARI, ProRes, 3GP, 3G2, MTS, M2TS, TS, VOB, OGV, RM, RMVB, ASF, M2V, F4V, MOD, TOD

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "0 image files updated" | MakerNotes corruption | Add `-ignoreMinorErrors -m` flags |
| App freezes at 400+ files | Zombie ExifTool processes | Implement group-based processing with pool restart |
| Unicode path errors | Norwegian characters (Ø, Æ, Å) | Use argument files with `-charset filename=utf8` |
| Backup files won't open | Wrong extension placement | Use `name_backup.ext` not `name.ext_backup` |
| Memory issues | No cleanup between groups | Add `gc.collect()` after each group |

## Testing Checklist
- [ ] Test with Norwegian characters in path (Ø, Æ, Å)
- [ ] Test with 500+ files (group processing)
- [ ] Test with corrupted EXIF files
- [ ] Test Single File Mode toggle
- [ ] Test corruption detection toggle
- [ ] Verify no zombie ExifTool processes after processing

## ADR Reference
Key architecture decisions are documented in `docs/adr/`:
- ADR-001: ExifTool Integration Architecture
- ADR-002: Time Synchronization Strategy  
- ADR-004: Single File Mode Implementation
- ADR-007: Group-Based Processing
- ADR-014: Multiple Repair Strategy Approach

## Dependencies
```
PyQt5==5.15.9
python-dateutil==2.8.2
ijson==2.3.2
ExifTool (external, must be in PATH or standard location)
```
