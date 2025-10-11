from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QComboBox, QSpinBox, QMessageBox, 
                              QTableWidget, QTableWidgetItem, QSizePolicy, QCompleter)
from PySide6.QtGui import QIcon, QColor
from PySide6.QtCore import Qt, QStringListModel
from src.utils import TransparentSelectionDelegate
from src.widgets.colorLabel import ColorLabel
from ui.ui_addManualWidget import Ui_AddManualWidget
from src.database import Container, DatabaseManager
from src.imageProvider import ImagesProvider
from config import AppConfig

class AddManualWidget(QWidget):

    def __init__(self, container:Container|None = None, parent=None):
        super(AddManualWidget, self).__init__(parent)

        self.ui = Ui_AddManualWidget()
        self.ui.setupUi(self)

        self.targetContainer = container
        self.iconSize = AppConfig.DEFAULT_ICON_SIZE

        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)

        self.setup_widget()

    def showEvent(self, event):
        # Popola i combobox
        self.populate_search_combos()
        self.populate_container_list()
        super().showEvent(event)

    def hideEvent(self, event):
        # Reset to dummy container
        self.ui.searchContainerComboBox.setCurrentIndex(0)
        self.clear_search()
        self.imgProvider.cleanup_tasks()
        super().hideEvent(event)

    def setup_widget(self):
        
        # Part ID
        self.ui.search_part_id_edit.textChanged.connect(self.on_search_part_id_changed)
        
        # Part Name
        self.ui.search_part_name_edit.textChanged.connect(self.on_search_part_name_changed)

        # Connect inputs to validation
        self.ui.search_part_id_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_part_name_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_color_combo.currentIndexChanged.connect(self.validate_search_inputs)
        self.ui.search_color_type_combo.currentIndexChanged.connect(self.validate_search_inputs)

        # Color
        self.ui.search_color_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Color Type
        self.ui.search_color_type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Pulsanti di ricerca
        self.ui.search_button.clicked.connect(self.perform_search)
        self.ui.search_clear_button.clicked.connect(self.clear_search)

        
        # Tabella risultati
        headerLabels = ["Image", "Part ID", "Part Name", "Color"]
        
        self.ui.search_results_table.setColumnCount(len(headerLabels))
        self.ui.search_results_table.setHorizontalHeaderLabels(headerLabels)
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.ui.search_results_table.verticalHeader().setVisible(False)
        self.ui.search_results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.ui.search_results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.ui.search_results_table.setSortingEnabled(True)
        self.ui.search_results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.ui.search_results_table.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.search_results_table))
        self.ui.search_results_table.setItemDelegateForColumn(3, TransparentSelectionDelegate(self.ui.search_results_table))

        # Imposta altezza righe per immagini
        self.ui.search_results_table.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        
        # Add button
        self.ui.search_add_button.setEnabled(False)  # Disabilitato finché non viene selezionato un item
        self.ui.search_add_button.clicked.connect(self.on_search_add_clicked)
        
        # Configura autocompletamento
        #self.setup_search_autocomplete()

        # Connect signals from file import widget
        #self.file_import_widget.part_added.connect(lambda: self.populate_container_list())
        
        # Connetti al segnale di selezione tabella
        self.ui.search_results_table.itemSelectionChanged.connect(self.on_search_selection_changed)
        
        # Initial validation
        self.validate_search_inputs()

    def populate_container_list(self):
        self.ui.searchContainerComboBox.clear()
        
        # Add dummy container as first option
        self.ui.searchContainerComboBox.addItem("Select Container...", None)
        
        # Get containers from database
        db_manager = DatabaseManager()
        containers = db_manager.getContainers()
        
        # Add containers to combobox
        for container in containers:
            if self.targetContainer != None and container.id != self.targetContainer.id:
                continue

            # Display name and part count
            display_text = f"{container.name} ({container.part_count} parts)"
            self.ui.searchContainerComboBox.addItem(display_text, (container.id, container.name))

        self.ui.searchContainerComboBox.setEnabled(self.targetContainer == None)
        
        # Connect to selection change event if not already connected
        try:
            self.ui.searchContainerComboBox.currentIndexChanged.disconnect(self.on_container_selection_changed)
        except:
            pass
        self.ui.searchContainerComboBox.currentIndexChanged.connect(self.on_container_selection_changed)
        
        # Update add button state
        self.on_container_selection_changed(self.ui.searchContainerComboBox.currentIndex())

    def populate_search_combos(self):
        # Aggiungi opzione "Any" ai combobox dei colori
        self.ui.search_color_combo.addItem("Any", None)
        self.ui.search_color_type_combo.addItem("Any", None)
        
        # Ottieni tutti i colori dal database
        dbManager = DatabaseManager()
        
        # Colori
        for color in dbManager.getColorsNames():
            self.ui.search_color_combo.addItem(color, color)
        
        # Tipi di colore
        for type in dbManager.getColorsTypesNames():
            self.ui.search_color_type_combo.addItem(type, type)

    def setup_search_autocomplete(self):
        dbManager = DatabaseManager()
        
        # Part ID completer
        part_ids = dbManager.getAllPartsIds()
        part_id_model = QStringListModel(part_ids)
        part_id_completer = QCompleter(part_id_model, self)
        part_id_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        part_id_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ui.search_part_id_edit.setCompleter(part_id_completer)
        
        # Part Name completer
        part_names = dbManager.getAllPartsNames()
        part_name_model = QStringListModel(part_names)
        part_name_completer = QCompleter(part_name_model, self)
        part_name_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        part_name_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.ui.search_part_name_edit.setCompleter(part_name_completer)

    def validate_search_inputs(self):
        """Enable search button only if at least one search criteria is provided"""
        has_part_id = bool(self.ui.search_part_id_edit.text().strip())
        has_part_name = bool(self.ui.search_part_name_edit.text().strip())
        has_color = self.ui.search_color_combo.currentIndex() > 0  # Index 0 is "Any"
        has_color_type = self.ui.search_color_type_combo.currentIndex() > 0  # Index 0 is "Any"
        
        # Enable search if at least one criteria is provided
        is_valid = has_part_id or has_part_name or has_color or has_color_type
        self.ui.search_button.setEnabled(is_valid)

    def on_search_part_id_changed(self, text):
        if text:
            self.ui.search_part_name_edit.blockSignals(True)
            self.ui.search_part_name_edit.clear()
            self.ui.search_part_name_edit.blockSignals(False)

    def on_search_part_name_changed(self, text):
        if text:
            self.ui.search_part_id_edit.blockSignals(True)
            self.ui.search_part_id_edit.clear()
            self.ui.search_part_id_edit.blockSignals(False)

    def clear_search(self):
        self.ui.search_part_id_edit.clear()
        self.ui.search_part_name_edit.clear()
        self.ui.search_color_combo.setCurrentIndex(0)
        self.ui.search_color_type_combo.setCurrentIndex(0)
        self.ui.search_results_table.setRowCount(0)
        self.ui.search_add_button.setEnabled(False)

        self.imgProvider.cleanup_tasks()
        # Validation will be triggered by the clear operations above

    def perform_search(self):
        # Pulisci risultati precedenti
        self.ui.search_results_table.setRowCount(0)
        
        # Ottieni criteri di ricerca
        part_id = self.ui.search_part_id_edit.text()
        part_name = self.ui.search_part_name_edit.text()
        color_name = self.ui.search_color_combo.currentData()
        color_type = self.ui.search_color_type_combo.currentData()
        
        # Esegui la ricerca nel database
        dbManager = DatabaseManager()
        results = dbManager.searchColorsParts(part_id=part_id, 
                                            part_name=part_name,
                                            color_name=color_name,
                                            color_type=color_type)
        
        # Mostra risultati
        if not results:
            QMessageBox.information(self, "No Results", "No parts found matching your search criteria.")
            return
        
        self.ui.search_results_table.setRowCount(len(results))
        
        for row, data in enumerate(results):
            # Colonna immagine
            image_item = QTableWidgetItem()
            image_item.setData(Qt.ItemDataRole.UserRole, data)  # Salva i dati completi per uso futuro
            
            # Prova a ottenere l'immagine
            part_id = data['part_id']
            color_id = data['color_id']
            img = self.imgProvider.get_part_image(part_id, color_id)
            if img is not None:
                scaled = img.scaled(self.iconSize, self.iconSize, 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
                image_item.setIcon(QIcon(scaled))
            
            self.ui.search_results_table.setItem(row, 0, image_item)
            
            # Part ID
            self.ui.search_results_table.setItem(row, 1, QTableWidgetItem(data['part_id']))
            
            # Part Name
            name_item = QTableWidgetItem(data['part_name'])
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.search_results_table.setItem(row, 2, name_item)
            
            # Color using ColorLabel widget
            rgb_hex = data['rgb'] if data['rgb'] else None
            color_label = ColorLabel(data['color_name'], rgb_hex, data['color_type'], data['color_id'])
            self.ui.search_results_table.setCellWidget(row, 3, color_label)
        
        # Regola larghezza colonne
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Dimensione fissa per colonna immagine
        self.ui.search_results_table.resizeColumnsToContents()
        
        # Limit Name column width
        name_column_index = 2
        max_name_width = 400
        if self.ui.search_results_table.columnWidth(name_column_index) > max_name_width:
            self.ui.search_results_table.setColumnWidth(name_column_index, max_name_width)
        
        self.ui.search_results_table.setWordWrap(True)
        self.ui.search_results_table.resizeRowsToContents()
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)

    def on_search_selection_changed(self):
        self.update_add_button_state()

    def on_search_add_clicked(self):
        try:
            # Ottieni riga selezionata
            current_row = self.ui.search_results_table.currentRow()
            if current_row < 0:
                return
            
            # Ottieni dati dalla tabella
            item = self.ui.search_results_table.item(current_row, 0)
            if not item:
                return
            
            # Recupera dati completi
            data = item.data(Qt.ItemDataRole.UserRole)
            
            # Ottieni container selezionato
            container_data = self.ui.searchContainerComboBox.currentData()
            if not container_data:
                QMessageBox.warning(self, "No Container", "Please select a container")
                return
            
            container_id, container_name = container_data
            
            # Ottieni quantità
            quantity = self.ui.search_qty_spinbox.value()
            if quantity <= 0:
                QMessageBox.warning(self, "Invalid Quantity", "Please enter a valid quantity")
                return
            
            # Ottieni ColorPart e aggiungi alla collezione
            dbManager = DatabaseManager()
            if not dbManager.addColorPartIDToContainer(data['id'], container_id, quantity):
                QMessageBox.critical(self, "Error", "Failed to add part to container")
                return
            
            # Aggiorna conteggio parti nel container
            self.update_container_combo_display()
            
            # Mostra messaggio di conferma
            msg = QMessageBox(self)
            msg.setWindowTitle("Part Added")
            msg.setText(f"Added {quantity} of part {data['part_id']} - {data['part_name']} in color {data['color_name']} to container {container_name}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Aggiungi immagine al messaggio
            pixmap = self.imgProvider.get_part_image(data['part_id'], data['color_id'])
            if pixmap:
                msg.setIconPixmap(pixmap)
            
            msg.exec()
            
            # Pulisci la selezione
            self.ui.search_results_table.clearSelection()
            self.ui.search_add_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def update_container_combo_display(self):
        current_index = self.ui.searchContainerComboBox.currentIndex()
        if current_index >= 0:
            container_id, container_name = self.ui.searchContainerComboBox.currentData()
            
            # Aggiorna il conteggio parti
            dbManager = DatabaseManager()
            part_count = dbManager.getConteinerPartCount(container_id)
            
            if part_count is not None:
                self.ui.searchContainerComboBox.setItemText(current_index, f"{container_name} ({part_count} parts)")

    def on_image_loaded(self, key, pixmap):
        # Parse key to get part_id and color_id
        try:
            part_id, color_id = key.split('_')
        except:
            return
        
        for row in range(self.ui.search_results_table.rowCount()):
            item = self.ui.search_results_table.item(row, 0)
            if not item:
                continue

            row_part_id = str(item.data(Qt.ItemDataRole.UserRole)['part_id'])
            row_color_id = str(item.data(Qt.ItemDataRole.UserRole)['color_id'])
            if row_part_id == part_id and row_color_id == color_id:
                self.update_part_image_search(pixmap, row)
                break

    def update_part_image_search(self, pixmap, row):
        if row < 0 or row >= self.ui.search_results_table.rowCount():
            return
            
        # Scale image
        scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                              Qt.AspectRatioMode.KeepAspectRatio, 
                              Qt.TransformationMode.SmoothTransformation)

        # Update image in table
        image_item = self.ui.search_results_table.item(row, 0)
        if image_item:
            image_item.setIcon(QIcon(scaled))
            self.ui.search_results_table.viewport().update()  # Force repaint
            self.ui.search_results_table.resizeColumnsToContents()

    def on_container_selection_changed(self, index):
        self.update_add_button_state()

    def update_add_button_state(self):
        # Disable add button if dummy container is selected
        container_data = self.ui.searchContainerComboBox.currentData()
        self.ui.search_add_button.setEnabled(container_data is not None and self.ui.search_results_table.currentRow() >= 0)


