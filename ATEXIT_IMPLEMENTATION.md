# Implementation Guide: atexit Safety Net

## File 1: main.py (Fix Critical Bug)

### Current (Broken)
```python
def cleanup(exif_handler):
    """Clean up resources before application exit"""
    logger.info("Performing application cleanup")
    try:
        # Stop the ExifTool process
        if hasattr(exif_handler, 'exiftool_process'):  # ❌ WRONG
            exif_handler.exiftool_process.stop()
            logger.info("ExifTool process stopped")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
```

### Fixed
```python
def cleanup(exif_handler):
    """Clean up resources before application exit"""
    logger.info("Performing application cleanup")
    try:
        # Stop the ExifTool process pool
        if hasattr(exif_handler, 'exiftool_pool'):  # ✅ CORRECT
            exif_handler.exiftool_pool.shutdown()
            logger.info("ExifTool process pool shut down")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
```

**Why:** Current code checks for wrong attribute name. ExifHandler has `exiftool_pool`, not `exiftool_process`.

---

## File 2: exiftool_pool.py (Add atexit Registration)

### Add Import at Top
```python
import atexit  # Add this import
import queue
import threading
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import time
```

### Modify __init__ Method
```python
def __init__(self, pool_size: int = 4, max_retries: int = 3):
    self.pool_size = pool_size
    self.max_retries = max_retries
    self.processes = []
    self.available = queue.Queue()
    self._lock = threading.Lock()
    self._shutdown = False

    # Register atexit handler as fallback safety net
    atexit.register(self._atexit_cleanup)

    # Initialize the pool
    self._initialize_pool()
```

### Add New Method (before `restart_pool`)
```python
def _atexit_cleanup(self):
    """
    Last-resort cleanup handler if normal shutdown fails.
    This is called automatically by Python during exit.
    """
    if self._shutdown:
        # Already cleaned up normally - nothing to do
        return

    logger.warning(
        "⚠️ atexit cleanup triggered - normal shutdown may have failed! "
        "This indicates the application may have been force-terminated or crashed."
    )

    try:
        self.shutdown()
    except Exception as e:
        logger.error(f"Error during atexit cleanup: {e}")

        # Last resort: force kill all processes
        logger.warning("Attempting force termination of all ExifTool processes...")
        for i, proc in enumerate(self.processes):
            try:
                if proc.process:
                    proc.process.kill()
                    logger.debug(f"Force killed ExifTool process {i + 1}")
            except Exception as kill_error:
                logger.debug(f"Could not force kill process {i + 1}: {kill_error}")
```

**Why:** This catches processes that were missed by normal cleanup path (crashes, force kills, etc.)

---

## File 3: exiftool_process.py (Add Secondary Safety Net)

### Add Import at Top
```python
import atexit  # Add this import
import subprocess
import logging
import os
import json
import time
import shutil
import threading
import tempfile
from typing import List, Dict, Any, Optional
```

### Modify __init__ Method
```python
def __init__(self, executable_path=None):
    self.executable_path = executable_path or self._find_exiftool()
    self.process = None
    self.running = False
    self.command_counter = 0
    self._lock = threading.Lock()

    # Register atexit handler as secondary safety net
    # (primary is ExifToolProcessPool._atexit_cleanup)
    atexit.register(self._atexit_cleanup)
```

### Add New Method (after `stop` method)
```python
def _atexit_cleanup(self):
    """
    Secondary fallback cleanup for individual process.
    Primary cleanup is handled by ExifToolProcessPool.
    This is a safety net in case pool cleanup fails or process is orphaned.
    """
    if not self.running:
        # Already stopped or never started
        return

    logger.warning(
        "⚠️ atexit cleanup triggered on ExifToolProcess - "
        "normal shutdown may have failed"
    )

    try:
        # Attempt graceful stop
        self.stop()
    except Exception as e:
        logger.debug(f"Graceful stop failed during atexit: {e}")

        # Force kill as fallback
        try:
            if self.process and self.process.poll() is None:
                self.process.kill()
                logger.debug("Force killed ExifTool process")
        except Exception as kill_error:
            logger.debug(f"Could not force kill: {kill_error}")
    finally:
        self.running = False
        self.process = None
```

**Why:** Catches individual processes that might be orphaned if pool cleanup fails.

---

## File 4: Update CLAUDE.md (Documentation)

### Add to "Key Configuration Values" Section
```markdown
## Resource Cleanup Strategy

### Process Lifecycle
1. **Startup**: ExifHandler creates ExifToolProcessPool (4 processes)
2. **Operation**: Processes reused via context manager from pool
3. **Shutdown**: Explicit cleanup OR atexit fallback

### Cleanup Paths (in order of preference)
1. **Primary** (Normal app): `app.aboutToQuit` signal → `cleanup()` → pool.shutdown()
2. **Secondary** (Threads): ExifHandler.closeEvent() handles scanner threads
3. **Fallback** (Crash/Force-kill): Python atexit handler → pool._atexit_cleanup()

### atexit Safety Net
Registered in ExifToolProcessPool and ExifToolProcess __init__ methods.
Triggers automatically if normal shutdown path fails (crash, force-close, etc.)
Prevents zombie processes that would otherwise consume resources.

**When to see atexit warnings:**
- User force-closes app: ⚠️ Warning is EXPECTED
- Normal exit: ✅ No warning (means cleanup worked)
- Crash: ⚠️ Warning is EXPECTED
```

---

## Testing Code

### Test 1: Verify Normal Shutdown (No Warnings)
```python
import logging
logging.basicConfig(level=logging.WARNING)

from src.core import ExifHandler

handler = ExifHandler()
# Do some operations
handler.read_metadata("test.jpg")

# Normal shutdown
handler.exiftool_pool.shutdown()
print("✅ Normal shutdown completed - no atexit warning should appear")
```

### Test 2: Simulate Force Kill
```python
import logging
import sys
logging.basicConfig(level=logging.WARNING)

from src.core import ExifHandler

handler = ExifHandler()
# Do some operations
handler.read_metadata("test.jpg")

print("⚠️ Exiting without calling shutdown()...")
# Don't call shutdown - simulate crash
sys.exit(0)  # Exit directly

# ✅ Should see atexit warning in logs
```

### Test 3: Pool Restart with atexit
```python
from src.core import ExifHandler
import time

handler = ExifHandler()

# Test restart with active processes
for i in range(100):
    try:
        handler.exiftool_pool.restart_pool()
        print(f"Restart {i + 1} successful")
    except Exception as e:
        print(f"❌ Restart {i + 1} failed: {e}")
    time.sleep(0.1)

print("✅ All restarts completed")
```

---

## Implementation Checklist

- [ ] Apply changes to `main.py` (fix cleanup bug)
- [ ] Apply changes to `exiftool_pool.py` (add atexit)
- [ ] Apply changes to `exiftool_process.py` (add atexit)
- [ ] Update `CLAUDE.md` with cleanup documentation
- [ ] Run Test 1 (verify normal shutdown is clean)
- [ ] Run Test 2 (verify atexit catches crash)
- [ ] Run Test 3 (verify restart robustness)
- [ ] Run existing unit tests (ensure no regression)
- [ ] Manual test: Force-close app, check Task Manager (Windows) or ps (Linux) for zombie processes
- [ ] Code review: Verify idempotent cleanup (safe to call multiple times)
- [ ] Documentation: Update README if cleanup strategy needs explanation

---

## Validation Checklist

✅ Does cleanup happen in all three scenarios?
- [ ] Normal exit (PyQt5 signal)
- [ ] Force kill (atexit)
- [ ] Crash (atexit)

✅ No regressions?
- [ ] Existing tests pass
- [ ] Pool still works normally
- [ ] No performance degradation

✅ Edge cases handled?
- [ ] Double-cleanup (safe due to _shutdown flag)
- [ ] Already-dead processes (handled in try/except)
- [ ] Multiple threads (protected by _lock)

✅ Logging clear?
- [ ] atexit warnings are clear and actionable
- [ ] No spurious warnings during normal operation
- [ ] Error messages help debug issues

---

## Rollback Plan

If atexit implementation causes issues:

1. Remove `atexit.register()` calls (2 lines each)
2. Remove `_atexit_cleanup()` methods (entire methods)
3. Keep the `main.py` fix (this is a bug fix, not atexit)

Rollback is very low-risk since atexit is purely additive.
