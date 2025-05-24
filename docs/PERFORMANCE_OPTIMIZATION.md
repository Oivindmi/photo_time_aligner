# Performance Optimization Guide

## Overview
This document details the performance optimizations implemented in Photo Time Aligner to handle large photo collections efficiently.

## Key Optimizations

### 1. ExifTool Process Pool
Instead of using a single ExifTool process, we now maintain a pool of processes:

```python
# Configuration in config.json
"performance": {
    "exiftool_pool_size": 3,
    "batch_size": 20,
    "max_concurrent_operations": 4
}
```
### 2. Asynchronous File Operations
All file scanning operations now use async/await patterns:

Directory scanning with os.scandir
Concurrent file filtering
Batch metadata reading

3. Optimized Batch Processing
Files are processed in configurable batches to balance performance and memory usage.
Performance Tuning
For Small Collections (<1000 files)

Default settings work well
Pool size of 3 processes is optimal

For Large Collections (>10,000 files)

Increase exiftool_pool_size to 5
Increase batch_size to 50
Ensure adequate system memory

For Network Drives

Reduce batch_size to 10
Reduce exiftool_pool_size to 2
Network latency is the bottleneck

Benchmarks
OperationFilesOld MethodNew MethodImprovementDirectory Scan1,0002.5s0.3s8.3xMetadata Read10010s2s5xTime Update50050s10s5xFull Workflow1,0002min20s6x
Troubleshooting
High Memory Usage

Reduce batch_size in configuration
Reduce exiftool_pool_size

Process Errors

Check ExifTool is properly installed
Verify no antivirus blocking
Check system resources

Slow Performance

Increase exiftool_pool_size (up to CPU cores)
Check disk I/O performance
Verify network connectivity for network drives

# Photo Time Aligner - Performance Optimization Documentation Update

## Recent Performance Improvements (May 2024)

### Problem: Application Freezing with Large File Collections
The application would freeze when processing large collections of files (400+ files), caused by:
- Zombie ExifTool processes accumulating over time
- Memory leaks in process pool management
- Inefficient metadata reading patterns
- Resource exhaustion during batch operations

### Solution: Group-Based Processing with Process Pool Management

#### Implementation: Strategy 6 - File Batching with Process Restart
- **Group Size**: 80 files per group (optimized from initial 50)
- **Process Pool**: 4 ExifTool processes (optimized from initial 3)
- **Restart Strategy**: Full process pool restart after every group
- **Batch Metadata Reading**: Read entire group metadata at once (C2 optimization)

#### Key Architectural Changes

##### 1. Group-Based File Processing
```
Before: Process all files sequentially → freeze at 400+ files
After:  Process in groups of 80 → restart pool → next group → stable at 3000+ files
```

##### 2. Enhanced Process Pool Management
- **Full Pool Restart**: Complete shutdown and restart of all ExifTool processes between groups
- **Zombie Process Prevention**: Eliminates process accumulation that caused freezing
- **Resource Cleanup**: Garbage collection and memory management after each group

##### 3. Batch Metadata Reading Optimization (C2)
```
Before: Read metadata in chunks of 10 files within each group
After:  Read metadata for entire group (80 files) at once
Result: ~20-25% performance improvement
```

##### 4. Enhanced Progress Feedback
- Group-level progress: "Processing group 3 of 30"
- Process restart notifications: "Restarting processes..."
- Real-time file count: "45 / 3000 files processed"
- Cancellation support with proper cleanup

#### Performance Characteristics
- **Small Collections** (<100 files): ~25% faster due to batch metadata reading
- **Large Collections** (400-3000+ files): Reliable processing (previously would freeze)
- **Memory Usage**: Stable across all collection sizes due to group-based cleanup
- **Process Management**: No zombie process accumulation
- **User Experience**: Non-blocking UI with real-time progress and cancellation

#### Testing Results
- ✅ **53 files**: Works perfectly
- ✅ **412 files**: Stable processing in 5 groups  
- ✅ **3000 files**: Successfully completed 
- ✅ **Process cleanup**: No zombie ExifTool processes remaining
- ✅ **Memory stability**: Consistent memory usage across all file counts

#### Configuration Parameters
```python
# Core settings (optimized through testing)
GROUP_SIZE = 80                    # Files per group before restart
EXIFTOOL_POOL_SIZE = 4             # Number of concurrent ExifTool processes  
METADATA_BATCH_SIZE = 80          # Files processed per metadata batch (matches group size)
RESTART_FREQUENCY = "every_group"  # Process pool restart after each group
```

### Architecture Decision Records

#### ADR-007: Group-Based Processing Implementation
**Status**: Accepted  
**Decision**: Implement file processing in groups with full process pool restart between groups  
**Rationale**: Prevents resource accumulation and zombie processes while maintaining performance  
**Alternatives Considered**: 
- Single process approach (too slow)
- Reduced restart frequency (caused freezing)
- Background threading (too complex for initial implementation)

#### ADR-008: Batch Metadata Reading Optimization  
**Status**: Accepted  
**Decision**: Read metadata for entire group at once instead of small chunks  
**Rationale**: 20-25% performance improvement with no stability issues  
**Testing**: Validated with 3000+ file collections  

#### ADR-009: Process Pool Size Optimization
**Status**: Accepted  
**Decision**: Use 4 ExifTool processes instead of 3  
**Rationale**: Better resource utilization without overwhelming system  
**Testing**: 2 processes caused instability, 4 processes optimal balance  

### Implementation Files Modified
- `src/core/file_processor.py`: Group-based processing logic
- `src/core/exiftool_pool.py`: Enhanced pool restart capability
- `src/ui/progress_dialog.py`: Group progress display
- `src/ui/main_window.py`: Progress callback integration
- `src/core/alignment_processor.py`: Integration with new processing flow

### Backward Compatibility
- **Breaking Change**: All file processing now uses group-based approach
- **Rationale**: Clean code architecture, single processing path
- **Migration**: No user action required, transparent improvement

### Future Optimization Opportunities
1. **Background Threading**: Move entire processing to background thread
2. **Selective Field Updates**: Only update essential datetime fields (C1 strategy)
3. **ExifTool Batch Updates**: Use ExifTool's native batch update capabilities
4. **Adaptive Group Sizing**: Dynamic group size based on file types and system resources

### Performance Metrics Summary
- **Scalability**: Improved from 400 files (freeze) to 3000+ files (stable)
- **Speed**: 20-25% faster due to batch metadata reading
- **Reliability**: 100% elimination of freeze issues
- **Memory**: Stable usage regardless of collection size
- **User Experience**: Real-time progress with cancellation support

This optimization represents a significant improvement in application stability and performance, enabling reliable processing of large photo collections that were previously impossible to handle.