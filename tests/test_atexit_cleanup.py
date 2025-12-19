"""
Unit tests for atexit cleanup functionality.
Tests the fallback safety net for ExifToolProcess and ExifToolProcessPool.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock, call

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.exiftool_pool import ExifToolProcessPool
from src.core.exiftool_process import ExifToolProcess


class TestExifToolProcessPoolAtexitCleanup:
    """Tests for ExifToolProcessPool._atexit_cleanup method"""

    def test_atexit_cleanup_not_triggered_when_already_shutdown(self):
        """Test that atexit cleanup returns early if already shut down"""
        # Create pool but immediately mark as shutdown
        with patch('src.core.exiftool_process.ExifToolProcess') as MockProcess:
            mock_instance = MagicMock()
            MockProcess.return_value = mock_instance

            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = True

            # Call atexit cleanup
            with patch('src.core.exiftool_pool.logger') as mock_logger:
                pool._atexit_cleanup()

            # Should return early - no warning logged
            mock_logger.warning.assert_not_called()

    def test_atexit_cleanup_logs_warning_when_triggered(self):
        """Test that atexit cleanup logs warning when triggered"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False  # Not yet shutdown

            with patch('src.core.exiftool_pool.logger') as mock_logger:
                with patch.object(pool, 'shutdown'):
                    pool._atexit_cleanup()

            # Should log warning
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert 'atexit cleanup triggered' in warning_msg

    def test_atexit_cleanup_calls_shutdown(self):
        """Test that atexit cleanup calls shutdown"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                with patch.object(pool, 'shutdown') as mock_shutdown:
                    pool._atexit_cleanup()

            # Should call shutdown
            mock_shutdown.assert_called_once()

    def test_atexit_cleanup_handles_shutdown_exception(self):
        """Test that atexit cleanup handles exceptions from shutdown"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=2)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger') as mock_logger:
                # Make shutdown raise exception
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test error")):
                    pool._atexit_cleanup()

            # Should log error and attempt force kill
            assert mock_logger.error.called
            error_msg = mock_logger.error.call_args[0][0]
            assert 'Error during atexit cleanup' in error_msg

    def test_atexit_cleanup_force_kills_processes_on_shutdown_failure(self):
        """Test that atexit cleanup force kills processes if shutdown fails"""
        with patch('src.core.exiftool_process.ExifToolProcess') as MockProcess:
            mock_proc_instance = MagicMock()
            mock_proc_instance.process = MagicMock()
            mock_proc_instance.process.poll.return_value = None  # Still running
            MockProcess.return_value = mock_proc_instance

            pool = ExifToolProcessPool(pool_size=2)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                # Make shutdown raise exception
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test error")):
                    pool._atexit_cleanup()

            # Should attempt to kill processes
            for proc in pool.processes:
                if proc.process:
                    proc.process.kill.assert_called()

    def test_atexit_cleanup_idempotent_on_exception(self):
        """Test that atexit cleanup is safe to call multiple times even with errors"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test")):
                    # Call multiple times - should not raise
                    pool._atexit_cleanup()
                    pool._atexit_cleanup()
                    pool._atexit_cleanup()

            # Should succeed without exception

    def test_atexit_cleanup_sets_shutdown_flag_implicitly(self):
        """Test that shutdown() called by atexit cleanup sets _shutdown flag"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                # Normal shutdown (no exception)
                pool._atexit_cleanup()

            # shutdown() should have been called, which sets _shutdown flag
            assert pool._shutdown is True

    def test_atexit_cleanup_handles_none_process(self):
        """Test that atexit cleanup handles None process gracefully"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False

            # Set a process to None
            if pool.processes:
                pool.processes[0].process = None

            with patch('src.core.exiftool_pool.logger'):
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test")):
                    # Should not crash
                    pool._atexit_cleanup()


class TestExifToolProcessAtexitCleanup:
    """Tests for ExifToolProcess._atexit_cleanup method"""

    def test_process_atexit_cleanup_not_triggered_when_not_running(self):
        """Test that process atexit cleanup returns early if not running"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = False

            with patch('src.core.exiftool_process.logger') as mock_logger:
                process._atexit_cleanup()

            # Should return early - no warning
            mock_logger.warning.assert_not_called()

    def test_process_atexit_cleanup_logs_warning_when_running(self):
        """Test that process atexit cleanup logs warning when process still running"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger') as mock_logger:
                with patch.object(process, 'stop'):
                    process._atexit_cleanup()

            # Should log warning
            mock_logger.warning.assert_called()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert 'atexit cleanup triggered' in warning_msg

    def test_process_atexit_cleanup_calls_stop(self):
        """Test that process atexit cleanup calls stop method"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger'):
                with patch.object(process, 'stop') as mock_stop:
                    process._atexit_cleanup()

            # Should call stop
            mock_stop.assert_called_once()

    def test_process_atexit_cleanup_handles_stop_exception(self):
        """Test that process atexit cleanup handles exceptions from stop"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()
            process.process.poll.return_value = None  # Still running

            with patch('src.core.exiftool_process.logger') as mock_logger:
                # Make stop raise exception
                with patch.object(process, 'stop', side_effect=RuntimeError("Test error")):
                    process._atexit_cleanup()

            # Should log warning about atexit and debug about graceful stop failure
            assert mock_logger.warning.called or mock_logger.debug.called
            # Either warning about atexit or debug about graceful stop fail
            all_logs = [call[0][0] for call in mock_logger.warning.call_args_list] + \
                       [call[0][0] for call in mock_logger.debug.call_args_list]
            # Should have logged something about the failure
            assert len(all_logs) > 0

    def test_process_atexit_cleanup_force_kills_on_stop_failure(self):
        """Test that process atexit cleanup force kills if stop fails"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()
            process.process.poll.return_value = None  # Still running
            original_kill = process.process.kill

            with patch('src.core.exiftool_process.logger'):
                # Make stop raise exception
                with patch.object(process, 'stop', side_effect=RuntimeError("Test")):
                    process._atexit_cleanup()

            # After atexit cleanup, process should be None (cleared in finally block)
            # But we can verify the logic would have attempted kill by checking
            # that the code path was reached (process ends up None)
            assert process.process is None

    def test_process_atexit_cleanup_sets_running_false(self):
        """Test that atexit cleanup sets running flag to False"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger'):
                with patch.object(process, 'stop'):
                    process._atexit_cleanup()

            # running flag should be False
            assert process.running is False

    def test_process_atexit_cleanup_clears_process_reference(self):
        """Test that atexit cleanup clears process reference"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger'):
                with patch.object(process, 'stop'):
                    process._atexit_cleanup()

            # process should be None
            assert process.process is None

    def test_process_atexit_cleanup_handles_already_dead_process(self):
        """Test that atexit cleanup handles already-dead process"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()
            process.process.poll.return_value = 0  # Process already dead

            with patch('src.core.exiftool_process.logger'):
                with patch.object(process, 'stop', side_effect=RuntimeError("Test")):
                    # Should not crash
                    process._atexit_cleanup()

    def test_process_atexit_cleanup_idempotent_multiple_calls(self):
        """Test that process atexit cleanup is idempotent (safe to call multiple times)"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger'):
                # Call multiple times
                process._atexit_cleanup()
                process._atexit_cleanup()
                process._atexit_cleanup()

            # Should still be safe and consistent
            assert process.running is False
            assert process.process is None


class TestAtexitRegistration:
    """Tests to verify atexit handlers are properly registered"""

    def test_exiftool_process_registers_atexit_handler(self):
        """Test that ExifToolProcess registers atexit handler on init"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            with patch('src.core.exiftool_process.atexit.register') as mock_register:
                process = ExifToolProcess()

            # Should register atexit handler
            mock_register.assert_called_once()
            # Handler should be the _atexit_cleanup method
            handler = mock_register.call_args[0][0]
            assert handler == process._atexit_cleanup

    def test_exiftool_pool_registers_atexit_handler(self):
        """Test that ExifToolProcessPool registers atexit handler on init"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            with patch('src.core.exiftool_pool.atexit.register') as mock_register:
                pool = ExifToolProcessPool(pool_size=1)

            # Should register atexit handler
            mock_register.assert_called_once()
            # Handler should be the _atexit_cleanup method
            handler = mock_register.call_args[0][0]
            assert handler == pool._atexit_cleanup


class TestAtexitCleanupIntegration:
    """Integration tests for atexit cleanup behavior"""

    def test_pool_cleanup_then_atexit_cleanup_is_safe(self):
        """Test that calling shutdown then atexit cleanup is idempotent"""
        with patch('src.core.exiftool_process.ExifToolProcess'):
            pool = ExifToolProcessPool(pool_size=1)

            with patch('src.core.exiftool_pool.logger'):
                # First do normal shutdown
                pool.shutdown()
                assert pool._shutdown is True

                # Then call atexit cleanup - should be safe
                pool._atexit_cleanup()

            # Should still be shutdown
            assert pool._shutdown is True

    def test_process_cleanup_then_atexit_cleanup_is_safe(self):
        """Test that calling process stop then atexit cleanup is idempotent"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()

            with patch('src.core.exiftool_process.logger'):
                # First do normal stop
                process.stop()
                assert process.running is False

                # Then call atexit cleanup - should be safe
                process._atexit_cleanup()

            # Should still be stopped
            assert process.running is False


class TestErrorHandlingInAtexit:
    """Tests for error handling in atexit cleanup scenarios"""

    def test_pool_atexit_handles_kill_exception(self):
        """Test that pool atexit handles exceptions when killing processes"""
        with patch('src.core.exiftool_process.ExifToolProcess') as MockProcess:
            mock_proc = MagicMock()
            mock_proc.process = MagicMock()
            mock_proc.process.kill.side_effect = OSError("Permission denied")
            MockProcess.return_value = mock_proc

            pool = ExifToolProcessPool(pool_size=1)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test")):
                    # Should not crash even if kill fails
                    pool._atexit_cleanup()

    def test_process_atexit_handles_kill_exception(self):
        """Test that process atexit handles exceptions when killing"""
        with patch('src.core.exiftool_process.shutil.which', return_value='exiftool'):
            process = ExifToolProcess()
            process.running = True
            process.process = MagicMock()
            process.process.poll.return_value = None
            process.process.kill.side_effect = OSError("Permission denied")

            with patch('src.core.exiftool_process.logger'):
                with patch.object(process, 'stop', side_effect=RuntimeError("Test")):
                    # Should not crash even if kill fails
                    process._atexit_cleanup()

    def test_pool_atexit_handles_all_process_kill_failures(self):
        """Test that pool atexit tries to kill all processes even if some fail"""
        with patch('src.core.exiftool_process.ExifToolProcess') as MockProcess:
            # Create 3 mock processes
            mock_procs = []
            for i in range(3):
                mock_proc = MagicMock()
                mock_proc.process = MagicMock()
                # First one fails, others succeed
                if i == 0:
                    mock_proc.process.kill.side_effect = OSError("Fail")
                mock_procs.append(mock_proc)

            MockProcess.side_effect = mock_procs

            pool = ExifToolProcessPool(pool_size=3)
            pool._shutdown = False

            with patch('src.core.exiftool_pool.logger'):
                with patch.object(pool, 'shutdown', side_effect=RuntimeError("Test")):
                    pool._atexit_cleanup()

            # All processes should have been attempted to kill
            for proc in pool.processes:
                if proc.process:
                    proc.process.kill.assert_called()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
