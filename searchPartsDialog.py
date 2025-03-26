from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QComboBox, QPushButton, QTableWidget, 
                              QTableWidgetItem, QFormLayout, QGroupBox, 
                              QMessageBox, QCompleter, QSizePolicy, QDialogButtonBox)
from PySide6.QtGui import QColor, QIcon
from PySide6.QtCore import Qt, QStringListModel
from widgets.searchManualWidget import SearchManualWidget
from database import DatabaseManager
from utils import TransparentSelectionDelegate
from imageProvider import ImagesProvider
from config import AppConfig
from partDetailDialog import PartDetailDialog

class SearchPartsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Parts")
        self.setBaseSize(800, 600)
        
        self.searchWidget = SearchManualWidget()
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.searchWidget)
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.reject)  # Close button will close the dialog
        main_layout.addWidget(self.buttonBox)

        self.setLayout(main_layout)
