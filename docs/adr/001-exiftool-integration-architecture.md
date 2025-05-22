# ADR-001: ExifTool Integration Architecture

## Status
Accepted

## Context
The application needs to process metadata from large numbers of photo and video files efficiently and reliably. Initial implementation caused stack overflow errors with 50+ files.

## Decision
Implement a hybrid approach using:
1. Persistent ExifTool process for performance
2. Argument file communication for reliability
3. Incremental UI updates for scalability

## Consequences
### Positive
- 5-10x performance improvement
- Handles hundreds of files without crashes
- Maintains reliability of original approach
- Better user experience with progress indication

### Negative
- More complex process management
- Additional error handling requirements
- Threading considerations for process safety

## Alternatives Considered
1. **Pure persistent process**: Too complex, Windows compatibility issues
2. **Original single-process approach**: Performance limitations, stack overflow
3. **Non-persistent with batching**: Better performance but still process overhead

## Implementation Notes
- Thread safety critical for process communication
- Argument files handle Windows path issues reliably
- Automatic process restart for error recovery