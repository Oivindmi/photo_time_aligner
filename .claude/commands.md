# Custom Slash Commands for Photo Time Aligner

## Available Commands

### /bug - Report and investigate a bug
**Usage**: `/bug [description]`

Initiates bug investigation workflow:
1. Gather reproduction steps
2. Check logs and relevant code
3. Identify root cause
4. Propose fix

**Example**: `/bug App freezes when processing 500+ files`

---

### /feature - Design a new feature
**Usage**: `/feature [description]`

Initiates feature design workflow:
1. Understand requirements
2. Identify affected modules
3. Design approach following existing patterns
4. Create implementation plan
5. Identify testing needs

**Example**: `/feature Add support for HEIF format metadata editing`

---

### /refactor - Plan and execute refactoring
**Usage**: `/refactor [target] [goal]`

Initiates refactoring workflow:
1. Understand current code
2. Identify all usages/dependencies
3. Plan changes with minimal risk
4. Execute with testing at each step

**Example**: `/refactor file_processor.py Simplify group processing logic`

---

### /test - Create or run tests
**Usage**: `/test [target]`

Initiates testing workflow:
1. Identify what needs testing
2. Create appropriate test type (unit/integration/manual)
3. Run tests and report results

**Example**: `/test time_calculator.py`

---

### /review - Review code changes
**Usage**: `/review [file or description]`

Initiates code review:
1. Check against project patterns
2. Look for critical issues
3. Verify error handling
4. Check Unicode/path handling
5. Provide structured feedback

**Example**: `/review repair_strategies.py`

---

### /doc - Update documentation
**Usage**: `/doc [target]`

Initiates documentation update:
1. Identify what needs documenting
2. Update appropriate files (docstrings, README, CLAUDE.md, ADRs)
3. Ensure consistency

**Example**: `/doc Add docstrings to corruption_detector.py`

---

### /check - Run project health checks
**Usage**: `/check`

Runs comprehensive project checks:
1. Verify all imports work
2. Check for syntax errors
3. Verify ExifTool availability
4. Run basic smoke tests

---

### /patterns - Show critical patterns
**Usage**: `/patterns [topic]`

Shows relevant code patterns:
- `/patterns unicode` - Unicode handling
- `/patterns exiftool` - ExifTool integration
- `/patterns process` - Process management
- `/patterns backup` - Backup creation
- `/patterns threading` - Thread safety

---

### /troubleshoot - Diagnose a file issue
**Usage**: `/troubleshoot [file_path]`

Runs diagnostic on a problematic file:
```bash
python troubleshoot_files.py <file_path>
```

---

### /adr - Create an Architecture Decision Record
**Usage**: `/adr [title]`

Creates new ADR in `docs/adr/` with proper template.

**Example**: `/adr Implement cloud backup integration`

---

## Command Implementation

When Claude Code supports custom commands, implement these as:

```json
{
  "commands": {
    "bug": {
      "description": "Investigate a bug",
      "handler": "Load @debugger agent, investigate issue"
    },
    "feature": {
      "description": "Design a new feature", 
      "handler": "Load @architect agent, design feature"
    },
    "refactor": {
      "description": "Plan refactoring",
      "handler": "Load @architect agent, plan refactoring"
    },
    "test": {
      "description": "Create or run tests",
      "handler": "Load @tester agent, handle testing"
    },
    "review": {
      "description": "Review code changes",
      "handler": "Load @reviewer agent, review code"
    },
    "doc": {
      "description": "Update documentation",
      "handler": "Load @documenter agent, update docs"
    }
  }
}
```

## Quick Reference Shortcuts

| Task | Command |
|------|---------|
| Fix a bug | `/bug [issue]` |
| Add feature | `/feature [description]` |
| Clean up code | `/refactor [target]` |
| Add tests | `/test [module]` |
| Review before commit | `/review [changes]` |
| Update docs | `/doc [target]` |
| Check project health | `/check` |
| Show patterns | `/patterns [topic]` |
| Debug specific file | `/troubleshoot [path]` |
| Document decision | `/adr [title]` |
