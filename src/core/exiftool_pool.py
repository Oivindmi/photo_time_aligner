import queue
import threading
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import time

logger = logging.getLogger(__name__)


class ExifToolProcessPool:
    """
    Pool of ExifTool processes for concurrent operations with restart capability.
    """

    def __init__(self, pool_size: int = 4, max_retries: int = 3):
        self.pool_size = pool_size
        self.max_retries = max_retries
        self.processes = []
        self.available = queue.Queue()
        self._lock = threading.Lock()
        self._shutdown = False

        # Initialize the pool
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the process pool"""
        from .exiftool_process import ExifToolProcess

        logger.info(f"Initializing ExifTool process pool with {self.pool_size} processes")

        for i in range(self.pool_size):
            try:
                process = ExifToolProcess()
                process.start()
                self.processes.append(process)
                self.available.put(process)
                logger.debug(f"Started ExifTool process {i + 1}/{self.pool_size}")
            except Exception as e:
                logger.error(f"Failed to start ExifTool process {i + 1}: {e}")
                raise

    def restart_pool(self):
        """Restart the entire process pool to prevent process accumulation"""
        logger.info("Restarting entire ExifTool process pool...")

        with self._lock:
            if self._shutdown:
                return

            try:
                # Stop all existing processes
                self._stop_all_processes()

                # Clear the queue and processes list
                while not self.available.empty():
                    try:
                        self.available.get_nowait()
                    except queue.Empty:
                        break

                self.processes.clear()

                # Wait a moment for processes to fully terminate
                time.sleep(0.5)

                # Reinitialize the pool
                self._initialize_pool()

                logger.info("ExifTool process pool restart completed successfully")

            except Exception as e:
                logger.error(f"Error during pool restart: {e}")
                # Try to salvage the situation by initializing fresh processes
                self.processes.clear()
                while not self.available.empty():
                    try:
                        self.available.get_nowait()
                    except queue.Empty:
                        break
                self._initialize_pool()

    def _stop_all_processes(self):
        """Stop all processes in the pool"""
        for process in self.processes:
            try:
                process.stop()
            except Exception as e:
                logger.warning(f"Error stopping process: {e}")

    @contextmanager
    def get_process(self, timeout: float = 30.0):
        """Get an available process from the pool"""
        process = None
        start_time = time.time()

        try:
            # Try to get a process with timeout
            process = self.available.get(timeout=timeout)
            yield process
        except queue.Empty:
            elapsed = time.time() - start_time
            raise TimeoutError(f"No available ExifTool process after {elapsed:.1f}s")
        finally:
            # Return the process to the pool
            if process and not self._shutdown:
                self.available.put(process)

    def read_metadata_batch_parallel(self, file_paths: List[str],
                                     chunk_size: int = 10) -> List[Dict[str, Any]]:
        """
        Read metadata from multiple files in parallel using the process pool.
        """
        if not file_paths:
            return []

        results = [{}] * len(file_paths)
        chunks = [file_paths[i:i + chunk_size] for i in range(0, len(file_paths), chunk_size)]
        threads = []

        def process_chunk(chunk_files, start_idx):
            try:
                with self.get_process() as process:
                    chunk_results = process.read_metadata_batch(chunk_files)
                    for i, result in enumerate(chunk_results):
                        results[start_idx + i] = result
            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                # Fill with empty dicts on error
                for i in range(len(chunk_files)):
                    results[start_idx + i] = {}

        # Process chunks in parallel
        for i, chunk in enumerate(chunks):
            start_idx = i * chunk_size
            thread = threading.Thread(
                target=process_chunk,
                args=(chunk, start_idx)
            )
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return results

    def shutdown(self):
        """Shutdown all processes in the pool"""
        logger.info("Shutting down ExifTool process pool...")
        self._shutdown = True

        # Stop all processes
        self._stop_all_processes()

        # Clear the queue
        while not self.available.empty():
            try:
                self.available.get_nowait()
            except queue.Empty:
                break

        logger.info("ExifTool process pool shut down completed")