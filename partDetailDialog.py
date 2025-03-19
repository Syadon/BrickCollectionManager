from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QSpinBox, QHBoxLayout, QPushButton, QComboBox, QDialogButtonBox, QMessageBox)
from PySide6.QtSql import QSqlQuery
from PySide6.QtGui import QColor
from database import DatabaseManager



class PartDetailDialog(QDialog):
    def __init__(self, part_data, container, parent=None):
        super().__init__(parent)
        self.part_data = part_data
        self.container = container
        self.db_manager = DatabaseManager()
        
        self.setWindowTitle(f"Brick Details - {part_data['part_name']}")
        self.resize(450, 350)
        
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Part information
        form_layout = QFormLayout()
        
        # Part ID and Name
        form_layout.addRow("Part ID:", QLabel(self.part_data['part_id']))
        form_layout.addRow("Name:", QLabel(self.part_data['part_name']))
        form_layout.addRow("Category:", QLabel(self.part_data['part_category']))
        
        # Color information with colored background
        color_label = QLabel(self.part_data['color_name'])
        rgb = QColor(f"#{self.part_data['rgb']}")
        luminance = (0.299 * rgb.red() + 0.587 * rgb.green() + 0.114 * rgb.blue())
        
        # Set stylesheet for colored background
        color_label.setStyleSheet(
            f"background-color: #{self.part_data['rgb']}; "
            f"color: {'white' if luminance < 128 else 'black'}; "
            f"padding: 4px; border-radius: 4px;"
        )
        
        form_layout.addRow("Color:", color_label)
        form_layout.addRow("Color Type:", QLabel(self.part_data['color_type']))
        
        # Current quantity
        self.current_quantity = self.part_data['quantity']
        form_layout.addRow("Current Quantity:", QLabel(str(self.current_quantity)))
        
        main_layout.addLayout(form_layout)
        
        # Modify quantity section
        main_layout.addSpacing(20)
        main_layout.addWidget(QLabel("<b>Modify Quantity</b>"))
        
        # Remove quantity
        remove_layout = QHBoxLayout()
        remove_layout.addWidget(QLabel("Remove:"))
        self.remove_spinbox = QSpinBox()
        self.remove_spinbox.setRange(1, self.current_quantity)
        self.remove_spinbox.setValue(1)
        remove_layout.addWidget(self.remove_spinbox)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.on_remove_clicked)
        remove_layout.addWidget(self.remove_button)
        
        main_layout.addLayout(remove_layout)
        
        # Move quantity to another container
        move_layout = QHBoxLayout()
        move_layout.addWidget(QLabel("Move:"))
        self.move_spinbox = QSpinBox()
        self.move_spinbox.setRange(1, self.current_quantity)
        self.move_spinbox.setValue(1)
        move_layout.addWidget(self.move_spinbox)
        
        move_layout.addWidget(QLabel("to:"))
        self.container_combo = QComboBox()
        self.populate_container_combo()
        move_layout.addWidget(self.container_combo)
        
        self.move_button = QPushButton("Move")
        self.move_button.clicked.connect(self.on_move_clicked)
        move_layout.addWidget(self.move_button)
        
        main_layout.addLayout(move_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.accept)
        main_layout.addWidget(button_box)
        
    def populate_container_combo(self):
        """Populate the container combo box with all containers except current one"""
        containers = self.db_manager.getContainers()
        
        for container in containers:
            if container.id != self.container.id:
                self.container_combo.addItem(container.name, container.id)
                
        if self.container_combo.count() == 0:
            self.move_button.setEnabled(False)
            self.container_combo.setEnabled(False)
            
    def on_remove_clicked(self):
        """Handle remove button click"""
        quantity = self.remove_spinbox.value()
        
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
        """Handle move button click"""
        quantity = self.move_spinbox.value()
        target_container_id = self.container_combo.currentData()
        
        if quantity <= 0 or quantity > self.current_quantity:
            QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity to move")
            return
            
        if target_container_id is None:
            QMessageBox.warning(self, "No Container", "Please select a target container")
            return
            
        # Move parts from one container to another
        if self.move_parts_to_container(quantity, target_container_id):
            QMessageBox.information(self, "Success", f"Moved {quantity} parts to {self.container_combo.currentText()}")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to move parts")
            
    def update_part_quantity(self, delta):
        """Update part quantity in database"""
        try:
            query = QSqlQuery()
            query.prepare("""
                UPDATE parts_collection 
                SET count = count + ? 
                WHERE item = ? AND container_id = ?
            """)
            query.addBindValue(delta)
            query.addBindValue(self.part_data['id'])
            query.addBindValue(self.container.id)
            
            if not query.exec():
                return False
                
            # If count is now zero, remove the entry
            if self.current_quantity + delta <= 0:
                query.prepare("""
                    DELETE FROM parts_collection
                    WHERE item = ? AND container_id = ?
                """)
                query.addBindValue(self.part_data['id'])
                query.addBindValue(self.container.id)
                
                if not query.exec():
                    return False
                    
            return True
            
        except Exception as e:
            print(f"Error updating quantity: {str(e)}")
            return False
            
    def move_parts_to_container(self, quantity, target_container_id):
        """Move parts from current container to target container"""
        try:
            # Start transaction
            self.db_manager.db.transaction()
            
            # Remove from current container
            if not self.update_part_quantity(-quantity):
                self.db_manager.db.rollback()
                return False
                
            # Add to target container
            query = QSqlQuery()
            
            # Check if part already exists in target container
            query.prepare("""
                SELECT count FROM parts_collection
                WHERE item = ? AND container_id = ?
            """)
            query.addBindValue(self.part_data['id'])
            query.addBindValue(target_container_id)
            
            if query.exec() and query.next():
                # Update existing entry
                current_count = query.value(0)
                
                query.prepare("""
                    UPDATE parts_collection
                    SET count = count + ?
                    WHERE item = ? AND container_id = ?
                """)
                query.addBindValue(quantity)
                query.addBindValue(self.part_data['id'])
                query.addBindValue(target_container_id)
            else:
                # Insert new entry
                query.prepare("""
                    INSERT INTO parts_collection (item, container_id, count)
                    VALUES (?, ?, ?)
                """)
                query.addBindValue(self.part_data['id'])
                query.addBindValue(target_container_id)
                query.addBindValue(quantity)
                
            if not query.exec():
                self.db_manager.db.rollback()
                return False
                
            # Commit transaction
            return self.db_manager.db.commit()
            
        except Exception as e:
            print(f"Error moving parts: {str(e)}")
            self.db_manager.db.rollback()
            return False
