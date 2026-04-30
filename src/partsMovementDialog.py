from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
)

from src import utils
from src.database import CollectionPart, Container, DatabaseManager


class PartsMovementDialog(QDialog):
    def __init__(
        self,
        parts: list[CollectionPart],
        container: Container,
        parent=None,
    ):
        super().__init__(parent)

        self.parts = parts
        self.container = container
        self.db_manager = DatabaseManager()

        self.setWindowTitle(f"Move parts from {container.name}")
        self.resize(450, 250)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        total_parts = sum(p.quantity for p in self.parts)
        unique_lots = len(self.parts)

        header = QLabel(
            f"Moving {total_parts} parts across {unique_lots} "
            f"lot{'s' if unique_lots != 1 else ''} from '{self.container.name}'."
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        self.toContainerRadioButton = QRadioButton("Move to another container")
        self.toContainerRadioButton.setChecked(True)
        options_layout.addWidget(self.toContainerRadioButton)

        combo_row = QHBoxLayout()
        combo_row.addSpacing(20)
        combo_row.addWidget(QLabel("Target container:"))
        self.containerCombo = QComboBox()
        utils.populate_container_combo(
            self.containerCombo, self.db_manager, None, [self.container.id]
        )
        utils.setup_container_combo_delegate(self.containerCombo)
        combo_row.addWidget(self.containerCombo)
        options_layout.addLayout(combo_row)

        self.toOutsideRadioButton = QRadioButton("Remove from collection")
        options_layout.addWidget(self.toOutsideRadioButton)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.toContainerRadioButton.toggled.connect(self.containerCombo.setEnabled)

        # If there are no other containers (combo only has the dummy entry),
        # disable the move option.
        if self.containerCombo.count() <= 1:
            self.toContainerRadioButton.setEnabled(False)
            self.containerCombo.setEnabled(False)
            self.toOutsideRadioButton.setChecked(True)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Move")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        try:
            if self.toContainerRadioButton.isChecked():
                target_data = self.containerCombo.currentData()
                if target_data is None:
                    QMessageBox.warning(
                        self, "No Target", "Please select a target container"
                    )
                    return

                try:
                    target_id = (
                        target_data[0]
                        if isinstance(target_data, tuple)
                        else target_data
                    )
                except (TypeError, IndexError):
                    target_id = target_data

                failures = []
                for part in self.parts:
                    ok = self.db_manager.movePartsBetweenContainers(
                        part.id, self.container.id, target_id, part.quantity
                    )
                    if not ok:
                        failures.append(part)

                if failures:
                    QMessageBox.warning(
                        self,
                        "Partial Move",
                        f"Failed to move {len(failures)} of {len(self.parts)} lots.",
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Moved {len(self.parts)} lots to "
                        f"{self.containerCombo.currentText()}",
                    )
                super().accept()
            else:
                reply = QMessageBox.question(
                    self,
                    "Confirm Removal",
                    f"Remove {len(self.parts)} lots "
                    f"({sum(p.quantity for p in self.parts)} parts) from your collection?\n\n"
                    "This cannot be undone.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

                failures = []
                for part in self.parts:
                    ok = self.db_manager.addColorPartIDToContainer(
                        part.id, self.container.id, -part.quantity
                    )
                    if not ok:
                        failures.append(part)

                if failures:
                    QMessageBox.warning(
                        self,
                        "Partial Removal",
                        f"Failed to remove {len(failures)} of {len(self.parts)} lots.",
                    )
                else:
                    QMessageBox.information(
                        self, "Success", f"Removed {len(self.parts)} lots"
                    )
                super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
