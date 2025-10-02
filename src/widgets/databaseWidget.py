from PySide6.QtWidgets import (QWidget, QFileDialog, QMessageBox, QDialogButtonBox)
from PySide6.QtCore import QDir
from ui.ui_databaseWidget import Ui_DatabaseWidget
from src.database import DatabaseManager
import os
import logging
import shutil
from datetime import datetime
from config import AppConfig
import xml.etree.ElementTree as ET

class DatabaseWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = Ui_DatabaseWidget()
        self.ui.setupUi(self)
        
        # Connetti il pulsante alla funzione
        self.ui.openFilesDirButton.clicked.connect(self.select_directory)
        
        # Connetti i pulsanti standard di dialogo
        self.ui.updateDBButton.clicked.connect(self.update_database)
        self.ui.dbRestorePointButton.clicked.connect(self.create_restore_database)
        # Inizializza il database manager
        self.db_manager = DatabaseManager()
        
        # Variabile per tracciare il percorso della directory selezionata
        self.selected_directory = None
        self.all_files_found = False

    def update_dbUpdate_button_state(self):
        if self.all_files_found:
            self.ui.updateDBButton.setEnabled(True)
        else:
            self.ui.updateDBButton.setEnabled(False)
    
    def select_directory(self):
        """Apre un dialogo per selezionare una directory"""
        # Ottieni la directory iniziale (cartella documenti dell'utente)
        initial_dir = QDir.homePath()
        
        # Mostra il dialogo di selezione directory
        directory = QFileDialog.getExistingDirectory(
            self,                           # parent widget
            "Select Directory with XML Files",  # titolo del dialogo
            initial_dir,                    # directory iniziale
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks  # opzioni
        )
        
        # Verifica se l'utente ha selezionato una directory
        if directory:
            # Salva la directory selezionata
            self.selected_directory = directory
            
            # # Visualizza il percorso nella UI
            # self.ui.directoryEdit.setText(directory)
            
            # Controlla i file nella directory
            self.check_directory_content(directory)
    
    def check_directory_content(self, directory):
        """Verifica se nella directory sono presenti i file XML richiesti e aggiorna l'UI"""
        try:
            # Lista dei file richiesti e corrispondenti campi di testo nell'UI
            required_files = [
                ("colors.xml", self.ui.colorsEdit),
                ("categories.xml", self.ui.categoriesEdit),
                ("parts.xml", self.ui.partsEdit),
                ("codes.xml", self.ui.colorPartEdit)
            ]
            
            # Flag per verificare se tutti i file sono stati trovati
            self.all_files_found = True
            
            # Pulisci i campi di testo
            for _, edit_field in required_files:
                edit_field.clear()
                edit_field.setStyleSheet("")
            
            # Cerca i file nella directory e nelle sue sottodirectory
            for root, _, files in os.walk(directory):
                for file_name, edit_field in required_files:
                    # Se il campo è già popolato, salta (abbiamo già trovato il file)
                    if edit_field.text():
                        continue
                        
                    # Controlla se il file esiste in questa directory
                    if file_name.lower() in [f.lower() for f in files]:
                        # Costruisci il percorso completo
                        file_path = os.path.join(root, file_name)
                        
                        # Verifica se è un file XML valido
                        if self.is_valid_xml_file(file_path):
                            # Mostra il percorso nel campo di testo
                            edit_field.setText(file_path)
                            edit_field.setStyleSheet("color: green;")
                        else:
                            # File trovato ma non valido
                            edit_field.setText(f"{file_path} (INVALID)")
                            edit_field.setStyleSheet("color: red;")
                            self.all_files_found = False
            
            # Verifica quali file non sono stati trovati
            missing_files = []
            for file_name, edit_field in required_files:
                if not edit_field.text():
                    edit_field.setText(f"Not found")
                    edit_field.setStyleSheet("color: red;")
                    missing_files.append(file_name)
                    self.all_files_found = False
            
            # Aggiorna l'interfaccia con un messaggio appropriato
            if self.all_files_found:
                QMessageBox.information(self, "Files Found", "All required XML files were found.\nClick OK to update the database.")
            else:
                #QMessageBox.warning(self, "Missing Files", f"The following files were not found:\n {'\n• '.join(missing_files)}\n\nPlease select a different directory.")
                QMessageBox.warning(self, "Missing Files", f"Missing files!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error scanning directory: {str(e)}")
            logging.error(f"Error scanning directory {directory}: {str(e)}")
            
        self.update_dbUpdate_button_state()

    def is_valid_xml_file(self, file_path):
        """Verifica se un file è un XML valido che può essere aperto e letto"""
        try:
            # Verifica se il file esiste e può essere aperto
            if not os.path.isfile(file_path):
                return False
                
            # Verifica se è un file XML valido
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Se siamo arrivati qui, il file è un XML valido
            return True
            
        except Exception as e:
            logging.warning(f"Invalid XML file {file_path}: {str(e)}")
            return False
    
    def update_database(self):
        dbManager = DatabaseManager()
        try:
            # Ottieni i percorsi dei file XML dai campi di testo
            colors_file = self.ui.colorsEdit.text()
            categories_file = self.ui.categoriesEdit.text()
            parts_file = self.ui.partsEdit.text()
            codes_file = self.ui.colorPartEdit.text()
            
            # Aggiorna il database con i file XML selezionati
            if not dbManager.import_colors_from_xml(colors_file):
                raise Exception("Failed to import colors from XML")
            
            if not dbManager.import_categories_from_xml(categories_file):
                raise Exception("Failed to import categories from XML")
            
            if not dbManager.import_parts_from_xml(parts_file):
                raise Exception("Failed to import parts from XML")
            
            if not dbManager.import_color_parts_from_xml(codes_file):
                raise Exception("Failed to import color parts from XML")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update the database: {str(e)}")
            logging.error(f"Failed to update the database: {str(e)}")
        else:
            QMessageBox.information(self, "Success", "Database has been successfully updated.")
            logging.error(f"Database has been successfully updated.")

    def create_restore_database(self):
        """Creates a backup copy of the database file with timestamp"""
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%Y_%m_%d")
            
            # Base backup filename
            base_backup_name = f"{AppConfig.DATABASE_FILE_NAME}_{timestamp}.db"
            backup_file_name = base_backup_name
            
            # Get the directory path from DATABASE_PATH
            backup_dir = AppConfig.DATABASE_PATH.parent
            backup_path = backup_dir / backup_file_name
            
            # Check if file exists and append counter if needed
            counter = 2
            while os.path.exists(backup_path):
                backup_file_name = f"brick_collection_{timestamp}_{counter}.db"
                backup_path = backup_dir / backup_file_name
                counter += 1

            # Copy the database file
            shutil.copy2(AppConfig.DATABASE_PATH, backup_path)
            
            QMessageBox.information(self, "Success", f"Database restore point created: {backup_path}")
            logging.info(f"Database backup created: {backup_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create database restore point: {str(e)}")
            logging.error(f"Failed to create database backup: {str(e)}")
        