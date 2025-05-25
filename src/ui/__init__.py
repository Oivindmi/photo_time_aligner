# src/ui/__init__.py - Updated with repair dialog

from .main_window import MainWindow
from .file_scanner_thread import FileScannerThread
from .progress_dialog import ProgressDialog
from .metadata_dialog import MetadataInvestigationDialog

# NEW: Repair dialog imports
from .repair_dialog import RepairDecisionDialog, RepairProgressDialog

__all__ = [
    # Existing exports
    'MainWindow',
    'FileScannerThread',
    'ProgressDialog',
    'MetadataInvestigationDialog',

    # NEW: Repair dialog exports
    'RepairDecisionDialog',
    'RepairProgressDialog'
]