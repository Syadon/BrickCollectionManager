from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from config import AppConfig
from src.database import (
    CONTAINER_TYPE_LABELS,
    CONTAINER_TYPE_VALUES,
    DatabaseManager,
)
from src.partCloneDialog import PartCloneDialog
from src.partColorChangeDialog import PartColorChangeDialog
from src.partDetailDialog import PartDetailDialog
from src.partsMovementDialog import PartsMovementDialog
from src.widgets.brickPreview import BrickPreview, get_global_image_provider
from src.widgets.colorLabel import ColorLabel
from ui.ui_containerDetailDialog import Ui_containerDetailDialog


class ContainerDetailDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)

        # Create and setup UI
        self.ui = Ui_containerDetailDialog()
        self.ui.setupUi(self)

        self.container = container
        self.parent_widget = parent

        # Setup container info
        self.ui.name_edit.setText(container.name)
        self.ui.description_edit.setText(container.description)
        self.ui.part_count_label.setText(str(container.part_count))
        self.ui.lots_count_label.setText(str(container.lot_count))

        # Setup type combobox
        if hasattr(container, "type"):
            self.ui.type_combobox.setCurrentText(
                CONTAINER_TYPE_LABELS.get(container.type, "Box")
            )

        # Add delete button
        self.delete_button = QPushButton("Delete Container")
        self.delete_button.setProperty("class", "danger")

        # Add button to the bottom layout by inserting before buttonBox
        main_layout = self.ui.verticalLayout

        # Create horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()  # Add stretch to push buttonBox to the right
        button_layout.addWidget(self.ui.buttonBox)

        # Remove buttonBox from main layout and add the new button layout
        main_layout.removeWidget(self.ui.buttonBox)
        main_layout.addLayout(button_layout)

        # Connect delete button
        self.delete_button.clicked.connect(self.on_delete_clicked)

        # Setup parts table

        self.name_column_index = 2
        self.max_name_width = 400
        self.type_column_index = 3
        self.max_type_width = 200

        self._sort_col: int | None = None
        self._sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
        self._sort_attr_by_col = {
            1: "part_id",
            2: "part_name",
            3: "part_category",
            4: "color_name",
            5: "quantity",
        }

        self.setup_parts_table()

        # Set dialog size based on parent window if available
        if self.parent_widget:
            parent_size = self.parent_widget.size()
            dialog_width = int(parent_size.width() * 0.9)
            dialog_height = int(parent_size.height() * 0.9)
            self.resize(dialog_width, dialog_height)
        else:
            # Default size if no parent
            self.resize(800, 600)

    def setup_parts_table(self):
        dbManager = DatabaseManager()
        self.dbManager = dbManager  # Store for later use

        self.parts_data = dbManager.getContainersParts(self.container.id)

        # Use global image provider and keep references to BrickPreview widgets
        self.imgProvider = get_global_image_provider()
        self.preview_widgets = []

        # Setup table headers
        headers = ["Image", "ID", "Part", "Category", "Color", "Quantity"]
        self.ui.partsView.setColumnCount(len(headers))
        self.ui.partsView.setHorizontalHeaderLabels(headers)

        # Set row count
        self.ui.partsView.setRowCount(len(self.parts_data))

        # Configure table widget
        self.ui.partsView.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.ui.partsView.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )

        # Right-click context menu for bulk actions
        self.ui.partsView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.partsView.customContextMenuRequested.connect(
            self.on_parts_context_menu
        )

        # Click headers to sort
        header = self.ui.partsView.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self.on_header_clicked)

        # Set row height for images (64px)
        self.ui.partsView.verticalHeader().setDefaultSectionSize(70)

        # Hide vertical header
        self.ui.partsView.verticalHeader().setVisible(False)

        # Set image column width
        self.ui.partsView.setColumnWidth(0, 70)  # Image column

        # Populate table with data
        self.populate_table_data()

        # Resize columns to content
        self.ui.partsView.resizeColumnsToContents()

        # Limit Name column width
        if self.ui.partsView.columnWidth(self.name_column_index) > self.max_name_width:
            self.ui.partsView.setColumnWidth(
                self.name_column_index, self.max_name_width
            )

        self.ui.partsView.setColumnWidth(self.type_column_index, 150)  # Category column

        self.ui.partsView.setWordWrap(True)
        self.ui.partsView.resizeRowsToContents()
        self.ui.partsView.horizontalHeader().setStretchLastSection(True)

        # Connect double-click signal
        self.ui.partsView.cellDoubleClicked.connect(self.on_part_double_clicked)

    def populate_table_data(self):
        """Populate the table widget with parts data"""
        for row, part in enumerate(self.parts_data):
            # Image column (0) - use BrickPreview widget
            if hasattr(part, "color_id") and hasattr(part, "part_id"):
                preview = BrickPreview(
                    part_id=part.part_id,
                    color_id=str(part.color_id),
                    size=64,
                    parent=self,
                )
                self.ui.partsView.setCellWidget(row, 0, preview)
                self.preview_widgets.append(preview)

            # ID column (1)
            id_item = QTableWidgetItem(str(part.part_id))
            id_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 1, id_item)

            # Part name column (2)
            name_item = QTableWidgetItem(part.part_name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.ui.partsView.setItem(row, 2, name_item)

            # Category column (3)
            category_item = QTableWidgetItem(part.part_category)
            category_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            self.ui.partsView.setItem(row, 3, category_item)

            # Color column (4) - using ColorLabel widget
            rgb_hex = part.rgb if hasattr(part, "rgb") else None
            color_id = part.color_id if hasattr(part, "color_id") else None
            color_label = ColorLabel(
                part.color_name, rgb_hex, part.color_type, color_id
            )

            self.ui.partsView.setCellWidget(row, 4, color_label)

            # Quantity column (5)
            quantity_item = QTableWidgetItem(str(part.quantity))
            quantity_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            self.ui.partsView.setItem(row, 5, quantity_item)

    # Note: _update_image method removed - BrickPreview widgets handle image loading automatically

    def on_part_double_clicked(self, row, column):
        """Handle double-click on a part row"""
        if row < len(self.parts_data):
            part_data = self.parts_data[row]
            dialog = PartDetailDialog(part_data, self.container, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Refresh the parts list
                self.refresh_parts_table()

    def on_header_clicked(self, col: int):
        """Sort parts_data by the column attribute and rebuild the table."""
        if col not in self._sort_attr_by_col:
            return

        if self._sort_col == col:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_col = col
            self._sort_order = Qt.SortOrder.AscendingOrder

        self.apply_sort()
        self.ui.partsView.horizontalHeader().setSortIndicator(
            self._sort_col, self._sort_order
        )

    def apply_sort(self):
        """Reorder self.parts_data per current sort state and repopulate."""
        if self._sort_col is None:
            return
        attr = self._sort_attr_by_col.get(self._sort_col)
        if attr is None:
            return

        def key(p):
            v = getattr(p, attr, None)
            if isinstance(v, str):
                return v.lower()
            return v if v is not None else 0

        self.parts_data = sorted(self.parts_data, key=key)
        if self._sort_order == Qt.SortOrder.DescendingOrder:
            self.parts_data.reverse()

        # Rebuild rows so cell widgets stay aligned with data
        self.ui.partsView.setRowCount(0)
        self.preview_widgets = []
        self.ui.partsView.setRowCount(len(self.parts_data))
        self.populate_table_data()
        self.ui.partsView.resizeRowsToContents()

    def on_parts_context_menu(self, pos):
        """Show context menu for selected parts rows."""
        selected_rows = sorted(
            {idx.row() for idx in self.ui.partsView.selectionModel().selectedRows()}
        )
        if not selected_rows:
            return

        menu = QMenu(self)
        move_action = menu.addAction("Move selected parts…")

        # Single row actions
        change_color_action = None
        clone_action = None
        if len(selected_rows) == 1:
            menu.addSeparator()
            change_color_action = menu.addAction("Change color…")
            clone_action = menu.addAction("Clone lot…")

        action = menu.exec(self.ui.partsView.viewport().mapToGlobal(pos))
        if action is None:
            return

        if action == move_action:
            selected_parts = [
                self.parts_data[r] for r in selected_rows if r < len(self.parts_data)
            ]
            if not selected_parts:
                return
            dialog = PartsMovementDialog(selected_parts, self.container, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_parts_table()
        elif action in (change_color_action, clone_action):
            row = selected_rows[0]
            if row >= len(self.parts_data):
                return
            part = self.parts_data[row]
            if action == change_color_action:
                dialog = PartColorChangeDialog(part, self.container, parent=self)
            else:
                dialog = PartCloneDialog(part, self.container, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_parts_table()

    def refresh_parts_table(self):
        """Refresh the parts table with updated data"""
        self.parts_data = self.dbManager.getContainersParts(self.container.id)

        # Clear and repopulate table; re-apply sort if one is active
        if self._sort_col is not None:
            self.apply_sort()
        else:
            self.ui.partsView.setRowCount(0)
            self.preview_widgets = []
            self.ui.partsView.setRowCount(len(self.parts_data))
            self.populate_table_data()

        # Update counts
        self.ui.part_count_label.setText(
            str(self.dbManager.getConteinerPartCount(self.container.id))
        )
        self.ui.lots_count_label.setText(
            str(self.dbManager.getConteinerLotCount(self.container.id))
        )

        # Resize columns to content
        self.ui.partsView.resizeColumnsToContents()

        # Limit Name column width
        if self.ui.partsView.columnWidth(self.name_column_index) > self.max_name_width:
            self.ui.partsView.setColumnWidth(
                self.name_column_index, self.max_name_width
            )

        if self.ui.partsView.columnWidth(self.type_column_index) > self.max_type_width:
            self.ui.partsView.setColumnWidth(
                self.type_column_index, self.max_type_width
            )

        self.ui.partsView.setWordWrap(True)
        self.ui.partsView.resizeRowsToContents()
        self.ui.partsView.horizontalHeader().setStretchLastSection(True)

    def on_delete_clicked(self):
        """Handle delete container button click"""
        # Check if container has parts
        if self.container.part_count > 0:
            # Show confirm dialog with options
            dialog = DeleteContainerDialog(self.container, self)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                # Container was deleted
                QMessageBox.information(
                    self,
                    "Success",
                    f"Container '{self.container.name}' deleted successfully",
                )
                self.accept()  # Close this dialog too
        else:
            # Just confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to delete container '{self.container.name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                db_manager = DatabaseManager()
                if db_manager.deleteContainer(self.container.id):
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Container '{self.container.name}' deleted successfully",
                    )
                    self.accept()
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete container")

    def accept(self):
        db_manager = DatabaseManager()

        # Update container object
        self.container.name = self.ui.name_edit.text()
        self.container.description = self.ui.description_edit.text()

        # Update type
        type_text = CONTAINER_TYPE_VALUES.get(
            self.ui.type_combobox.currentText(), "box"
        )
        self.container.type = type_text

        # Save to database
        if db_manager.updateContainer(self.container):
            super().accept()


class DeleteContainerDialog(QDialog):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.db_manager = DatabaseManager()

        self.setWindowTitle(f"Delete Container - {container.name}")
        self.resize(400, 250)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Warning message
        warning_label = QLabel(
            f"Container '{self.container.name}' contains {self.container.part_count} parts "
            f"in {self.container.lot_count} lots.\n\n"
            f"What would you like to do with these parts?"
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        # Move to another container option
        self.move_radio = QRadioButton("Move parts to another container")
        self.move_radio.setChecked(True)
        self.move_radio.toggled.connect(self.on_option_toggled)
        options_layout.addWidget(self.move_radio)

        # Container selector
        container_layout = QHBoxLayout()
        container_layout.addSpacing(20)  # Indent
        container_layout.addWidget(QLabel("Target container:"))
        self.container_combo = QComboBox()
        self.populate_container_combo()
        container_layout.addWidget(self.container_combo)
        options_layout.addLayout(container_layout)

        # Delete entirely option
        self.delete_radio = QRadioButton("Delete parts permanently")
        self.delete_radio.toggled.connect(self.on_option_toggled)
        options_layout.addWidget(self.delete_radio)

        # Warning for delete option
        delete_warning = QLabel(
            "Warning: This will permanently remove all parts from your collection!"
        )
        delete_warning.setProperty("class", "danger")

        delete_warning.setWordWrap(True)
        container_layout = QHBoxLayout()
        container_layout.addSpacing(20)  # Indent
        container_layout.addWidget(delete_warning)
        options_layout.addLayout(container_layout)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Set default state
        self.on_option_toggled()

    def populate_container_combo(self):
        """Populate the container combo box with all containers except current one"""
        import src.utils as utils

        containers = self.db_manager.getContainers(order_by="name")

        for container in containers:
            if container.id != self.container.id:
                part_count = container.part_count or 0
                container_type = getattr(container, "type", "box")
                display_text = f"{container.name} ({part_count} parts)"

                # Store complete data: (id, name, type, part_count)
                container_data = (
                    container.id,
                    container.name,
                    container_type,
                    part_count,
                )
                self.container_combo.addItem(display_text, container_data)

        # Setup custom delegate for better rendering
        utils.setup_container_combo_delegate(self.container_combo)

        if self.container_combo.count() == 0:
            # Disable move option if no other containers
            self.move_radio.setEnabled(False)
            self.container_combo.setEnabled(False)
            self.delete_radio.setChecked(True)

    def on_option_toggled(self):
        """Enable/disable container combo based on selected option"""
        self.container_combo.setEnabled(self.move_radio.isChecked())

    def accept(self):
        """Process container deletion based on selected option"""
        try:
            if self.move_radio.isChecked():
                # Get target container
                target_data = self.container_combo.currentData()
                if target_data is None:
                    QMessageBox.warning(
                        self, "No Target", "Please select a target container"
                    )
                    return

                # Extract container ID from data tuple (id, name, type, part_count)
                try:
                    target_id = (
                        target_data[0]
                        if isinstance(target_data, tuple)
                        else target_data
                    )
                except (TypeError, IndexError):
                    target_id = target_data

                # Move all parts to target container
                if self.db_manager.moveAllParts(self.container.id, target_id):
                    # Now delete the empty container
                    if self.db_manager.deleteContainer(self.container.id):
                        super().accept()
                    else:
                        QMessageBox.critical(
                            self,
                            "Error",
                            "Failed to delete container after moving parts",
                        )
                else:
                    QMessageBox.critical(
                        self, "Error", "Failed to move parts to target container"
                    )
            else:
                # Confirm deletion of parts
                reply = QMessageBox.question(
                    self,
                    "Confirm Deletion",
                    "Are you sure you want to PERMANENTLY DELETE all parts in this container?\n\n"
                    "This action cannot be undone!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Delete container and all parts
                    if self.db_manager.deleteContainerWithParts(self.container.id):
                        super().accept()
                    else:
                        QMessageBox.critical(
                            self, "Error", "Failed to delete container and parts"
                        )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
