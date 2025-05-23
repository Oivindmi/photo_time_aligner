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