from PySide6.QtWidgets import QDialog
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from config import AppConfig

class AddBricksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create and setup UI
        self.ui = Ui_AddBricksDialog()
        self.ui.setupUi(self)
