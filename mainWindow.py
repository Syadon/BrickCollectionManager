from PySide6.QtWidgets import QMainWindow, QWidget, QMenuBar, QStatusBar
from PySide6.QtCore import Qt
from ui.ui_mainwindow import Ui_MainWindow
from addBricksDialog import AddBricksDialog
from addContainerDialog import AddContainerDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create and setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Connect button to dialog
        self.ui.addBricksButton.clicked.connect(self.openAddBricksDialog)
        self.ui.addNewContainerButton.clicked.connect(self.openAddContainerDialog)

    def openAddBricksDialog(self):
        dialog = AddBricksDialog(self)
        dialog.exec()

    def openAddContainerDialog(self):
        dialog = AddContainerDialog(self)
        dialog.exec()
