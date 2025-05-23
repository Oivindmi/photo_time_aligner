from functools import lru_cache
import hashlib
import os
from typing import Dict, Any, Optional
from datetime import datetime
import pickle
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CachedExifHandler:
    """
    ExifHandler with caching capabilities for improved performance.
    """

    def __init__(self, exif_handler, cache_dir: Optional[str] = None):
        self.exif_handler = exif_handler
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), 'photo_aligner_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self._memory_cache = {}

    def _get_file_hash(self, file_path: str) -> str:
        """Get a hash of file path and modification time"""
        stat = os.stat(file_path)
        key = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, file_hash: str) -> str:
        """Get the cache file path for a given hash"""
        return os.path.join(self.cache_dir, f"{file_hash}.cache")

    def read_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read metadata with caching"""
        file_hash = self._get_file_hash(file_path)

        # Check memory cache first
        if file_hash in self._memory_cache:
            return self._memory_cache[file_hash]

        # Check disk cache
        cache_path = self._get_cache_path(file_hash)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    metadata = pickle.load(f)
                self._memory_cache[file_hash] = metadata
                return metadata
            except Exception as e:
                logger.debug(f"Failed to load cache for {file_path}: {e}")

        # Read from ExifTool - this should call the underlying handler's method
        metadata = self.exif_handler.read_metadata(file_path)

        # Save to cache
        self._memory_cache[file_hash] = metadata
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(metadata, f)
        except Exception as e:
            logger.debug(f"Failed to save cache for {file_path}: {e}")

        return metadata

    def invalidate(self, file_path: str):
        """Invalidate cache for a specific file"""
        try:
            file_hash = self._get_file_hash(file_path)

            # Remove from memory cache
            if file_hash in self._memory_cache:
                del self._memory_cache[file_hash]

            # Remove from disk cache
            cache_path = self._get_cache_path(file_hash)
            if os.path.exists(cache_path):
                os.remove(cache_path)
        except Exception as e:
            logger.debug(f"Error invalidating cache for {file_path}: {e}")

    def clear_cache(self):
        """Clear all cache"""
        self._memory_cache.clear()

        # Clear disk cache
        for cache_file in Path(self.cache_dir).glob("*.cache"):
            try:
                cache_file.unlink()
            except:
                pass

    @lru_cache(maxsize=1000)
    def get_datetime_fields(self, file_path: str) -> Dict[str, Optional[datetime]]:
        """Get datetime fields with LRU caching"""
        return self.exif_handler.get_datetime_fields(file_path)