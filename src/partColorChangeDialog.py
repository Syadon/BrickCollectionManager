from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from src import utils
from src.database import CollectionPart, Container, DatabaseManager
from src.widgets.colorComboBox import ColorComboBox
from src.widgets.colorLabel import ColorLabel


class PartColorChangeDialog(QDialog):
    """Change the color of a lot, keeping it in the same container."""

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

        # Colors the catalog knows for this part, excluding the current one
        self.available_colors = [
            color
            for color in self.db_manager.getPartColors(part.part_id)
            if color.id != part.color_id
        ]

        self.setWindowTitle(f"Change color - {part.part_name}")
        self.resize(450, 300)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(
            f"<b>{self.part.part_name}</b> ({self.part.part_id})<br>"
            f"{self.part.quantity} piece{'s' if self.part.quantity != 1 else ''} "
            f"in '{self.container.name}'"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        layout.addWidget(QLabel("Current color:"))
        self.currentColorLabel = ColorLabel(
            self.part.color_name,
            self.part.rgb,
            self.part.color_type,
            self.part.color_id,
        )
        layout.addWidget(self.currentColorLabel)

        combo_row = QHBoxLayout()
        combo_row.addWidget(QLabel("New color:"))
        self.colorCombo = ColorComboBox()
        utils.populate_color_combo(
            self.colorCombo,
            self.db_manager,
            include_any_option=False,
            colors=self.available_colors,
        )
        utils.setup_color_combo_delegate(self.colorCombo)
        combo_row.addWidget(self.colorCombo, 1)
        layout.addLayout(combo_row)

        note = QLabel(
            f"The whole lot ({self.part.quantity} "
            f"piece{'s' if self.part.quantity != 1 else ''}) will be recolored."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Change color"
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # No alternative color available for this part
        if not self.available_colors:
            self.colorCombo.setEnabled(False)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            note.setText("No other compatible color for this part in the catalog.")

    def accept(self):
        try:
            color_data = self.colorCombo.currentData()
            if color_data is None:
                QMessageBox.warning(self, "No Color", "Please select a new color")
                return

            new_color_id = (
                color_data[0] if isinstance(color_data, tuple) else color_data
            )

            color_part = self.db_manager.getColorPart(self.part.part_id, new_color_id)
            if color_part is None:
                QMessageBox.warning(
                    self,
                    "Invalid Color",
                    "This part is not available in the selected color",
                )
                return

            # The target lot may already exist: the change merges the two lots
            existing_qty = self.db_manager.getContainerItemCount(
                color_part.id, self.container.id
            )
            if existing_qty > 0:
                reply = QMessageBox.question(
                    self,
                    "Merge Lots",
                    f"A lot of this part in {self.colorCombo.currentText()} already "
                    f"exists in '{self.container.name}' ({existing_qty} pieces).\n\n"
                    f"The two lots will be merged into one of "
                    f"{existing_qty + self.part.quantity} pieces. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            ok = self.db_manager.changePartColorInContainer(
                self.part.id, color_part.id, self.container.id, self.part.quantity
            )
            if not ok:
                QMessageBox.critical(
                    self, "Error", "Failed to change the color of this lot"
                )
                return

            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
