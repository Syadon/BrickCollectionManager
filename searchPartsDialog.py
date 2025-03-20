from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QComboBox, QPushButton, QTableWidget, 
                              QTableWidgetItem, QFormLayout, QGroupBox, 
                              QMessageBox, QCompleter, QSizePolicy, QDialogButtonBox)
from PySide6.QtGui import QColor, QIcon
from PySide6.QtCore import Qt, QStringListModel
from database import DatabaseManager
from utils import TransparentSelectionDelegate
from imageProvider import ImagesProvider
from config import AppConfig
from partDetailDialog import PartDetailDialog

class SearchPartsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Parts")
        self.resize(800, 600)
        
        self.db_manager = DatabaseManager()
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)
        
        # Set icon size
        self.iconSize = 64
        
        self.setup_ui()
        self.populate_combos()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Search criteria section
        search_group = QGroupBox("Search Criteria")
        search_layout = QFormLayout()
        
        # Part ID
        self.part_id_edit = QLineEdit()
        self.part_id_edit.setPlaceholderText("e.g. 3001")
        self.part_id_edit.textChanged.connect(self.on_part_id_changed)
        search_layout.addRow("Part ID:", self.part_id_edit)
        
        # Part Name
        self.part_name_edit = QLineEdit()
        self.part_name_edit.setPlaceholderText("e.g. Brick 2 x 4")
        self.part_name_edit.textChanged.connect(self.on_part_name_changed)
        search_layout.addRow("Part Name:", self.part_name_edit)
        
        # Color
        self.color_combo = QComboBox()
        self.color_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout.addRow("Color:", self.color_combo)
        
        # Color Type
        self.color_type_combo = QComboBox()
        self.color_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout.addRow("Color Type:", self.color_type_combo)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        
        buttons_layout.addWidget(self.search_button)
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        
        # Results table
        result_label = QLabel("<b>Search Results:</b>")
        main_layout.addWidget(result_label)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(["Image", "Part ID", "Part Name", "Category", "Color", "Color Type", "Container", "Quantity"])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSortingEnabled(True)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.results_table))
        self.results_table.setItemDelegateForColumn(4, TransparentSelectionDelegate(self.results_table))
        
        # Connect double-click signal
        self.results_table.cellDoubleClicked.connect(self.on_result_double_clicked)
        
        # Set row height for images
        self.results_table.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        
        main_layout.addWidget(self.results_table)
        
        # Add DialogButtonBox at the bottom
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.reject)  # Close button will close the dialog
        main_layout.addWidget(self.buttonBox)
        
        # Setup autocompletion
        self.setup_autocompletion()
        
    def setup_autocompletion(self):
        dbManager = DatabaseManager()

        # Part ID completer
        self.part_ids = dbManager.getAllPartsIds()
        part_id_model = QStringListModel(self.part_ids)
        part_id_completer = QCompleter(part_id_model, self)
        part_id_completer.setCaseSensitivity(Qt.CaseInsensitive)
        part_id_completer.setFilterMode(Qt.MatchContains)
        self.part_id_edit.setCompleter(part_id_completer)
        
        # Part Name completer
        self.part_names = dbManager.getAllPartsNames()
        part_name_model = QStringListModel(self.part_names)
        part_name_completer = QCompleter(part_name_model, self)
        part_name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        part_name_completer.setFilterMode(Qt.MatchContains)
        self.part_name_edit.setCompleter(part_name_completer)
        
    def populate_combos(self):
        # Add "Any" option to color combo
        self.color_combo.addItem("Any", None)
        self.color_type_combo.addItem("Any", None)
        
        # Get all colors
        dbManager = DatabaseManager()

        for color in dbManager.getColorsNames():
            self.color_combo.addItem(color, color)
        
        # Get all color types
        for type in dbManager.getColorsTypesNames():
             self.color_type_combo.addItem(type, type)

        
    def on_part_id_changed(self, text):
        if text:
            self.part_name_edit.blockSignals(True)
            self.part_name_edit.clear()
            self.part_name_edit.blockSignals(False)
            
    def on_part_name_changed(self, text):
        if text:
            self.part_id_edit.blockSignals(True)
            self.part_id_edit.clear()
            self.part_id_edit.blockSignals(False)
    
    def clear_search(self):
        self.part_id_edit.clear()
        self.part_name_edit.clear()
        self.color_combo.setCurrentIndex(0)
        self.color_type_combo.setCurrentIndex(0)
        self.results_table.setRowCount(0)
        
    def perform_search(self):
        # Clear previous results
        self.results_table.setRowCount(0)
        
        dbManager = DatabaseManager()
        results =dbManager.searchIntoCollection(part_id=self.part_id_edit.text(), 
                                               part_name=self.part_name_edit.text(),
                                               color_name=self.color_combo.currentData(),
                                               color_type=self.color_type_combo.currentData())
            
        # Display results
        if not results:
            QMessageBox.information(self, "No Results", "No parts found matching your search criteria.")
            return
            
        self.results_table.setRowCount(len(results))
        
        for row, data in enumerate(results):
            # Image column
            image_item = QTableWidgetItem()
            image_item.setData(Qt.UserRole, data)  # Store full data for later use
            
            # Try to get image
            part_id = data['part_id']
            color_id = data['color_id']
            img = self.imgProvider.get_part_image(part_id, color_id)
            if img is not None:
                scaled = img.scaled(self.iconSize, self.iconSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_item.setIcon(QIcon(scaled))
            
            self.results_table.setItem(row, 0, image_item)
            
            # Part ID
            self.results_table.setItem(row, 1, QTableWidgetItem(data['part_id']))
            
            # Part Name
            self.results_table.setItem(row, 2, QTableWidgetItem(data['part_name']))

            self.results_table.setItem(row, 3, QTableWidgetItem(data['part_category']))
            
            # Color with background color
            color_item = QTableWidgetItem(data['color_name'])
            if data['rgb']:
                bg_color = QColor(f"#{data['rgb']}")
                color_item.setBackground(bg_color)
                
                # Set text color for better visibility
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                text_color = Qt.white if luminance < 128 else Qt.black
                color_item.setForeground(text_color)
                
            self.results_table.setItem(row, 4, color_item)

            self.results_table.setItem(row, 5, QTableWidgetItem(data['color_type']))
            
            # Container
            self.results_table.setItem(row, 6, QTableWidgetItem(data['container_name']))
            
            # Quantity
            quantity_item = QTableWidgetItem()
            quantity_item.setData(Qt.DisplayRole, data['quantity'])
            self.results_table.setItem(row, 7, quantity_item)
            
        # Adjust column widths
        self.results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column
        self.results_table.resizeColumnsToContents()
    
    def on_image_loaded(self, key, pixmap):
        # Parse key to get part_id and color_id
        try:
            part_id, color_id = key.split('_')
        except:
            return
            
        # Find matching rows in the table
        for row in range(self.results_table.rowCount()):
            item = self.results_table.item(row, 0)
            if not item:
                continue
                
            data = item.data(Qt.UserRole)
            if data['id'] == part_id and str(data['color_id']) == color_id:
                # Update the icon
                scaled = pixmap.scaled(self.iconSize, self.iconSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(scaled))
                
                # Force update
                self.results_table.viewport().update()
    
    def on_result_double_clicked(self, row, column):
        # Get the data from the row
        item = self.results_table.item(row, 0)  # First column has the complete data
        if not item:
            return
            
        part_data = item.data(Qt.UserRole)
        if not part_data:
            return
        
        container_id = part_data.get('container_id')
        container_name = part_data.get('container_name')
            
        # Create container object
        from database import Container
        container = Container(container_id, container_name, "", 0, 0)
        
        # Open part detail dialog
        dialog = PartDetailDialog(part_data, container, self)
        result = dialog.exec()
        
        # If the dialog was accepted (changed were made), refresh the search results
        if result == QDialog.Accepted:
            self.perform_search()  # Re-run the search to refresh the results