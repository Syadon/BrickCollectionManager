from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.addContainerDialog import AddContainerDialog
from src.containerDetailDialog import ContainerDetailDialog
from src.database import DatabaseManager
from src.logger import get_logger


class ContainerTableModel(QAbstractTableModel):
    def __init__(self, containers, parent=None):
        super().__init__(parent)
        self.containers = containers
        self.attrOrder = [
            "id",
            "type",
            "name",
            "part_count",
            "lot_count",
            "description",
        ]
        self.headerList = [
            "ID",
            "Type",
            "Name",
            "Part Count",
            "Lot Count",
            "Description",
        ]

    def rowCount(self, parent=None) -> int:
        return len(self.containers)

    def columnCount(self, parent=None) -> int:
        return len(self.headerList)

    def data(self, index, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        c = self.containers[index.row()]
        attr = self.attrOrder[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            if attr == "type":
                # Don't display text for type column, just the icon
                return ""
            else:
                return getattr(c, attr, "")

        elif role == Qt.ItemDataRole.DecorationRole:
            if attr == "type":
                # Return appropriate icon based on container type
                container_type = getattr(c, "type", "box")
                if container_type == "bag":
                    return QIcon(":/icons/container_bag.png")
                else:
                    return QIcon(":/icons/container_box.png")

        return None

    def headerData(self, col, orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.headerList[col]
        return None

    def sort(self, col, order=Qt.SortOrder.AscendingOrder):
        attr = self.attrOrder[col]
        self.layoutAboutToBeChanged.emit()
        self.containers = sorted(self.containers, key=lambda x: getattr(x, attr, ""))
        if order == Qt.SortOrder.DescendingOrder:
            self.containers.reverse()
        self.layoutChanged.emit()


class ContainerListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger()
        self.logger.debug("Initializing ContainerListWidget")

        # Create main layout
        layout = QVBoxLayout(self)

        # Create counters layout
        counters_layout = QHBoxLayout()

        # Total parts counter
        self.total_parts_label = QLabel("Total Parts: 0")
        # self.total_parts_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #2E7D32;")
        counters_layout.addWidget(self.total_parts_label)

        counters_layout.addStretch()  # Push labels to the left

        layout.addLayout(counters_layout)

        # Create buttons layout
        button_layout = QHBoxLayout()

        # Add Container button
        self.add_container_btn = QPushButton("Add New Container")
        self.add_container_btn.clicked.connect(self.add_container)
        button_layout.addWidget(self.add_container_btn)

        # Add to layout
        layout.addLayout(button_layout)

        # Create table view
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.table_view.doubleClicked.connect(self.on_container_double_clicked)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table_view)

        # Initialize model
        self.model: ContainerTableModel | None = None
        # self.update_view()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_view()

    def update_view(self):
        dbManager = DatabaseManager()
        containers = dbManager.getContainers()
        self.model = ContainerTableModel(containers)
        self.table_view.setModel(self.model)

        # Configure column sizing
        self.table_view.resizeColumnsToContents()  # Resize all columns to fit content

        # Set specific width for type column (icon only)
        self.table_view.setColumnWidth(1, 60)  # Type column - just wide enough for icon

        self.table_view.horizontalHeader().setStretchLastSection(
            True
        )  # Make last column stretch to fill remaining space

        # Update counters
        self.update_counters()

    def update_counters(self):
        """Update the collection counters"""
        dbManager = DatabaseManager()

        # Get total parts count
        total_parts = dbManager.getCollectionPartsCount()
        self.total_parts_label.setText(f"Total Parts: {total_parts}")

    def add_container(self):
        dialog = AddContainerDialog(self)
        if dialog.exec() == AddContainerDialog.DialogCode.Accepted:
            self.update_view()

    def on_container_double_clicked(self, index):
        if self.model is None:
            return

        container = self.model.containers[index.row()]
        self.open_container_dialog(container)

    def show_context_menu(self, position):
        if self.model is None:
            return

        index = self.table_view.indexAt(position)

        if index.isValid():
            context_menu = QMenu(self)
            # add_bricks_action = context_menu.addAction("Add Bricks")
            edit_action = context_menu.addAction("Edit")

            # Show context menu at cursor position
            action = context_menu.exec(self.table_view.viewport().mapToGlobal(position))

            if action == edit_action:
                container = self.model.containers[index.row()]
                self.open_container_dialog(container)
            # elif action == add_bricks_action:
            #    container = self.model.containers[index.row()]
            #    dialog = AddBricksDialog(targetContainer=container, parent=self)
            #    dialog.exec()
            #    self.update_view()

    def open_container_dialog(self, container):
        dialog = ContainerDetailDialog(container, self)
        if dialog.exec() == QMessageBox.DialogCode.Accepted:
            self.update_view()
