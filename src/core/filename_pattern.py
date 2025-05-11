
import re
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FilenamePatternMatcher:
    """Handles filename pattern detection and matching"""

    @staticmethod
    def extract_pattern(filename: str) -> Dict[str, any]:
        """Extract pattern components from a filename"""
        name_without_ext = os.path.splitext(filename)[0]

        # Extended patterns including video-specific ones
        patterns = [
            # Existing photo patterns
            (r'^([A-Z]+)([_-])(\d+)$', 'prefix_separator_number'),
            (r'^(\d{8})([_-])(\d{6})$', 'date_separator_time'),
            (r'^([A-Za-z]+)\s+(\d{2}-\d{2}-\d{4}),\s+(\d{2}\s+\d{2}\s+\d{2})$', 'word_date_time'),
            (r'^([A-Z]+)(\d+)$', 'prefix_number'),
            (r'^(Screenshot)([_-])(\d{8}-\d{6})([_-])(.+)$', 'screenshot_pattern'),

            # Video-specific patterns
            (r'^(VID|MOV|MVI)([_-])(\d+)$', 'video_prefix_number'),
            (r'^(VID|VIDEO)([_-])(\d{8})([_-])(\d{6})$', 'video_timestamp'),
            (r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2})$', 'video_date_time'),
            (r'^(Screencast|Recording)([_-])(\d{4}-\d{2}-\d{2})([_-])(\d{2}-\d{2}-\d{2})$', 'screen_recording'),

            # GoPro/Action camera patterns
            (r'^(GH|GP|GX|GOPR)(\d+)$', 'gopro_pattern'),
            (r'^(DJI)([_-])(\d+)$', 'dji_pattern'),

            # Generic: any prefix followed by numbers
            (r'^([^0-9]+)(\d+)(.*)$', 'generic')
        ]

        for pattern, pattern_type in patterns:
            match = re.match(pattern, name_without_ext)
            if match:
                groups = match.groups()
                result = {
                    'type': pattern_type,
                    'pattern': pattern,
                    'groups': groups,
                    'display': _format_pattern_display(pattern_type, groups)
                }
                logger.debug(f"Extracted pattern from '{filename}': {result}")
                return result

        # No pattern found - just use the full prefix
        result = {
            'type': 'no_pattern',
            'pattern': None,
            'groups': [name_without_ext],
            'display': f'Prefix: {name_without_ext[:10]}...' if len(name_without_ext) > 10 else name_without_ext
        }
        logger.debug(f"No pattern found for '{filename}': {result}")
        return result

    @staticmethod
    def matches_pattern(filename: str, reference_pattern: Dict[str, any]) -> bool:
        """Check if a filename matches the reference pattern"""
        name_without_ext = os.path.splitext(filename)[0]

        if reference_pattern['type'] == 'no_pattern':
            # For no pattern, just check if it starts with the same prefix
            matches = name_without_ext.startswith(reference_pattern['groups'][0])
            logger.debug(
                f"Pattern match check (no_pattern) '{filename}' vs '{reference_pattern['groups'][0]}': {matches}")
            return matches

        # Check if filename matches the same pattern
        if reference_pattern['pattern']:
            match = re.match(reference_pattern['pattern'], name_without_ext)
            if match:
                # For these patterns, we want exact prefix match
                if reference_pattern['type'] in [
                    'prefix_separator_number', 'prefix_number', 'screenshot_pattern',
                    'generic', 'video_prefix_number', 'gopro_pattern', 'dji_pattern'
                ]:
                    ref_prefix = reference_pattern['groups'][0]
                    file_prefix = match.groups()[0]
                    matches = ref_prefix == file_prefix
                    logger.debug(
                        f"Pattern match check ({reference_pattern['type']}) '{filename}' prefix '{file_prefix}' vs '{ref_prefix}': {matches}")
                    return matches
                logger.debug(f"Pattern match check (other) '{filename}' matches pattern: True")
                return True
            else:
                logger.debug(f"Pattern match check '{filename}' doesn't match pattern {reference_pattern['pattern']}")

        return False


def _format_pattern_display(pattern_type: str, groups: tuple) -> str:
    """Format pattern for display to user"""
    if pattern_type == 'prefix_separator_number':
        return f"{groups[0]}{groups[1]}####"
    elif pattern_type == 'date_separator_time':
        return "YYYYMMDD_HHMMSS"
    elif pattern_type == 'word_date_time':
        return f"{groups[0]} DD-MM-YYYY, HH MM SS"
    elif pattern_type == 'prefix_number':
        return f"{groups[0]}####"
    elif pattern_type == 'screenshot_pattern':
        return f"Screenshot_########-######_*"
    elif pattern_type == 'video_prefix_number':
        return f"{groups[0]}{groups[1]}####"
    elif pattern_type == 'video_timestamp':
        return f"{groups[0]}_YYYYMMDD_HHMMSS"
    elif pattern_type == 'video_date_time':
        return "YYYY-MM-DD HH-MM-SS"
    elif pattern_type == 'screen_recording':
        return f"{groups[0]}_YYYY-MM-DD_HH-MM-SS"
    elif pattern_type == 'gopro_pattern':
        return f"{groups[0]}####"
    elif pattern_type == 'dji_pattern':
        return f"{groups[0]}{groups[1]}####"
    elif pattern_type == 'generic':
        prefix = groups[0]
        return f"{prefix}####"
    else:
        return "Unknown pattern"