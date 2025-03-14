from PySide6.QtWidgets import QMainWindow, QWidget, QMenuBar, QStatusBar
from PySide6.QtCore import Qt
from ui.ui_mainwindow import Ui_MainWindow
from config import AppConfig

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create and setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Configure window
        self.setWindowTitle(AppConfig.WINDOW_TITLE)
        self.resize(AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)

