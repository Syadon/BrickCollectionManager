from PySide6.QtWidgets import (QDialog, QMessageBox)
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtCore import Qt
from src.database import DatabaseManager
from src.imageProvider import ImagesProvider
from config import AppConfig
from ui.ui_detailPartDialog import Ui_DeatilPartDialog

class PartDetailDialog(QDialog):
    def __init__(self, part_data, container, qty = 1, outsideDefault = False, parent=None):
        super().__init__(parent)

        self.imgSize = 256
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)

        # Create and setup UI
        self.ui = Ui_DeatilPartDialog()
        self.ui.setupUi(self)

        self.part_data = part_data
        self.container = container

        self.imgProvider.image_loaded.connect(self.setup_image)
        
        self.setup_ui()

        self.ui.qtySpinBox.setValue(qty)
        self.ui.toOutsideRadioButton.setChecked(outsideDefault)
        
    def setup_ui(self):
        
        image = self.imgProvider.get_part_image(self.part_data['part_id'], self.part_data['color_id'])
        if image is not None:
            self.setup_image("", image)

        # Part ID and Name
        self.ui.idValLabel.setText(self.part_data['part_id'])
        self.ui.nameValLabel.setText(self.part_data['part_name'])
        self.ui.categoryValLabel.setText(self.part_data['part_category'])
        
        # Color information with colored background
        self.ui.colorValLabel.setText(self.part_data['color_name'])
        rgb = QColor(f"#{self.part_data['rgb']}")
        luminance = (0.299 * rgb.red() + 0.587 * rgb.green() + 0.114 * rgb.blue())
        
        # Set stylesheet for colored background
        self.ui.colorValLabel.setStyleSheet(
            f"background-color: #{self.part_data['rgb']}; "
            f"color: {'white' if luminance < 128 else 'black'}; "
            f"padding: 4px; border-radius: 4px;"
        )

        self.ui.colorTypeValLabel.setText(self.part_data['color_type'])

        self.ui.currentContainerValue.setText(self.container.name)
        
        # Current quantity
        self.current_quantity = self.part_data['quantity']
        self.ui.currentQtyValLabel.setText(str(self.current_quantity))
    
        self.ui.qtySpinBox.setRange(1, self.current_quantity)
        self.ui.qtySpinBox.setValue(1)

        self.ui.moveButton.clicked.connect(self.on_move_remove_clicked)
        self.ui.toContainerRadioButton.toggled.connect(self.ui.containerCombo.setEnabled)
        
        self.populate_container_combo()

    def setup_image(self, key, pixmap:QPixmap):
        sz = pixmap.size()
        if sz.width() > self.imgSize or sz.height() > self.imgSize:
            image = pixmap.scaled(self.imgSize, self.imgSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.ui.imageLabel.setPixmap(image)
        else:
            self.ui.imageLabel.setPixmap(pixmap)
        
    def populate_container_combo(self):
        dbManager = DatabaseManager()
        containers = dbManager.getContainers()
        
        for container in containers:
            if container.id != self.container.id:
                self.ui.containerCombo.addItem(container.name, container.id)
                
        if self.ui.containerCombo.count() == 0:
            self.ui.toContainerRadioButton.setEnabled(False)
            self.ui.containerCombo.setEnabled(False)
            self.ui.toOutsideRadioButton.setChecked(True)

    def on_move_remove_clicked(self):
        if self.ui.toContainerRadioButton.isChecked():
            self.on_move_clicked()
        elif self.ui.toOutsideRadioButton.isChecked():
            self.on_remove_clicked()
            
    def on_remove_clicked(self):
        quantity = self.ui.qtySpinBox.value()
        
        if quantity <= 0 or quantity > self.current_quantity:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity to remove")
            return
            
        # Add function to database manager to remove parts
        if self.update_part_quantity(-quantity):
            QMessageBox.information(self, "Success", f"Removed {quantity} parts")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to remove parts")
            
    def on_move_clicked(self):
        quantity = self.ui.qtySpinBox.value()
        target_container_id = self.ui.containerCombo.currentData()
        
        if quantity <= 0 or quantity > self.current_quantity:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity to move")
            return
            
        if target_container_id is None:
            QMessageBox.warning(self, "No Container", "Please select a target container")
            return
            
        # Move parts from one container to another
        if self.move_parts_to_container(quantity, target_container_id):
            QMessageBox.information(self, "Success", f"Moved {quantity} parts to {self.ui.containerCombo.currentText()}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to move parts")
            
    def update_part_quantity(self, delta):
        dbManager = DatabaseManager()
        result = dbManager.addColorPartIDToContainer(self.part_data['id'], self.container.id, delta)
        return result

    def move_parts_to_container(self, quantity, target_container_id):
        dbManager = DatabaseManager()
        result = dbManager.movePartsBetweenContainers(self.part_data['id'], self.container.id, target_container_id, quantity)
        return result
