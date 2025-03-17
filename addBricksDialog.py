from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt, QByteArray, QBuffer, QRect
from PySide6.QtGui import QImage, QColor
from database import DatabaseManager, BrickColor
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from widgets.cameraStreamView import CameraStreamView
from config import AppConfig
import cv2
import logging
import requests

class AddBricksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create and setup UI
        self.ui = Ui_AddBricksDialog()
        self.ui.setupUi(self)

        self.video_view = CameraStreamView()
        self.ui.cameraLayout.insertWidget(0, self.video_view)

        # Create camera selection combobox
        self.populate_camera_list()
        self.ui.acquisition_combo.currentIndexChanged.connect(self.switch_camera)

        # Connect capture button
        self.ui.captureButton.clicked.connect(self.video_view.capture_image)
        self.video_view.image_captured.connect(self.on_image_captured)

        # Connect list item selection
        self.ui.parts_list.itemSelectionChanged.connect(self.on_part_selected)

        # Populate container combobox
        self.populate_container_list()

        # Connect add part button
        self.ui.addToContainerButton.clicked.connect(self.on_add_part_clicked)
        self.ui.qtySpinBox.setValue(1)  # Set default quantity to 1

        if self.ui.acquisition_combo.count() > 1:
            self.ui.acquisition_combo.setCurrentIndex(1)

    def populate_camera_list(self):
        self.ui.acquisition_combo.clear()
        self.ui.acquisition_combo.addItem("Manual", {"method": 0})

        camera_count = 0
        
        # Try cameras until we find one that doesn't open
        while True:
            cap = cv2.VideoCapture(camera_count)
            if not cap.isOpened():
                break
            
            # Get camera name if possible, otherwise use index
            ret, _ = cap.read()
            if ret:
                camera_name = f"Camera {camera_count}"
                self.ui.acquisition_combo.addItem(camera_name, {"method": 1, "camera_count": camera_count})
            
            cap.release()
            camera_count += 1

    def switch_camera(self, index):
        acqMethod = self.ui.acquisition_combo.itemData(index)
        if acqMethod["method"] == 1:
            self.video_view.show()
            self.video_view.switch_camera(acqMethod["camera_count"])
        else:
            print("No Camera")
            self.video_view.close_stream()
            self.video_view.hide()

    def on_image_captured(self, image:QImage):
        # Convert QImage to bytes in memory
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.WriteOnly)
        image.save(buffer, "JPG")
        buffer.close()

        # Prepare files for POST request 
        files = {'query_image': ('image.jpg', byte_array.data(), 'image/jpeg')}
        # Make POST request to API
        response = requests.post('https://api.brickognize.com/predict/parts', files=files)
        # Print response
        if response.status_code == 200:
            self.on_part_detected(image, response.json())
        else:
            print(f"Error: {response.status_code}", response.text)

    def on_part_detected(self, image, detectionData):
        # Convert bounding box coordinates
        bbleft = int(detectionData['bounding_box']['left'])
        bbright = int(detectionData['bounding_box']['right']) 
        bbupper = int(detectionData['bounding_box']['upper'])
        bblower = int(detectionData['bounding_box']['lower'])
        bb = QRect(bbleft, bbupper, bbright-bbleft, bblower-bbupper)

        self.video_view.setDetectionImage(image, bb)

        # Clear previous items
        self.ui.parts_list.clear()

        # Add detected parts to list widget
        for item in detectionData['items']:
            # Create list item with part info
            list_item = QListWidgetItem()
            list_item.setText(f"{item['id']} - {item['name']} - Score: {item['score']:.2%} ")
            
            # Store full item data in item's data role
            list_item.setData(Qt.UserRole, item)
            
            # Add item to list
            self.ui.parts_list.addItem(list_item)
        
        # Select first item if available
        if self.ui.parts_list.count() > 0:
            self.ui.parts_list.setCurrentRow(0)

    def on_part_selected(self):
        current_item = self.ui.parts_list.currentItem()
        if current_item:
            part_data = current_item.data(Qt.UserRole)
            logging.info(f"Selected part: {part_data['id']} - {part_data['name']}")
            self.update_colors_list(part_data['id'])

    def update_colors_list(self, part_id):
        self.ui.colors_list.clear()
        dbManage = DatabaseManager()
        colors = dbManage.getPartColors(part_id)
        for color in colors:                
            # Create list item
            item = self.create_color_list_item(color)
            self.ui.colors_list.addItem(item)

    def create_color_list_item(self, color:BrickColor) -> QListWidgetItem:
        item = QListWidgetItem()

        itemNext = f"{color.name} - {color.type}" if color.type else color.name
        item.setText(itemNext)

        bgColor = QColor(f"#{color.rgb}")
        item.setBackground(bgColor)

            # Set text color for better visibility
        luminance = (0.299 * bgColor.red() + 0.587 * bgColor.green() + 0.114 * bgColor.blue())
        text_color = Qt.white if luminance < 128 else Qt.black
        item.setForeground(text_color)

        item.setData(Qt.UserRole, color)
        return item

    def populate_container_list(self):
        self.ui.containerCombobox.clear()
        
        # Get containers from database
        db_manager = DatabaseManager()
        containers = db_manager.getContainers()
        
        # Add containers to combobox
        for container in containers:
            # Display name and part count
            display_text = f"{container.name} ({container.part_count} parts)"
            self.ui.containerCombobox.addItem(display_text, container.id)

    def on_add_part_clicked(self):
        """Handle adding part to container"""
        try:
            # Get selected part
            part_item = self.ui.parts_list.currentItem()
            if not part_item:
                logging.warning("No part selected")
                return

            # Get selected color
            color_item = self.ui.colors_list.currentItem()
            if not color_item:
                logging.warning("No color selected")
                return

            # Get selected container
            container_id = self.ui.containerCombobox.currentData()
            if container_id is None:
                logging.warning("No container selected")
                return

            # Get quantity
            quantity = self.ui.qtySpinBox.value()
            if quantity <= 0:
                logging.warning("Invalid quantity")
                return

            # Get part and color IDs
            part_data = part_item.data(Qt.UserRole)
            color_data = color_item.data(Qt.UserRole)
            
            # Get colors_parts ID
            dbManager = DatabaseManager()
            colorPart = dbManager.getColorPart(part_data['id'], color_data.id)
            if colorPart is None:
                logging.warning("No color_part found")
                return        

            # Insert into parts_collection
            if not dbManager.addColorPartToContainer(colorPart, container_id, quantity):
                logging.warning("Color_part not added to collection!")
                return                 

            logging.info(f"Added {quantity} of part {part_data['id']} in color {color_data.name} to container {container_id}")
            
            self.video_view.startStream()
            # Clear selection and reset quantity
            #self.ui.qtySpinBox.setValue(1)
            #self.video_view.clear_detection()
            #self.ui.parts_list.clear()
            #self.ui.colors_list.clear()

        except Exception as e:
            logging.error(f"Error adding part to collection: {str(e)}")

    def closeEvent(self, event):
        self.video_view.close_stream()
        super().closeEvent(event)

