import subprocess
import logging
import os
import json
import time
import shutil
import threading
import tempfile
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExifToolProcess:
    """
    Persistent ExifTool process using the reliable argument file approach.
    Combines the performance of persistent process with the reliability of argument files.
    """

    def __init__(self, executable_path=None):
        self.executable_path = executable_path or self._find_exiftool()
        self.process = None
        self.running = False
        self.command_counter = 0
        self._lock = threading.Lock()

    def _find_exiftool(self) -> str:
        """Find ExifTool executable"""
        if shutil.which("exiftool"):
            return "exiftool"

        common_paths = [
            r"C:\Program Files\ExifTool\exiftool.exe",
            r"C:\ExifTool\exiftool.exe",
            r"C:\Windows\exiftool.exe",
            os.path.expanduser(r"~\AppData\Local\ExifTool\exiftool.exe")
        ]

        for path in common_paths:
            if os.path.isfile(path):
                return path

        raise ValueError("ExifTool not found")

    def start(self):
        """Start the ExifTool process"""
        if self.running:
            return

        logger.info(f"Starting persistent ExifTool process with path: {self.executable_path}")
        try:
            self.process = subprocess.Popen(
                [self.executable_path, "-stay_open", "True", "-@", "-"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.running = True
            logger.info("ExifTool process started successfully")

            # Test the connection
            test_result = self.execute_command(["-ver"])
            logger.info(f"ExifTool version: {test_result.strip()}")

        except Exception as e:
            logger.error(f"Failed to start ExifTool process: {str(e)}")
            raise

    def execute_command(self, args: List[str], timeout: float = 30.0) -> str:
        """Execute a command using the persistent process"""
        with self._lock:
            if not self.running:
                self.start()

            self.command_counter += 1

            # Build command - exactly like the original but for persistent process
            cmd_parts = args + ["-execute"]
            cmd_str = "\n".join(cmd_parts) + "\n"

            try:
                # Send command
                self.process.stdin.write(cmd_str)
                self.process.stdin.flush()

                # Read response
                output_lines = []
                start_time = time.time()

                while time.time() - start_time < timeout:
                    if self.process.poll() is not None:
                        raise RuntimeError("ExifTool process died")

                    line = self.process.stdout.readline()
                    if line:
                        output_lines.append(line)
                        if "{ready}" in line:
                            break
                    else:
                        time.sleep(0.01)
                else:
                    raise TimeoutError(f"Command timed out after {timeout} seconds")

                # Join output and clean up
                output = "".join(output_lines)
                output = output.replace("{ready}", "").strip()

                return output

            except Exception as e:
                logger.error(f"Error executing command: {str(e)}")
                self.restart()
                raise

    def read_metadata_batch(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Read metadata from multiple files using argument file - persistent process version"""
        if not file_paths:
            return []

        # Create temporary argument file - exactly like the original
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            for file_path in file_paths:
                arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            # Use the exact same command structure as the original, but with persistent process
            cmd = [
                '-json',
                '-charset', 'filename=utf8',
                '-time:all',
                '-make',
                '-model',
                '-@', arg_file_path  # Key: Using argument file approach
            ]

            logger.debug(f"ExifTool command: {' '.join(cmd)}")

            # Execute using persistent process
            output = self.execute_command(cmd)

            if not output.strip():
                logger.warning("ExifTool returned empty output")
                return [{}] * len(file_paths)

            # Parse JSON exactly like the original
            metadata_list = json.loads(output)

            # Ensure we have the right number of results
            if len(metadata_list) != len(file_paths):
                logger.warning(f"Expected {len(file_paths)} results, got {len(metadata_list)}")

            return metadata_list

        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Error parsing metadata: {e}")
            logger.error(f"Output was: {output[:500] if 'output' in locals() else 'No output'}")
            return [{}] * len(file_paths)
        except Exception as e:
            logger.error(f"Error in batch metadata reading: {str(e)}")
            return [{}] * len(file_paths)
        finally:
            # Clean up the argument file
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    def read_metadata(self, file_path: str) -> Dict[str, Any]:
        """Read metadata from a single file"""
        results = self.read_metadata_batch([file_path])
        return results[0] if results else {}

    def update_datetime_fields(self, file_path: str, fields: Dict[str, Any]) -> bool:
        """Update datetime fields using argument file approach with persistent process"""
        # Create temporary argument file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            cmd = ['-charset', 'filename=utf8', '-overwrite_original']

            for field, value in fields.items():
                if hasattr(value, 'strftime'):
                    formatted_value = value.strftime("%Y:%m:%d %H:%M:%S")
                    cmd.append(f'-{field}={formatted_value}')

            cmd.extend(['-@', arg_file_path])

            output = self.execute_command(cmd)
            success = "1 image files updated" in output or "1 files updated" in output

            if not success:
                logger.warning(f"Unexpected update output for {file_path}: {output}")

            return success

        except Exception as e:
            logger.error(f"Error updating datetime fields: {str(e)}")
            return False
        finally:
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)

    def restart(self):
        """Restart the ExifTool process"""
        logger.warning("Restarting ExifTool process")
        self.stop()
        time.sleep(0.2)
        self.start()

    def stop(self):
        """Stop the ExifTool process"""
        if not self.running:
            return

        logger.info("Stopping ExifTool process")
        with self._lock:
            try:
                if self.process and self.process.stdin:
                    self.process.stdin.write("-stay_open\nFalse\n")
                    self.process.stdin.flush()
                if self.process:
                    try:
                        self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
            except Exception as e:
                logger.warning(f"Error while stopping ExifTool: {str(e)}")
                try:
                    if self.process:
                        self.process.kill()
                except:
                    pass
            finally:
                self.running = False
                self.process = None

    def get_comprehensive_metadata(self, file_path: str) -> str:
        """Get comprehensive metadata using -a -u -g1 flags for a single file"""
        # Create temporary argument file with single file - exactly like batch operations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as arg_file:
            arg_file.write(file_path + '\n')
            arg_file_path = arg_file.name

        try:
            # Use the same command structure as batch operations, but with comprehensive flags
            cmd = [
                '-a',  # Allow duplicate tags
                '-u',  # Unknown tags
                '-g1',  # Group by category level 1
                '-charset', 'filename=utf8',
                '-@', arg_file_path  # Single-file argument file (same as batch approach)
            ]

            logger.debug(f"ExifTool comprehensive command: {' '.join(cmd)}")

            # Execute using persistent process (same as batch operations)
            output = self.execute_command(cmd)

            if not output.strip():
                logger.warning("ExifTool returned empty comprehensive metadata")
                return "No metadata found"

            return output.strip()

        except Exception as e:
            logger.error(f"Error getting comprehensive metadata: {str(e)}")
            return f"Error reading metadata: {str(e)}"
        finally:
            # Clean up the argument file (same as batch operations)
            if os.path.exists(arg_file_path):
                os.remove(arg_file_path)
    def __del__(self):
        """Ensure the process is terminated when the object is deleted"""
        self.stop()