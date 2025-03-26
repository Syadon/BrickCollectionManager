from PySide6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QTableWidget, QDialog, QCompleter
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QStringListModel
from database import DatabaseManager, Container
from imageProvider import ImagesProvider
from config import AppConfig
from utils import TransparentSelectionDelegate
from partDetailDialog import PartDetailDialog
from ui.ui_searchManualWidget import Ui_SearchManualWidget

class SearchManualWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Search Parts")

        # Set icon size
        self.iconSize = 64

        self.db_manager = DatabaseManager()
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)

        self.ui = Ui_SearchManualWidget()
        self.ui.setupUi(self)

        self.setupWidget()

    def setupWidget(self):
        self.ui.search_part_id_edit.textChanged.connect(self.on_part_id_changed)
        self.ui.search_part_name_edit.textChanged.connect(self.on_part_name_changed)
        self.ui.search_button.clicked.connect(self.perform_search)
        self.ui.search_clear_button.clicked.connect(self.clear_search)

        self.ui.search_results_table.setColumnCount(8)
        self.ui.search_results_table.setHorizontalHeaderLabels(["Image", "Part ID", "Part Name", "Category", "Color", "Color Type", "Container", "Quantity"])
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.ui.search_results_table.verticalHeader().setVisible(False)
        self.ui.search_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ui.search_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ui.search_results_table.setSortingEnabled(True)
        self.ui.search_results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.ui.search_results_table.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.search_results_table))
        self.ui.search_results_table.setItemDelegateForColumn(4, TransparentSelectionDelegate(self.ui.search_results_table))
        
        # Connect double-click signal
        self.ui.search_results_table.cellDoubleClicked.connect(self.on_result_double_clicked)

        self.populate_combos()

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
        self.ui.search_part_id_edit.setCompleter(part_id_completer)
        
        # Part Name completer
        self.part_names = dbManager.getAllPartsNames()
        part_name_model = QStringListModel(self.part_names)
        part_name_completer = QCompleter(part_name_model, self)
        part_name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        part_name_completer.setFilterMode(Qt.MatchContains)
        self.ui.search_part_name_edit.setCompleter(part_name_completer)

    def populate_combos(self):
        # Add "Any" option to color combo
        self.ui.search_color_combo.addItem("Any", None)
        self.ui.search_color_type_combo.addItem("Any", None)
        
        # Get all colors
        dbManager = DatabaseManager()

        for color in dbManager.getColorsNames():
            self.ui.search_color_combo.addItem(color, color)
        
        # Get all color types
        for type in dbManager.getColorsTypesNames():
             self.ui.search_color_type_combo.addItem(type, type)

    def on_part_id_changed(self, text):
        if text:
            self.ui.search_part_name_edit.blockSignals(True)
            self.ui.search_part_name_edit.clear()
            self.ui.search_part_name_edit.blockSignals(False)

    def on_part_name_changed(self, text):
        if text:
            self.ui.search_part_id_edit.blockSignals(True)
            self.ui.search_part_id_edit.clear()
            self.ui.search_part_id_edit.blockSignals(False)

    def on_image_loaded(self, key, pixmap):
        # Parse key to get part_id and color_id
        try:
            part_id, color_id = key.split('_')
        except:
            return
            
        # Find matching rows in the table
        for row in range(self.ui.search_results_table.rowCount()):
            item = self.ui.search_results_table.item(row, 0)
            if not item:
                continue
                
            data = item.data(Qt.UserRole)
            if data['id'] == part_id and str(data['color_id']) == color_id:
                # Update the icon
                scaled = pixmap.scaled(self.iconSize, self.iconSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(scaled))
                
                # Force update
                self.ui.search_results_table.viewport().update()

    def perform_search(self):
        # Clear previous results
        self.ui.search_results_table.setRowCount(0)
        
        dbManager = DatabaseManager()
        results =dbManager.searchIntoCollection(part_id=self.ui.search_part_id_edit.text(), 
                                               part_name=self.ui.search_part_name_edit.text(),
                                               color_name=self.ui.search_color_combo.currentData(),
                                               color_type=self.ui.search_color_type_combo.currentData())
            
        # Display results
        if not results:
            QMessageBox.information(self, "No Results", "No parts found matching your search criteria.")
            return
            
        self.ui.search_results_table.setRowCount(len(results))
        
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
            
            self.ui.search_results_table.setItem(row, 0, image_item)
            
            # Part ID
            self.ui.search_results_table.setItem(row, 1, QTableWidgetItem(data['part_id']))
            
            # Part Name
            self.ui.search_results_table.setItem(row, 2, QTableWidgetItem(data['part_name']))

            self.ui.search_results_table.setItem(row, 3, QTableWidgetItem(data['part_category']))
            
            # Color with background color
            color_item = QTableWidgetItem(data['color_name'])
            if data['rgb']:
                bg_color = QColor(f"#{data['rgb']}")
                color_item.setBackground(bg_color)
                
                # Set text color for better visibility
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                text_color = Qt.white if luminance < 128 else Qt.black
                color_item.setForeground(text_color)
                
            self.ui.search_results_table.setItem(row, 4, color_item)

            self.ui.search_results_table.setItem(row, 5, QTableWidgetItem(data['color_type']))
            
            # Container
            self.ui.search_results_table.setItem(row, 6, QTableWidgetItem(data['container_name']))
            
            # Quantity
            quantity_item = QTableWidgetItem()
            quantity_item.setData(Qt.DisplayRole, data['quantity'])
            self.ui.search_results_table.setItem(row, 7, quantity_item)
            
        # Adjust column widths
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column
        self.ui.search_results_table.resizeColumnsToContents()

    def clear_search(self):
        self.ui.search_part_id_edit.clear()
        self.ui.search_part_name_edit.clear()
        self.ui.search_color_combo.setCurrentIndex(0)
        self.ui.search_color_type_combo.setCurrentIndex(0)
        self.ui.search_results_table.setRowCount(0)

    def on_result_double_clicked(self, row, column):
        # Get the data from the row
        item = self.ui.search_results_table.item(row, 0)  # First column has the complete data
        if not item:
            return
            
        part_data = item.data(Qt.UserRole)
        if not part_data:
            return
        
        container_id = part_data.get('container_id')
        container_name = part_data.get('container_name')
        qty = part_data.get('quantity')
            
        # Create container object
        container = Container(container_id, container_name, "", 0, 0)
        
        # Open part detail dialog
        dialog = PartDetailDialog(part_data, container, qty=qty, outsideDefault=True, parent = self)
        result = dialog.exec()
        
        # If the dialog was accepted (changed were made), refresh the search results
        if result == QDialog.Accepted:
            self.perform_search()  # Re-run the search to refresh the results
