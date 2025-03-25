from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from database import Container
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from widgets.addFromFileWidget import AddFromFileWidget
from widgets.addFromCameraWidget import AddFromCameraWidget
from widgets.addManualWidget import AddManualWidget


class AddBricksDialog(QDialog):
    def __init__(self, targetContainer:Container= None, parent=None):
        super().__init__(parent)

        # Create and setup UI
        self.ui = Ui_AddBricksDialog()
        self.ui.setupUi(self)

        self.manual_widget = AddManualWidget(container=targetContainer, parent=self.ui.tabWidget)
        self.ui.tabWidget.addTab(self.manual_widget, "Manual Search")

        self.camera_detection_widget = AddFromCameraWidget(container=targetContainer, parent=self.ui.tabWidget)
        self.ui.tabWidget.addTab(self.camera_detection_widget, "Camera Detection")

        #Setup load from file tab
        self.file_import_widget = AddFromFileWidget(container=targetContainer, parent=self.ui.tabWidget)
        self.ui.tabWidget.addTab(self.file_import_widget, "Load from File")

        # Connect tab change signal
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Initial check of camera tab visibility
        self.on_tab_changed(self.ui.tabWidget.currentIndex())


    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter or event.key() == Qt.Key_Escape:
            # Impedisce la propagazione dell'evento
            event.accept()
            return
        
        # Per altri tasti, passa al gestore di eventi della classe padre
        super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)

    def on_tab_changed(self, index):
        pass
