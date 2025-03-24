pyside6-rcc resources\resources.qrc -o resources_rc.py

pyside6-uic ./ui/mainwindow.ui -o ./ui/ui_mainwindow.py
pyside6-uic ./ui/addBricksDialog.ui -o ./ui/ui_addbricksdialog.py
pyside6-uic ./ui/addContainerDialog.ui -o ./ui/ui_addcontainerdialog.py
pyside6-uic ./ui/containerDetailDialog.ui -o ./ui/ui_containerDetailDialog.py
pyside6-uic ./ui/detailPartDialog.ui -o ./ui/ui_detailPartDialog.py
pyside6-uic ./ui/addFromFileWidget.ui -o ./ui/ui_addFromFileWidget.py