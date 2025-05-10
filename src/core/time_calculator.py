from datetime import datetime, timedelta
import re
from typing import Optional, Tuple
from dateutil import parser


class TimeCalculator:
    """Handles time offset calculations and datetime parsing"""

    @staticmethod
    def parse_datetime_naive(date_string: str) -> Optional[datetime]:
        """Parse datetime string and return naive datetime (no timezone)"""
        if not date_string:
            return None

        try:
            # Remove timezone information if present
            # This regex removes timezone patterns like +00:00, -05:00, Z, etc.
            date_string = re.sub(r'[+-]\d{2}:?\d{2}$|Z$', '', date_string).strip()

            # Try parsing with dateutil
            dt = parser.parse(date_string)

            # Make sure it's naive (no timezone)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            return dt

        except (ValueError, TypeError):
            # Try manual parsing for common EXIF formats
            formats = [
                '%Y:%m:%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y:%m:%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S.%f',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue

            return None

    @staticmethod
    def calculate_offset(reference_time: datetime, target_time: datetime) -> timedelta:
        """Calculate time offset between two datetime objects"""
        return target_time - reference_time

    @staticmethod
    def format_offset(offset: timedelta) -> Tuple[str, str]:
        """Format timedelta as human-readable string and direction"""
        total_seconds = offset.total_seconds()

        # Determine direction
        direction = "ahead of" if total_seconds > 0 else "behind"

        # Work with absolute values for display
        total_seconds = abs(total_seconds)

        days = int(total_seconds // 86400)
        hours = int((total_seconds % 86400) // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        offset_str = ", ".join(parts)

        return offset_str, direction