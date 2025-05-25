# ADR-004: Single File Mode Implementation

## Status
Accepted

## Context
Users frequently need to investigate individual file metadata without the overhead and complexity of full batch processing. The existing interface, while powerful for batch operations, creates unnecessary cognitive load and resource usage when users simply want to examine a single file's time fields, camera settings, or metadata structure.

### Problems Identified
1. **Resource Inefficiency**: 4 ExifTool processes running when only examining one file
2. **UI Complexity**: Processing controls create distraction during investigation
3. **Workflow Mismatch**: Users often investigate before processing, requiring two separate tools or complex setup
4. **Learning Curve**: New users get overwhelmed by batch processing features when they just want to examine files

## Decision
Implement a "Single File Mode" toggle that transforms the application into a focused investigation tool while maintaining the option to switch to full processing mode.

### Implementation Approach
- **Toggle Control**: Prominent checkbox at top of interface
- **Adaptive UI**: Selectively disable processing controls rather than hiding them
- **Resource Optimization**: Use 1 ExifTool process instead of 4 in investigation mode
- **Seamless Switching**: Allow users to toggle between modes without losing loaded files
- **Preference Persistence**: Remember user's preferred mode between sessions

## Consequences

### Positive
- **Resource Efficiency**: 75% reduction in ExifTool processes during investigation
- **Simplified Workflow**: Users can focus on investigation without processing distractions
- **Better User Experience**: Clear mode indication and appropriate feature availability
- **Educational Value**: Users can learn about metadata before attempting processing
- **Flexible Usage**: Same interface serves both investigation and processing needs

### Negative
- **Code Complexity**: Additional state management and UI control logic
- **Testing Overhead**: Need to test both modes and transitions between them
- **Documentation Burden**: More features to document and explain
- **Support Complexity**: Users may be confused about mode-specific capabilities

## Alternatives Considered

### Alternative 1: Separate Investigation Application
- **Description**: Create a standalone metadata investigation tool
- **Rejected Because**: Context switching between applications is inefficient, and maintaining two codebases is costly

### Alternative 2: Tab-Based Interface
- **Description**: Implement tabs for "Processing" and "Investigation" modes
- **Rejected Because**: Takes valuable UI space and creates artificial separation between related workflows

### Alternative 3: Wizard-Style Interface
- **Description**: Step-by-step guided interface for different workflows
- **Rejected Because**: Less flexible and doesn't support quick switching between investigation and processing

### Alternative 4: Always-On Process Pool
- **Description**: Keep 4 ExifTool processes running regardless of mode
- **Rejected Because**: Wasteful of system resources when only investigating files

## Implementation Details

### UI Changes
```python
# Toggle control
self.single_file_mode_check = QCheckBox("Single File Mode (Investigation Only)")

# Adaptive UI control
def update_ui_for_single_file_mode(self):
    normal_mode = not self.single_file_mode
    # Selectively enable/disable controls based on mode
    self.target_drop.setEnabled(normal_mode)
    self.apply_button.setEnabled(normal_mode and self.can_apply_alignment())
    # ... other controls
```

### Resource Management
```python
# Mode switching with resource optimization
if self.single_file_mode:
    # Shutdown process pool, create single process
    self.exif_handler.exiftool_pool.shutdown()
    self.exif_handler._single_process = ExifToolProcess()
    self.exif_handler._single_process.start()
else:
    # Stop single process, restart pool
    self.exif_handler._single_process.stop()
    self.exif_handler.exiftool_pool = ExifToolProcessPool(pool_size=4)
```

### Adaptive Operation Selection
```python
# ExifHandler adapts to available resources
def read_metadata(self, file_path: str):
    if hasattr(self, '_single_process') and self._single_process:
        return self._single_process.read_metadata(file_path)
    else:
        with self.exiftool_pool.get_process() as process:
            return process.read_metadata(file_path)
```

## Success Metrics
- **Resource Usage**: Measure memory and CPU reduction in Single File Mode
- **User Adoption**: Track usage patterns and mode preferences
- **Error Reduction**: Monitor if investigation-first workflow reduces processing errors
- **Performance**: Ensure mode switching is fast and seamless

## Risks and Mitigations

### Risk: Mode Confusion
- **Mitigation**: Clear visual indicators, status bar messages, and tooltips
- **Status**: Addressed through UI design

### Risk: Resource Management Bugs
- **Mitigation**: Comprehensive testing of mode transitions and process lifecycle
- **Status**: Requires ongoing attention

### Risk: Feature Fragmentation
- **Mitigation**: Maintain feature parity where appropriate, clear documentation of mode-specific features
- **Status**: Addressed through documentation

## Future Considerations
- **Hybrid Mode**: Could implement a mode that allows light processing during investigation
- **Batch Investigation**: Extend Single File Mode to examine multiple files without processing
- **Performance Analytics**: Track and optimize resource usage patterns
- **Auto-Mode Selection**: Intelligently suggest optimal mode based on user behavior

## Related Decisions
- [ADR-001: ExifTool Integration Architecture](001-exiftool-integration-architecture.md)
- [ADR-002: Time Synchronization Strategy](002-time-synchronization-strategy.md)
- [ADR-003: UI Interaction Model](003-ui-interaction-model.md)

## References
- User feedback requesting investigation-only mode
- Performance analysis showing resource waste during investigation
- UI/UX best practices for mode-based interfaces