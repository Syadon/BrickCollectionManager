from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                              QTextEdit, QDialogButtonBox, QLabel, QTableView)
from PySide6.QtCore import Qt, QAbstractTableModel
from PySide6.QtSql import QSqlQuery
from containerPartsModel import ContainerPartsModel
from database import DatabaseManager, Container, ColorPart
from ui.ui_containerDetailDialog import Ui_containerDetailDialog

class ContainerDetailDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        
        # Create and setup UI
        self.ui = Ui_containerDetailDialog()
        self.ui.setupUi(self)

        self.container = container

        # Setup container info
        self.ui.name_edit.setText(container.name)
        self.ui.description_edit.setText(container.description)
        self.ui.part_count_label.setText(str(container.part_count))
        self.ui.lots_count_label.setText(str(container.lot_count))

        # Setup parts table
        self.setup_parts_table()

    def setup_parts_table(self):
        dbManager = DatabaseManager()

        parts_data = dbManager.getContainersParts(self.container.id)
        # Create and set model
        self.parts_model = ContainerPartsModel(parts_data)
        self.ui.partsView.setModel(self.parts_model)

        # Configure table view
        self.ui.partsView.horizontalHeader().setStretchLastSection(True)
        self.ui.partsView.setSelectionBehavior(QTableView.SelectRows)
        self.ui.partsView.setSelectionMode(QTableView.SingleSelection)
        self.ui.partsView.resizeColumnsToContents()

    def accept(self):
        db_manager = DatabaseManager()
        
        # Update container object
        self.container.name = self.ui.name_edit.text()
        self.container.description = self.ui.description_edit.toPlainText()
        
        # Save to database
        if db_manager.updateContainer(self.container):
            super().accept()
