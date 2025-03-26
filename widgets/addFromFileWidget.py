from PySide6.QtWidgets import (QWidget, QFileDialog, QTableWidgetItem, QMessageBox, 
                              QMenu, QSpinBox, QStyledItemDelegate, QTableWidget)
from PySide6.QtCore import Qt, QDir, Signal, QSize, QModelIndex
from PySide6.QtGui import QColor, QIcon
from ui.ui_addFromFileWidget import Ui_AddFromFileWidget
from database import DatabaseManager, Container
from utils import TransparentSelectionDelegate
from imageProvider import ImagesProvider
from config import AppConfig
from partsFileParser import XmlParser
import logging


class SpinBoxDelegate(QStyledItemDelegate):
    """Delegate per mostrare uno spinbox nelle celle della tabella"""
    def __init__(self, parent=None, min_value=1, max_value=9999):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        
    def createEditor(self, parent, option, index):
        """Crea l'editor (uno spinbox) per la cella"""
        editor = QSpinBox(parent)
        editor.setMinimum(self.min_value)
        editor.setMaximum(self.max_value)
        editor.setAlignment(Qt.AlignCenter)
        return editor
        
    def setEditorData(self, editor, index):
        """Imposta il valore dell'editor in base al valore nella cella"""
        value = int(index.model().data(index, Qt.DisplayRole) or 0)
        editor.setValue(value)
        
    def setModelData(self, editor, model, index):
        """Imposta il valore del modello quando l'editing è completato"""
        editor.interpretText()
        value = editor.value()
        model.setData(index, value, Qt.EditRole)
        
    def updateEditorGeometry(self, editor, option, index):
        """Aggiorna la geometria dell'editor"""
        editor.setGeometry(option.rect)
        
    def displayText(self, value, locale):
        """Formatta il valore per la visualizzazione"""
        try:
            return str(int(value))
        except:
            return str(value)


class AddFromFileWidget(QWidget):
    # Signal emitted when parts are added to a container
    part_added = Signal()
    
    def __init__(self, container:Container = None, parent=None):
        super(AddFromFileWidget, self).__init__(parent)

        self.ui = Ui_AddFromFileWidget()
        self.ui.setupUi(self)

        self.targetContainer = container
        
        # Crea l'image provider
        self.iconSize = AppConfig.DEFAULT_ICON_SIZE
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)
        
        # Connetti il pulsante openFile all'azione di apertura del file
        self.ui.openFileButton.clicked.connect(self.open_file_dialog)
        
        # Imposta il campo fileEdit come sola lettura
        self.ui.fileEdit.setReadOnly(True)
        
        # Connetti il pulsante load all'azione di caricamento
        self.ui.loadButton.clicked.connect(self.load_file)
        
        # Connetti il pulsante clear all'azione di pulizia
        self.ui.clearButton.clicked.connect(self.clear_table)
        
        # Connetti il pulsante di aggiunta all'azione di aggiunta al container
        self.ui.pushButton.clicked.connect(self.add_to_container)
        
        # Configura la tabella
        self.setup_table()
        
        # Popola il combobox dei container
        self.populate_container_combo()

        # Enable context menu
        self.ui.tableWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.show_context_menu)
    
        # Dizionario per mappare le righe della tabella alle informazioni complete del pezzo
        self.parts_data = []

    def setup_table(self):
        headers = ["Image", "ID", "Name", "Color", "Color Type", "Quantity"]
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        
        # Imposta l'altezza delle righe per le immagini
        self.ui.tableWidget.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        self.ui.tableWidget.verticalHeader().setVisible(False)

        self.ui.tableWidget.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.tableWidget))
        self.ui.tableWidget.setItemDelegateForColumn(3, TransparentSelectionDelegate(self.ui.tableWidget))
        
        # Imposta il delegate per la colonna della quantità (colonna 5)
        self.ui.tableWidget.setItemDelegateForColumn(5, SpinBoxDelegate(self.ui.tableWidget, 1, 9999))
        
        # Consenti l'editing solo per la colonna della quantità
        #self.ui.tableWidget.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

        self.ui.tableWidget.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Connetti il segnale per aggiornare i dati quando viene modificata una cella
        self.ui.tableWidget.cellChanged.connect(self.on_cell_changed)
        
        # Configura l'espansione delle colonne
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)
    
    def open_file_dialog(self):
        """Apre un dialogo per selezionare un file XML e imposta il percorso nel campo fileEdit"""
        # Ottieni la directory iniziale (cartella documenti dell'utente)
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
    
    def load_file(self):
        """Carica e elabora il file XML specificato nel campo fileEdit"""
        file_path = self.ui.fileEdit.text()
        if not file_path:
            QMessageBox.warning(self, "No File Selected", "Please select an XML file first.")
            return
        
        try:
            # Pulisci la tabella e i dati esistenti
            self.clear_table()

            parser_result = XmlParser.parse_file(file_path)
            
            if not parser_result.success:
                # Mostra gli errori all'utente
                errors = "\n".join(parser_result.errors)
                QMessageBox.critical(self, "XML Error", f"Could not parse the XML file:\n{errors}")
                return
            
            if len(parser_result.warnings) > 0:
                # Mostra avvisi non bloccanti
                warnings = "\n".join(parser_result.warnings)
                logging.warning(f"XML parsing warnings: {warnings}")
            
            # Prepara le query per il database
            db_manager = DatabaseManager()
            
            # Elabora le parti trovate nel file XML
            parts_to_add = []
            missing_parts = []
            
            for part_info in parser_result.parts:
                part_id = part_info['part_id']
                color_id = part_info['color_id']
                quantity = part_info['quantity']
                
                # Cerca il pezzo e il colore nel database
                color_parts = db_manager.searchColorsParts(part_id=part_id, color_id=color_id)
                
                if color_parts:
                    # Aggiungi ai pezzi da visualizzare
                    part_data = color_parts[0]
                    part_data['quantity'] = quantity
                    parts_to_add.append(part_data)
                else:
                    # Registra i pezzi mancanti per informare l'utente
                    missing_parts.append((part_id, color_id, quantity))
            
            # Aggiungi i pezzi alla tabella
            self.add_parts_to_table(parts_to_add)
            
            # Mostra un messaggio di riepilogo
            if len(parts_to_add) > 0:
                message = f"Loaded {len(parts_to_add)} parts from the file."
                if missing_parts:
                    message += f"\n{len(missing_parts)} parts were not found in the database."
                QMessageBox.information(self, "File Loaded", message)
            elif missing_parts:
                part_list = "\n".join([f"{p[0]} (color {p[1]}): {p[2]} pcs" for p in missing_parts[:5]])
                if len(missing_parts) > 5:
                    part_list += f"\n... and {len(missing_parts) - 5} more"
                QMessageBox.warning(
                    self, 
                    "No Parts Found", 
                    f"None of the {len(missing_parts)} parts in the file were found in the database.\nExamples:\n{part_list}"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "No Parts Found", 
                    "No parts were found in the XML file or the file format is not supported."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")
            logging.error(f"Error loading XML file: {str(e)}", exc_info=True)
    
    def add_parts_to_table(self, parts_data):
        # Disconnetti il segnale cellChanged temporaneamente per evitare chiamate durante il popolamento
        self.ui.tableWidget.cellChanged.disconnect(self.on_cell_changed)
        
        self.parts_data = parts_data
        self.ui.tableWidget.setRowCount(len(parts_data))
        
        for row, part in enumerate(parts_data):
            # Crea gli elementi della tabella
            
            # Colonna immagine
            image_item = QTableWidgetItem()
            # Tenta di caricare l'immagine
            if 'part_id' in part and 'color_id' in part:
                img = self.imgProvider.get_part_image(part['part_id'], part['color_id'])
                if img is not None:
                    scaled = img.scaled(self.iconSize, self.iconSize, 
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_item.setIcon(QIcon(scaled))
            self.ui.tableWidget.setItem(row, 0, image_item)
            
            # Colonna Part ID
            id_item = QTableWidgetItem(part.get('part_id', 'Unknown'))
            self.ui.tableWidget.setItem(row, 1, id_item)
            
            # Colonna Part Name
            name_item = QTableWidgetItem(part.get('part_name', 'Unknown'))
            self.ui.tableWidget.setItem(row, 2, name_item)
            name_item.setSizeHint(QSize(400, self.iconSize))
            
            # Colonna Color con sfondo colorato
            color_item = QTableWidgetItem(part.get('color_name', 'Unknown'))
            if 'rgb' in part and part['rgb']:
                bg_color = QColor(f"#{part['rgb']}")
                color_item.setBackground(bg_color)
                
                # Imposta il colore del testo per migliorare la leggibilità
                luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                text_color = Qt.white if luminance < 128 else Qt.black
                color_item.setForeground(text_color)
            self.ui.tableWidget.setItem(row, 3, color_item)
            
            # Colonna Color Type
            type_item = QTableWidgetItem(part.get('color_type', 'Unknown'))
            self.ui.tableWidget.setItem(row, 4, type_item)
            
            # Colonna Quantity - imposta l'EditRole per permettere l'editing
            qty_item = QTableWidgetItem()
            qty_item.setData(Qt.EditRole, part.get('quantity', 1))
            qty_item.setTextAlignment(Qt.AlignCenter)
            self.ui.tableWidget.setItem(row, 5, qty_item)
        
        # Regola la larghezza delle colonne
        self.ui.tableWidget.setColumnWidth(0, self.iconSize + 8)
        self.ui.tableWidget.resizeColumnsToContents()
        
        # Riconnetti il segnale cellChanged
        self.ui.tableWidget.cellChanged.connect(self.on_cell_changed)
    
    def clear_table(self):
        """Pulisce la tabella e i dati associati"""
        self.ui.tableWidget.setRowCount(0)
        self.parts_data = []
        self.imgProvider.cleanup_tasks()
    
    def populate_container_combo(self):
        """Popola il combobox dei container"""
        self.ui.containerCombo.clear()
        
        # Ottieni i container dal database
        db_manager = DatabaseManager()
        containers = db_manager.getContainers()
        
        # Aggiungi i container al combobox
        for container in containers:
            if self.targetContainer == None or container.id == self.targetContainer.id:
                part_count = container.part_count or 0
                display_text = f"{container.name} ({part_count} parts)"
                self.ui.containerCombo.addItem(display_text, (container.id, container.name))

        self.ui.containerCombo.setEnabled(self.targetContainer == None)
    
    def add_to_container(self):
        """Aggiunge i pezzi selezionati al container selezionato"""
        # Verifica che sia selezionato un containers
        if self.ui.containerCombo.count() == 0:
            QMessageBox.warning(self, "No Container", "Please create a container first.")
            return
        
        # Ottieni il container selezionato
        container_data = self.ui.containerCombo.currentData()
        if not container_data:
            QMessageBox.warning(self, "Invalid Container", "Please select a valid container.")
            return
        
        container_id, container_name = container_data
        
        # # Ottieni le righe selezionate
        # selected_rows = set(index.row() for index in self.ui.tableWidget.selectedIndexes())
        
        # if not selected_rows:
        #     # Se nessuna riga è selezionata, usa tutte le righe
        selected_rows = range(self.ui.tableWidget.rowCount())
        
        # Verifica che ci siano righe da aggiungere
        if not selected_rows:
            QMessageBox.warning(self, "No Parts", "No parts to add.")
            return
        
        # Aggiungi i pezzi al container
        db_manager = DatabaseManager()
        
        # Inizia una transazione
        success_count = 0
        error_count = 0
        missing_id_count = 0

        success_qty = 0
        error_qty = 0
        missing_qty = 0
        
        try:
            for row in selected_rows:
                if row >= len(self.parts_data):
                    continue
                
                part_data = self.parts_data[row]
                quantity = part_data['quantity']
                
                # Verifica che il pezzo abbia un ID di color_part
                if part_data.get('id') is None:
                    # Cerca il color_part nel database
                    color_part = db_manager.getColorPart(part_data['part_id'], part_data['color_id'])
                    
                    if color_part:
                        part_data['id'] = color_part.id
                    else:
                        missing_id_count += 1
                        missing_qty += quantity
                        continue
                
                # Aggiungi il pezzo al container
                if db_manager.addColorPartIDToContainer(part_data['id'], container_id, quantity):
                    success_count += 1
                    success_qty += quantity
                else:
                    error_count += 1
                    error_qty += quantity
            
            # Mostra un messaggio di riepilogo
            if success_count > 0:
                # Emetti il segnale che sono stati aggiunti dei pezzi
                self.part_added.emit()
                
                # Aggiorna il combobox dei container
                self.populate_container_combo()
                
                message = f"Added {success_count} lots to container '{container_name}'."
                if error_count > 0:
                    message += f"\n{error_count} lots could not be added."
                if missing_id_count > 0:
                    message += f"\n{missing_id_count} lots were not found in the database."
                
                QMessageBox.information(self, "Parts Added", message)
            else:
                message = "No parts were added to the container."
                if missing_id_count > 0:
                    message += f"\n{missing_id_count} parts were not found in the database."
                
                QMessageBox.warning(self, "No Parts Added", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            logging.error(f"Error adding parts to container: {str(e)}")
    
    def on_image_loaded(self, key, pixmap):
        """Callback chiamato quando un'immagine viene caricata dall'ImageProvider"""
        try:
            part_id, color_id = key.split('_')
        except:
            return
        
        # Cerca le righe che corrispondono a questo part_id e color_id
        for row, part_data in enumerate(self.parts_data):
            if str(part_data.get('part_id')) == part_id and str(part_data.get('color_id')) == color_id:
                # Aggiorna l'icona
                scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Ottieni l'item della tabella
                item = self.ui.tableWidget.item(row, 0)
                if item:
                    item.setIcon(QIcon(scaled))

    def on_cell_changed(self, row, column):
        """Gestisce le modifiche alle celle della tabella"""
        # Aggiorna solo se è la colonna della quantità (colonna 5)
        if column == 5 and row < len(self.parts_data):
            item = self.ui.tableWidget.item(row, column)
            if item:
                try:
                    new_value = int(item.text())
                    if new_value > 0:
                        # Aggiorna il valore nei dati
                        self.parts_data[row]['quantity'] = new_value
                except ValueError:
                    # Ripristina il valore originale se non è un numero valido
                    item.setText(str(self.parts_data[row].get('quantity', 1)))

    def show_context_menu(self, position):
        index = self.ui.tableWidget.indexAt(position)

        if index.isValid():
            context_menu = QMenu(self)
            remove_action = context_menu.addAction("Remove")
            
            # Aggiungi opzioni per modificare la quantità
            edit_qty_action = context_menu.addAction("Edit Quantity")
            
            # Show context menu at cursor position
            action = context_menu.exec(self.ui.tableWidget.viewport().mapToGlobal(position))
            
            row = index.row()
            
            if action == remove_action:
                # Remove the row from the table
                self.ui.tableWidget.removeRow(row)
                
                # Remove the corresponding data from parts_data
                if row < len(self.parts_data):
                    self.parts_data.pop(row)
            
            elif action == edit_qty_action:
                # Focus sulla cella della quantità per quella riga e inizia l'editing
                qty_cell = self.ui.tableWidget.item(row, 5)
                if qty_cell:
                    self.ui.tableWidget.setCurrentItem(qty_cell)
                    self.ui.tableWidget.editItem(qty_cell)