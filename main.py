import os
import sys

from PySide6.QtCore import QFile
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox
from qt_material import apply_stylesheet

import resources_rc as resources_rc  # Importa il file delle risorse generato
from config import AppConfig
from src.database import DatabaseManager
from src.logger import get_logger, log_exception, setup_exception_hook
from src.mainWindow import MainWindow


def setup_window_geometry(app: QApplication, window: MainWindow):
    """Set optimal window size and center it on screen"""
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()
    screen_width = screen_geometry.width()
    screen_height = screen_geometry.height()

    # Set window size to 80% of screen dimensions for optimal viewing
    optimal_width = int(screen_width * 0.8)
    optimal_height = int(screen_height * 0.8)

    window.resize(optimal_width, optimal_height)

    # Center the window on screen
    window.move(
        (screen_width - optimal_width) // 2, (screen_height - optimal_height) // 2
    )


def main():
    # Setup logging system
    setup_exception_hook()
    logger = get_logger()

    try:
        logger.info("Starting application")

        # Create the application
        app = QApplication(sys.argv)

        # Initialize application configuration
        logger.info("Initializing application configuration")
        AppConfig.initialize()

        app.setApplicationName(AppConfig.APP_NAME)
        app.setApplicationVersion(AppConfig.APP_VERSION)
        app.setOrganizationName(AppConfig.ORGANIZATION_NAME)
        logger.info(f"Application: {AppConfig.APP_NAME} v{AppConfig.APP_VERSION}")

        # Set application icon from resources
        logger.debug("Loading application icon")
        app_icon = QIcon(":/icons/app_icon.png")
        app.setWindowIcon(app_icon)

        # Check if placeholder icon exists in resources
        placeholder = QPixmap(":/images/app_icon.png")
        if placeholder.isNull():
            logger.warning("app_icon.png not found in resources")

        # Initialize database
        logger.info("Initializing database")
        db_manager = DatabaseManager()
        if not db_manager.initialize_database():
            logger.critical("Failed to initialize database")
            _ = QMessageBox.critical(
                None,
                "Database Error",
                "Could not initialize the database. The application will now exit.",
            )
            sys.exit(1)
        logger.info("Database initialized successfully")

        logger.info("Applying theme and stylesheet")
        extra = {
            # Button colors
            "danger": "#dc3545",
            "warning": "#ffc107",
            "success": "#17a2b8",
            # Font
            # 'font_family': 'Roboto',
            # 'font_size': '12',     # Adjust font size as needed
            "density_scale": "0",  # Adjust density scale as needed
        }
        apply_stylesheet(app, theme="dark_blue.xml", extra=extra)

        stylesheet = app.styleSheet()
        style_from_resources = QFile(":/styles/custom.css")
        if style_from_resources.open(
            QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text
        ):
            styleStr = bytearray(style_from_resources.readAll().data()).decode("utf-8")
            app.setStyleSheet(stylesheet + styleStr.format(**os.environ))
            style_from_resources.close()
            logger.debug("Custom stylesheet loaded successfully")
        else:
            logger.warning("Failed to load custom stylesheet")

        # with open('resources/custom.css') as file:
        #     app.setStyleSheet(stylesheet + file.read().format(**os.environ))

        # Create and show main window
        logger.info("Creating main window")
        window = MainWindow()
        window.show()

        setup_window_geometry(app, window)
        logger.info("Main window displayed")

        # Start the event loop
        logger.info("Starting event loop")
        exit_code = app.exec()

        # Cleanup
        logger.info("Application shutting down")
        db_manager.close_connection()
        logger.info("Database connection closed")
        logger.info("=" * 70)
        sys.exit(exit_code)
    except Exception as e:
        log_exception(e, "Fatal error during application startup")
        _ = QMessageBox.critical(
            None,
            "Application Error",
            f"An unexpected error occurred: {e}\nThe application will now exit.\n\nCheck logs for details.",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
