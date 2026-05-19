from PySide6.QtWidgets import QDialog, QMessageBox

from src import utils
from src.database import CollectionPart, Container, DatabaseManager
from src.widgets.colorLabel import ColorLabel
from ui.ui_detailPartDialog import Ui_DeatilPartDialog


class PartDetailDialog(QDialog):
    def __init__(
        self,
        part_data: CollectionPart,
        container: Container,
        qty=1,
        outsideDefault=False,
        target_container_id: int | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.imgSize = 256

        # Create and setup UI
        self.ui = Ui_DeatilPartDialog()
        self.ui.setupUi(self)

        self.part_data = part_data
        self.container = container
        self.target_container_id = target_container_id

        self.setup_ui()

        self.ui.qtySpinBox.setValue(qty)
        self.ui.toOutsideRadioButton.setChecked(outsideDefault)

    def setup_ui(self):
        # The BrickPreview widget is now defined directly in the UI file
        # Just configure it with the part data
        self.ui.imageLabel.set_size(self.imgSize)
        self.ui.imageLabel.load_part_image(
            self.part_data.part_id, str(self.part_data.color_id)
        )

        # Part ID and Name
        self.ui.idValLabel.setText(self.part_data.part_id)
        self.ui.nameValLabel.setText(self.part_data.part_name)
        self.ui.categoryValLabel.setText(self.part_data.part_category)

        # Create and add ColorLabel
        rgb_hex = self.part_data.rgb if hasattr(self.part_data, "rgb") else None
        color_id = (
            self.part_data.color_id if hasattr(self.part_data, "color_id") else None
        )
        color_type = (
            self.part_data.color_type if hasattr(self.part_data, "color_type") else None
        )

        self.color_label = ColorLabel(
            self.part_data.color_name, rgb_hex, color_type, color_id
        )
        self.ui.infoLayout.addWidget(self.color_label, 3, 1)

        self.ui.currentContainerValue.setText(self.container.name)

        # Current quantity
        self.current_quantity = self.part_data.quantity
        self.ui.currentQtyValLabel.setText(str(self.current_quantity))

        self.ui.qtySpinBox.setRange(1, self.current_quantity)
        self.ui.qtySpinBox.setValue(1)

        self.ui.moveButton.setProperty("class", "warning")
        self.ui.moveButton.clicked.connect(self.on_move_remove_clicked)
        self.ui.toContainerRadioButton.toggled.connect(
            self.ui.containerCombo.setEnabled
        )

        self.populate_container_combo()

    def populate_container_combo(self):
        utils.populate_container_combo(
            self.ui.containerCombo, DatabaseManager(), None, [self.container.id]
        )

        # Setup custom delegate for better rendering
        utils.setup_container_combo_delegate(self.ui.containerCombo)

        self.ui.containerCombo.setCurrentIndex(0)

        # Pre-select the target container as move destination, if given
        if (
            self.target_container_id is not None
            and self.target_container_id != self.container.id
        ):
            for index in range(self.ui.containerCombo.count()):
                data = self.ui.containerCombo.itemData(index)
                data_id = data[0] if isinstance(data, tuple) else data
                if data_id == self.target_container_id:
                    self.ui.containerCombo.setCurrentIndex(index)
                    self.ui.toContainerRadioButton.setChecked(True)
                    self.ui.containerCombo.setEnabled(True)
                    break

        # dbManager = DatabaseManager()
        # containers = dbManager.getContainers()

        # for container in containers:
        #     if container.id != self.container.id:
        #         self.ui.containerCombo.addItem(container.name, container.id)

        # if self.ui.containerCombo.count() == 0:
        #     self.ui.toContainerRadioButton.setEnabled(False)
        #     self.ui.containerCombo.setEnabled(False)
        #     self.ui.toOutsideRadioButton.setChecked(True)

    def on_move_remove_clicked(self):
        if self.ui.toContainerRadioButton.isChecked():
            self.on_move_clicked()
        elif self.ui.toOutsideRadioButton.isChecked():
            self.on_remove_clicked()

    def on_remove_clicked(self):
        quantity = self.ui.qtySpinBox.value()

        if quantity <= 0 or quantity > self.current_quantity:
            QMessageBox.warning(
                self, "Invalid Quantity", "Please enter a valid quantity to remove"
            )
            return

        # Add function to database manager to remove parts
        if self.update_part_quantity(-quantity):
            QMessageBox.information(self, "Success", f"Removed {quantity} parts")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to remove parts")

    def on_move_clicked(self):
        quantity = self.ui.qtySpinBox.value()
        target_container_data = self.ui.containerCombo.currentData()

        if quantity <= 0 or quantity > self.current_quantity:
            QMessageBox.warning(
                self, "Invalid Quantity", "Please enter a valid quantity to move"
            )
            return

        if target_container_data is None:
            QMessageBox.warning(
                self, "No Container", "Please select a target container"
            )
            return

        # Extract container ID from data tuple (id, name, type, part_count)
        try:
            target_container_id = (
                target_container_data[0]
                if isinstance(target_container_data, tuple)
                else target_container_data
            )
        except (TypeError, IndexError):
            target_container_id = target_container_data

        # Move parts from one container to another
        if self.move_parts_to_container(quantity, target_container_id):
            QMessageBox.information(
                self,
                "Success",
                f"Moved {quantity} parts to {self.ui.containerCombo.currentText()}",
            )
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to move parts")

    def update_part_quantity(self, delta):
        dbManager = DatabaseManager()
        result = dbManager.addColorPartIDToContainer(
            self.part_data.id, self.container.id, delta
        )
        return result

    def move_parts_to_container(self, quantity, target_container_id):
        dbManager = DatabaseManager()
        result = dbManager.movePartsBetweenContainers(
            self.part_data.id, self.container.id, target_container_id, quantity
        )
        return result
