from PySide6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem, QTableWidget, QDialog, QCompleter, QFileDialog
from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtCore import Qt, QStringListModel, QDir, QFile
from database import DatabaseManager, Container
from imageProvider import ImagesProvider
from config import AppConfig
from utils import TransparentSelectionDelegate
from partDetailDialog import PartDetailDialog
from partsFileParser import XmlParser
import logging
from ui.ui_searchManualWidget import Ui_SearchManualWidget

class SearchManualWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
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

        self.ui.search_results_table.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column

        # Configura l'espansione delle colonne
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        
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
        filePath = self.ui.fileEdit.text()
        
        if self.ui.fileEdit.text() and QFile.exists(filePath):
            self.perform_file_search(filePath)
        else:
            self.perform_manual_search()

    def perform_file_search(self, filePath):
        # Clear previous results
        self.ui.search_results_table.setRowCount(0)
        
        try:
            # Parse the file
            parser_result = XmlParser.parse_file(filePath)
            
            if not parser_result.success:
                # Mostra gli errori all'utente
                errors = "\n".join(parser_result.errors)
                QMessageBox.critical(self, "XML Error", f"Could not parse the XML file:\n{errors}")
                return
            
            if not parser_result.parts or len(parser_result.parts) == 0:
                QMessageBox.information(self, "No Results", "No parts found in the file.")
                return
            
            # Prepare DatabaseManager
            dbManager = self.db_manager
            
            # Track results to display in the table
            display_results = []
            missing_parts = []
            
            # Process each part in the file
            for part_info in parser_result.parts:
                part_id = part_info['part_id']
                color_id = part_info['color_id']
                required_qty = part_info['quantity']
                
                # Cerca nelle parti della collezione per trovare i container che contengono questo pezzo
                matching_parts = dbManager.searchIntoCollection(part_id=part_id, color_id=color_id)

                if not matching_parts:
                    # Cerca informazioni sul pezzo anche se non è nella collezione
                    color_part_info = dbManager.searchColorsParts(part_id=part_id, color_id=color_id)
                    
                    if color_part_info:
                        # Abbiamo trovato il pezzo ma non è nella collezione
                        part_data = color_part_info[0]
                        part_data['quantity'] = 0
                        part_data['container_name'] = "Not in collection"
                        part_data['container_id'] = None
                        part_data['required_quantity'] = required_qty
                        part_data['part_category'] = "Unknown"  # Potrebbe essere aggiunto con una query aggiuntiva
                        missing_parts.append(part_data)
                    else:
                        # Il pezzo non è proprio nel database
                        missing_parts.append({
                            'part_id': part_id,
                            'color_id': color_id,
                            'part_name': "Unknown",
                            'color_name': "Unknown",
                            'color_type': "Unknown",
                            'rgb': None,
                            'quantity': 0,
                            'container_name': "Not in database",
                            'container_id': None,
                            'required_quantity': required_qty,
                            'part_category': "Unknown"
                        })

                    continue
                
                # Aggiungi ogni container che contiene il pezzo
                required_qty_count = required_qty
                for part in matching_parts:
                    if required_qty_count <= part['quantity']:
                        part['required_quantity'] = required_qty_count
                        required_qty_count -= part['quantity']
                        display_results.append(part)
                        break
                    else:
                        part['required_quantity'] = part['quantity']
                        required_qty_count -= part['quantity']
                        display_results.append(part)

                if required_qty_count > 0:
                    display_results.append({
                        'part_id': part_id,
                        'color_id': color_id,
                        'part_name': part['part_name'],
                        'color_name': part['color_name'],
                        'color_type': part['color_type'],
                        'rgb': part['rgb'],
                        'quantity': 0,
                        'container_name': "Not enough parts",
                        'container_id': None,
                        'required_quantity': required_qty_count,
                        'part_category': part['part_category']
                    })

            # Aggiungi anche i pezzi mancanti
            for part in missing_parts:
                display_results.append(part)
            
            # Mostra i risultati nella tabella
            self.ui.search_results_table.setRowCount(len(display_results))
            
            for row, data in enumerate(display_results):
                self.addItemToTable(row, data)
            
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
            QMessageBox.critical(self, "Error", f"An error occurred while processing the file: {str(e)}")
            logging.error(f"Error in perform_file_search: {str(e)}", exc_info=True)

    def perform_manual_search(self):
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
            self.addItemToTable(row, data)
            
        # Adjust column widths
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Set fixed width for image column
        self.ui.search_results_table.resizeColumnsToContents()

    def addItemToTable(self, row, data):
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
        self.ui.search_results_table.setItem(row, 2, QTableWidgetItem(data.get('part_name', 'Unknown')))

        # Part Category
        self.ui.search_results_table.setItem(row, 3, QTableWidgetItem(data.get('part_category', 'Unknown')))
        
        # Color with background color
        color_item = QTableWidgetItem(data.get('color_name', 'Unknown'))
        if data.get('rgb'):
            bg_color = QColor(f"#{data['rgb']}")
            color_item.setBackground(bg_color)
            
            # Set text color for better visibility
            luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
            text_color = Qt.white if luminance < 128 else Qt.black
            color_item.setForeground(text_color)
        
        self.ui.search_results_table.setItem(row, 4, color_item)
        
        # Color Type
        self.ui.search_results_table.setItem(row, 5, QTableWidgetItem(data.get('color_type', 'Unknown')))
        
        # Container
        container_item = QTableWidgetItem(data['container_name'])
        self.ui.search_results_table.setItem(row, 6, container_item)

        # Quantity
        if "required_quantity" in data:
            # Evidenzia in rosso i container che non hanno abbastanza pezzi
            if data['quantity'] < data['required_quantity']:
                container_item.setForeground(QColor(255, 0, 0))
            
            # Quantity - Mostra "X / Y" dove X è la quantità disponibile e Y la quantità richiesta
            qty_text = f"{data['quantity']} / {data['required_quantity']}"
            quantity_item = QTableWidgetItem(qty_text)
            # Colora in rosso se non ci sono abbastanza pezzi
            if data['quantity'] < data['required_quantity']:
                quantity_item.setForeground(QColor(255, 0, 0))
            self.ui.search_results_table.setItem(row, 7, quantity_item)
        else:
            quantity_item = QTableWidgetItem()
            quantity_item.setData(Qt.DisplayRole, data['quantity'])
            self.ui.search_results_table.setItem(row, 7, quantity_item)


    def clear_search(self):
        self.ui.search_part_id_edit.clear()
        self.ui.search_part_name_edit.clear()
        self.ui.search_color_combo.setCurrentIndex(0)
        self.ui.search_color_type_combo.setCurrentIndex(0)
        self.ui.search_results_table.setRowCount(0)
        self.ui.fileEdit.clear()

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
        required_qty = part_data.get('required_quantity')
            
        # Create container object
        container = Container(container_id, container_name, "", 0, 0)
        
        # Open part detail dialog
        defaultQty = required_qty if required_qty and required_qty > 0 else qty
        dialog = PartDetailDialog(part_data, container, qty=defaultQty, outsideDefault=True, parent = self)
        result = dialog.exec()
        
        # If the dialog was accepted (changed were made), refresh the search results
        if result == QDialog.Accepted:
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
