import os
import logging
from datetime import datetime
from typing import List, Tuple
from .alignment_processor import ProcessingStatus
from .time_calculator import TimeCalculator

logger = logging.getLogger(__name__)


class AlignmentReport:
    """Generate reports and logs for the alignment operation"""

    def __init__(self, config_manager):
        self.config_manager = config_manager

    def generate_console_report(self, status: ProcessingStatus, time_offset: datetime.timedelta,
                                start_time: datetime, end_time: datetime,
                                master_folder_org: str = "Root folder") -> str:
        """Generate a formatted console report"""
        offset_str, direction = TimeCalculator.format_offset(time_offset)

        report = []
        report.append("=== Photo Time Alignment Report ===")
        report.append(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append(f"Time Offset Applied: {offset_str}")
        report.append("")

        # Metadata updates section
        report.append("Metadata Updates:")
        report.append(f"✓ Successfully updated: {status.metadata_updated} files")
        if status.metadata_errors:
            report.append(f"✗ Errors: {len(status.metadata_errors)} files")
        if status.metadata_skipped:
            report.append(f"⚠ Skipped: {len(status.metadata_skipped)} files")
        report.append("")

        # File moves section
        if status.files_moved > 0 or status.move_skipped or status.move_errors:
            report.append("File Moves:")
            report.append(f"✓ Successfully moved: {status.files_moved} files")
            if status.move_skipped:
                report.append(f"⚠ Skipped: {len(status.move_skipped)} files")
            if status.move_errors:
                report.append(f"✗ Errors: {len(status.move_errors)} files")
            report.append("")

        # Summary
        report.append("Summary:")
        report.append(f"- Total files processed: {status.total_files}")
        report.append(f"- Successfully processed: {status.metadata_updated}/{status.total_files} files")
        if status.metadata_errors:
            report.append(f"- Metadata update errors: {len(status.metadata_errors)} files")
        if status.metadata_skipped:
            report.append(f"- Metadata update skipped: {len(status.metadata_skipped)} files")
        if status.move_skipped:
            report.append(f"- File move skipped: {len(status.move_skipped)} files")
        if status.files_moved > 0:
            report.append(f"- Files moved to master folder: {status.files_moved} files")
        report.append("")

        # Master folder organization
        if status.camera_folders:
            report.append(f"Master Folder Organization: {master_folder_org}")
            for camera_id, folder_path in sorted(status.camera_folders.items()):
                file_count = self._count_files_in_folder(folder_path)
                report.append(f"- {folder_path}: {file_count} files")
            report.append("")

        # Error details
        if status.metadata_errors:
            report.append("Metadata Update Errors:")
            for file_path, error_msg in status.metadata_errors:
                report.append(f"- {os.path.basename(file_path)}: {error_msg}")
            report.append("")

        if status.metadata_skipped:
            report.append("Metadata Update Skipped (missing selected field):")
            for file_path, reason in status.metadata_skipped:
                report.append(f"- {os.path.basename(file_path)}: {reason}")
            report.append("")

        if status.move_skipped:
            report.append("File Move Skipped (already exists):")
            for file_path, reason in status.move_skipped:
                report.append(f"- {os.path.basename(file_path)}: {reason}")
            report.append("")

        if status.move_errors:
            report.append("File Move Errors:")
            for file_path, error_msg in status.move_errors:
                report.append(f"- {os.path.basename(file_path)}: {error_msg}")
            report.append("")

        return "\n".join(report)

    def save_log_file(self, report: str, status: ProcessingStatus) -> str:
        """Save the report to a log file"""
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"photo_time_aligner_{timestamp}.log"

        # Get log directory (config directory)
        log_dir = self.config_manager.config_dir
        log_path = os.path.join(log_dir, log_filename)

        # Write log file
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(report)
                f.write("\n\n")
                f.write("=== Detailed Processing Log ===\n")
                f.write(self._generate_detailed_log(status))

            logger.info(f"Log file saved to: {log_path}")
            return log_path
        except Exception as e:
            logger.error(f"Error saving log file: {str(e)}")
            return ""

    def _count_files_in_folder(self, folder_path: str) -> int:
        """Count the number of files in a folder"""
        try:
            return len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        except:
            return 0

    def _generate_detailed_log(self, status: ProcessingStatus) -> str:
        """Generate detailed processing log for the file"""
        log = []

        # Add detailed information about each processed file
        log.append("File Processing Details:")
        log.append("-" * 50)

        # You can add more detailed logging here if needed

        return "\n".join(log)