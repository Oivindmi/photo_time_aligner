# src/core/concurrent_file_processor.py
import os
import asyncio
import concurrent.futures
from typing import List, Dict, Callable, Optional, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConcurrentFileProcessor:
    """
    High-performance file processor using concurrent operations.
    """

    def __init__(self, exif_handler, max_workers: int = 4):
        self.exif_handler = exif_handler
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    async def scan_directory_async(self, directory: str,
                                   extensions: Set[str]) -> List[str]:
        """
        Asynchronously scan directory for files with given extensions.

        This is much faster than os.listdir for large directories.
        """
        loop = asyncio.get_event_loop()

        def _scan():
            results = []
            try:
                # Use os.scandir for better performance
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if entry.is_file():
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in extensions:
                                results.append(entry.path)
            except Exception as e:
                logger.error(f"Error scanning directory: {e}")
            return results

        return await loop.run_in_executor(self.executor, _scan)

    async def filter_files_by_criteria_async(
            self,
            files: List[str],
            camera_info: Optional[Dict[str, str]] = None,
            pattern: Optional[Dict] = None,
            progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """
        Filter files by camera and pattern criteria asynchronously.
        """
        if not files:
            return []

        # Process files in chunks for better performance
        chunk_size = 50
        matching_files = []

        for i in range(0, len(files), chunk_size):
            chunk = files[i:i + chunk_size]

            # Process chunk asynchronously
            tasks = []
            for file_path in chunk:
                task = self._check_file_criteria(file_path, camera_info, pattern)
                tasks.append(task)

            # Wait for chunk results
            results = await asyncio.gather(*tasks)

            # Collect matching files
            for file_path, matches in zip(chunk, results):
                if matches:
                    matching_files.append(file_path)

            # Report progress
            if progress_callback:
                progress_callback(min(i + chunk_size, len(files)), len(files))

        return matching_files

    async def _check_file_criteria(
            self,
            file_path: str,
            camera_info: Optional[Dict[str, str]],
            pattern: Optional[Dict]
    ) -> bool:
        """Check if a file matches the given criteria"""
        loop = asyncio.get_event_loop()

        def _check():
            try:
                # Check pattern first (faster)
                if pattern:
                    from .filename_pattern import FilenamePatternMatcher
                    filename = os.path.basename(file_path)
                    if not FilenamePatternMatcher.matches_pattern(filename, pattern):
                        return False

                # Check camera info if needed
                if camera_info is not None:
                    file_camera = self.exif_handler.get_camera_info(file_path)

                    # Handle empty camera info matching
                    if not camera_info.get('make') and not camera_info.get('model'):
                        if file_camera.get('make') or file_camera.get('model'):
                            return False
                    else:
                        if (file_camera.get('make') != camera_info.get('make') or
                                file_camera.get('model') != camera_info.get('model')):
                            return False

                return True

            except Exception as e:
                logger.debug(f"Error checking file {file_path}: {e}")
                return False

        return await loop.run_in_executor(self.executor, _check)