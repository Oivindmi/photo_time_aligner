# ExifTool Implementation Guide

## Core Components

### ExifToolProcess Class
**Location**: `src/core/exiftool_process.py`
**Purpose**: Manages persistent ExifTool process with argument file communication

#### Key Methods:
- `read_metadata_batch()`: Process multiple files using argument files
- `execute_command()`: Send commands to persistent process
- `update_datetime_fields()`: Update file metadata using argument files

### Critical Implementation Details

#### Thread Safety
```python
self._lock = threading.Lock()  # Protects process communication