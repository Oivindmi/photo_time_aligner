## New: docs/adr/002-time-synchronization-strategy.md

```markdown
# ADR-002: Time Synchronization Strategy

## Status
Accepted

## Context
When aligning photos from different cameras, we need a clear strategy for how time fields are synchronized within files and across groups.

## Decision
Implement per-file field synchronization where:
1. Each file's time fields are synchronized to a single reference time
2. Reference group files: all fields match the selected field
3. Target group files: all fields match the selected field plus offset
4. Empty fields are never populated

## Consequences
### Positive
- Maintains internal consistency within each file
- Preserves relative timing between files
- Non-destructive (doesn't add data that wasn't there)
- Simple mental model for users

### Negative
- Cannot selectively update only some fields
- May overwrite fields that had different times for valid reasons

## Alternatives Considered
1. **Update only selected field**: Would leave files internally inconsistent
2. **Global time sync**: Would lose relative timing between photos
3. **Smart field detection**: Too complex and unpredictable