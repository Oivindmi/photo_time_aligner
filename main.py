import sys
import traceback
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from src.core import ConfigManager, ExifHandler
from src.ui import MainWindow
from src.utils import ExifToolNotFoundError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('photo_time_aligner.log', encoding='utf-8')  # Add encoding
    ]
)
logger = logging.getLogger(__name__)

# Test imports at the top of main.py
try:
    from src.core import CorruptionDetector, FileRepairer
    from src.ui import RepairDecisionDialog
    print("✅ Repair functionality imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")

def main():
    app = QApplication(sys.argv)

    try:
        logger.info("Starting Photo Time Aligner application")

        # Initialize core components
        config_manager = ConfigManager()
        exif_handler = ExifHandler()

        logger.info(f"ExifTool found at: {exif_handler.exiftool_path}")

        # Create and show main window
        main_window = MainWindow(config_manager, exif_handler)
        main_window.show()

        # Set up cleanup handler
        app.aboutToQuit.connect(lambda: cleanup(exif_handler))

    except ExifToolNotFoundError as e:
        logger.error(f"ExifTool not found: {str(e)}")
        QMessageBox.critical(
            None,
            "ExifTool Not Found",
            str(e)
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        QMessageBox.critical(
            None,
            "Error",
            f"An unexpected error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        )
        sys.exit(1)

    sys.exit(app.exec_())

def cleanup(exif_handler):
    """Clean up resources before application exit"""
    logger.info("Performing application cleanup")
    try:
        # Stop the ExifTool process
        if hasattr(exif_handler, 'exiftool_process'):
            exif_handler.exiftool_process.stop()
            logger.info("ExifTool process stopped")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


if __name__ == "__main__":
    main()