pyside6-rcc resources\resources.qrc -o resources_rc.py

pyside6-uic ./ui/addContainerDialog.ui -o ./ui/ui_addcontainerdialog.py
pyside6-uic ./ui/containerDetailDialog.ui -o ./ui/ui_containerDetailDialog.py
pyside6-uic ./ui/detailPartDialog.ui -o ./ui/ui_detailPartDialog.py
pyside6-uic ./ui/addFromFileWidget.ui -o ./ui/ui_addFromFileWidget.py
pyside6-uic ./ui/addFromCameraWidget.ui -o ./ui/ui_addFromCameraWidget.py
pyside6-uic ./ui/addManualWidget.ui -o ./ui/ui_addManualWidget.py
pyside6-uic ./ui/searchManualWidget.ui -o ./ui/ui_searchManualWidget.py
pyside6-uic ./ui/updateDBDialog.ui -o ./ui/ui_updateDBDialog.py
