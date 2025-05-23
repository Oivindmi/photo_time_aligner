# ExifTool Implementation Guide

## Overview
This document details the ExifTool integration in Photo Time Aligner, explaining the architecture, implementation details, and best practices developed through iterative refinement.

## Architecture Overview

### Core Components

#### ExifToolProcess Class
**Location**: `src/core/exiftool_process.py`  
**Purpose**: Individual ExifTool process management

**Key Features**:
- Persistent process with -stay_open flag
- Argument file communication for Windows compatibility
- Automatic restart on failure
- Thread-safe command execution

#### ExifToolProcessPool Class
**Location**: `src/core/exiftool_pool.py`  
**Purpose**: Manages pool of ExifTool processes for concurrent operations

**Key Features**:
- Configurable pool size (default: 3 processes)
- Thread-safe process allocation using queue
- Context manager for automatic process return
- Parallel batch metadata reading
- Graceful shutdown handling

#### ExifHandler Class
**Location**: `src/core/exif_handler.py`  
**Purpose**: High-level interface for EXIF operations using process pool

**Key Features**:
- Automatic process pool initialization
- Simplified API for metadata operations
- Batch processing support
- Direct pool access (no caching layer)

#### ConcurrentFileProcessor Class
**Location**: `src/core/concurrent_file_processor.py`  
**Purpose**: Async file operations for performance

**Key Features**:
- Asynchronous directory scanning
- Concurrent file filtering
- Progress callback support
- Configurable batch sizes

## Performance Architecture

### Process Pool Benefits
- Eliminates process startup overhead
- Enables true parallel processing
- Scales with CPU cores
- Maintains compatibility with existing code

### Async Operations
- Non-blocking directory traversal
- Concurrent metadata extraction
- UI remains responsive during long operations
- Efficient resource utilization

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