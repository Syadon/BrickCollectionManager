from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from src import utils
from src.database import CollectionPart, Container, DatabaseManager
from src.widgets.brickPreview import BrickPreview
from src.widgets.colorComboBox import ColorComboBox
from src.widgets.colorLabel import ColorLabel


class PartLotEditDialog(QDialog):
    """Edit color and quantity of a lot inside a container."""

    def __init__(
        self,
        part: CollectionPart,
        container: Container,
        parent=None,
    ):
        super().__init__(parent)

        self.part = part
        self.container = container
        self.db_manager = DatabaseManager()

        # Colors the catalog knows for this part, current one included
        self.available_colors = self.db_manager.getPartColors(part.part_id)

        self.setWindowTitle(f"Edit lot - {part.part_name}")
        self.resize(480, 380)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            f"<b>{self.part.part_name}</b> ({self.part.part_id})<br>"
            f"in '{self.container.name}'"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # Current state: preview (follows the selected color) and current values
        current_row = QHBoxLayout()
        self.preview = BrickPreview(
            part_id=self.part.part_id,
            color_id=str(self.part.color_id),
            size=128,
            parent=self,
        )
        current_row.addWidget(self.preview)

        current_info = QVBoxLayout()
        self.currentColorLabel = ColorLabel(
            self.part.color_name,
            self.part.rgb,
            self.part.color_type,
            self.part.color_id,
        )
        current_info.addWidget(self.currentColorLabel)
        current_info.addWidget(
            QLabel(
                f"Current: {self.part.quantity} "
                f"piece{'s' if self.part.quantity != 1 else ''}"
            )
        )
        current_info.addStretch()
        current_row.addLayout(current_info, 1)
        layout.addLayout(current_row)

        # New color
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color:"))
        self.colorCombo = ColorComboBox()
        utils.populate_color_combo(
            self.colorCombo,
            self.db_manager,
            include_any_option=False,
            colors=self.available_colors,
        )
        utils.setup_color_combo_delegate(self.colorCombo)
        self.select_current_color()
        self.colorCombo.currentIndexChanged.connect(self.on_color_changed)
        color_row.addWidget(self.colorCombo, 1)
        layout.addLayout(color_row)

        # New quantity
        quantity_row = QHBoxLayout()
        quantity_row.addWidget(QLabel("Quantity:"))
        self.quantitySpinBox = QSpinBox()
        self.quantitySpinBox.setRange(0, 999999)
        self.quantitySpinBox.setValue(self.part.quantity)
        quantity_row.addWidget(self.quantitySpinBox)
        quantity_row.addWidget(
            QLabel(f"(was {self.part.quantity} - 0 removes the lot)")
        )
        quantity_row.addStretch()
        layout.addLayout(quantity_row)

        layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Apply")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Only one catalog color for this part: nothing to switch to
        if len(self.available_colors) <= 1:
            self.colorCombo.setEnabled(False)

    def select_current_color(self):
        """Pre-select the current color of the lot in the combo"""
        for index in range(self.colorCombo.count()):
            if self.selected_color_id(self.colorCombo.itemData(index)) == (
                self.part.color_id
            ):
                self.colorCombo.setCurrentIndex(index)
                return

    @staticmethod
    def selected_color_id(color_data):
        """Extract the color id from the combo data tuple (id, name, rgb)"""
        if color_data is None:
            return None
        return color_data[0] if isinstance(color_data, tuple) else color_data

    def on_color_changed(self, index):
        """Keep the preview image in sync with the selected color"""
        color_id = self.selected_color_id(self.colorCombo.itemData(index))
        if color_id is not None:
            self.preview.load_part_image(self.part.part_id, str(color_id))

    def accept(self):
        try:
            new_color_id = self.selected_color_id(self.colorCombo.currentData())
            if new_color_id is None:
                QMessageBox.warning(self, "No Color", "Please select a color")
                return

            color_part = self.db_manager.getColorPart(self.part.part_id, new_color_id)
            if color_part is None:
                QMessageBox.warning(
                    self,
                    "Invalid Color",
                    "This part is not available in the selected color",
                )
                return

            new_quantity = self.quantitySpinBox.value()

            # Nothing changed: close without touching the database
            if (
                new_color_id == self.part.color_id
                and new_quantity == self.part.quantity
            ):
                super().reject()
                return

            if new_quantity == 0:
                reply = QMessageBox.question(
                    self,
                    "Remove Lot",
                    f"Remove this lot ({self.part.quantity} "
                    f"{self.part.color_name} {self.part.part_name}) from "
                    f"'{self.container.name}'?\n\nThis cannot be undone.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            elif color_part.id != self.part.id:
                # The target lot may already exist: the change merges the two lots
                existing_qty = self.db_manager.getContainerItemCount(
                    color_part.id, self.container.id
                )
                if existing_qty > 0:
                    reply = QMessageBox.question(
                        self,
                        "Merge Lots",
                        f"A lot of this part in {self.colorCombo.currentText()} "
                        f"already exists in '{self.container.name}' "
                        f"({existing_qty} pieces).\n\n"
                        f"The two lots will be merged into one of "
                        f"{existing_qty + new_quantity} pieces. Continue?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if reply != QMessageBox.StandardButton.Yes:
                        return

            ok = self.db_manager.updateLotInContainer(
                self.part.id,
                color_part.id,
                self.container.id,
                self.part.quantity,
                new_quantity,
            )
            if not ok:
                QMessageBox.critical(self, "Error", "Failed to update this lot")
                return

            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
