from PySide6.QtWidgets import (QMainWindow, QWidget, QMenuBar, QStatusBar, 
                              QMenu, QDialog, QMessageBox)
from PySide6.QtCore import Qt, QAbstractTableModel, SIGNAL
from ui.ui_mainwindow import Ui_MainWindow
from addBricksDialog import AddBricksDialog
from addContainerDialog import AddContainerDialog
from containerDetailDialog import ContainerDetailDialog
from searchPartsDialog import SearchPartsDialog
from updateDBDialog import UpdateDBDialog
from database import DatabaseManager
import operator

class ContainerTableModel(QAbstractTableModel):
    def __init__(self, containers, parent=None):
        super().__init__(parent)
        self.containers = containers
        self.attrOrder = ["id", "name", "part_count", "lot_count", "description"]
        self.headetList = ["ID", "Name", "Part Count", "Lot Count", "Description"]

    def rowCount(self, parent):
        return len(self.containers)

    def columnCount(self, parent):
        return len(self.headetList)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        else:
            c = self.containers[index.row()]
            attr = self.attrOrder[index.column()]
            return getattr(c, attr)
        
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headetList[col]
        return None

    def sort(self, col, order):
        attr = self.attrOrder[col]
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.containers = sorted(self.containers,
            key=operator.attrgetter(attr))
        if order == Qt.DescendingOrder:
            self.mylist.reverse()
        self.emit(SIGNAL("layoutChanged()"))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create and setup UI
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.containersModel = ContainerTableModel([])
        self.updateContainerView()

        # Connect button to dialog
        self.ui.addBricksButton.clicked.connect(self.openAddBricksDialog)
        self.ui.addNewContainerButton.clicked.connect(self.openAddContainerDialog)

        self.ui.findBricksButton.clicked.connect(self.openFindDialog)

        # Connect double click signal
        self.ui.containerView.doubleClicked.connect(self.on_container_double_clicked)
        
        # Enable context menu
        self.ui.containerView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.containerView.customContextMenuRequested.connect(self.show_context_menu)
        
        # Connect updateDBAction to openUpdateDBDialog method
        self.ui.updateDBAction.triggered.connect(self.openUpdateDBDialog)

    def openAddBricksDialog(self):
        dialog = AddBricksDialog(targetContainer=None, parent=self)
        dialog.exec()
        self.updateContainerView()

    def openAddContainerDialog(self):
        dialog = AddContainerDialog(self)
        if dialog.exec() == AddContainerDialog.Accepted:
            self.updateContainerView()

    def openFindDialog(self):
        dialog = SearchPartsDialog(self)
        dialog.exec()
    
    def openUpdateDBDialog(self):
        """Open dialog to update the database"""
        try:
            dialog = UpdateDBDialog(self)
            result = dialog.exec()
            
            # If database was updated, refresh the container view
            if result == QDialog.Accepted:
                self.updateContainerView()
                QMessageBox.information(self, "Database Update", "Database has been successfully updated.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open database update dialog: {str(e)}")

    def updateContainerView(self):
        dbManager = DatabaseManager()
        containers = dbManager.getContainers()
        self.containersModel = ContainerTableModel(containers)

        self.ui.containerView.setModel(self.containersModel)

    def on_container_double_clicked(self, index):
        container = self.containersModel.containers[index.row()]
        self.open_container_dialog(container)

    def show_context_menu(self, position):
        index = self.ui.containerView.indexAt(position)
        
        if index.isValid():
            context_menu = QMenu(self)
            add_bricks_action = context_menu.addAction("Add Bricks")
            edit_action = context_menu.addAction("Edit")
            
            # Show context menu at cursor position
            action = context_menu.exec(self.ui.containerView.viewport().mapToGlobal(position))
            
            if action == edit_action:
                container = self.containersModel.containers[index.row()]
                self.open_container_dialog(container)
            elif action == add_bricks_action:
                container = self.containersModel.containers[index.row()]
                dialog = AddBricksDialog(targetContainer=container, parent=self)
                dialog.exec()
                self.updateContainerView()

    def open_container_dialog(self, container):
        dialog = ContainerDetailDialog(container, self)
        if dialog.exec() == QDialog.Accepted:
            self.updateContainerView()

