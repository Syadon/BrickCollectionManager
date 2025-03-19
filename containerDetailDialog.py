from PySide6.QtWidgets import (QDialog, QTableView, QHeaderView, QComboBox, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QLabel, 
                             QDialogButtonBox, QMessageBox, QRadioButton, 
                             QGroupBox, QFormLayout, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtSql import QSqlQuery
from containerPartsModel import ContainerPartsModel
from database import DatabaseManager
from utils import TransparentSelectionDelegate
from partDetailDialog import PartDetailDialog
from ui.ui_containerDetailDialog import Ui_containerDetailDialog

class ContainerDetailDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        
        # Create and setup UI
        self.ui = Ui_containerDetailDialog()
        self.ui.setupUi(self)

        self.container = container
        self.parent_widget = parent

        # Setup container info
        self.ui.name_edit.setText(container.name)
        self.ui.description_edit.setText(container.description)
        self.ui.part_count_label.setText(str(container.part_count))
        self.ui.lots_count_label.setText(str(container.lot_count))

        # Add delete button
        self.delete_button = QPushButton("Delete Container")
        self.delete_button.setStyleSheet("background-color: #e74c3c; color: white;")
        
        # Add button to the bottom left
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()  # Add stretch to push buttonBox to the right
        button_layout.addWidget(self.ui.buttonBox)
        
        # Replace the default button layout
        layout = self.layout()
        layout.removeWidget(self.ui.buttonBox)
        layout.addLayout(button_layout)
        
        # Connect delete button
        self.delete_button.clicked.connect(self.on_delete_clicked)

        # Setup parts table
        self.setup_parts_table()

    def setup_parts_table(self):
        dbManager = DatabaseManager()
        self.dbManager = dbManager  # Store for later use

        parts_data = dbManager.getContainersParts(self.container.id)
        
        # Create and set model
        self.parts_model = ContainerPartsModel(parts_data)
        self.ui.partsView.setModel(self.parts_model)
        
        # Configure table view
        self.ui.partsView.setSelectionBehavior(QTableView.SelectRows)
        self.ui.partsView.setSelectionMode(QTableView.SingleSelection)
        
        # Imposta l'altezza delle righe in base alle immagini (64px)
        self.ui.partsView.verticalHeader().setDefaultSectionSize(70)
        
        # Nascondi l'header verticale
        self.ui.partsView.verticalHeader().setVisible(False)
        
        # Imposta la larghezza della colonna immagine
        self.ui.partsView.setColumnWidth(0, 70)  # Colonna immagine
        
        # Impedisci che la colonna dell'immagine mostri lo sfondo di selezione        
        delegate = TransparentSelectionDelegate(self.ui.partsView)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.imageColumnIndex, delegate)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.colorColumnIndex, delegate)
        
        # Ridimensiona le altre colonne in base al contenuto
        self.ui.partsView.resizeColumnsToContents()
        
        # Connect double-click signal
        self.ui.partsView.doubleClicked.connect(self.on_part_double_clicked)

    def on_part_double_clicked(self, index):
        row_index = index.row()
        part_data = self.parts_model.parts_data[row_index]
        dialog = PartDetailDialog(part_data, self.container, self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh the parts list
            self.refresh_parts_table()
            
    def refresh_parts_table(self):
        parts_data = self.dbManager.getContainersParts(self.container.id)
        self.parts_model = ContainerPartsModel(parts_data)
        self.ui.partsView.setModel(self.parts_model)
        
        # Update counts
        self.ui.part_count_label.setText(str(self.dbManager.getConteinerPartCount(self.container.id)))
        self.ui.lots_count_label.setText(str(self.dbManager.getConteinerLotCount(self.container.id)))
        
        # Reapply delegate
        delegate = TransparentSelectionDelegate(self.ui.partsView)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.imageColumnIndex, delegate)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.colorColumnIndex, delegate)
        
        # Ridimensiona le colonne
        self.ui.partsView.resizeColumnsToContents()

    def on_delete_clicked(self):
        """Handle delete container button click"""
        # Check if container has parts
        if self.container.part_count > 0:
            # Show confirm dialog with options
            dialog = DeleteContainerDialog(self.container, self)
            result = dialog.exec()
            
            if result == QDialog.Accepted:
                # Container was deleted
                QMessageBox.information(self, "Success", f"Container '{self.container.name}' deleted successfully")
                self.accept()  # Close this dialog too
        else:
            # Just confirm deletion
            reply = QMessageBox.question(
                self, 
                "Confirm Deletion", 
                f"Are you sure you want to delete container '{self.container.name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                db_manager = DatabaseManager()
                if db_manager.deleteContainer(self.container.id):
                    QMessageBox.information(self, "Success", f"Container '{self.container.name}' deleted successfully")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete container")

    def accept(self):
        db_manager = DatabaseManager()
        
        # Update container object
        self.container.name = self.ui.name_edit.text()
        self.container.description = self.ui.description_edit.text()
        
        # Save to database
        if db_manager.updateContainer(self.container):
            super().accept()


class DeleteContainerDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.db_manager = DatabaseManager()
        
        self.setWindowTitle(f"Delete Container - {container.name}")
        self.resize(400, 250)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Warning message
        warning_label = QLabel(
            f"Container '{self.container.name}' contains {self.container.part_count} parts "
            f"in {self.container.lot_count} lots.\n\n"
            f"What would you like to do with these parts?"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        # Move to another container option
        self.move_radio = QRadioButton("Move parts to another container")
        self.move_radio.setChecked(True)
        self.move_radio.toggled.connect(self.on_option_toggled)
        options_layout.addWidget(self.move_radio)
        
        # Container selector
        container_layout = QHBoxLayout()
        container_layout.addSpacing(20)  # Indent
        container_layout.addWidget(QLabel("Target container:"))
        self.container_combo = QComboBox()
        self.populate_container_combo()
        container_layout.addWidget(self.container_combo)
        options_layout.addLayout(container_layout)
        
        # Delete entirely option
        self.delete_radio = QRadioButton("Delete parts permanently")
        self.delete_radio.toggled.connect(self.on_option_toggled)
        options_layout.addWidget(self.delete_radio)
        
        # Warning for delete option
        delete_warning = QLabel("Warning: This will permanently remove all parts from your collection!")
        delete_warning.setStyleSheet("color: #e74c3c; font-weight: bold;")
        delete_warning.setWordWrap(True)
        container_layout = QHBoxLayout()
        container_layout.addSpacing(20)  # Indent
        container_layout.addWidget(delete_warning)
        options_layout.addLayout(container_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set default state
        self.on_option_toggled()
        
    def populate_container_combo(self):
        """Populate the container combo box with all containers except current one"""
        containers = self.db_manager.getContainers()
        
        for container in containers:
            if container.id != self.container.id:
                self.container_combo.addItem(container.name, container.id)
                
        if self.container_combo.count() == 0:
            # Disable move option if no other containers
            self.move_radio.setEnabled(False)
            self.container_combo.setEnabled(False)
            self.delete_radio.setChecked(True)
            
    def on_option_toggled(self):
        """Enable/disable container combo based on selected option"""
        self.container_combo.setEnabled(self.move_radio.isChecked())
            
    def accept(self):
        """Process container deletion based on selected option"""
        try:
            if self.move_radio.isChecked():
                # Get target container
                target_id = self.container_combo.currentData()
                if target_id is None:
                    QMessageBox.warning(self, "No Target", "Please select a target container")
                    return
                
                # Move all parts to target container
                if self.db_manager.moveAllParts(self.container.id, target_id):
                    # Now delete the empty container
                    if self.db_manager.deleteContainer(self.container.id):
                        super().accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to delete container after moving parts")
                else:
                    QMessageBox.critical(self, "Error", "Failed to move parts to target container")
            else:
                # Confirm deletion of parts
                reply = QMessageBox.question(
                    self, 
                    "Confirm Deletion", 
                    "Are you sure you want to PERMANENTLY DELETE all parts in this container?\n\n"
                    "This action cannot be undone!",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Delete container and all parts
                    if self.db_manager.deleteContainerWithParts(self.container.id):
                        super().accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to delete container and parts")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

