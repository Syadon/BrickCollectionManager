from PySide6.QtCore import QDir, QFile, QStringListModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from config import AppConfig
from src.containerSelectionDialog import ContainerSelectionDialog
from src.database import CollectionPart, Container, DatabaseManager
from src.logger import get_logger, log_exception
from src.partDetailDialog import PartDetailDialog
from src.partsFileParser import XmlParser
from src.utils import (
    TransparentSelectionDelegate,
    populate_color_combo,
    setup_color_combo_delegate,
)
from src.widgets.brickPreview import BrickPreview, get_global_image_provider
from src.widgets.colorLabel import ColorLabel
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
        # Use global image provider and keep references to BrickPreview widgets
        self.imgProvider = get_global_image_provider()
        self.preview_widgets = []

        # Containers to restrict the search to; None means all containers
        self.selected_container_ids: set[int] | None = None

        # Target container: the move destination for double-click actions
        self.target_container_id: int | None = None

        self.ui = Ui_SearchManualWidget()
        self.ui.setupUi(self)

        self.setupWidget()

    def setupWidget(self):
        self.ui.search_part_id_edit.textChanged.connect(self.on_part_id_changed)
        self.ui.search_part_name_edit.textChanged.connect(self.on_part_name_changed)
        self.ui.search_button.clicked.connect(self.perform_search)
        self.ui.search_clear_button.clicked.connect(self.clear_search)
        self.ui.openFileButton.clicked.connect(self.openFile)
        self.ui.selectContainersButton.clicked.connect(self.open_container_selection)
        self.ui.selectTargetButton.clicked.connect(self.open_target_selection)

        # Connect inputs to validation
        self.ui.search_part_id_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_part_name_edit.textChanged.connect(self.validate_search_inputs)
        self.ui.search_color_combo.currentIndexChanged.connect(
            self.validate_search_inputs
        )
        self.ui.search_color_type_combo.currentIndexChanged.connect(
            self.validate_search_inputs
        )
        self.ui.fileEdit.textChanged.connect(self.validate_search_inputs)

        table_header_labels = [
            "Image",
            "Container",
            "Quantity",
            "Part ID",
            "Part Name",
            "Category",
            "Color",
        ]
        tree = self.ui.search_results_tree
        tree.setColumnCount(7)
        tree.setHeaderLabels(table_header_labels)
        tree.setRootIsDecorated(True)
        tree.setUniformRowHeights(False)
        tree.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        tree.setSortingEnabled(True)
        tree.setItemDelegateForColumn(0, TransparentSelectionDelegate(tree))
        tree.setItemDelegateForColumn(6, TransparentSelectionDelegate(tree))

        # Column sizing: image column fixed (must hold the branch indicator +
        # the BrickPreview widget), the rest auto-fit their content.
        header = tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        for col in (1, 2, 3, 4, 5):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        # Image cell starts after the tree indentation (expand arrow)
        self._image_column_width = self.iconSize + tree.indentation() + 12
        tree.setColumnWidth(0, self._image_column_width)

        # Connect double-click signal
        tree.itemDoubleClicked.connect(self.on_result_double_clicked)

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
        populate_color_combo(
            self.ui.search_color_combo, dbManager, include_any_option=True
        )
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
        has_color_type = (
            self.ui.search_color_type_combo.currentIndex() > 0
        )  # Index 0 is "Any"
        has_file = bool(self.ui.fileEdit.text().strip())

        # Enable search if at least one criteria is provided
        is_valid = (
            has_part_id or has_part_name or has_color or has_color_type or has_file
        )
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

    # Note: on_image_loaded method removed - BrickPreview widgets handle image loading automatically

    def perform_search(self):
        filePath = self.ui.fileEdit.text()

        if self.ui.fileEdit.text() and QFile.exists(filePath):
            self.perform_file_search(filePath)
        else:
            self.perform_manual_search()

    def perform_file_search(self, filePath):
        self.logger.info(f"Performing file search: {filePath}")
        # Clear previous results
        self.ui.search_results_tree.clear()

        try:
            # Parse the file
            parser_result = XmlParser.parse_file(filePath)

            if not parser_result.success:
                # Mostra gli errori all'utente
                errors = "\n".join(parser_result.errors)
                self.logger.error(f"XML parsing failed: {errors}")
                QMessageBox.critical(
                    self, "XML Error", f"Could not parse the XML file:\n{errors}"
                )
                return

            if not parser_result.parts or len(parser_result.parts) == 0:
                self.logger.warning("No parts found in XML file")
                QMessageBox.information(
                    self, "No Results", "No parts found in the file."
                )
                return

            self.logger.info(f"Found {len(parser_result.parts)} parts in XML file")

            dbManager = self.db_manager

            partIdEdit = self.ui.search_part_id_edit.text()
            partNameEdit = self.ui.search_part_name_edit.text()

            # Extract color ID from color data tuple
            color_data = self.ui.search_color_combo.currentData()
            colorIdEdit = (
                color_data[0] if color_data is not None else None
            )  # color_data is (id, name, rgb)

            colorTypeEdit = self.ui.search_color_type_combo.currentData()

            # Flat list of CollectionPart (one per container) + required qty per brick
            results = []
            required_map: dict[tuple, int] = {}
            seen_keys = set()
            total_parts = len(parser_result.parts)
            missing_count = 0
            insufficient_count = 0

            # Process each part in the file
            for part_info in parser_result.parts:
                part_id = part_info["part_id"]
                color_id = part_info["color_id"]
                required_qty = part_info["quantity"]

                if partIdEdit and part_id != partIdEdit:
                    continue

                if colorIdEdit and color_id != int(colorIdEdit):
                    continue

                key = (part_id, color_id)

                # Cerca i container che contengono questo pezzo
                matching_parts = dbManager.searchIntoCollection(
                    part_id=part_id,
                    color_id=color_id,
                    include_original_box=self.ui.includeOriginalBoxCheck.isChecked(),
                    include_build=self.ui.includeBuildCheck.isChecked(),
                    container_ids=self._effective_container_ids(),
                )

                if len(matching_parts) < 1:
                    # Cerca informazioni sul pezzo anche se non è nella collezione
                    color_part_info = dbManager.searchColorsParts(
                        part_id=part_id, color_id=color_id
                    )

                    if color_part_info and len(color_part_info) > 0:
                        # Pezzo trovato nel catalogo ma non nella collezione
                        part_data = CollectionPart(
                            id=color_part_info[0]["id"],
                            part_id=color_part_info[0]["part_id"],
                            part_name=color_part_info[0]["part_name"],
                            part_category="Unknown",
                            color_id=color_part_info[0]["color_id"],
                            color_name=color_part_info[0]["color_name"],
                            rgb=color_part_info[0]["rgb"],
                            color_type=color_part_info[0]["color_type"],
                            container_name="Not in collection",
                            quantity=0,
                            container_id=None,
                        )
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
                            container_id=None,
                        )

                    if key not in seen_keys:
                        results.append(part_data)
                        seen_keys.add(key)
                    required_map[key] = required_map.get(key, 0) + required_qty
                    missing_count += 1
                    continue

                sample = matching_parts[0]

                if colorTypeEdit and sample.color_type != colorTypeEdit:
                    continue

                if (
                    partNameEdit
                    and partNameEdit.lower() not in sample.part_name.lower()
                ):
                    continue

                total_avail = sum(p.quantity for p in matching_parts)
                if key not in seen_keys:
                    results.extend(matching_parts)
                    seen_keys.add(key)
                required_map[key] = required_map.get(key, 0) + required_qty
                if total_avail < required_qty:
                    insufficient_count += 1

            self.populate_results_tree(results, required_map)

            # Mostra una sintesi dei risultati
            found_count = total_parts - missing_count
            if missing_count > 0 or insufficient_count > 0:
                QMessageBox.information(
                    self,
                    "Search Results",
                    f"Found {found_count} of {total_parts} parts in your collection.\n"
                    f"{missing_count} parts are missing, "
                    f"{insufficient_count} have insufficient quantity.",
                )

        except Exception as e:
            log_exception(e, "Error in perform_file_search")
            QMessageBox.critical(
                self, "Error", f"An error occurred while processing the file: {str(e)}"
            )

    def perform_manual_search(self):
        self.logger.info("Performing manual search")
        # Clear previous results
        self.ui.search_results_tree.clear()

        # Extract color name from color data tuple
        color_data = self.ui.search_color_combo.currentData()
        if color_data is not None:
            # color_data is a tuple: (id, name, rgb)
            colorName = color_data[1]
        else:
            colorName = None

        dbManager = DatabaseManager()
        results = dbManager.searchIntoCollection(
            part_id=self.ui.search_part_id_edit.text(),
            part_name=self.ui.search_part_name_edit.text(),
            color_name=colorName,
            color_type=self.ui.search_color_type_combo.currentData(),
            include_original_box=self.ui.includeOriginalBoxCheck.isChecked(),
            include_build=self.ui.includeBuildCheck.isChecked(),
            container_ids=self._effective_container_ids(),
        )

        # Display results
        if not results:
            self.logger.info("No results found for manual search")
            QMessageBox.information(
                self, "No Results", "No parts found matching your search criteria."
            )
            return

        self.logger.info(f"Found {len(results)} results for manual search")
        self.populate_results_tree(results)

    def populate_results_tree(
        self, results: list[CollectionPart], required_map: dict | None = None
    ):
        """Group flat search results by brick (part + color) into an expandable tree.

        Each top-level item is a brick; its children are the containers holding it.
        When ``required_map`` is given (file search) the brick row shows
        "available / required" and is highlighted red when stock is insufficient.
        """
        tree = self.ui.search_results_tree
        tree.setSortingEnabled(False)
        tree.clear()
        self.preview_widgets.clear()

        # Group results by (part_id, color_id), preserving first-seen order
        groups: dict[tuple, list[CollectionPart]] = {}
        order: list[tuple] = []
        for part in results:
            key = (part.part_id, part.color_id)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(part)

        red = QColor(255, 0, 0)

        for key in order:
            parts = groups[key]
            first = parts[0]

            required = required_map.get(key) if required_map else None

            # Quantity of this brick already inside the target container
            target_qty = None
            if self.target_container_id is not None:
                target_qty = sum(
                    p.quantity
                    for p in parts
                    if p.container_id == self.target_container_id
                )
                # Hide bricks already fully stocked in the target container —
                # only the still-missing parts stay in the results.
                if required is not None and target_qty >= required:
                    continue

            brick_item = QTreeWidgetItem(tree)
            brick_item.setText(1, f"{len(parts)} container(s)")
            brick_item.setText(3, first.part_id)
            brick_item.setText(4, first.part_name)
            brick_item.setText(5, first.part_category)

            total = sum(p.quantity for p in parts)
            target_suffix = (
                f"  (in target: {target_qty})" if target_qty is not None else ""
            )
            if required is not None:
                brick_item.setText(2, f"{total} / {required}{target_suffix}")
                if total < required:
                    brick_item.setForeground(2, red)
            elif target_suffix:
                brick_item.setText(2, f"{total}{target_suffix}")
            else:
                brick_item.setData(2, Qt.ItemDataRole.DisplayRole, total)

            # Store data for the detail dialog / double-click handler
            brick_item.setData(0, Qt.ItemDataRole.UserRole, (first, required))

            # Image + color widgets (only on the brick row; children share them)
            preview = BrickPreview(
                part_id=first.part_id,
                color_id=str(first.color_id),
                size=self.iconSize,
                parent=self,
            )
            tree.setItemWidget(brick_item, 0, preview)
            self.preview_widgets.append(preview)

            color_label = ColorLabel(
                first.color_name,
                first.rgb if first.rgb else None,
                first.color_type,
                first.color_id,
            )
            tree.setItemWidget(brick_item, 6, color_label)

            # One child per container holding this brick
            for part in parts:
                child = QTreeWidgetItem(brick_item)
                child.setText(1, part.container_name)
                child.setData(2, Qt.ItemDataRole.DisplayRole, part.quantity)
                child.setData(0, Qt.ItemDataRole.UserRole, (part, required))
                # Pseudo-containers (missing / not in DB) are highlighted red
                if part.container_id is None:
                    child.setForeground(1, red)
                    child.setForeground(2, red)

        tree.setSortingEnabled(True)
        tree.setColumnWidth(0, self._image_column_width)

    def open_container_selection(self):
        dialog = ContainerSelectionDialog(self, self.selected_container_ids)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dialog.selected_container_ids()
        all_ids = {c.id for c in self.db_manager.getContainers()}
        # If every container is selected, store None to keep "all" semantics
        self.selected_container_ids = None if selected == all_ids else selected

    def open_target_selection(self):
        preselect = (
            {self.target_container_id}
            if self.target_container_id is not None
            else None
        )
        dialog = ContainerSelectionDialog(self, preselect, single_selection=True)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.target_container_id = dialog.selected_container_id()
        self._update_target_button_text()

    def _update_target_button_text(self):
        if self.target_container_id is None:
            self.ui.selectTargetButton.setText("Select Target…")
            return
        container = self.db_manager.getContainerById(self.target_container_id)
        name = container.name if container else str(self.target_container_id)
        self.ui.selectTargetButton.setText(f"Select Target… ({name})")

    def _effective_container_ids(self) -> set[int] | None:
        """Container set to search: the restricted set, plus the target if it
        would otherwise be filtered out. None means all containers."""
        if self.selected_container_ids is None:
            return None
        if (
            self.target_container_id is not None
            and self.target_container_id not in self.selected_container_ids
        ):
            return self.selected_container_ids | {self.target_container_id}
        return self.selected_container_ids

    def clear_search(self):
        self.ui.search_part_id_edit.clear()
        self.ui.search_part_name_edit.clear()
        self.ui.search_color_combo.setCurrentIndex(0)
        self.ui.search_color_type_combo.setCurrentIndex(0)
        self.ui.search_results_tree.clear()
        self.ui.fileEdit.clear()
        self.ui.includeOriginalBoxCheck.setChecked(False)
        self.ui.includeBuildCheck.setChecked(False)
        self.selected_container_ids = None
        self.target_container_id = None
        self._update_target_button_text()
        self.preview_widgets.clear()
        # Validation will be triggered by the clear operations above

    def on_result_double_clicked(self, item, column):
        # Brick (top-level) rows just toggle expansion
        if item.parent() is None:
            item.setExpanded(not item.isExpanded())
            return

        part_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not part_data:
            return

        part = part_data[0]
        container_id = part.container_id
        container_name = part.container_name
        qty = part.quantity
        required_qty = part_data[1]

        # Create container object
        container = Container(container_id, container_name, "", 0, 0)

        # Current stock of this brick already in the target container
        target_qty = 0
        if self.target_container_id is not None:
            brick_item = item.parent()
            for i in range(brick_item.childCount()):
                child_data = brick_item.child(i).data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data[0].container_id == self.target_container_id:
                    target_qty = child_data[0].quantity
                    break

        # Move qty default: for file searches, the amount still missing in the
        # target, capped by what this container holds; otherwise this row's qty.
        if required_qty is not None:
            missing = max(required_qty - target_qty, 0)
            max_move = min(qty, missing)
        else:
            max_move = qty
        defaultQty = max(1, min(max_move, qty))

        # Don't preselect the target as destination of a move out of itself
        target_for_dialog = (
            self.target_container_id
            if self.target_container_id != container_id
            else None
        )

        # Open part detail dialog
        dialog = PartDetailDialog(
            part,
            container,
            qty=defaultQty,
            outsideDefault=target_for_dialog is None,
            target_container_id=target_for_dialog,
            parent=self,
        )
        result = dialog.exec()

        # If the dialog was accepted (changed were made), refresh the search results
        if result == QDialog.DialogCode.Accepted:
            self.perform_search()  # Re-run the search to refresh the results

    def openFile(self):
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
