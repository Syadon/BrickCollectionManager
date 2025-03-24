from PySide6.QtWidgets import QWidget, QFileDialog, QTableWidgetItem, QMessageBox, QHeaderView
from PySide6.QtCore import Qt, QDir, Signal, QSize
from PySide6.QtGui import QColor, QIcon
from ui.ui_addFromFileWidget import Ui_AddFromFileWidget
from database import DatabaseManager
from utils import TransparentSelectionDelegate
from imageProvider import ImagesProvider
from config import AppConfig
import xml.etree.ElementTree as ET
import logging


class AddFromFileWidget(QWidget):
    # Signal emitted when parts are added to a container
    part_added = Signal()
    
    def __init__(self, parent=None):
        super(AddFromFileWidget, self).__init__(parent)

        self.ui = Ui_AddFromFileWidget()
        self.ui.setupUi(self)
        
        # Crea l'image provider
        self.icon_size = 48
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
    
        # Dizionario per mappare le righe della tabella alle informazioni complete del pezzo
        self.parts_data = []

    def setup_table(self):
        headers = ["Image", "ID", "Name", "Color", "Color Type", "Quantity"]
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        
        # Imposta l'altezza delle righe per le immagini
        self.ui.tableWidget.verticalHeader().setDefaultSectionSize(self.icon_size + 4)
        self.ui.tableWidget.verticalHeader().setVisible(False)

        self.ui.tableWidget.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.tableWidget))
        self.ui.tableWidget.setItemDelegateForColumn(3, TransparentSelectionDelegate(self.ui.tableWidget))
        
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
            
            # Carica il file XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Prepara le query per il database
            db_manager = DatabaseManager()
            
            # Processa gli elementi nel file XML
            parts_to_add = []
            
            for item in root.findall('ITEM'):
                item_type = item.find('ITEMTYPE')
                item_id = item.find('ITEMID')
                color_id = item.find('COLOR')
                quantity = item.find('MINQTY')
                
                # Salta se mancano informazioni essenziali
                if None in (item_type, item_id, color_id, quantity):
                    continue
                
                # Estrai i valori dagli elementi
                item_type_text = item_type.text
                item_id_text = item_id.text
                color_id_text = color_id.text
                quantity_value = int(quantity.text)
                
                # Verifica che sia un pezzo (P) e non un set (S) o altro
                if item_type_text != 'P':
                    continue
                
                # Cerca il pezzo e il colore nel database
                color_part = db_manager.searchColorsParts(part_id=item_id_text, color_id=int(color_id_text))
                if len(color_part) == 1:
                    part_data = color_part[0]
                    part_data['quantity'] = quantity_value
                    parts_to_add.append(part_data)
                else:
                    # TODO: problem
                    break
            
            # Aggiungi i pezzi alla tabella
            self.add_parts_to_table(parts_to_add)
            
            # Mostra un messaggio di successo
            if len(parts_to_add) > 0:
                QMessageBox.information(
                    self, 
                    "File Loaded", 
                    f"Loaded {len(parts_to_add)} parts from the file."
                )
            else:
                QMessageBox.warning(
                    self, 
                    "No Parts Found", 
                    "No matching parts were found in the database."
                )
                
        except ET.ParseError:
            QMessageBox.critical(self, "XML Error", "Could not parse the XML file. Make sure it is a valid XML file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while loading the file: {str(e)}")
            logging.error(f"Error loading XML file: {str(e)}")
    
    def add_parts_to_table(self, parts_data):
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
                    scaled = img.scaled(self.icon_size, self.icon_size, 
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_item.setIcon(QIcon(scaled))
            self.ui.tableWidget.setItem(row, 0, image_item)
            
            # Colonna Part ID
            id_item = QTableWidgetItem(part.get('part_id', 'Unknown'))
            self.ui.tableWidget.setItem(row, 1, id_item)
            
            # Colonna Part Name
            name_item = QTableWidgetItem(part.get('part_name', 'Unknown'))
            self.ui.tableWidget.setItem(row, 2, name_item)
            name_item.setSizeHint(QSize(400, self.icon_size))
            
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
            
            # Colonna Quantity
            qty_item = QTableWidgetItem(str(part.get('quantity', 0)))
            self.ui.tableWidget.setItem(row, 5, qty_item)
        
        # Regola la larghezza delle colonne
        self.ui.tableWidget.setColumnWidth(0, self.icon_size + 8)
        self.ui.tableWidget.resizeColumnsToContents()
    
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
            part_count = container.part_count or 0
            display_text = f"{container.name} ({part_count} parts)"
            self.ui.containerCombo.addItem(display_text, (container.id, container.name))
    
    def add_to_container(self):
        """Aggiunge i pezzi selezionati al container selezionato"""
        # Verifica che sia selezionato un container
        if self.ui.containerCombo.count() == 0:
            QMessageBox.warning(self, "No Container", "Please create a container first.")
            return
        
        # Ottieni il container selezionato
        container_data = self.ui.containerCombo.currentData()
        if not container_data:
            QMessageBox.warning(self, "Invalid Container", "Please select a valid container.")
            return
        
        container_id, container_name = container_data
        
        # Ottieni le righe selezionate
        selected_rows = set(index.row() for index in self.ui.tableWidget.selectedIndexes())
        
        if not selected_rows:
            # Se nessuna riga è selezionata, usa tutte le righe
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
        
        try:
            for row in selected_rows:
                if row >= len(self.parts_data):
                    continue
                
                part_data = self.parts_data[row]
                
                # Verifica che il pezzo abbia un ID di color_part
                if part_data.get('id') is None:
                    # Cerca il color_part nel database
                    color_part = db_manager.getColorPart(part_data['part_id'], part_data['color_id'])
                    
                    if color_part:
                        part_data['id'] = color_part.id
                    else:
                        missing_id_count += 1
                        continue
                
                # Aggiungi il pezzo al container
                quantity = part_data['quantity']
                if db_manager.addColorPartIDToContainer(part_data['id'], container_id, quantity):
                    success_count += 1
                else:
                    error_count += 1
            
            # Mostra un messaggio di riepilogo
            if success_count > 0:
                # Emetti il segnale che sono stati aggiunti dei pezzi
                self.part_added.emit()
                
                # Aggiorna il combobox dei container
                self.populate_container_combo()
                
                message = f"Added {success_count} parts to container '{container_name}'."
                if error_count > 0:
                    message += f"\n{error_count} parts could not be added."
                if missing_id_count > 0:
                    message += f"\n{missing_id_count} parts were not found in the database."
                
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
                scaled = pixmap.scaled(self.icon_size, self.icon_size, 
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Ottieni l'item della tabella
                item = self.ui.tableWidget.item(row, 0)
                if item:
                    item.setIcon(QIcon(scaled))

