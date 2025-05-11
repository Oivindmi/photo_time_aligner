import sys
import traceback
import logging
from PyQt5.QtWidgets import QApplication, QMessageBox
from src.core import ConfigManager, ExifHandler
from src.ui import MainWindow
from src.utils import ExifToolNotFoundError

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG to see detailed logging and debug information
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('photo_time_aligner.log')
    ]
)
logger = logging.getLogger(__name__)


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


if __name__ == "__main__":
    main()