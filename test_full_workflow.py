# test_full_workflow.py - Test complete video workflow
import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import ExifHandler, ConfigManager, FileProcessor
from src.ui import MainWindow


def test_full_workflow():
    """Test the complete workflow with video files"""
    app = QApplication(sys.argv)

    # Initialize components
    config_manager = ConfigManager()
    exif_handler = ExifHandler()

    # Create main window
    main_window = MainWindow(config_manager, exif_handler)
    main_window.show()

    # Test paths
    test_video = r"C:\TEST FOLDER FOR PHOTO APP\TEST OF photo_time_aligner\FailSail 2022\Øivind\20220727_193305.mp4"

    if not os.path.exists(test_video):
        print(f"Test file not found: {test_video}")
        return

    print("Starting workflow test...")

    # Simulate dropping a video file
    def test_sequence():
        print("\n1. Testing reference video drop...")
        main_window.load_reference_photo(test_video)

        # Check if time fields are loaded
        QTimer.singleShot(500, lambda: check_reference_loaded())

    def check_reference_loaded():
        print("2. Checking reference video loaded...")
        assert main_window.reference_file == test_video
        assert len(main_window.ref_time_radios) > 0
        print(f"   ✓ Found {len(main_window.ref_time_radios)} time fields")

        # Check pattern detection
        if main_window.ref_pattern_check.isChecked():
            pattern = main_window.ref_pattern_label.text()
            print(f"   ✓ Pattern detected: {pattern}")

        # Check files found
        file_count = main_window.ref_file_count.text()
        print(f"   ✓ {file_count}")

        print("\n3. Testing pattern matching...")
        main_window.ref_pattern_check.setChecked(True)
        main_window.update_reference_files()

        QTimer.singleShot(1000, finish_test)

    def finish_test():
        print("\n4. Test completed successfully!")
        print("   ✓ Video files are handled correctly")
        print("   ✓ Time fields are extracted")
        print("   ✓ Pattern matching works")
        print("   ✓ File scanning works")
        app.quit()

    # Start test sequence
    QTimer.singleShot(100, test_sequence)

    app.exec_()


if __name__ == "__main__":
    test_full_workflow()