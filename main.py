from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from mainWindow import MainWindow
from config import AppConfig
from database import DatabaseManager
import sys
import resources_rc  # Importa il file delle risorse generato

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
    
    # Set application style sheet from resources
    style_from_resources = """QResource(":/styles/style.qss")"""
    if style_from_resources:
        app.setStyleSheet(style_from_resources)
    else:
        # Fallback to file-based stylesheet
        app.setStyleSheet(AppConfig.load_stylesheet())
    
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
