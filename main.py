from PySide6.QtWidgets import QApplication, QMessageBox
from mainWindow import MainWindow
from config import AppConfig
from database import DatabaseManager
import sys

def main():
    # Initialize application configuration
    AppConfig.initialize()
    
    # Create the application
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setOrganizationName(AppConfig.ORGANIZATION_NAME)
    
    # Initialize database
    db_manager = DatabaseManager()
    if not db_manager.initialize_database():
        QMessageBox.critical(None, "Database Error", 
                           "Could not initialize the database. The application will now exit.")
        sys.exit(1)
    
    # Set application style sheet
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
