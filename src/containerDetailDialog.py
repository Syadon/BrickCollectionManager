from PySide6.QtWidgets import (QDialog, QTableWidget, QTableWidgetItem, QComboBox, 
                             QPushButton, QVBoxLayout, QHBoxLayout, QLabel, 
                             QDialogButtonBox, QMessageBox, QRadioButton, 
                             QGroupBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QBrush, QPixmap
from src.database import DatabaseManager
from src.partDetailDialog import PartDetailDialog
from src.imageProvider import ImagesProvider
from src.widgets.colorLabel import ColorLabel
from ui.ui_containerDetailDialog import Ui_containerDetailDialog
from config import AppConfig


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
        self.delete_button.setProperty('class', 'danger')
        
        # Add button to the bottom layout by inserting before buttonBox
        main_layout = self.ui.verticalLayout
        
        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()  # Add stretch to push buttonBox to the right
        button_layout.addWidget(self.ui.buttonBox)
        
        # Remove buttonBox from main layout and add the new button layout
        main_layout.removeWidget(self.ui.buttonBox)
        main_layout.addLayout(button_layout)
        
        # Connect delete button
        self.delete_button.clicked.connect(self.on_delete_clicked)

        # Setup parts table
        self.setup_parts_table()
        
        # Set dialog size based on parent window if available
        if self.parent_widget:
            parent_size = self.parent_widget.size()
            dialog_width = int(parent_size.width() * 0.9)
            dialog_height = int(parent_size.height() * 0.9)
            self.resize(dialog_width, dialog_height)
        else:
            # Default size if no parent
            self.resize(800, 600)

    def setup_parts_table(self):
        dbManager = DatabaseManager()
        self.dbManager = dbManager  # Store for later use

        self.parts_data = dbManager.getContainersParts(self.container.id)
        
        # Initialize image provider
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self._update_image)

        # Setup table headers
        headers = ["Image", "ID", "Part", "Category", "Color", "Color Type", "Quantity"]
        self.ui.partsView.setColumnCount(len(headers))
        self.ui.partsView.setHorizontalHeaderLabels(headers)
        
        # Set row count
        self.ui.partsView.setRowCount(len(self.parts_data))
        
        # Configure table widget
        self.ui.partsView.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ui.partsView.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Set row height for images (64px)
        self.ui.partsView.verticalHeader().setDefaultSectionSize(70)
        
        # Hide vertical header
        self.ui.partsView.verticalHeader().setVisible(False)
        
        # Set image column width
        self.ui.partsView.setColumnWidth(0, 70)  # Image column
        
        # Populate table with data
        self.populate_table_data()
        
        # Resize columns to content
        self.ui.partsView.resizeColumnsToContents()
        
        
        # Limit Name column width
        name_column_index = 2
        max_name_width = 400
        if self.ui.partsView.columnWidth(name_column_index) > max_name_width:
            self.ui.partsView.setColumnWidth(name_column_index, max_name_width)
        
        self.ui.partsView.setWordWrap(True)
        self.ui.partsView.resizeRowsToContents()
        self.ui.partsView.horizontalHeader().setStretchLastSection(True)
        
        # Connect double-click signal
        self.ui.partsView.cellDoubleClicked.connect(self.on_part_double_clicked)

    def populate_table_data(self):
        """Populate the table widget with parts data"""
        for row, part in enumerate(self.parts_data):
            # Image column (0)
            image_item = QTableWidgetItem()
            image_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            
            # Try to get image
            if hasattr(part, 'color_id') and hasattr(part, 'part_id'):
                image = self.imgProvider.get_part_image(part.part_id, part.color_id)
                if image is not None:
                    scaled_image = image.scaled(QSize(64, 64), 
                                              Qt.AspectRatioMode.KeepAspectRatio, 
                                              Qt.TransformationMode.SmoothTransformation)
                    image_item.setData(Qt.ItemDataRole.DecorationRole, scaled_image)
            
            self.ui.partsView.setItem(row, 0, image_item)
            
            # ID column (1)
            id_item = QTableWidgetItem(str(part.part_id))
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 1, id_item)
            
            # Part name column (2)
            name_item = QTableWidgetItem(part.part_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 2, name_item)
            
            # Category column (3)
            category_item = QTableWidgetItem(part.part_category)
            category_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 3, category_item)
            
            # Color column (4) - using ColorLabel widget
            rgb_hex = part.rgb if hasattr(part, 'rgb') else None
            color_id = part.color_id if hasattr(part, 'color_id') else None
            color_label = ColorLabel(part.color_name, rgb_hex, part.color_type, color_id)
            
            self.ui.partsView.setCellWidget(row, 4, color_label)
            
            # Color type column (5)
            color_type_item = QTableWidgetItem(part.color_type)
            color_type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 5, color_type_item)
            
            # Quantity column (6)
            quantity_item = QTableWidgetItem(str(part.quantity))
            quantity_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 6, quantity_item)

    def _update_image(self, key, pixmap):
        """Update image in table when it's loaded asynchronously"""
        part_id, color_id = key.split('_')
        
        # Find all rows with this part_id and color_id
        for row in range(self.ui.partsView.rowCount()):
            part = self.parts_data[row]
            if (part.part_id == part_id and str(part.color_id) == color_id):
                # Update the image in the table
                image_item = self.ui.partsView.item(row, 0)
                if image_item:
                    scaled_image = pixmap.scaled(QSize(64, 64), 
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
                    image_item.setData(Qt.ItemDataRole.DecorationRole, scaled_image)

    def on_part_double_clicked(self, row, column):
        """Handle double-click on a part row"""
        if row < len(self.parts_data):
            part_data = self.parts_data[row]
            dialog = PartDetailDialog(part_data, self.container, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the parts list
                self.refresh_parts_table()
            
    def refresh_parts_table(self):
        """Refresh the parts table with updated data"""
        self.parts_data = self.dbManager.getContainersParts(self.container.id)
        
        # Clear and repopulate table
        self.ui.partsView.setRowCount(len(self.parts_data))
        self.populate_table_data()
        
        # Update counts
        self.ui.part_count_label.setText(str(self.dbManager.getConteinerPartCount(self.container.id)))
        self.ui.lots_count_label.setText(str(self.dbManager.getConteinerLotCount(self.container.id)))
        
        # Resize columns to content
        self.ui.partsView.resizeColumnsToContents()
        
        # Limit Name column width
        name_column_index = 2
        max_name_width = 400
        if self.ui.partsView.columnWidth(name_column_index) > max_name_width:
            self.ui.partsView.setColumnWidth(name_column_index, max_name_width)
        
        self.ui.partsView.setWordWrap(True)
        self.ui.partsView.resizeRowsToContents()
        self.ui.partsView.horizontalHeader().setStretchLastSection(True)

    def on_delete_clicked(self):
        """Handle delete container button click"""
        # Check if container has parts
        if self.container.part_count > 0:
            # Show confirm dialog with options
            dialog = DeleteContainerDialog(self.container, self)
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted:
                # Container was deleted
                QMessageBox.information(self, "Success", f"Container '{self.container.name}' deleted successfully")
                self.accept()  # Close this dialog too
        else:
            # Just confirm deletion
            reply = QMessageBox.question(
                self, 
                "Confirm Deletion", 
                f"Are you sure you want to delete container '{self.container.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
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
        delete_warning.setProperty('class', 'danger')

        delete_warning.setWordWrap(True)
        container_layout = QHBoxLayout()
        container_layout.addSpacing(20)  # Indent
        container_layout.addWidget(delete_warning)
        options_layout.addLayout(container_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Delete container and all parts
                    if self.db_manager.deleteContainerWithParts(self.container.id):
                        super().accept()
                    else:
                        QMessageBox.critical(self, "Error", "Failed to delete container and parts")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

