from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QListWidgetItem

from src.database import DatabaseManager, container_type_icon_path
from ui.ui_containerSelectionDialog import Ui_ContainerSelectionDialog


class ContainerSelectionDialog(QDialog):
    """Dialog to pick which containers a search runs against."""

    def __init__(self, parent=None, selected_ids: set[int] | None = None):
        super().__init__(parent)

        self.ui = Ui_ContainerSelectionDialog()
        self.ui.setupUi(self)

        self.ui.selectAllButton.clicked.connect(self.select_all)
        self.ui.unselectAllButton.clicked.connect(self.unselect_all)

        self._populate(selected_ids)

    def _populate(self, selected_ids: set[int] | None):
        dbManager = DatabaseManager()
        containers = dbManager.getContainers(order_by="name")

        for container in containers:
            item = QListWidgetItem(
                QIcon(container_type_icon_path(container.type)),
                f"{container.name}  ({container.part_count} parts)",
            )
            item.setData(Qt.ItemDataRole.UserRole, container.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            checked = selected_ids is None or container.id in selected_ids
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            self.ui.containerList.addItem(item)

    def _set_all(self, state: Qt.CheckState):
        for row in range(self.ui.containerList.count()):
            self.ui.containerList.item(row).setCheckState(state)

    def select_all(self):
        self._set_all(Qt.CheckState.Checked)

    def unselect_all(self):
        self._set_all(Qt.CheckState.Unchecked)

    def selected_container_ids(self) -> set[int]:
        ids = set()
        for row in range(self.ui.containerList.count()):
            item = self.ui.containerList.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                ids.add(item.data(Qt.ItemDataRole.UserRole))
        return ids
