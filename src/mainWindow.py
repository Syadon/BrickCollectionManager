from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QToolBar, QStackedLayout, QDialog, QPushButton, QMessageBox, QStatusBar)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QDesktopServices
from src.widgets import (ContainerListWidget, SearchManualWidget, AddManualWidget,
                        AddFromCameraWidget, AddFromFileWidget, DatabaseWidget)
from config import AppConfig
from src.logger import get_logger, get_log_file_path, get_log_dir
import resources_rc

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.logger.info("Initializing MainWindow")
        
        self.setWindowTitle("Brick Collection Manager")
        self.setMinimumSize(1200, 700)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create left toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Orientation.Vertical)
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        
        main_layout.addWidget(self.toolbar)

        # Create stacked layout for different pages
        self.stack_layout = QStackedLayout()
        main_layout.addLayout(self.stack_layout)
        main_layout.setStretch(1, 1)  # Make the stacked layout take more space

        # Create all widgets
        self.container_list = ContainerListWidget()
        self.search_widget = SearchManualWidget()
        self.add_manual_widget = AddManualWidget()
        self.add_camera_widget = AddFromCameraWidget()
        self.add_file_widget = AddFromFileWidget()
        self.database_widget = DatabaseWidget()

        # Add widgets to stack
        self.stack_layout.addWidget(self.container_list)
        self.stack_layout.addWidget(self.search_widget)
        self.stack_layout.addWidget(self.add_manual_widget)
        self.stack_layout.addWidget(self.add_camera_widget)
        self.stack_layout.addWidget(self.add_file_widget)
        self.stack_layout.addWidget(self.database_widget)

        # Create toolbar actions
        self.setup_toolbar()
        
        # Setup menu bar
        self.setup_menu_bar()
        
        # Setup status bar
        self.setup_status_bar()

    def setup_toolbar(self):
        # Containers action
        containers_action = QAction(QIcon(":/icons/container.png"), "Containers", self)
        containers_action.setCheckable(True)
        containers_action.triggered.connect(lambda: self.switch_page(0))
        self.toolbar.addAction(containers_action)

        # Search action
        search_action = QAction(QIcon(":/icons/search.png"), "Search Parts", self)
        search_action.setCheckable(True)
        search_action.triggered.connect(lambda: self.switch_page(1))
        self.toolbar.addAction(search_action)

        # Add Manual action
        add_manual_action = QAction(QIcon(":/icons/addManually.png"), "Add Manually", self)
        add_manual_action.setCheckable(True)
        add_manual_action.triggered.connect(lambda: self.switch_page(2))
        self.toolbar.addAction(add_manual_action)

        # Add Camera action
        add_camera_action = QAction(QIcon(":/icons/addCamera.png"), "Add From Camera", self)
        add_camera_action.setCheckable(True)
        add_camera_action.triggered.connect(lambda: self.switch_page(3))
        self.toolbar.addAction(add_camera_action)

        # Add File action
        add_file_action = QAction(QIcon(":/icons/addFile.png"), "Add From File", self)
        add_file_action.setCheckable(True)
        add_file_action.triggered.connect(lambda: self.switch_page(4))
        self.toolbar.addAction(add_file_action)

        # Add separator before database action
        #self.toolbar.addSeparator()

        # Database action
        database_action = QAction(QIcon(":/icons/database.png"), "Database", self)
        database_action.setCheckable(True)
        database_action.triggered.connect(lambda: self.switch_page(5))
        self.toolbar.addAction(database_action)

        # Set containers as default selected
        containers_action.setChecked(True)
        self.toolbar.actions()[0].setChecked(True)

    def setup_menu_bar(self):
        """Setup the menu bar with Help menu"""
        menubar = self.menuBar()
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # Open logs folder action
        open_logs_action = QAction("Open Logs Folder", self)
        open_logs_action.triggered.connect(self.open_logs_folder)
        help_menu.addAction(open_logs_action)
        
        # View log file action
        view_log_action = QAction("View Log File", self)
        view_log_action.triggered.connect(self.view_log_file)
        help_menu.addAction(view_log_action)
        
        help_menu.addSeparator()
        
        # About action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def open_logs_folder(self):
        """Open the logs folder in the system file manager"""
        try:
            log_dir = get_log_dir()
            self.logger.info(f"Opening logs folder: {log_dir}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_dir)))
        except Exception as e:
            self.logger.error(f"Failed to open logs folder: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to open logs folder:\n{e}")
    
    def view_log_file(self):
        """Open the current log file in the default text editor"""
        try:
            log_file = get_log_file_path()
            self.logger.info(f"Opening log file: {log_file}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_file)))
        except Exception as e:
            self.logger.error(f"Failed to open log file: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to open log file:\n{e}")
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
        <h2>{AppConfig.APP_NAME}</h2>
        <p>Version: {AppConfig.APP_VERSION}</p>
        <p>A comprehensive tool for managing your LEGO brick collection.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Organize bricks in containers</li>
            <li>Search and filter your collection</li>
            <li>Import from BrickLink XML files</li>
            <li>Camera-based brick recognition</li>
            <li>Database management tools</li>
        </ul>
        <p>Logs are stored in: {get_log_dir()}</p>
        """
        QMessageBox.about(self, "About", about_text)

    def setup_status_bar(self):
        """Setup the status bar with app version"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Display app version
        version_text = f"{getattr(AppConfig, 'APP_NAME', '0.0.0')} v{getattr(AppConfig, 'APP_VERSION', '0.0.0')}"
        status_bar.showMessage(version_text)

    def switch_page(self, index):
        page_names = ["Containers", "Search Parts", "Add Manually", "Add From Camera", "Add From File", "Database"]
        page_name = page_names[index] if index < len(page_names) else f"Page {index}"
        self.logger.debug(f"Switching to page: {page_name} (index: {index})")
        
        # Uncheck all actions except the selected one
        for i, action in enumerate(self.toolbar.actions()):
            if action.isCheckable():  # Only modify checkable actions
                action.setChecked(i == index)
        
        # Switch to the selected page
        self.stack_layout.setCurrentIndex(index)
