"""
Media file generator for creating test files programmatically.

This module provides utilities to:
- Create synthetic test media files
- Generate files with specific metadata
- Create corrupted file samples
- Generate batch test files
"""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import subprocess


class MediaGenerator:
    """Generate test media files for testing."""

    def __init__(self, output_dir: Path):
        """
        Initialize media generator.

        Args:
            output_dir: Directory to create generated files in
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_minimal_jpeg(file_path: Path) -> bool:
        """
        Create a minimal valid JPEG file.

        Args:
            file_path: Path where JPEG should be created

        Returns:
            bool: True if successful, False otherwise

        Note:
            Creates a valid but empty JPEG using PIL if available,
            otherwise creates a minimal JPEG structure.
        """
        try:
            from PIL import Image

            # Create a minimal image (1x1 pixel)
            img = Image.new("RGB", (1, 1), color="white")
            img.save(file_path, "JPEG")
            return True

        except ImportError:
            # Fallback: Create minimal JPEG structure
            # This is a valid JPEG header and minimal structure
            minimal_jpeg = bytes([
                0xFF, 0xD8,  # Start of Image
                0xFF, 0xE0,  # APP0 marker
                0x00, 0x10,  # Length
                0x4A, 0x46, 0x49, 0x46, 0x00,  # JFIF
                0x01, 0x01,  # Version
                0x00,  # Units
                0x00, 0x01, 0x00, 0x01,  # X, Y density
                0x00, 0x00,  # Thumbnail dimensions
                0xFF, 0xDB,  # DQT marker
                0x00, 0x43,  # Length
                0x00,  # Precision and table
                # Quantization table (64 bytes)
                0x10, 0x0B, 0x0C, 0x0E, 0x0C, 0x0A, 0x10, 0x0E,
                0x0D, 0x0E, 0x12, 0x11, 0x10, 0x13, 0x18, 0x28,
                0x1A, 0x18, 0x16, 0x16, 0x18, 0x31, 0x23, 0x25,
                0x1D, 0x28, 0x3A, 0x33, 0x3D, 0x3C, 0x39, 0x33,
                0x38, 0x37, 0x40, 0x48, 0x5C, 0x4E, 0x40, 0x44,
                0x57, 0x45, 0x37, 0x38, 0x50, 0x6D, 0x51, 0x57,
                0x5F, 0x62, 0x67, 0x68, 0x67, 0x3E, 0x4D, 0x71,
                0x79, 0x70, 0x64, 0x78, 0x5C, 0x65, 0x67, 0x63,
                0xFF, 0xC0,  # SOF0 marker
                0x00, 0x0B,  # Length
                0x08,  # Precision
                0x00, 0x01, 0x00, 0x01,  # Height, Width
                0x01,  # Components
                0x01, 0x11, 0x00,  # Component info
                0xFF, 0xC4,  # DHT marker
                0x00, 0x1F,  # Length
                0x00,  # Table class and destination
                # Huffman table
                0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01,
                0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                0x08, 0x09, 0x0A, 0x0B,
                0xFF, 0xDA,  # SOS marker
                0x00, 0x08,  # Length
                0x01,  # Components
                0x01, 0x00,  # Component selector
                0x00, 0x3F, 0x00,  # Start/end spectral
                0x7F,  # Scan data
                0xFF, 0xD9,  # End of Image
            ])

            with open(file_path, "wb") as f:
                f.write(minimal_jpeg)

            return True

    def create_jpeg_with_metadata(
        self,
        file_path: Path,
        create_date: Optional[datetime] = None,
        model: str = "Test Camera",
        make: str = "Test"
    ) -> bool:
        """
        Create a JPEG file with metadata.

        Args:
            file_path: Path where JPEG should be created
            create_date: Creation date for the file
            model: Camera model string
            make: Camera make string

        Returns:
            bool: True if successful, False otherwise
        """
        # First create a minimal JPEG
        if not self.create_minimal_jpeg(file_path):
            return False

        # Add metadata using exiftool if available
        try:
            args = ["exiftool", "-overwrite_original"]

            if create_date:
                date_str = create_date.strftime("%Y:%m:%d %H:%M:%S")
                args.extend(["-DateTimeOriginal=" + date_str,
                            "-CreateDate=" + date_str])

            if model:
                args.append(f"-Model={model}")
            if make:
                args.append(f"-Make={make}")

            args.append(str(file_path))

            subprocess.run(args, capture_output=True, timeout=5, check=True)
            return True

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # ExifTool not available or failed, but JPEG was created
            return True

    def create_corrupted_exif(self, file_path: Path) -> bool:
        """
        Create a JPEG with corrupted EXIF structure.

        Args:
            file_path: Path where file should be created

        Returns:
            bool: True if successful
        """
        # Create a valid JPEG first
        if not self.create_minimal_jpeg(file_path):
            return False

        # Try to corrupt EXIF using exiftool
        try:
            # This will fail on purpose to create invalid EXIF
            subprocess.run(
                ["exiftool", "-DateTimeOriginal=invalid_date", "-overwrite_original", str(file_path)],
                capture_output=True,
                timeout=5
            )
            return True

        except (FileNotFoundError, subprocess.TimeoutExpired):
            return True

    def create_batch_photos(
        self,
        count: int,
        base_dir: Path,
        camera_model: str = "TestCamera",
        base_date: Optional[datetime] = None
    ) -> List[Path]:
        """
        Create a batch of test photos with varying metadata.

        Args:
            count: Number of photos to create
            base_dir: Directory to create photos in
            camera_model: Camera model string
            base_date: Starting date (will increment for each photo)

        Returns:
            List[Path]: Paths to created photo files
        """
        base_dir.mkdir(parents=True, exist_ok=True)

        if base_date is None:
            base_date = datetime(2023, 12, 25, 10, 0, 0)

        created_files = []

        for i in range(count):
            file_path = base_dir / f"photo_{i:04d}.jpg"

            # Increment date for each photo (1 second apart)
            photo_date = base_date + timedelta(seconds=i)

            if self.create_jpeg_with_metadata(
                file_path,
                create_date=photo_date,
                model=camera_model,
                make="Test"
            ):
                created_files.append(file_path)

        return created_files

    def create_multi_camera_batch(
        self,
        base_dir: Path,
        cameras: dict,
        count_per_camera: int = 10
    ) -> dict:
        """
        Create batch photos from multiple cameras with different times.

        Args:
            base_dir: Directory to create photos in
            cameras: Dict of {camera_name: time_offset_seconds}
            count_per_camera: Photos to create per camera

        Returns:
            dict: {camera_name: [list of file paths]}

        Example:
            gen.create_multi_camera_batch(
                temp_dir,
                {"Camera A": 0, "Camera B": 30}  # B is 30s behind
            )
        """
        base_dir.mkdir(parents=True, exist_ok=True)
        result = {}

        base_time = datetime(2023, 12, 25, 10, 0, 0)

        for camera_name, time_offset in cameras.items():
            camera_dir = base_dir / camera_name.replace(" ", "_")
            camera_dir.mkdir(exist_ok=True)

            start_time = base_time + timedelta(seconds=time_offset)

            files = self.create_batch_photos(
                count_per_camera,
                camera_dir,
                camera_model=camera_name,
                base_date=start_time
            )

            result[camera_name] = files

        return result

    def copy_and_rename(self, source: Path, dest: Path, new_name: str) -> Path:
        """
        Copy a file to a new location with a new name.

        Args:
            source: Source file path
            dest: Destination directory
            new_name: New filename

        Returns:
            Path: Path to copied file
        """
        dest.mkdir(parents=True, exist_ok=True)
        dest_file = dest / new_name
        shutil.copy2(source, dest_file)
        return dest_file


class BulkMediaGenerator:
    """Generate large quantities of test media for performance testing."""

    @staticmethod
    def generate_batch_for_performance_test(
        output_dir: Path,
        sizes: List[int] = None
    ) -> dict:
        """
        Generate media batches of various sizes for performance testing.

        Args:
            output_dir: Where to create test files
            sizes: List of batch sizes (default: [50, 200, 500])

        Returns:
            dict: {size: [list of file paths]}

        Example:
            batches = BulkMediaGenerator.generate_batch_for_performance_test(
                Path("tests/fixtures/sample_media/batch_test_base"),
                sizes=[50, 200, 500]
            )
        """
        if sizes is None:
            sizes = [50, 200, 500]

        result = {}
        gen = MediaGenerator(output_dir)

        for size in sizes:
            batch_dir = output_dir / f"batch_{size}"
            batch_dir.mkdir(parents=True, exist_ok=True)

            files = gen.create_batch_photos(
                size,
                batch_dir,
                camera_model=f"BatchTest_{size}",
                base_date=datetime(2023, 12, 25, 10, 0, 0)
            )

            result[size] = files

        return result
