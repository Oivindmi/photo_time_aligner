# Photo Time Aligner - Design Decisions and Architecture

## Overview
This document captures the key design decisions made during the development of Photo Time Aligner, explaining the rationale behind architectural choices and their impact on the final implementation.

## Core Design Philosophy

### Simplicity First
- **Decision**: Keep the codebase minimal and focused
- **Rationale**: Avoid over-engineering for a specialized tool
- **Impact**: No unnecessary caching, database, or complex abstractions

### Dual-Mode Operation (New)
- **Decision**: Implement both investigation-only and full-processing modes
- **Rationale**: Users often need different approaches - sometimes just examining files, sometimes processing them
- **Impact**: Adaptive resource management and simplified workflows for different use cases

### User Experience Priority
- **Decision**: Continuous drag-and-drop operation with flexible workflows
- **Rationale**: Users often need different approaches - sometimes comparing two photos, sometimes adjusting a single photo, sometimes just investigating
- **Impact**: UI adapts to different modes and supports multiple workflows seamlessly

### Comprehensive Metadata Access
- **Decision**: Provide full access to all available metadata
- **Rationale**: Users need to investigate and understand their file metadata for informed decisions
- **Impact**: Added metadata investigation feature with complete ExifTool output

## User Interface Decisions

### Single File Mode Implementation (New)
- **Decision**: Add toggleable "Single File Mode" rather than separate application or window
- **Options Considered**:
  - Separate investigation application
  - Tab-based interface
  - Wizard-style workflow
  - Toggle mode with selective UI disable (chosen)
- **Rationale**: Single interface with adaptive controls reduces complexity while providing focused workflows
- **Impact**: Users can quickly switch between investigation and processing without learning new interfaces

### Adaptive Resource Management (New)
- **Decision**: Use different ExifTool process counts based on mode
- **Implementation**: 1 process for Single File Mode, 4 processes for Full Processing Mode
- **Rationale**: Optimize resources for the task at hand
- **Impact**: Better performance and lower resource usage when appropriate

### Dual Workflow Support
- **Decision**: Support both two-photo alignment and single-photo manual offset
- **Options Considered**:
  - Two-photo workflow only (original)
  - Wizard-style sequential interface
  - Tabbed interface for different modes
  - Single interface with adaptive controls (chosen)
- **Rationale**: Single interface adapts based on loaded photos, reducing complexity
- **Impact**: Manual offset controls appear when target photo is missing

### Manual Time Offset Design
- **Decision**: Comprehensive time input (years, days, hours, minutes, seconds)
- **Rationale**: Users need flexibility for various correction scenarios (timezone, date errors, precision adjustments)
- **Implementation**: Single-line compact layout with validation
- **Impact**: Handles everything from timezone corrections to date restoration

### Metadata Investigation Integration
- **Decision**: Integrated button with file selection rather than separate window
- **Rationale**: Investigation is part of the workflow, not a separate tool
- **Implementation**: Modal dialog with comprehensive search and copy features
- **Impact**: Users can investigate metadata while maintaining main workflow context

### Drag & Drop Interface
- **Decision**: Single window with two drop zones
- **Options Considered**:
  - Sequential file selection via context menu
  - Clipboard-based selection
  - System tray monitoring
  - Drag & drop window (chosen)
- **Rationale**: Most intuitive for comparing two photos side-by-side
- **Impact**: Clear visual metaphor for the alignment process

### Real-time Feedback
- **Decision**: Calculate offset immediately when fields are selected
- **Rationale**: Instant feedback improves user confidence
- **Impact**: No need for separate "Calculate" button

## File Processing Architecture

### Adaptive Process Management (New)
- **Decision**: Different ExifTool configurations based on operation mode
- **Implementation**:
  - Single File Mode: 1 ExifTool process for minimal resource usage
  - Full Processing Mode: 4 ExifTool processes for maximum throughput
  - Automatic switching between configurations
- **Rationale**: Optimize resources for the specific task
- **Impact**: Better performance characteristics and user experience

### Group Identification Strategy
- **Decision**: Three independent, combinable filters
- **Implementation**:
  1. Camera Model (primary)
  2. File Extension (secondary)
  3. Filename Pattern (tertiary)
- **Rationale**: Handles various scenarios (missing EXIF, mixed folders)
- **Impact**: Flexible matching without complex cascading logic

### Filename Pattern Matching
- **Decision**: Smart pattern learning with manual toggle
- **Rationale**: Screenshots and some cameras lack EXIF data
- **Implementation**: Detects patterns like DSC_####, IMG_####, Screenshot_*, VID_####
- **Impact**: Enables processing of files without camera metadata

### Empty Camera Metadata Handling
- **Decision**: Empty metadata matches only other empty metadata
- **Rationale**: Prevents false positives in mixed folders
- **Impact**: Accurate grouping for screenshots and metadata-less files

## Time Synchronization Logic

### Unified Processing Architecture
- **Decision**: Single processing path for both calculated and manual offsets
- **Rationale**: Consistent behavior regardless of offset source
- **Implementation**: AlignmentProcessor accepts any timedelta offset
- **Impact**: Manual and calculated offsets processed identically

### Field Synchronization Approach
- **Decision**: Sync all fields within each file to selected field
- **Rationale**: Maintains consistency within individual files
- **Implementation**:
  - Reference files: All fields → selected field value
  - Target files: All fields → (selected field + offset)
  - Manual mode: All fields → (selected field + manual offset)
- **Impact**: Preserves relative timestamps between files

### Timezone Handling
- **Decision**: Strip all timezone information
- **Rationale**: Avoid offset-naive vs offset-aware datetime errors
- **Impact**: Simplified time calculations, consistent behavior

### Empty Field Policy
- **Decision**: Never populate empty/missing fields
- **Rationale**: Respect original file structure
- **Impact**: Non-destructive updates only

## Metadata Investigation Architecture

### Mode-Aware Operation (New)
- **Decision**: Same investigation dialog works in both Single File Mode and Full Processing Mode
- **Rationale**: Consistent user experience across modes
- **Implementation**: Dialog adapts radio button availability based on current mode
- **Impact**: Seamless investigation regardless of operation mode

### Comprehensive Data Access
- **Decision**: Use ExifTool's most comprehensive flags (-a -u -g1)
- **Rationale**: Users need access to all available metadata, not filtered subsets
- **Implementation**: Separate comprehensive metadata extraction method
- **Impact**: Shows everything ExifTool can extract, letting users filter as needed

### Single-File Processing
- **Decision**: Process only the selected file for investigation
- **Rationale**: Investigation is focused on understanding one file at a time
- **Implementation**: Argument file with single filename to avoid batch processing
- **Impact**: Fast, focused metadata extraction without performance issues

### Structured Presentation
- **Decision**: Flat list with group headers and search functionality
- **Rationale**: Balance between structure and searchability
- **Implementation**: Parse ExifTool grouped output into searchable table
- **Impact**: Easy to find specific fields while maintaining organization

### Time Field Highlighting
- **Decision**: Bold formatting for date/time related fields
- **Rationale**: Time fields are primary user interest without hiding other data
- **Implementation**: Keyword matching against field names
- **Impact**: Quick identification of relevant fields while preserving complete data

## Performance and Scalability

### Adaptive Resource Management (New)
- **Decision**: Different resource allocation based on operation mode
- **Implementation**:
  - Single File Mode: Minimal resources (1 ExifTool process)
  - Full Processing Mode: Maximum resources (4 ExifTool processes)
  - Automatic transition between modes
- **Rationale**: Optimize system resources for the task at hand
- **Impact**: Better user experience and system performance

### Threading Architecture
- **Decision**: QThread for file scanning only
- **Rationale**: Keep UI responsive during long operations
- **Impact**: Smooth user experience with large folders

### ExifTool Integration Evolution

#### Problem: Stack Overflow with Large File Sets
- **Issue**: Application crashed with stack overflow error (0xC0000409) when processing 50+ files
- **Root Cause**: Large JSON responses from ExifTool were causing recursive parsing to exceed stack limits

#### Solution: Hybrid Approach
1. **Persistent Process**: Single ExifTool instance eliminates startup overhead
2. **Argument Files**: Use `-@` flag for reliable Windows path handling
3. **Batch Processing**: Process files in chunks of 50
4. **Incremental Updates**: Emit results progressively

#### Performance Characteristics
- **File Discovery**: ~5-10x faster with persistent process
- **Metadata Updates**: ~3-5x faster than individual calls
- **Memory Usage**: Adaptive based on mode
- **Scalability**: Tested with 500+ files successfully

### Performance Optimization Evolution (May 2024)

#### Problem: Single Process Bottleneck
- **Issue**: Single ExifTool process limited throughput to ~10 files/second
- **Root Cause**: Sequential processing with process startup overhead

#### Solution: Process Pool Architecture
1. **ExifTool Process Pool**: Variable concurrent processes handle operations in parallel
2. **Async Directory Scanning**: Using `os.scandir` and asyncio for I/O operations
3. **Batch Metadata Operations**: Process files in groups of 20
4. **Simplified Architecture**: Removed caching layer that caused recursion issues

#### Performance Improvements
- **Before**: 50 files in ~5 seconds (10 files/second)
- **After**: 50 files in ~1 second (50 files/second)
- **Large Folders**: 1000+ files processed without UI freezing
- **Single File Mode**: Minimal resource usage for investigation tasks

### Metadata Investigation Performance
- **Decision**: Use appropriate process architecture for investigation
- **Implementation**: Single process in Single File Mode, pool process in Full Processing Mode
- **Impact**: Fast metadata extraction without unnecessary resource usage

### Architecture Simplification
- **Decision**: Remove backward compatibility code
- **Rationale**: Cleaner codebase, easier maintenance
- **Impact**: All file scanning now uses async operations exclusively

### Windows-Specific Optimizations
- **Decision**: Handle command line length limits
- **Implementation**: Chunk processing when paths exceed 32KB
- **Impact**: Reliable operation with large folders

## Error Handling and Recovery

### Mode-Aware Error Handling (New)
- **Decision**: Different error handling strategies based on operation mode
- **Implementation**: Single File Mode uses simple error messages, Full Processing Mode uses comprehensive error reporting
- **Rationale**: Match error complexity to user expectations in each mode
- **Impact**: Appropriate error feedback without overwhelming users

### Graceful Degradation
- **Decision**: Fallback from batch to individual processing
- **Rationale**: Better to be slow than to fail
- **Impact**: Reliable operation even with problematic files

### Comprehensive Logging
- **Decision**: Detailed logging with multiple levels
- **Implementation**: Console + file logging with DEBUG option
- **Impact**: Easier troubleshooting and user support

### Process Recovery
- **Decision**: Automatic ExifTool restart on failure
- **Rationale**: Long-running operations shouldn't fail completely
- **Impact**: Robust operation over extended sessions

## Configuration and Persistence

### Mode Preference Persistence (New)
- **Decision**: Save Single File Mode preference between sessions
- **Rationale**: Users often have preferred workflows
- **Implementation**: Boolean flag in JSON configuration
- **Impact**: Application remembers user's preferred mode

### Settings Storage
- **Decision**: JSON file in AppData
- **Rationale**: Simple, human-readable, portable
- **Impact**: Easy backup and troubleshooting

### Manual Offset Persistence
- **Decision**: Don't persist manual offset values between sessions
- **Rationale**: Manual offsets are typically one-time corrections
- **Impact**: Clean slate for each session, preventing accidental reuse

### No Auto-Update
- **Decision**: Manual updates only
- **Rationale**: Simplicity and user control
- **Impact**: Predictable behavior, no surprise changes

## Media Format Support

### Comprehensive Format Coverage
- **Decision**: Support 50+ photo and video formats
- **Rationale**: Users have diverse camera equipment
- **Impact**: Single tool for all media types

### Uniform Processing
- **Decision**: Treat photos and videos identically
- **Implementation**: ExifTool handles both transparently
- **Impact**: No special cases in code

## UI/UX Improvements

### Mode Toggle Design (New)
- **Decision**: Prominent checkbox at top of interface
- **Rationale**: Mode selection should be immediately visible and accessible
- **Implementation**: Checkbox with descriptive tooltip
- **Impact**: Clear mode indication and easy switching

### Adaptive UI Controls (New)
- **Decision**: Selectively enable/disable controls based on mode rather than hiding them
- **Rationale**: Users understand disabled controls better than missing controls
- **Implementation**: Qt's built-in disabled styling
- **Impact**: Intuitive interface state indication

### Apply Button Logic
- **Decision**: Enable apply button when reference photo is loaded (unless in Single File Mode)
- **Rationale**: Both workflows should be equally accessible, but processing should be disabled in investigation mode
- **Impact**: Users can process single photos as easily as photo pairs, but investigation mode prevents accidental processing

### Adaptive Controls
- **Decision**: Manual offset controls automatically enable/disable based on loaded photos and mode
- **Rationale**: Clear visual indication of which workflow is active
- **Impact**: Prevents user confusion about which workflow is active

### Status Bar Communication (New)
- **Decision**: Use status bar to indicate current mode and resource usage
- **Implementation**: Different messages for each mode with resource information
- **Rationale**: Users should understand what resources are being used
- **Impact**: Transparency about application behavior and resource usage

### Comprehensive Help
- **Decision**: Detailed documentation with use cases and examples
- **Rationale**: Complex tool with multiple modes requires thorough explanation
- **Impact**: Users can understand and effectively use all features

## Architecture Decision Records

### ADR-010: Single File Mode Implementation (New)
**Status**: Accepted  
**Decision**: Implement Single File Mode as a toggle within the main interface  
**Rationale**: Users need quick investigation capabilities without the overhead of full processing setup  
**Alternatives Considered**: Separate application, tab interface, wizard workflow  
**Implementation**: Checkbox toggle with selective UI disable and adaptive resource management  

### ADR-011: Adaptive Resource Management (New)
**Status**: Accepted  
**Decision**: Use different ExifTool process counts based on operation mode  
**Rationale**: Optimize resources for the specific task - investigation needs minimal resources, processing needs maximum throughput  
**Implementation**: 1 process for Single File Mode, 4 processes for Full Processing Mode  
**Impact**: Better performance characteristics and resource utilization  

### ADR-012: Mode-Aware UI Design (New)
**Status**: Accepted  
**Decision**: Disable rather than hide UI elements in Single File Mode  
**Rationale**: Users understand disabled controls better than missing ones  
**Implementation**: Selective enable/disable of UI elements based on mode  
**Alternatives Considered**: Hidden elements, separate interfaces, modal dialogs  

## Abandoned Approaches

### Separate Investigation Application
- **Considered**: Standalone metadata investigation tool
- **Rejected**: Context switching between applications is inefficient
- **Chosen Instead**: Integrated Single File Mode

### Tab-Based Mode Selection
- **Considered**: Tabs for "Processing" and "Investigation"
- **Rejected**: Takes up valuable UI space and creates artificial separation
- **Chosen Instead**: Toggle checkbox with adaptive interface

### Always-On Process Pool
- **Considered**: Keep 4 ExifTool processes running regardless of mode
- **Rejected**: Wasteful of resources when only investigating files
- **Chosen Instead**: Adaptive process management

### Database Storage
- **Considered**: SQLite for metadata caching
- **Rejected**: Unnecessary complexity for single-session tool

### Complex Threading
- **Considered**: Worker pools for parallel processing
- **Rejected**: ExifTool batch mode sufficient

### Automatic Backup
- **Considered**: Backup before modification
- **Rejected**: User preference for speed over safety

### Recursive Folder Scanning
- **Considered**: Process subfolders automatically
- **Rejected**: User wants explicit control

### Wizard Interface
- **Considered**: Step-by-step workflow wizard
- **Rejected**: Single adaptive interface more efficient

### Resource-Heavy Investigation
- **Considered**: Use full process pool for metadata investigation
- **Rejected**: Wasteful for single-file operations
- **Chosen Instead**: Single process for investigation, pool for processing

### Hidden UI Elements in Single File Mode
- **Considered**: Hide processing controls completely in Single File Mode
- **Rejected**: Users prefer to see disabled controls rather than missing ones
- **Chosen Instead**: Selective disable with visual feedback

## Future Considerations

### Advanced Investigation Features
- **Enhanced Comparison**: Side-by-side metadata comparison in Single File Mode
- **Batch Investigation**: Investigate multiple files without processing
- **Export Capabilities**: Export metadata investigations to CSV/JSON
- **Visualization**: Graphical representation of time field relationships

### Performance Improvements
- **Dynamic Pool Sizing**: Adjust process count based on system resources and workload
- **Memory Management**: Better resource cleanup and monitoring
- **Caching Strategy**: Intelligent metadata caching for frequently accessed files
- **Background Operations**: Pre-load metadata for better responsiveness

### User Experience Enhancements
- **Workflow Wizards**: Guided setup for complex scenarios
- **Template System**: Save and reuse common processing configurations
- **Drag and Drop Improvements**: Multiple file selection and batch operations
- **Keyboard Shortcuts**: More comprehensive keyboard navigation

### Architecture Evolution
- **Plugin System**: Extensible architecture for custom processing
- **API Layer**: External tool integration capabilities
- **Cloud Integration**: Support for cloud storage metadata operations
- **Cross-Platform**: Linux and macOS support

These design decisions resulted in a flexible, resource-efficient tool that supports both quick investigation and comprehensive processing workflows while maintaining simplicity and performance across different use cases.