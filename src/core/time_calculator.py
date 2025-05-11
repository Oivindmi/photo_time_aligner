from datetime import datetime, timedelta
import re
from typing import Optional, Tuple
from dateutil import parser
import logging

logger = logging.getLogger(__name__)


class TimeCalculator:
    """Handles time offset calculations and datetime parsing"""

    @staticmethod
    def parse_datetime_naive(date_string: str) -> Optional[datetime]:
        """Parse datetime string and return naive datetime (no timezone)"""
        if not date_string:
            return None

        try:
            # Clean the date string first
            original_string = date_string
            date_string = TimeCalculator._clean_date_string(date_string)

            logger.debug(f"Parsing datetime - Original: '{original_string}', Cleaned: '{date_string}'")

            # Skip obviously invalid date strings
            if len(date_string) < 10:  # Minimum valid date is "YYYY-MM-DD"
                logger.warning(f"Date string too short to be valid: '{original_string}'")
                return None

            # First try common EXIF format explicitly
            if ':' in date_string:
                try:
                    # Replace first two ':' with '-' for date part if in EXIF format
                    parts = date_string.split(' ', 1)
                    if len(parts) >= 1:
                        date_part = parts[0]
                        time_part = parts[1] if len(parts) > 1 else ""

                        # Check if date part has colons (EXIF format)
                        if date_part.count(':') >= 2:
                            date_components = date_part.split(':')
                            if len(date_components) >= 3:
                                # Verify year is reasonable (4 digits)
                                if len(date_components[0]) == 4 and date_components[0].isdigit():
                                    date_part = f"{date_components[0]}-{date_components[1]}-{date_components[2]}"
                                else:
                                    logger.warning(f"Invalid year in date: '{original_string}'")
                                    return None

                        date_string = f"{date_part} {time_part}".strip()
                        logger.debug(f"Reformatted date string: '{date_string}'")
                except Exception as e:
                    logger.debug(f"Error reformatting date: {e}")

            # Try parsing with dateutil
            dt = parser.parse(date_string, dayfirst=False)

            # Ensure it's naive (no timezone)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            logger.debug(f"Successfully parsed: {dt}")
            return dt

        except (ValueError, TypeError) as e:
            logger.debug(f"dateutil parsing failed: {e}, trying manual formats...")

            # Try manual parsing for common EXIF formats
            formats = [
                '%Y:%m:%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y:%m:%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S.%f',
            ]

            cleaned_original = TimeCalculator._clean_date_string(original_string)
            for fmt in formats:
                try:
                    dt = datetime.strptime(cleaned_original, fmt)
                    logger.debug(f"Successfully parsed with format {fmt}: {dt}")
                    return dt
                except ValueError:
                    continue

            logger.warning(f"Failed to parse datetime: '{original_string}'")
            return None

    @staticmethod
    def _clean_date_string(date_string: str) -> str:
        """Clean up date string for parsing"""
        if not isinstance(date_string, str):
            return str(date_string)

        # Remove timezone information
        cleaned = re.sub(r'[+-]\d{2}:?\d{2}$|Z$', '', date_string).strip()

        # Don't replace T with space if we might have an EXIF format date
        if 'T' in cleaned and cleaned.count(':') < 3:
            cleaned = cleaned.replace('T', ' ')

        # Remove any milliseconds beyond 6 digits
        cleaned = re.sub(r'\.(\d{6})\d+', r'.\1', cleaned)

        return cleaned

    @staticmethod
    def calculate_offset(reference_time: datetime, target_time: datetime) -> timedelta:
        """
        Calculate time offset between two datetime objects.
        Returns: target_time - reference_time
        If positive: target is ahead of reference
        If negative: target is behind reference
        """
        return target_time - reference_time

    @staticmethod
    def format_offset(offset: timedelta) -> Tuple[str, str]:
        """Format timedelta as human-readable string and direction"""
        total_seconds = offset.total_seconds()

        # Determine direction
        if total_seconds > 0:
            direction = "ahead of"
        elif total_seconds < 0:
            direction = "behind"
        else:
            direction = "equal to"

        # Work with absolute values for display
        abs_seconds = abs(total_seconds)

        # Calculate components directly from total seconds
        days = int(abs_seconds // 86400)
        hours = int((abs_seconds % 86400) // 3600)
        minutes = int((abs_seconds % 3600) // 60)
        seconds = int(abs_seconds % 60)

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