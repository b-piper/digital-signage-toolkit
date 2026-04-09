#!/usr/bin/env python3
"""Main entry point for Digital Signage Toolkit."""
import os
import sys

# Check if running on Linux
if sys.platform != 'linux':
    print("Warning: This application is designed for Linux systems.")
    print("Some features may not work correctly on other platforms.")

from PyQt6.QtWidgets import QApplication

from digital_signage_toolkit.gui.main_window import MainWindow


def main():
    """Main application entry point."""
    # Initialize logging
    from digital_signage_toolkit.utils.logger import get_logger
    logger = get_logger()

    # Check if running on Linux
    if sys.platform != 'linux':
        logger.app_logger.warning("Warning: This application is designed for Linux systems.")
        logger.app_logger.warning("Some features may not work correctly on other platforms.")

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Digital Signage Toolkit")
    app.setOrganizationName("Southwestern CC")

    # Set dark theme style
    app.setStyle('Fusion')

    # Log application start
    logger.log_operation("APPLICATION_START", os.environ.get('USER', 'unknown'), "Application launched", True)

    # Create and show main window
    try:
        window = MainWindow()
        window.show()

        # Run application
        sys.exit(app.exec())
    except Exception as e:
        logger.log_error(e, "APPLICATION_START")
        raise


if __name__ == '__main__':
    main()

