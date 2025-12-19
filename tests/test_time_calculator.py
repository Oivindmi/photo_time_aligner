"""
Comprehensive unit tests for TimeCalculator class.
Tests all public methods, edge cases, None values, and Norwegian date formats.
"""
import os
import sys
from datetime import datetime, timedelta
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.time_calculator import TimeCalculator


class TestParseDatetimeNaive:
    """Tests for parse_datetime_naive method"""

    def test_parse_valid_exif_format(self):
        """Test parsing standard EXIF format YYYY:MM:DD HH:MM:SS"""
        result = TimeCalculator.parse_datetime_naive("2023:12:25 14:30:45")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

    def test_parse_iso_format(self):
        """Test parsing ISO format YYYY-MM-DDTHH:MM:SS"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25

    def test_parse_iso_format_with_milliseconds(self):
        """Test parsing ISO format with milliseconds"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45.123456")
        assert result is not None
        assert result.microsecond == 123456

    def test_parse_iso_format_with_timezone_z(self):
        """Test parsing ISO format with Z timezone"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45Z")
        assert result is not None
        assert result.tzinfo is None  # Should be naive (no timezone)

    def test_parse_iso_format_with_timezone_offset(self):
        """Test parsing ISO format with timezone offset"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45+02:00")
        assert result is not None
        assert result.tzinfo is None  # Should be naive

    def test_parse_iso_format_with_timezone_offset_no_colon(self):
        """Test parsing ISO format with timezone offset (no colon)"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45+0200")
        assert result is not None
        assert result.tzinfo is None

    def test_parse_dash_format(self):
        """Test parsing YYYY-MM-DD HH:MM:SS format"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 14:30:45")
        assert result is not None
        assert result.year == 2023

    def test_parse_slash_format(self):
        """Test parsing YYYY/MM/DD HH:MM:SS format"""
        result = TimeCalculator.parse_datetime_naive("2023/12/25 14:30:45")
        assert result is not None
        assert result.year == 2023

    def test_parse_dot_format(self):
        """Test parsing YYYY.MM.DD HH:MM:SS format"""
        result = TimeCalculator.parse_datetime_naive("2023.12.25 14:30:45")
        assert result is not None
        assert result.year == 2023

    def test_parse_compact_format(self):
        """Test parsing compact format YYYYMMDDHHMMSS"""
        result = TimeCalculator.parse_datetime_naive("20231225143045")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 14

    def test_parse_european_format(self):
        """Test parsing DD/MM/YYYY HH:MM:SS format"""
        result = TimeCalculator.parse_datetime_naive("25/12/2023 14:30:45")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25

    def test_parse_us_format(self):
        """Test parsing MM/DD/YYYY HH:MM:SS format"""
        result = TimeCalculator.parse_datetime_naive("12/25/2023 14:30:45")
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25

    def test_parse_with_utc_timezone_string(self):
        """Test parsing with UTC timezone string"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 14:30:45 UTC")
        assert result is not None
        assert result.year == 2023

    def test_parse_with_gmt_timezone_string(self):
        """Test parsing with GMT timezone string"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 14:30:45 GMT")
        assert result is not None
        assert result.year == 2023

    def test_parse_empty_string(self):
        """Test parsing empty string returns None"""
        result = TimeCalculator.parse_datetime_naive("")
        assert result is None

    def test_parse_none_value(self):
        """Test parsing None value returns None"""
        result = TimeCalculator.parse_datetime_naive(None)
        assert result is None

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only string returns None"""
        result = TimeCalculator.parse_datetime_naive("   ")
        assert result is None

    def test_parse_timezone_offset_only(self):
        """Test parsing timezone offset only returns None"""
        result = TimeCalculator.parse_datetime_naive("+02:00")
        assert result is None

    def test_parse_partial_date(self):
        """Test parsing partial date returns None"""
        result = TimeCalculator.parse_datetime_naive("2023-12")
        assert result is None

    def test_parse_invalid_date(self):
        """Test parsing invalid date returns None"""
        result = TimeCalculator.parse_datetime_naive("2023-13-45")
        assert result is None

    def test_parse_short_numeric_string(self):
        """Test parsing short numeric string returns None"""
        result = TimeCalculator.parse_datetime_naive("12345")
        assert result is None

    def test_parse_random_text(self):
        """Test parsing random text returns None"""
        result = TimeCalculator.parse_datetime_naive("not a date")
        assert result is None

    def test_parse_numeric_string_8_digits(self):
        """Test parsing 8-digit numeric string (YYYYMMDD)"""
        result = TimeCalculator.parse_datetime_naive("20231225")
        # 8-digit string gets treated as short numeric and returns None
        # Only 14-digit compact format (YYYYMMDDHHMMSS) is parsed successfully
        assert result is None

    def test_parse_milliseconds_truncation(self):
        """Test that milliseconds beyond 6 digits are truncated"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45.123456789")
        assert result is not None
        # Should truncate to 6 digits
        assert result.microsecond == 123456


class TestNorwegianDateFormats:
    """Tests for Norwegian date formats and characters"""

    def test_parse_norwegian_date_dash_format(self):
        """Test parsing Norwegian standard date format YYYY-MM-DD"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 14:30:45")
        assert result is not None
        assert result.year == 2023

    def test_parse_norwegian_date_with_time(self):
        """Test parsing Norwegian date with time"""
        result = TimeCalculator.parse_datetime_naive("25.12.2023 14:30:45")
        assert result is not None
        assert result.day == 25
        assert result.month == 12
        assert result.year == 2023

    def test_parse_year_2024(self):
        """Test parsing recent Norwegian date"""
        result = TimeCalculator.parse_datetime_naive("2024-01-15 10:45:30")
        assert result is not None
        assert result.year == 2024

    def test_parse_year_2025(self):
        """Test parsing current year date"""
        result = TimeCalculator.parse_datetime_naive("2025-06-20 09:15:00")
        assert result is not None
        assert result.year == 2025

    def test_parse_historical_date(self):
        """Test parsing historical date"""
        result = TimeCalculator.parse_datetime_naive("2000-01-01 00:00:00")
        assert result is not None
        assert result.year == 2000
        assert result.month == 1
        assert result.day == 1


class TestCalculateOffset:
    """Tests for calculate_offset method"""

    def test_calculate_positive_offset(self):
        """Test calculating positive offset (target ahead)"""
        ref_time = datetime(2023, 12, 25, 14, 0, 0)
        target_time = datetime(2023, 12, 25, 15, 30, 0)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 5400  # 1.5 hours in seconds

    def test_calculate_negative_offset(self):
        """Test calculating negative offset (target behind)"""
        ref_time = datetime(2023, 12, 25, 15, 30, 0)
        target_time = datetime(2023, 12, 25, 14, 0, 0)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == -5400

    def test_calculate_zero_offset(self):
        """Test calculating zero offset (same time)"""
        ref_time = datetime(2023, 12, 25, 14, 30, 0)
        target_time = datetime(2023, 12, 25, 14, 30, 0)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 0

    def test_calculate_offset_multiple_days(self):
        """Test calculating offset spanning multiple days"""
        ref_time = datetime(2023, 12, 24, 14, 0, 0)
        target_time = datetime(2023, 12, 26, 14, 0, 0)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 172800  # 2 days

    def test_calculate_offset_one_second(self):
        """Test calculating one-second offset"""
        ref_time = datetime(2023, 12, 25, 14, 30, 0)
        target_time = datetime(2023, 12, 25, 14, 30, 1)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 1

    def test_calculate_offset_microseconds(self):
        """Test calculating offset with microseconds"""
        ref_time = datetime(2023, 12, 25, 14, 30, 0, 0)
        target_time = datetime(2023, 12, 25, 14, 30, 0, 500000)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 0.5

    def test_calculate_offset_negative_multiple_days(self):
        """Test calculating negative offset spanning days"""
        ref_time = datetime(2023, 12, 26, 14, 0, 0)
        target_time = datetime(2023, 12, 24, 14, 0, 0)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == -172800


class TestFormatOffset:
    """Tests for format_offset method"""

    def test_format_offset_positive(self):
        """Test formatting positive offset"""
        offset = timedelta(hours=1, minutes=30)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "1 hour" in offset_str
        assert "30 minute" in offset_str

    def test_format_offset_negative(self):
        """Test formatting negative offset"""
        offset = timedelta(hours=-2, minutes=-15)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "behind"
        assert "2 hour" in offset_str
        assert "15 minute" in offset_str

    def test_format_offset_zero(self):
        """Test formatting zero offset"""
        offset = timedelta(seconds=0)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "equal to"
        assert "0 second" in offset_str

    def test_format_offset_days_only(self):
        """Test formatting offset with days only"""
        offset = timedelta(days=5)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "5 day" in offset_str

    def test_format_offset_one_day(self):
        """Test formatting one day offset (singular)"""
        offset = timedelta(days=1)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert "1 day" in offset_str  # Singular, not "days"

    def test_format_offset_hours_only(self):
        """Test formatting offset with hours only"""
        offset = timedelta(hours=3)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "3 hour" in offset_str

    def test_format_offset_one_hour(self):
        """Test formatting one hour offset (singular)"""
        offset = timedelta(hours=1)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert "1 hour" in offset_str  # Singular

    def test_format_offset_minutes_only(self):
        """Test formatting offset with minutes only"""
        offset = timedelta(minutes=45)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "45 minute" in offset_str

    def test_format_offset_one_minute(self):
        """Test formatting one minute offset (singular)"""
        offset = timedelta(minutes=1)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert "1 minute" in offset_str  # Singular

    def test_format_offset_seconds_only(self):
        """Test formatting offset with seconds only"""
        offset = timedelta(seconds=30)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "30 second" in offset_str

    def test_format_offset_one_second(self):
        """Test formatting one second offset (singular)"""
        offset = timedelta(seconds=1)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert "1 second" in offset_str  # Singular

    def test_format_offset_complex(self):
        """Test formatting complex offset with multiple components"""
        offset = timedelta(days=2, hours=5, minutes=30, seconds=45)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "2 day" in offset_str
        assert "5 hour" in offset_str
        assert "30 minute" in offset_str
        assert "45 second" in offset_str

    def test_format_offset_negative_multiple_days(self):
        """Test formatting negative offset spanning days"""
        offset = timedelta(days=-3, hours=-12)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "behind"
        assert "3 day" in offset_str
        assert "12 hour" in offset_str

    def test_format_offset_large_offset(self):
        """Test formatting large offset"""
        offset = timedelta(days=365)
        offset_str, direction = TimeCalculator.format_offset(offset)
        assert direction == "ahead of"
        assert "365 day" in offset_str

    def test_format_offset_fractional_seconds(self):
        """Test formatting offset with fractional seconds"""
        offset = timedelta(seconds=5.5)
        offset_str, direction = TimeCalculator.format_offset(offset)
        # Should round down to 5 seconds
        assert "5 second" in offset_str


class TestCleanDateString:
    """Tests for _clean_date_string method"""

    def test_clean_timezone_offset_with_colon(self):
        """Test cleaning timezone offset with colon"""
        result = TimeCalculator._clean_date_string("2023-12-25T14:30:45+02:00")
        assert "+02:00" not in result
        # T is replaced with space when there are < 3 colons
        assert "2023-12-25 14:30:45" in result

    def test_clean_timezone_offset_without_colon(self):
        """Test cleaning timezone offset without colon"""
        result = TimeCalculator._clean_date_string("2023-12-25T14:30:45+0200")
        assert "+0200" not in result

    def test_clean_negative_timezone_offset(self):
        """Test cleaning negative timezone offset"""
        result = TimeCalculator._clean_date_string("2023-12-25T14:30:45-05:00")
        assert "-05:00" not in result

    def test_clean_z_timezone(self):
        """Test cleaning Z timezone marker"""
        result = TimeCalculator._clean_date_string("2023-12-25T14:30:45Z")
        assert "Z" not in result
        # T is replaced with space when there are < 3 colons
        assert "2023-12-25 14:30:45" in result

    def test_clean_utc_string(self):
        """Test cleaning UTC string"""
        result = TimeCalculator._clean_date_string("2023-12-25 14:30:45 UTC")
        assert "UTC" not in result
        assert "2023-12-25 14:30:45" in result

    def test_clean_gmt_string(self):
        """Test cleaning GMT string"""
        result = TimeCalculator._clean_date_string("2023-12-25 14:30:45 GMT")
        assert "GMT" not in result
        assert "2023-12-25 14:30:45" in result

    def test_clean_t_separator_iso_format(self):
        """Test cleaning T separator (ISO format)"""
        result = TimeCalculator._clean_date_string("2023-12-25T14:30:45")
        assert "2023-12-25 14:30:45" in result

    def test_clean_excessive_milliseconds(self):
        """Test cleaning milliseconds beyond 6 digits"""
        result = TimeCalculator._clean_date_string("2023-12-25 14:30:45.123456789")
        assert ".123456" in result
        assert ".123456789" not in result

    def test_clean_milliseconds_exactly_6_digits(self):
        """Test cleaning with exactly 6 digit milliseconds"""
        result = TimeCalculator._clean_date_string("2023-12-25 14:30:45.123456")
        assert ".123456" in result

    def test_clean_non_string_input(self):
        """Test cleaning non-string input"""
        result = TimeCalculator._clean_date_string(123)
        assert "123" in result

    def test_clean_empty_string(self):
        """Test cleaning empty string"""
        result = TimeCalculator._clean_date_string("")
        assert result == ""

    def test_clean_multiple_timezone_markers(self):
        """Test cleaning with multiple timezone patterns"""
        result = TimeCalculator._clean_date_string("2023-12-25 14:30:45 UTC")
        assert "UTC" not in result
        assert result.strip() == "2023-12-25 14:30:45"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_leap_year_february_29(self):
        """Test parsing leap year date February 29"""
        result = TimeCalculator.parse_datetime_naive("2024-02-29 12:00:00")
        assert result is not None
        assert result.month == 2
        assert result.day == 29

    def test_century_boundary_year_2000(self):
        """Test parsing year 2000"""
        result = TimeCalculator.parse_datetime_naive("2000-01-01 00:00:00")
        assert result is not None
        assert result.year == 2000

    def test_midnight(self):
        """Test parsing midnight time"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 00:00:00")
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_end_of_day(self):
        """Test parsing end of day time"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 23:59:59")
        assert result is not None
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_december_31(self):
        """Test parsing December 31 (year boundary)"""
        result = TimeCalculator.parse_datetime_naive("2023-12-31 23:59:59")
        assert result is not None
        assert result.month == 12
        assert result.day == 31

    def test_january_1(self):
        """Test parsing January 1 (year start)"""
        result = TimeCalculator.parse_datetime_naive("2023-01-01 00:00:00")
        assert result is not None
        assert result.month == 1
        assert result.day == 1

    def test_offset_at_year_boundary(self):
        """Test calculating offset at year boundary"""
        ref_time = datetime(2023, 12, 31, 23, 59, 59)
        target_time = datetime(2024, 1, 1, 0, 0, 1)
        offset = TimeCalculator.calculate_offset(ref_time, target_time)
        assert offset.total_seconds() == 2

    def test_maximum_microseconds(self):
        """Test parsing with maximum microseconds"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25 14:30:45.999999")
        assert result is not None
        assert result.microsecond == 999999

    def test_single_digit_day(self):
        """Test parsing single digit day"""
        result = TimeCalculator.parse_datetime_naive("2023-12-05 14:30:45")
        assert result is not None
        assert result.day == 5

    def test_single_digit_month(self):
        """Test parsing single digit month"""
        result = TimeCalculator.parse_datetime_naive("2023-01-25 14:30:45")
        assert result is not None
        assert result.month == 1


class TestRealWorldScenarios:
    """Tests with real-world photo/video metadata scenarios"""

    def test_camera_timestamp_photo(self):
        """Test parsing typical camera photo timestamp"""
        result = TimeCalculator.parse_datetime_naive("2023:12:25 14:30:45")
        assert result is not None

    def test_video_creation_time(self):
        """Test parsing typical video creation timestamp"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45")
        assert result is not None

    def test_video_with_timezone(self):
        """Test parsing video timestamp with timezone"""
        result = TimeCalculator.parse_datetime_naive("2023-12-25T14:30:45+02:00")
        assert result is not None
        assert result.tzinfo is None

    def test_synchronizing_two_cameras(self):
        """Test scenario: synchronizing timestamps from two cameras"""
        camera1_time = TimeCalculator.parse_datetime_naive("2023:12:25 14:30:45")
        camera2_time = TimeCalculator.parse_datetime_naive("2023:12:25 14:35:20")

        assert camera1_time is not None
        assert camera2_time is not None

        offset = TimeCalculator.calculate_offset(camera1_time, camera2_time)
        offset_str, direction = TimeCalculator.format_offset(offset)

        assert direction == "ahead of"
        assert "4 minute" in offset_str
        assert "35 second" in offset_str

    def test_time_correction_workflow(self):
        """Test workflow: detect time difference and format correction message"""
        reference_photo_time = TimeCalculator.parse_datetime_naive("2023:12:25 10:00:00")
        video_creation_time = TimeCalculator.parse_datetime_naive("2023-12-25T09:45:30")

        offset = TimeCalculator.calculate_offset(reference_photo_time, video_creation_time)
        offset_str, direction = TimeCalculator.format_offset(offset)

        # Video is 14.5 minutes behind
        assert "behind" in direction
        assert "14 minute" in offset_str


class TestIntegrationWithDateutil:
    """Tests to ensure dateutil parsing works correctly"""

    def test_dateutil_flexible_parsing(self):
        """Test that dateutil can parse various formats"""
        test_cases = [
            "2023-12-25 14:30:45",
            "Dec 25, 2023 2:30 PM",
            "25 December 2023 14:30",
            "25/12/2023",
        ]

        for test_case in test_cases:
            result = TimeCalculator.parse_datetime_naive(test_case)
            # Most should parse successfully
            if result is not None:
                assert result.year == 2023

    def test_dateutil_ambiguous_date(self):
        """Test dateutil with ambiguous date format"""
        # With dayfirst=False, this should parse as MM/DD/YYYY
        result = TimeCalculator.parse_datetime_naive("02/01/2023")
        assert result is not None
        assert result.month == 2
        assert result.day == 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
