from PySide6.QtWidgets import QDialog
from ui.ui_addcontainerdialog import Ui_AddContainerDialog
from database import DatabaseManager

class AddContainerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create and setup UI
        self.ui = Ui_AddContainerDialog()
        self.ui.setupUi(self)

        # # Connect the OK button to accept() slot
        # self.ui.buttonBox.accepted.connect(self.accept)
        # self.ui.buttonBox.rejected.connect(self.reject)

    def accept(self):
        self.addContainer()
        super().accept()

    def addContainer(self):
        dbManager = DatabaseManager()
        dbManager.addContainer(self.ui.nameEdit.text(), self.ui.descriptionEdit.text())