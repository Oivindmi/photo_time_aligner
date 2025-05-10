import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from src.core import ConfigManager, ExifHandler
from src.ui import MainWindow
from src.utils import ExifToolNotFoundError


def main():
    app = QApplication(sys.argv)

    try:
        # Initialize core components
        config_manager = ConfigManager()
        exif_handler = ExifHandler()

        # Create and show main window
        main_window = MainWindow(config_manager, exif_handler)
        main_window.show()

    except ExifToolNotFoundError as e:
        QMessageBox.critical(
            None,
            "ExifTool Not Found",
            str(e)
        )
        sys.exit(1)
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error",
            f"An unexpected error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        )
        sys.exit(1)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()