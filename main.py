from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QFile
from src.mainWindow import MainWindow
from config import AppConfig
from src.database import DatabaseManager
import sys
import resources_rc as resources_rc  # Importa il file delle risorse generato
import os

from qt_material import apply_stylesheet

def main():
    # Initialize application configuration
    AppConfig.initialize()
    
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setOrganizationName(AppConfig.ORGANIZATION_NAME)
    
    # Set application icon from resources
    app_icon = QIcon(":/icons/app_icon.png")
    app.setWindowIcon(app_icon)
    
    # Check if placeholder icon exists in resources
    placeholder = QPixmap(":/images/placeholder_icon.png")
    if placeholder.isNull():
        print("Warning: placeholder_icon.png not found in resources")
    
    # Initialize database
    db_manager = DatabaseManager()
    if not db_manager.initialize_database():
        QMessageBox.critical(None, "Database Error", 
                           "Could not initialize the database. The application will now exit.")
        sys.exit(1)
    
    extra = {
        # Button colors
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#17a2b8',

        # Font
        # 'font_family': 'Roboto',
        # 'font_size': '12',     # Adjust font size as needed

        'density_scale': '0',  # Adjust density scale as needed
    }
    apply_stylesheet(app, theme='dark_blue.xml', extra=extra)
    
    stylesheet = app.styleSheet()
    style_from_resources = QFile(":/styles/custom.css")
    if style_from_resources.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        styleStr = bytearray(style_from_resources.readAll().data()).decode('utf-8')
        app.setStyleSheet(stylesheet + styleStr.format(**os.environ))
        style_from_resources.close()

    # with open('resources/custom.css') as file:
    #     app.setStyleSheet(stylesheet + file.read().format(**os.environ))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start the event loop
    exit_code = app.exec()
    
    # Cleanup
    db_manager.close_connection()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
