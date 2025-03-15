from PySide6.QtWidgets import QMainWindow, QWidget, QMenuBar, QStatusBar
from PySide6.QtCore import Qt, QAbstractTableModel, SIGNAL
from ui.ui_mainwindow import Ui_MainWindow
from addBricksDialog import AddBricksDialog
from addContainerDialog import AddContainerDialog
from database import DatabaseManager
import operator

class ContainerTableModel(QAbstractTableModel):
    def __init__(self, containers, parent=None):
        super().__init__(parent)
        self.containers = containers

    def rowCount(self, parent):
        return len(self.containers)

    def columnCount(self, parent):
        return 4

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
        else:
            c = self.containers[index.row()]
            return c.toTuple()[index.column()]
        
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["ID", "Name", "Description", "Part Count"][col]
        return None

    def sort(self, col, order):
        attr = ["id", "name", "description", "part_count"][col]
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

    def openAddBricksDialog(self):
        dialog = AddBricksDialog(self)
        dialog.exec()
        self.updateContainerView()

    def openAddContainerDialog(self):
        dialog = AddContainerDialog(self)
        if dialog.exec() == AddContainerDialog.Accepted:
            self.updateContainerView()

    def updateContainerView(self):
        dbManager = DatabaseManager()
        containers = dbManager.getContainers()
        self.containersModel = ContainerTableModel(containers)

        self.ui.containerView.setModel(self.containersModel)
