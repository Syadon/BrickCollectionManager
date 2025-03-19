from PySide6.QtWidgets import (QDialog, QTableView)
from containerPartsModel import ContainerPartsModel
from database import DatabaseManager
from utils import TransparentSelectionDelegate
from partDetailDialog import PartDetailDialog
from ui.ui_containerDetailDialog import Ui_containerDetailDialog

class ContainerDetailDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        
        # Create and setup UI
        self.ui = Ui_containerDetailDialog()
        self.ui.setupUi(self)

        self.container = container

        # Setup container info
        self.ui.name_edit.setText(container.name)
        self.ui.description_edit.setText(container.description)
        self.ui.part_count_label.setText(str(container.part_count))
        self.ui.lots_count_label.setText(str(container.lot_count))

        # Setup parts table
        self.setup_parts_table()

    def setup_parts_table(self):
        dbManager = DatabaseManager()
        self.dbManager = dbManager  # Store for later use

        parts_data = dbManager.getContainersParts(self.container.id)
        
        # Create and set model
        self.parts_model = ContainerPartsModel(parts_data)
        self.ui.partsView.setModel(self.parts_model)
        
        # Configure table view
        self.ui.partsView.setSelectionBehavior(QTableView.SelectRows)
        self.ui.partsView.setSelectionMode(QTableView.SingleSelection)
        
        # Imposta l'altezza delle righe in base alle immagini (64px)
        self.ui.partsView.verticalHeader().setDefaultSectionSize(70)
        
        # Nascondi l'header verticale
        self.ui.partsView.verticalHeader().setVisible(False)
        
        # Imposta la larghezza della colonna immagine
        self.ui.partsView.setColumnWidth(0, 70)  # Colonna immagine
        
        # Impedisci che la colonna dell'immagine mostri lo sfondo di selezione        
        delegate = TransparentSelectionDelegate(self.ui.partsView)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.imageColumnIndex, delegate)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.colorColumnIndex, delegate)
        
        # Ridimensiona le altre colonne in base al contenuto
        self.ui.partsView.resizeColumnsToContents()
        
        # Connect double-click signal
        self.ui.partsView.doubleClicked.connect(self.on_part_double_clicked)

    def on_part_double_clicked(self, index):
        row_index = index.row()
        part_data = self.parts_model.parts_data[row_index]
        dialog = PartDetailDialog(part_data, self.container, self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh the parts list
            self.refresh_parts_table()
            
    def refresh_parts_table(self):
        parts_data = self.dbManager.getContainersParts(self.container.id)
        self.parts_model = ContainerPartsModel(parts_data)
        self.ui.partsView.setModel(self.parts_model)
        
        # Update counts
        self.ui.part_count_label.setText(str(self.dbManager.getConteinerPartCount(self.container.id)))
        self.ui.lots_count_label.setText(str(self.dbManager.getConteinerLotCount(self.container.id)))
        
        # Reapply delegate
        delegate = TransparentSelectionDelegate(self.ui.partsView)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.imageColumnIndex, delegate)
        self.ui.partsView.setItemDelegateForColumn(self.parts_model.colorColumnIndex, delegate)
        
        # Ridimensiona le colonne
        self.ui.partsView.resizeColumnsToContents()

    def accept(self):
        db_manager = DatabaseManager()
        
        # Update container object
        self.container.name = self.ui.name_edit.text()
        self.container.description = self.ui.description_edit.text()
        
        # Save to database
        if db_manager.updateContainer(self.container):
            super().accept()

