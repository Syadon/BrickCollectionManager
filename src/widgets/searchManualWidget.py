from PySide6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QTableWidget, QDialog, QCompleter, QFileDialog
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QStringListModel, QDir, QFile
from src.database import DatabaseManager, Container, CollectionPart
from src.imageProvider import ImagesProvider
from src.widgets.colorLabel import ColorLabel
from config import AppConfig
from src.utils import TransparentSelectionDelegate, populate_color_combo, setup_color_combo_delegate
from src.partDetailDialog import PartDetailDialog
from src.partsFileParser import XmlParser
from src.logger import get_logger, log_exception
import logging
import copy
from ui.ui_searchManualWidget import Ui_SearchManualWidget

class SearchManualWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logger = get_logger()
        self.logger.debug("Initializing SearchManualWidget")
        
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Search Parts")

        # Set icon size
        self.iconSize = AppConfig.DEFAULT_ICON_SIZE

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
        self.ui.openFileButton.clicked.connect(self.openFile)

        # Connect inputs to validation
        self.ui.search_part_id_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_part_name_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_color_combo.currentIndexChanged.connect(self.validate_search_inputs)
        self.ui.search_color_type_combo.currentIndexChanged.connect(self.validate_search_inputs)
        self.ui.fileEdit.textChanged.connect(self.validate_search_inputs)

        table_header_labels = ["Image", "Part ID", "Part Name", "Category", "Color", "Container", "Quantity"] 
        self.ui.search_results_table.setColumnCount(7)
        self.ui.search_results_table.setHorizontalHeaderLabels(table_header_labels)
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.ui.search_results_table.verticalHeader().setVisible(False)
        self.ui.search_results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ui.search_results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ui.search_results_table.setSortingEnabled(True)
        self.ui.search_results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ui.search_results_table.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.search_results_table))
        self.ui.search_results_table.setItemDelegateForColumn(4, TransparentSelectionDelegate(self.ui.search_results_table))

        self.ui.search_results_table.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column

        # Configura l'espansione delle colonne
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        
        # Connect double-click signal
        self.ui.search_results_table.cellDoubleClicked.connect(self.on_result_double_clicked)

        self.populate_combos()

        # Setup autocompletion
        self.setup_autocompletion()
        
        # Initial validation
        self.validate_search_inputs()

    def setup_autocompletion(self):
        dbManager = DatabaseManager()

        # Part ID completer
        self.part_ids = dbManager.getAllPartsIds()
        part_id_model = QStringListModel(self.part_ids)
        part_id_completer = QCompleter(part_id_model, self)
        part_id_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        part_id_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ui.search_part_id_edit.setCompleter(part_id_completer)
        
        # Part Name completer
        self.part_names = dbManager.getAllPartsNames()
        part_name_model = QStringListModel(self.part_names)
        part_name_completer = QCompleter(part_name_model, self)
        part_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        part_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ui.search_part_name_edit.setCompleter(part_name_completer)

    def populate_combos(self):
        dbManager = DatabaseManager()
        
        # Setup color combo with delegate
        populate_color_combo(self.ui.search_color_combo, dbManager, include_any_option=True)
        setup_color_combo_delegate(self.ui.search_color_combo)
        
        # Add "Any" option to color type combo
        self.ui.search_color_type_combo.addItem("Any", None)
        
        # Get all color types
        for type in dbManager.getColorsTypesNames():
             self.ui.search_color_type_combo.addItem(type, type)

    def validate_search_inputs(self):
        """Enable search button only if at least one search criteria is provided"""
        has_part_id = bool(self.ui.search_part_id_edit.text().strip())
        has_part_name = bool(self.ui.search_part_name_edit.text().strip())
        has_color = self.ui.search_color_combo.currentIndex() > 0  # Index 0 is "Any"
        has_color_type = self.ui.search_color_type_combo.currentIndex() > 0  # Index 0 is "Any"
        has_file = bool(self.ui.fileEdit.text().strip())
        
        # Enable search if at least one criteria is provided
        is_valid = has_part_id or has_part_name or has_color or has_color_type or has_file
        self.ui.search_button.setEnabled(is_valid)

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
                
            data = item.data(Qt.ItemDataRole.UserRole)
            part = data[0]
            if part.id == part_id and str(part.color_id) == color_id:
                # Update the icon
                scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                                       Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
                item.setIcon(QIcon(scaled))
                
                # Force update
                self.ui.search_results_table.viewport().update()

    def perform_search(self):
        filePath = self.ui.fileEdit.text()
        
        if self.ui.fileEdit.text() and QFile.exists(filePath):
            self.perform_file_search(filePath)
        else:
            self.perform_manual_search()

    def perform_file_search(self, filePath):
        self.logger.info(f"Performing file search: {filePath}")
        # Clear previous results
        self.ui.search_results_table.setRowCount(0)
        
        try:
            # Parse the file
            parser_result = XmlParser.parse_file(filePath)
            
            if not parser_result.success:
                # Mostra gli errori all'utente
                errors = "\n".join(parser_result.errors)
                self.logger.error(f"XML parsing failed: {errors}")
                QMessageBox.critical(self, "XML Error", f"Could not parse the XML file:\n{errors}")
                return
            
            if not parser_result.parts or len(parser_result.parts) == 0:
                self.logger.warning("No parts found in XML file")
                QMessageBox.information(self, "No Results", "No parts found in the file.")
                return
            
            self.logger.info(f"Found {len(parser_result.parts)} parts in XML file")
            
            # Prepare DatabaseManager
            dbManager = self.db_manager
            
            # Track results to display in the table
            display_results = []
            missing_parts = []

            partIdEdit = self.ui.search_part_id_edit.text()
            partNameEdit = self.ui.search_part_name_edit.text()
            
            # Extract color ID from color data tuple
            color_data = self.ui.search_color_combo.currentData()
            colorIdEdit = color_data[0] if color_data is not None else None  # color_data is (id, name, rgb)
            
            colorTypeEdit = self.ui.search_color_type_combo.currentData()
            
            # Process each part in the file
            for part_info in parser_result.parts:
                part_id = part_info['part_id']
                color_id = part_info['color_id']
                required_qty = part_info['quantity']

                if partIdEdit and part_id != partIdEdit:
                    continue

                if colorIdEdit and color_id != int(colorIdEdit):
                    continue
                
                # Cerca nelle parti della collezione per trovare i container che contengono questo pezzo
                matching_parts = dbManager.searchIntoCollection(part_id=part_id, color_id=color_id)

                part_data = None
                if len(matching_parts) < 1:
                    # Cerca informazioni sul pezzo anche se non è nella collezione
                    color_part_info = dbManager.searchColorsParts(part_id=part_id, color_id=color_id)
                    
                    if color_part_info and len(color_part_info) > 0:
                        # Abbiamo trovato il pezzo ma non è nella collezione
                        part_data = CollectionPart(
                            id=color_part_info[0]['id'],
                            part_id=color_part_info[0]['part_id'],
                            part_name=color_part_info[0]['part_name'],
                            part_category="Unknown",
                            color_id=color_part_info[0]['color_id'],
                            color_name=color_part_info[0]['color_name'],
                            rgb=color_part_info[0]['rgb'],
                            color_type=color_part_info[0]['color_type'],
                            container_name="Not in collection",
                            quantity=0,
                            container_id=None
                        )
                        missing_parts.append((part_data, required_qty))
                    else:
                        # Il pezzo non è proprio nel database
                        part_data = CollectionPart(
                            id=0,
                            part_id=part_id,
                            part_name="Unknown",
                            part_category="Unknown",
                            color_id=color_id,
                            color_name="Unknown",
                            rgb=None,
                            color_type="Unknown",
                            container_name="Not in database",
                            quantity=0,
                            container_id=None
                        )
                        missing_parts.append((part_data, required_qty))
                    continue
                else:
                    part_data = copy.copy(matching_parts[0])
                    part_data.container_name = ""
                    part_data.quantity = 0
                    part_data.container_id = None


                if colorTypeEdit and part_data.color_type != colorTypeEdit:
                    continue

                if partNameEdit and partNameEdit.lower() not in part_data.part_name.lower():
                    continue
                
                # Aggiungi ogni container che contiene il pezzo                   
                required_qty_count = required_qty
                for part in matching_parts:
                    if required_qty_count <= part.quantity:
                        display_results.append((part, required_qty_count))
                        required_qty_count -= part.quantity
                        break
                    else:
                        display_results.append((part, part.quantity))
                        required_qty_count -= part.quantity

                if required_qty_count > 0:
                    not_enough_part = copy.copy(part_data)
                    not_enough_part.quantity = 0
                    not_enough_part.container_name = "Not enough parts"
                    not_enough_part.container_id = None
                    display_results.append((not_enough_part, required_qty_count))

            # Aggiungi anche i pezzi mancanti
            for part, req_qty in missing_parts:
                display_results.append((part, req_qty))
            
            # Mostra i risultati nella tabella
            self.ui.search_results_table.setRowCount(len(display_results))
            
            for row, (part, req_qty) in enumerate(display_results):
                self.addItemToTable(row, part, req_qty)
            
            # Adjust column widths
            self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column
            self.ui.search_results_table.resizeColumnsToContents()
            
            # Mostra una sintesi dei risultati
            total_parts = len(parser_result.parts)
            missing_count = len(missing_parts)
            found_count = total_parts - missing_count
            
            if missing_count > 0:
                QMessageBox.information(
                    self, 
                    "Search Results", 
                    f"Found {found_count} of {total_parts} parts in your collection.\n"
                    f"{missing_count} parts are missing or have insufficient quantity."
                )
            
        except Exception as e:
            log_exception(e, "Error in perform_file_search")
            QMessageBox.critical(self, "Error", f"An error occurred while processing the file: {str(e)}")

    def perform_manual_search(self):
        self.logger.info("Performing manual search")
        # Clear previous results
        self.ui.search_results_table.setRowCount(0)
        
        # Extract color name from color data tuple
        color_data = self.ui.search_color_combo.currentData()
        if color_data is not None:
            # color_data is a tuple: (id, name, rgb)
            colorName = color_data[1]
        else:
            colorName = None

        dbManager = DatabaseManager()
        results = dbManager.searchIntoCollection(part_id=self.ui.search_part_id_edit.text(), 
                                               part_name=self.ui.search_part_name_edit.text(),
                                               color_name=colorName,
                                               color_type=self.ui.search_color_type_combo.currentData())
            
        # Display results
        if not results:
            self.logger.info("No results found for manual search")
            QMessageBox.information(self, "No Results", "No parts found matching your search criteria.")
            return
        
        self.logger.info(f"Found {len(results)} results for manual search")
        self.ui.search_results_table.setRowCount(len(results))
        
        for row, data in enumerate(results):
            self.addItemToTable(row, data)
            
        # Adjust column widths
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column
        self.ui.search_results_table.resizeColumnsToContents()
        
        # Limit Name column width
        name_column_index = 2
        max_name_width = 400
        if self.ui.search_results_table.columnWidth(name_column_index) > max_name_width:
            self.ui.search_results_table.setColumnWidth(name_column_index, max_name_width)
            
        type_column_index = 3
        max_type_width = 200
        if self.ui.search_results_table.columnWidth(type_column_index) > max_type_width:
            self.ui.search_results_table.setColumnWidth(type_column_index, max_type_width)

        self.ui.search_results_table.setWordWrap(True)
        self.ui.search_results_table.resizeRowsToContents()
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)

    def addItemToTable(self, row, part: CollectionPart, required_quantity: int|None = None):
        # Image column
        image_item = QTableWidgetItem()
        image_item.setData(Qt.ItemDataRole.UserRole, (part, required_quantity))  # Store full data for later use
        
        # Try to get image
        img = self.imgProvider.get_part_image(part.part_id, part.color_id)
        if img is not None:
            scaled = img.scaled(self.iconSize, self.iconSize, 
                                Qt.AspectRatioMode.KeepAspectRatio, 
                                Qt.TransformationMode.SmoothTransformation)
            image_item.setIcon(QIcon(scaled))
        
        self.ui.search_results_table.setItem(row, 0, image_item)
        
        # Part ID
        self.ui.search_results_table.setItem(row, 1, QTableWidgetItem(part.part_id))
        
        # Part Name
        name_item = QTableWidgetItem(part.part_name)
        name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.ui.search_results_table.setItem(row, 2, name_item)

        # Part Category
        self.ui.search_results_table.setItem(row, 3, QTableWidgetItem(part.part_category))
        
        # Color using ColorLabel widget
        rgb_hex = part.rgb if part.rgb else None
        color_label = ColorLabel(part.color_name, rgb_hex, part.color_type, part.color_id)
        self.ui.search_results_table.setCellWidget(row, 4, color_label)
        
        # Container
        container_item = QTableWidgetItem(part.container_name)
        self.ui.search_results_table.setItem(row, 5, container_item)

        # Quantity
        if required_quantity is not None:
            # Highlight containers that don't have enough parts in red
            if part.quantity < required_quantity:
                container_item.setForeground(QColor(255, 0, 0))
            
            # Quantity - Show "X / Y" where X is available quantity and Y is required quantity
            qty_text = f"{part.quantity} / {required_quantity}"
            quantity_item = QTableWidgetItem(qty_text)
            # Color in red if there aren't enough parts
            if part.quantity < required_quantity:
                quantity_item.setForeground(QColor(255, 0, 0))
            self.ui.search_results_table.setItem(row, 6, quantity_item)
        else:
            quantity_item = QTableWidgetItem()
            quantity_item.setData(Qt.ItemDataRole.DisplayRole, part.quantity)
            self.ui.search_results_table.setItem(row, 6, quantity_item)


    def clear_search(self):
        self.ui.search_part_id_edit.clear()
        self.ui.search_part_name_edit.clear()
        self.ui.search_color_combo.setCurrentIndex(0)
        self.ui.search_color_type_combo.setCurrentIndex(0)
        self.ui.search_results_table.setRowCount(0)
        self.ui.fileEdit.clear()
        # Validation will be triggered by the clear operations above

    def on_result_double_clicked(self, row, column):
        # Get the data from the row
        item = self.ui.search_results_table.item(row, 0)  # First column has the complete data
        if not item:
            return

        part_data = item.data(Qt.ItemDataRole.UserRole)
        if not part_data:
            return
        
        part = part_data[0]
        container_id = part.container_id
        container_name = part.container_name
        qty = part.quantity
        required_qty = part_data[1]
            
        # Create container object
        container = Container(container_id, container_name, "", 0, 0)
        
        # Open part detail dialog
        defaultQty = required_qty if required_qty and required_qty > 0 else qty
        dialog = PartDetailDialog(part, container, qty=defaultQty, outsideDefault=True, parent = self)
        result = dialog.exec()
        
        # If the dialog was accepted (changed were made), refresh the search results
        if result == QDialog.DialogCode.Accepted:
            self.perform_search()  # Re-run the search to refresh the results

    def openFile(self):
        initial_dir = QDir.homePath()
        
        # Apri il dialogo di selezione file
        file_path, _ = QFileDialog.getOpenFileName(
            self,                          # parent widget
            "Select XML File",             # titolo del dialogo
            initial_dir,                   # directory iniziale
            "XML Files (*.xml);;All Files (*.*)"  # filtro per i file
        )
        
        # Se un file è stato selezionato, imposta il percorso nel campo di testo
        if file_path:
            self.ui.fileEdit.setText(file_path)
