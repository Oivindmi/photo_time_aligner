# src/utils/performance_monitor.py
import time
import logging
from contextlib import contextmanager
from typing import Dict, List
import statistics

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitor and report performance metrics"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}

    @contextmanager
    def measure(self, operation: str):
        """Measure operation duration"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(duration)
            logger.debug(f"{operation} took {duration:.3f}s")

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """Get performance summary"""
        summary = {}
        for operation, durations in self.metrics.items():
            if durations:
                summary[operation] = {
                    'count': len(durations),
                    'total': sum(durations),
                    'average': statistics.mean(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'median': statistics.median(durations)
                }
        return summary

    def log_summary(self):
        """Log performance summary"""
        summary = self.get_summary()
        logger.info("Performance Summary:")
        for operation, stats in summary.items():
            logger.info(f"  {operation}:")
            logger.info(f"    Count: {stats['count']}")
            logger.info(f"    Average: {stats['average']:.3f}s")
            logger.info(f"    Total: {stats['total']:.3f}s")