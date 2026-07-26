import logging

from PySide6.QtCore import QDir, QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QMenu,
    QMessageBox,
    QSpinBox,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from config import AppConfig
from src import utils
from src.database import Container, DatabaseManager
from src.logger import get_logger, log_exception
from src.partsFileParser import XmlParser
from src.utils import TransparentSelectionDelegate
from src.widgets.brickPreview import BrickPreview
from src.widgets.colorLabel import ColorLabel
from ui.ui_addFromFileWidget import Ui_AddFromFileWidget


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
        editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return editor

    def setEditorData(self, editor, index):
        """Imposta il valore dell'editor in base al valore nella cella"""
        value = int(index.model().data(index, Qt.ItemDataRole.DisplayRole) or 0)
        editor.setValue(value)

    def setModelData(self, editor, model, index):
        """Imposta il valore del modello quando l'editing è completato"""
        editor.interpretText()
        value = editor.value()
        model.setData(index, value, Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        """Aggiorna la geometria dell'editor"""
        editor.setGeometry(option.rect)

    def displayText(self, value, locale):
        """Formatta il valore per la visualizzazione"""
        try:
            return str(int(value))
        except Exception:
            return str(value)


class AddFromFileWidget(QWidget):
    # Signal emitted when parts are added to a container
    part_added = Signal()

    # Testo mostrato in fileEdit quando l'XML arriva dagli appunti
    CLIPBOARD_SOURCE_LABEL = "[Clipboard]"

    def __init__(self, container: Container | None = None, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.logger.debug("Initializing AddFromFileWidget")

        self.ui = Ui_AddFromFileWidget()
        self.ui.setupUi(self)

        self.targetContainer = container

        # Use global image provider and keep references to BrickPreview widgets
        self.iconSize = AppConfig.DEFAULT_ICON_SIZE
        self.preview_widgets = []

        # Connetti il pulsante openFile all'azione di apertura del file
        self.ui.openFileButton.clicked.connect(self.open_file_dialog)

        # Connetti il pulsante paste al caricamento dell'XML dagli appunti
        self.ui.pasteButton.clicked.connect(self.load_from_clipboard)

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
        self.ui.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.tableWidget.customContextMenuRequested.connect(self.show_context_menu)

        # List to store parts data from file
        self.parts_data = []

    def setup_table(self):
        headers = ["Image", "ID", "Name", "Color", "Quantity"]
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)

        # Imposta l'altezza delle righe per le immagini
        self.ui.tableWidget.verticalHeader().setDefaultSectionSize(self.iconSize + 4)
        self.ui.tableWidget.verticalHeader().setVisible(False)

        self.ui.tableWidget.setItemDelegateForColumn(
            0, TransparentSelectionDelegate(self.ui.tableWidget)
        )
        self.ui.tableWidget.setItemDelegateForColumn(
            3, TransparentSelectionDelegate(self.ui.tableWidget)
        )

        # Imposta il delegate per la colonna della quantità (colonna 4)
        self.ui.tableWidget.setItemDelegateForColumn(
            4, SpinBoxDelegate(self.ui.tableWidget, 1, 9999)
        )

        # Consenti l'editing solo per la colonna della quantità
        # self.ui.tableWidget.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

        self.ui.tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

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
            self,  # parent widget
            "Select XML File",  # titolo del dialogo
            initial_dir,  # directory iniziale
            "XML Files (*.xml);;All Files (*.*)",  # filtro per i file
        )

        # Se un file è stato selezionato, imposta il percorso nel campo di testo
        if file_path:
            self.ui.fileEdit.setText(file_path)

    def load_file(self):
        """Carica e elabora il file XML specificato nel campo fileEdit"""
        file_path = self.ui.fileEdit.text()
        if not file_path:
            QMessageBox.warning(
                self, "No File Selected", "Please select an XML file first."
            )
            return

        if file_path == self.CLIPBOARD_SOURCE_LABEL:
            QMessageBox.warning(
                self,
                "No File Selected",
                "The last import came from the clipboard. "
                "Use 'Paste XML' again or select an XML file.",
            )
            return

        self.logger.info(f"Parsing XML file: {file_path}")
        self._load_parts(lambda: XmlParser.parse_file(file_path), "file")

    def load_from_clipboard(self):
        """Carica e elabora l'XML copiato negli appunti (es. da Rebrickable)"""
        xml_text = QGuiApplication.clipboard().text()

        if not xml_text or not xml_text.strip():
            QMessageBox.warning(
                self,
                "Empty Clipboard",
                "The clipboard does not contain any text. "
                "Copy the XML content first.",
            )
            return

        self.ui.fileEdit.setText(self.CLIPBOARD_SOURCE_LABEL)
        self.logger.info(f"Parsing XML from clipboard ({len(xml_text)} chars)")
        self._load_parts(lambda: XmlParser.parse_string(xml_text), "clipboard")

    def _load_parts(self, parse_callable, source_desc):
        """Esegue il parsing tramite parse_callable ed elabora il risultato

        source_desc descrive l'origine dei dati ("file" o "clipboard") ed è usato
        nei messaggi mostrati all'utente.
        """
        try:
            # Pulisci la tabella e i dati esistenti
            self.clear_table()

            parser_result = parse_callable()

            if not parser_result.success:
                # Mostra gli errori all'utente
                errors = "\n".join(parser_result.errors)
                self.logger.error(f"XML parsing failed: {errors}")
                QMessageBox.critical(
                    self,
                    "XML Error",
                    f"Could not parse the XML from the {source_desc}:\n{errors}",
                )
                return

            if len(parser_result.warnings) > 0:
                # Mostra avvisi non bloccanti
                warnings = "\n".join(parser_result.warnings)
                self.logger.warning(f"XML parsing warnings: {warnings}")

            self.logger.info(
                f"Successfully parsed {len(parser_result.parts)} parts from XML"
            )

            # Prepara le query per il database
            db_manager = DatabaseManager()

            # Elabora le parti trovate nel file XML
            parts_to_add = []
            missing_parts = []

            for part_info in parser_result.parts:
                part_id = part_info["part_id"]
                color_id = part_info["color_id"]
                quantity = part_info["quantity"]

                # Cerca il pezzo e il colore nel database
                color_parts = db_manager.searchColorsParts(
                    part_id=part_id, color_id=color_id
                )

                if color_parts:
                    # Aggiungi ai pezzi da visualizzare
                    part_data = color_parts[0]
                    part_data["quantity"] = quantity
                    parts_to_add.append(part_data)
                else:
                    # Registra i pezzi mancanti per informare l'utente
                    missing_parts.append((part_id, color_id, quantity))

            # Aggiungi i pezzi alla tabella
            self.add_parts_to_table(parts_to_add)

            # Mostra un messaggio di riepilogo
            if len(parts_to_add) > 0:
                message = f"Loaded {len(parts_to_add)} parts from the {source_desc}."
                if missing_parts:
                    message += (
                        f"\n{len(missing_parts)} parts were not found in the database."
                    )
                    # Create a formatted list of missing parts to show to the user
                    missing_part_list = "\n".join(
                        [
                            f"  - {p[0]} (color {p[1]}): {p[2]} pcs"
                            for p in missing_parts[:10]
                        ]
                    )
                    if len(missing_parts) > 10:
                        missing_part_list += (
                            f"\n  ... and {len(missing_parts) - 10} more"
                        )
                    message += f"\n\nMissing parts:\n{missing_part_list}"
                QMessageBox.information(self, "XML Loaded", message)
            elif missing_parts:
                part_list = "\n".join(
                    [f"{p[0]} (color {p[1]}): {p[2]} pcs" for p in missing_parts[:5]]
                )
                if len(missing_parts) > 5:
                    part_list += f"\n... and {len(missing_parts) - 5} more"
                QMessageBox.warning(
                    self,
                    "No Parts Found",
                    f"None of the {len(missing_parts)} parts in the {source_desc} were found in the database.\nExamples:\n{part_list}",
                )
            else:
                QMessageBox.warning(
                    self,
                    "No Parts Found",
                    f"No parts were found in the XML from the {source_desc} "
                    "or the format is not supported.",
                )

        except Exception as e:
            log_exception(e, f"Error loading XML from {source_desc}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while loading the {source_desc}: {str(e)}",
            )

        self.update_add_button_state()

    def add_parts_to_table(self, parts_data):
        # Disconnetti il segnale cellChanged temporaneamente per evitare chiamate durante il popolamento
        self.ui.tableWidget.cellChanged.disconnect(self.on_cell_changed)

        # Clear previous preview widgets
        self.preview_widgets.clear()

        self.parts_data = parts_data
        self.ui.tableWidget.setRowCount(len(parts_data))

        for row, part in enumerate(parts_data):
            # Crea gli elementi della tabella

            # Colonna immagine - use BrickPreview widget
            if "part_id" in part and "color_id" in part:
                preview = BrickPreview(
                    part_id=part["part_id"],
                    color_id=str(part["color_id"]),
                    size=self.iconSize,
                    parent=self,
                )
                self.ui.tableWidget.setCellWidget(row, 0, preview)
                self.preview_widgets.append(preview)

            # Colonna Part ID
            id_item = QTableWidgetItem(part.get("part_id", "Unknown"))
            self.ui.tableWidget.setItem(row, 1, id_item)

            # Colonna Part Name
            name_item = QTableWidgetItem(part.get("part_name", "Unknown"))
            name_item.setFlags(
                name_item.flags()
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
            )
            self.ui.tableWidget.setItem(row, 2, name_item)
            name_item.setSizeHint(QSize(400, self.iconSize))

            # Colonna Color using ColorLabel widget
            rgb_hex = part.get("rgb") if part.get("rgb") else None
            color_label = ColorLabel(
                part.get("color_name", "Unknown"),
                rgb_hex,
                part.get("color_type", "Unknown"),
                part.get("color_id"),
            )
            self.ui.tableWidget.setCellWidget(row, 3, color_label)

            # Colonna Quantity - imposta l'EditRole per permettere l'editing
            qty_item = QTableWidgetItem()
            qty_item.setData(Qt.ItemDataRole.EditRole, part.get("quantity", 1))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tableWidget.setItem(row, 4, qty_item)

        # Regola la larghezza delle colonne
        self.ui.tableWidget.setColumnWidth(0, self.iconSize + 8)
        self.ui.tableWidget.resizeColumnsToContents()

        # Limit Name column width
        name_column_index = 2
        max_name_width = 400
        if self.ui.tableWidget.columnWidth(name_column_index) > max_name_width:
            self.ui.tableWidget.setColumnWidth(name_column_index, max_name_width)

        self.ui.tableWidget.setWordWrap(True)
        self.ui.tableWidget.resizeRowsToContents()
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)

        # Riconnetti il segnale cellChanged
        self.ui.tableWidget.cellChanged.connect(self.on_cell_changed)

    def clear_table(self):
        """Pulisce la tabella e i dati associati"""
        self.ui.tableWidget.setRowCount(0)
        self.parts_data = []
        self.preview_widgets.clear()
        self.update_add_button_state()

    def populate_container_combo(self):
        utils.populate_container_combo(
            self.ui.containerCombo, DatabaseManager(), self.targetContainer
        )

        # Setup custom delegate for better rendering
        utils.setup_container_combo_delegate(self.ui.containerCombo)

        # Connect to selection change event if not already connected
        try:
            self.ui.containerCombo.currentIndexChanged.disconnect(
                self.on_container_selection_changed
            )
        except Exception:
            pass
        self.ui.containerCombo.currentIndexChanged.connect(
            self.on_container_selection_changed
        )

        # Update add button state
        self.on_container_selection_changed(self.ui.containerCombo.currentIndex())

    def hideEvent(self, event):
        # Reset to dummy container
        self.ui.containerCombo.setCurrentIndex(0)
        self.clear_table()
        self.ui.fileEdit.clear()
        super().hideEvent(event)

    def showEvent(self, event):
        self.populate_container_combo()
        return super().showEvent(event)

    def on_container_selection_changed(self, index):
        self.update_add_button_state()

    def update_add_button_state(self):
        # Disable add button if dummy container is selected
        container_data = self.ui.containerCombo.currentData()
        self.ui.pushButton.setEnabled(
            container_data is not None and self.ui.tableWidget.rowCount() > 0
        )

    def add_to_container(self):
        """Aggiunge i pezzi selezionati al container selezionato"""
        # Verifica che sia selezionato un containers
        if self.ui.containerCombo.count() == 0:
            QMessageBox.warning(
                self, "No Container", "Please create a container first."
            )
            return

        # Ottieni il container selezionato
        container_data = self.ui.containerCombo.currentData()
        if not container_data:
            QMessageBox.warning(
                self, "Invalid Container", "Please select a valid container."
            )
            return

        # Extract container ID and name from data tuple (id, name, type, part_count)
        container_id: int = -1
        container_name: str = "Unknown"
        try:
            if isinstance(container_data, tuple):
                container_id = container_data[0]
                container_name = (
                    container_data[1] if len(container_data) > 1 else "Unknown"
                )
        except Exception:
            pass

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
                quantity = part_data["quantity"]

                # Verifica che il pezzo abbia un ID di color_part
                if part_data.get("id") is None:
                    # Cerca il color_part nel database
                    color_part = db_manager.getColorPart(
                        part_data["part_id"], part_data["color_id"]
                    )

                    if color_part:
                        part_data["id"] = color_part.id
                    else:
                        missing_id_count += 1
                        missing_qty += quantity
                        continue

                # Aggiungi il pezzo al container
                if db_manager.addColorPartIDToContainer(
                    part_data["id"], container_id, quantity
                ):
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
                utils.update_container_combo_single_parts_count(
                    self.ui.containerCombo,
                    db_manager,
                    self.ui.containerCombo.currentIndex(),
                )

                message = f"Added {success_count} lots to container '{container_name}'."
                if error_count > 0:
                    message += f"\n{error_count} lots could not be added."
                if missing_id_count > 0:
                    message += (
                        f"\n{missing_id_count} lots were not found in the database."
                    )

                QMessageBox.information(self, "Parts Added", message)
            else:
                message = "No parts were added to the container."
                if missing_id_count > 0:
                    message += (
                        f"\n{missing_id_count} parts were not found in the database."
                    )

                QMessageBox.warning(self, "No Parts Added", message)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            logging.error(f"Error adding parts to container: {str(e)}")

    # Note: on_image_loaded method removed - BrickPreview widgets handle image loading automatically

    def on_cell_changed(self, row, column):
        """Gestisce le modifiche alle celle della tabella"""
        # Aggiorna solo se è la colonna della quantità (colonna 4)
        if column == 4 and row < len(self.parts_data):
            item = self.ui.tableWidget.item(row, column)
            if item:
                try:
                    new_value = int(item.text())
                    if new_value > 0:
                        # Aggiorna il valore nei dati
                        self.parts_data[row]["quantity"] = new_value
                except ValueError:
                    # Ripristina il valore originale se non è un numero valido
                    item.setText(str(self.parts_data[row].get("quantity", 1)))

    def show_context_menu(self, position):
        index = self.ui.tableWidget.indexAt(position)

        if index.isValid():
            context_menu = QMenu(self)
            remove_action = context_menu.addAction("Remove")

            # Aggiungi opzioni per modificare la quantità
            edit_qty_action = context_menu.addAction("Edit Quantity")

            # Show context menu at cursor position
            action = context_menu.exec(
                self.ui.tableWidget.viewport().mapToGlobal(position)
            )

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
