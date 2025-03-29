from PySide6.QtWidgets import QWidget, QTableWidgetItem, QTableWidget, QSizePolicy, QMessageBox, QCompleter
from PySide6.QtGui import QIcon, QColor
from PySide6.QtCore import Qt, QStringListModel
from src.utils import TransparentSelectionDelegate
from ui.ui_addManualWidget import Ui_AddManualWidget
from src.database import Container, DatabaseManager
from src.imageProvider import ImagesProvider
from config import AppConfig

class AddManualWidget(QWidget):

    def __init__(self, container:Container = None, parent=None):
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
        self.clear_search()
        self.imgProvider.cleanup_tasks()
        super().hideEvent(event)

    def setup_widget(self):
        
        # Part ID
        self.ui.search_part_id_edit.textChanged.connect(self.on_search_part_id_changed)
        
        # Part Name
        self.ui.search_part_name_edit.textChanged.connect(self.on_search_part_name_changed)

        # Color
        self.ui.search_color_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Color Type
        self.ui.search_color_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Pulsanti di ricerca
        self.ui.search_button.clicked.connect(self.perform_search)
        self.ui.search_clear_button.clicked.connect(self.clear_search)

        
        # Tabella risultati
        headerLabels = ["Image", "Part ID", "Part Name", "Color", "Color Type"]
        
        self.ui.search_results_table.setColumnCount(len(headerLabels))
        self.ui.search_results_table.setHorizontalHeaderLabels(headerLabels)
        self.ui.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.ui.search_results_table.verticalHeader().setVisible(False)
        self.ui.search_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ui.search_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ui.search_results_table.setSortingEnabled(True)
        self.ui.search_results_table.setSelectionMode(QTableWidget.SingleSelection)
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

    def populate_container_list(self):
        self.ui.searchContainerComboBox.clear()
        
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
        part_id_completer.setCaseSensitivity(Qt.CaseInsensitive)
        part_id_completer.setFilterMode(Qt.MatchContains)
        self.search_part_id_edit.setCompleter(part_id_completer)
        
        # Part Name completer
        part_names = dbManager.getAllPartsNames()
        part_name_model = QStringListModel(part_names)
        part_name_completer = QCompleter(part_name_model, self)
        part_name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        part_name_completer.setFilterMode(Qt.MatchContains)
        self.ui.search_part_name_edit.setCompleter(part_name_completer)

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
            image_item.setData(Qt.UserRole, data)  # Salva i dati completi per uso futuro
            
            # Prova a ottenere l'immagine
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
            
            # Color con sfondo colorato
            color_item = QTableWidgetItem(data['color_name'])
            if data['rgb']:
                bg_color = QColor(f"#{data['rgb']}")
                color_item.setBackground(bg_color)
                
                # Imposta colore del testo per migliore visibilità
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                text_color = Qt.white if luminance < 128 else Qt.black
                color_item.setForeground(text_color)
            
            self.ui.search_results_table.setItem(row, 3, color_item)
            
            # Color Type
            self.ui.search_results_table.setItem(row, 4, QTableWidgetItem(data['color_type']))
        
        # Regola larghezza colonne
        self.ui.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Dimensione fissa per colonna immagine
        self.ui.search_results_table.resizeColumnsToContents()

    def on_search_selection_changed(self):
        self.ui.search_add_button.setEnabled(self.ui.search_results_table.currentRow() >= 0)

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
            data = item.data(Qt.UserRole)
            
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
            msg.setStandardButtons(QMessageBox.Ok)
            
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

            row_part_id = str(item.data(Qt.UserRole)['part_id'])
            row_color_id = str(item.data(Qt.UserRole)['color_id'])
            if row_part_id == part_id and row_color_id == color_id:
                self.update_part_image_search(pixmap, row)
                break

    def update_part_image_search(self, pixmap, row):
        if row < 0 or row >= self.ui.search_results_table.rowCount():
            return
            
        # Scale image
        scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                              Qt.KeepAspectRatio, 
                              Qt.SmoothTransformation)
        
        # Update image in table
        image_item = self.ui.search_results_table.item(row, 0)
        if image_item:
            image_item.setIcon(QIcon(scaled))
            self.ui.search_results_table.viewport().update()  # Force repaint
            self.ui.search_results_table.resizeColumnsToContents()
