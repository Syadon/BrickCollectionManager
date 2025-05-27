from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QToolBar, QStackedLayout, QDialog, QPushButton, QMessageBox)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import Qt, QSize
from src.widgets import (ContainerListWidget, SearchManualWidget, AddManualWidget,
                        AddFromCameraWidget, AddFromFileWidget)
from src.updateDBDialog import UpdateDBDialog
from config import AppConfig
import resources_rc

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Brick Collection Manager")
        self.setMinimumSize(1024, 768)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create left toolbar
        self.toolbar = QToolBar()
        self.toolbar.setOrientation(Qt.Vertical)
        self.toolbar.setIconSize(QSize(32, 32))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
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

        # Add widgets to stack
        self.stack_layout.addWidget(self.container_list)
        self.stack_layout.addWidget(self.search_widget)
        self.stack_layout.addWidget(self.add_manual_widget)
        self.stack_layout.addWidget(self.add_camera_widget)
        self.stack_layout.addWidget(self.add_file_widget)

        # Create toolbar actions
        self.setup_toolbar()

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
        self.toolbar.addSeparator()

        # Database action
        database_action = QAction(QIcon(":/icons/database.png"), "Update Database", self)
        database_action.triggered.connect(self.open_update_db_dialog)
        self.toolbar.addAction(database_action)

        # Set containers as default selected
        containers_action.setChecked(True)
        self.toolbar.actions()[0].setChecked(True)

    def switch_page(self, index):
        # Uncheck all actions except the selected one
        for i, action in enumerate(self.toolbar.actions()):
            if action.isCheckable():  # Only modify checkable actions
                action.setChecked(i == index)
        
        # Switch to the selected page
        self.stack_layout.setCurrentIndex(index)

    def open_update_db_dialog(self):
        try:
            dialog = UpdateDBDialog(self)
            result = dialog.exec()
            
            # If database was updated, refresh all widgets
            if result == QDialog.Accepted:
                # Refresh container list
                self.container_list.update_view()
                
                # Show success message
                QMessageBox.information(self, "Database Update", 
                                     "Database has been successfully updated.")
        except Exception as e:
            QMessageBox.critical(self, "Database Update Error", 
                                 f"An error occurred while updating the database: {e}")

