# src/__init__.py - Updated version info and exports

"""Photo Time Aligner - Synchronize timestamps across photos from different cameras with repair functionality"""

__version__ = "2.0.0"  # Updated version to reflect repair functionality
__author__ = "Øivind Hoem"

# Main application exports
from .core import (
    ExifHandler, ConfigManager, FileProcessor, TimeCalculator,
    FilenamePatternMatcher, AlignmentProcessor, ProcessingStatus, AlignmentReport,
    CorruptionDetector, CorruptionType, FileRepairer, RepairStrategy
)

from .ui import (
    MainWindow, FileScannerThread, ProgressDialog, MetadataInvestigationDialog,
    RepairDecisionDialog, RepairProgressDialog
)

__all__ = [
    # Core functionality
    'ExifHandler', 'ConfigManager', 'FileProcessor', 'TimeCalculator',
    'FilenamePatternMatcher', 'AlignmentProcessor', 'ProcessingStatus', 'AlignmentReport',

    # Repair functionality
    'CorruptionDetector', 'CorruptionType', 'FileRepairer', 'RepairStrategy',

    # UI components
    'MainWindow', 'FileScannerThread', 'ProgressDialog', 'MetadataInvestigationDialog',
    'RepairDecisionDialog', 'RepairProgressDialog'
]