"""
main.py
-------
Entry point for the F&O UDIFF Bhavcopy Analyzer desktop application.

Run with:
    python main.py
"""

import sys

from PySide6.QtWidgets import QApplication

from utils.logger_setup import setup_logger
from gui.main_window import MainWindow


def main() -> None:
    logger = setup_logger()
    logger.info("Starting F&O UDIFF Bhavcopy Analyzer")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    logger.info("Application exited with code %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
