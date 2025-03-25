from PySide6.QtWidgets import (QDialog, QTableWidgetItem, QComboBox, 
                             QSpinBox, QPushButton, QVBoxLayout, QFormLayout, QCompleter,
                             QHBoxLayout, QLabel, QGroupBox, QSizePolicy, QMessageBox, QLineEdit, QTableWidget)
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QColor, QIcon
from database import DatabaseManager, Container
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from widgets.addFromFileWidget import AddFromFileWidget
from widgets.addFromCameraWidget import AddFromCameraWidget
from config import AppConfig
from utils import TransparentSelectionDelegate
from imageProvider import ImagesProvider

class AddBricksDialog(QDialog):
    def __init__(self, targetContainer:Container= None, parent=None):
        super().__init__(parent)

        self.iconSize = 64
        self.targetContainer = targetContainer
        
        # Create image provider
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)

        # Create and setup UI
        self.ui = Ui_AddBricksDialog()
        self.ui.setupUi(self)

        self.camera_detection_widget = AddFromCameraWidget(container=self.targetContainer, parent=self.ui.tabWidget)
        self.ui.tabWidget.addTab(self.camera_detection_widget, "Camera Detection")

        #Setup load from file tab
        self.file_import_widget = AddFromFileWidget(container=self.targetContainer, parent=self.ui.tabWidget)
        self.ui.tabWidget.addTab(self.file_import_widget, "Load from File")


        # Crea e configura l'UI per la scheda search
        self.setup_search_tab()

        # Populate container combobox
        self.populate_container_list()

        # Connect tab change signal
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Initial check of camera tab visibility
        self.on_tab_changed(self.ui.tabWidget.currentIndex())

    def populate_container_list(self):
        self.searchContainerComboBox.clear()
        
        # Get containers from database
        db_manager = DatabaseManager()
        containers = db_manager.getContainers()
        
        # Add containers to combobox
        for container in containers:
            if self.targetContainer != None and container.id != self.targetContainer.id:
                continue

            # Display name and part count
            display_text = f"{container.name} ({container.part_count} parts)"
            self.searchContainerComboBox.addItem(display_text, (container.id, container.name))

        self.searchContainerComboBox.setEnabled(self.targetContainer == None)

    def closeEvent(self, event):
        self.imgProvider.cleanup_tasks()
        super().closeEvent(event)

    def on_image_loaded(self, key, pixmap):
        # Parse key to get part_id and color_id
        try:
            part_id, color_id = key.split('_')
        except:
            return
        
        if self.ui.tabWidget.currentIndex() == self.ui.tabWidget.indexOf(self.ui.cameraTab):       
            pass
        elif self.ui.tabWidget.currentIndex() == self.ui.tabWidget.indexOf(self.ui.searchTab):
            for row in range(self.search_results_table.rowCount()):
                item = self.search_results_table.item(row, 0)
                if not item:
                    continue

                row_part_id = str(item.data(Qt.UserRole)['part_id'])
                row_color_id = str(item.data(Qt.UserRole)['color_id'])
                if row_part_id == part_id and row_color_id == color_id:
                    self.update_part_image_search(pixmap, row)
                    break

    def update_part_image_search(self, pixmap, row):
        if row < 0 or row >= self.search_results_table.rowCount():
            return
            
        # Scale image
        scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                              Qt.KeepAspectRatio, 
                              Qt.SmoothTransformation)
        
        # Update image in table
        image_item = self.search_results_table.item(row, 0)
        if image_item:
            image_item.setIcon(QIcon(scaled))
            self.search_results_table.viewport().update()  # Force repaint
            self.search_results_table.resizeColumnsToContents()

    def on_tab_changed(self, index):
        self.imgProvider.cleanup_tasks()

        if self.ui.tabWidget.currentIndex() == self.ui.tabWidget.indexOf(self.ui.searchTab):
            self.clear_search()
            self.populate_container_list()

    def setup_search_tab(self):
        # Layout principale
        main_layout = QVBoxLayout()
        
        # Sezione criteri di ricerca
        search_group = QGroupBox("Search Criteria")
        search_layout = QFormLayout()
        
        # Part ID
        self.search_part_id_edit = QLineEdit()
        self.search_part_id_edit.setPlaceholderText("e.g. 3001")
        self.search_part_id_edit.textChanged.connect(self.on_search_part_id_changed)
        search_layout.addRow("Part ID:", self.search_part_id_edit)
        
        # Part Name
        self.search_part_name_edit = QLineEdit()
        self.search_part_name_edit.setPlaceholderText("e.g. Brick 2 x 4")
        self.search_part_name_edit.textChanged.connect(self.on_search_part_name_changed)
        search_layout.addRow("Part Name:", self.search_part_name_edit)
        
        # Color
        self.search_color_combo = QComboBox()
        self.search_color_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout.addRow("Color:", self.search_color_combo)
        
        # Color Type
        self.search_color_type_combo = QComboBox()
        self.search_color_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout.addRow("Color Type:", self.search_color_type_combo)
        
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)
        
        # Pulsanti di ricerca
        buttons_layout = QHBoxLayout()
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.search_clear_button = QPushButton("Clear")
        self.search_clear_button.clicked.connect(self.clear_search)
        
        buttons_layout.addWidget(self.search_button)
        buttons_layout.addWidget(self.search_clear_button)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        
        # Tabella risultati
        result_label = QLabel("<b>Search Results:</b>")
        main_layout.addWidget(result_label)

        headerLabels = ["Image", "Part ID", "Part Name", "Color", "Color Type"]
        
        self.search_results_table = QTableWidget()
        self.search_results_table.setColumnCount(len(headerLabels))
        self.search_results_table.setHorizontalHeaderLabels(headerLabels)
        self.search_results_table.horizontalHeader().setStretchLastSection(True)
        self.search_results_table.verticalHeader().setVisible(False)
        self.search_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.search_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.search_results_table.setSortingEnabled(True)
        self.search_results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.search_results_table.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.search_results_table))
        self.search_results_table.setItemDelegateForColumn(3, TransparentSelectionDelegate(self.search_results_table))

        # Imposta altezza righe per immagini
        self.search_results_table.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        
        main_layout.addWidget(self.search_results_table)
        
        # Sezione per aggiungere alla collezione
        add_group = QGroupBox("Add to Collection")
        add_layout = QFormLayout()
        
        # Quantity
        self.search_qty_spinbox = QSpinBox()
        self.search_qty_spinbox.setMinimum(1)
        self.search_qty_spinbox.setMaximum(9999)
        self.search_qty_spinbox.setValue(1)
        add_layout.addRow("Quantity:", self.search_qty_spinbox)
        
        self.searchContainerComboBox = QComboBox()
        add_layout.addRow("Container:", self.searchContainerComboBox)
        
        # Add button
        self.search_add_button = QPushButton("Add to Container")
        self.search_add_button.setMinimumHeight(40)
        self.search_add_button.setEnabled(False)  # Disabilitato finché non viene selezionato un item
        self.search_add_button.clicked.connect(self.on_search_add_clicked)
        
        add_group.setLayout(add_layout)
        main_layout.addWidget(add_group)
        
        # Aggiungi pulsante
        add_button_layout = QHBoxLayout()
        add_button_layout.addStretch()
        add_button_layout.addWidget(self.search_add_button)
        add_button_layout.addStretch()
        main_layout.addLayout(add_button_layout)
        
        # Imposta il layout nella tab
        self.ui.searchTabLayout.addLayout(main_layout)
        
        # Popola i combobox
        self.populate_search_combos()
        
        # Configura autocompletamento
        #self.setup_search_autocomplete()

        # Connect signals from file import widget
        #self.file_import_widget.part_added.connect(lambda: self.populate_container_list())
        
        # Connetti al segnale di selezione tabella
        self.search_results_table.itemSelectionChanged.connect(self.on_search_selection_changed)

    def populate_search_combos(self):
        # Aggiungi opzione "Any" ai combobox dei colori
        self.search_color_combo.addItem("Any", None)
        self.search_color_type_combo.addItem("Any", None)
        
        # Ottieni tutti i colori dal database
        dbManager = DatabaseManager()
        
        # Colori
        for color in dbManager.getColorsNames():
            self.search_color_combo.addItem(color, color)
        
        # Tipi di colore
        for type in dbManager.getColorsTypesNames():
            self.search_color_type_combo.addItem(type, type)

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
        self.search_part_name_edit.setCompleter(part_name_completer)

    def on_search_part_id_changed(self, text):
        if text:
            self.search_part_name_edit.blockSignals(True)
            self.search_part_name_edit.clear()
            self.search_part_name_edit.blockSignals(False)

    def on_search_part_name_changed(self, text):
        if text:
            self.search_part_id_edit.blockSignals(True)
            self.search_part_id_edit.clear()
            self.search_part_id_edit.blockSignals(False)

    def clear_search(self):
        self.search_part_id_edit.clear()
        self.search_part_name_edit.clear()
        self.search_color_combo.setCurrentIndex(0)
        self.search_color_type_combo.setCurrentIndex(0)
        self.search_results_table.setRowCount(0)
        self.search_add_button.setEnabled(False)

        self.imgProvider.cleanup_tasks()

    def perform_search(self):
        # Pulisci risultati precedenti
        self.search_results_table.setRowCount(0)
        
        # Ottieni criteri di ricerca
        part_id = self.search_part_id_edit.text()
        part_name = self.search_part_name_edit.text()
        color_name = self.search_color_combo.currentData()
        color_type = self.search_color_type_combo.currentData()
        
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
        
        self.search_results_table.setRowCount(len(results))
        
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
            
            self.search_results_table.setItem(row, 0, image_item)
            
            # Part ID
            self.search_results_table.setItem(row, 1, QTableWidgetItem(data['part_id']))
            
            # Part Name
            self.search_results_table.setItem(row, 2, QTableWidgetItem(data['part_name']))
            
            # Color con sfondo colorato
            color_item = QTableWidgetItem(data['color_name'])
            if data['rgb']:
                bg_color = QColor(f"#{data['rgb']}")
                color_item.setBackground(bg_color)
                
                # Imposta colore del testo per migliore visibilità
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                text_color = Qt.white if luminance < 128 else Qt.black
                color_item.setForeground(text_color)
            
            self.search_results_table.setItem(row, 3, color_item)
            
            # Color Type
            self.search_results_table.setItem(row, 4, QTableWidgetItem(data['color_type']))
        
        # Regola larghezza colonne
        self.search_results_table.setColumnWidth(0, self.iconSize + 8)  # Dimensione fissa per colonna immagine
        self.search_results_table.resizeColumnsToContents()

    def on_search_selection_changed(self):
        self.search_add_button.setEnabled(self.search_results_table.currentRow() >= 0)

    def on_search_add_clicked(self):
        try:
            # Ottieni riga selezionata
            current_row = self.search_results_table.currentRow()
            if current_row < 0:
                return
            
            # Ottieni dati dalla tabella
            item = self.search_results_table.item(current_row, 0)
            if not item:
                return
            
            # Recupera dati completi
            data = item.data(Qt.UserRole)
            
            # Ottieni container selezionato
            container_data = self.searchContainerComboBox.currentData()
            if not container_data:
                QMessageBox.warning(self, "No Container", "Please select a container")
                return
            
            container_id, container_name = container_data
            
            # Ottieni quantità
            quantity = self.search_qty_spinbox.value()
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
            self.search_results_table.clearSelection()
            self.search_add_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

