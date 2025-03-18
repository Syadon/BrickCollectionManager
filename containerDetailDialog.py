from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                              QTextEdit, QDialogButtonBox, QLabel)
from PySide6.QtCore import Qt
from database import DatabaseManager, Container

class ContainerDetailDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.setWindowTitle(f"Edit Container - {container.name}")
        self.setMinimumSize(400, 300)

        # Create layout
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Create widgets
        self.name_edit = QLineEdit(container.name)
        self.description_edit = QTextEdit(container.description)
        self.part_count_label = QLabel(str(container.part_count))

        # Add widgets to form
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Part Count:", self.part_count_label)

        # Create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Add layouts
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    def accept(self):
        db_manager = DatabaseManager()
        
        # Update container object
        self.container.name = self.name_edit.text()
        self.container.description = self.description_edit.toPlainText()
        
        # Save to database
        if db_manager.updateContainer(self.container):
            super().accept()