# ExifTool Implementation Guide

## Overview
This document details the ExifTool integration in Photo Time Aligner, explaining the architecture, implementation details, and best practices developed through iterative refinement.

## Architecture Overview

### Core Components

#### ExifToolProcess Class
**Location**: `src/core/exiftool_process.py`  
**Purpose**: Manages persistent ExifTool process with optimized communication

**Key Features**:
- Maintains single ExifTool instance throughout application lifetime
- Uses argument files for reliable Windows path handling
- Implements thread-safe command execution
- Automatic process recovery on failures

#### ExifHandler Class
**Location**: `src/core/exif_handler.py`  
**Purpose**: High-level interface for EXIF operations

**Key Features**:
- Abstracts ExifTool complexity from rest of application
- Provides typed interfaces for common operations
- Handles datetime parsing and timezone stripping
- Manages ExifTool path discovery

## Implementation Details

### Process Lifecycle Management

```python
# Startup sequence
1. Find ExifTool executable (PATH, common locations)
2. Start persistent process with -stay_open flag
3. Verify connection with version check
4. Ready for operations

# Shutdown sequence
1. Send -stay_open False command
2. Wait for graceful termination (2s timeout)
3. Force terminate if needed
4. Clean up resources