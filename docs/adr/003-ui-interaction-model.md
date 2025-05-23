# ADR-003: UI Interaction Model

## Status
Accepted

## Context
Need to decide how users select and process photos from different cameras, considering Windows Explorer limitations and user workflow preferences.

## Decision
Implement a persistent drag-and-drop window that:
1. Accepts photos from different Explorer windows
2. Remains open for continuous operation
3. Automatically calculates offsets when fields are selected
4. Provides immediate visual feedback

## Consequences
### Positive
- Intuitive interaction model
- Supports rapid batch processing
- Clear visual representation of the alignment process
- No complex multi-window selection mechanisms

### Negative
- Requires window to remain open
- Cannot select multiple files from Explorer at once

## Alternatives Considered
1. **Context menu integration**: Too complex for cross-window selection
2. **System tray monitoring**: Not intuitive for users
3. **Clipboard-based selection**: Conflicts with normal clipboard use