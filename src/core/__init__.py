# src/core/__init__.py - Updated with repair functionality

from .exif_handler import ExifHandler
from .config_manager import ConfigManager
from .file_processor import FileProcessor
from .time_calculator import TimeCalculator
from .filename_pattern import FilenamePatternMatcher
from .alignment_processor import AlignmentProcessor, ProcessingStatus
from .alignment_report import AlignmentReport

# NEW: Repair functionality imports
from .corruption_detector import CorruptionDetector, CorruptionType, CorruptionInfo
from .repair_strategies import FileRepairer, RepairStrategy, RepairResult

__all__ = [
    # Existing exports
    'ExifHandler',
    'ConfigManager',
    'FileProcessor',
    'TimeCalculator',
    'FilenamePatternMatcher',
    'AlignmentProcessor',
    'ProcessingStatus',
    'AlignmentReport',

    # NEW: Repair functionality exports
    'CorruptionDetector',
    'CorruptionType',
    'CorruptionInfo',
    'FileRepairer',
    'RepairStrategy',
    'RepairResult'
]