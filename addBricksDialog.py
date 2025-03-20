from PySide6.QtWidgets import QDialog, QListWidgetItem, QTableWidgetItem
from PySide6.QtCore import Qt, QByteArray, QBuffer, QRect
from PySide6.QtGui import QImage, QColor, QIcon, QPixmap
from database import DatabaseManager, BrickColor
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from cameraStreamManager import CameraStreamManager
from config import AppConfig
from utils import rgb_to_hsv, calculate_hsv_similarity, qImageToOpenCV, TransparentSelectionDelegate
from imageProvider import ImagesProvider
from brickRecongnition import BrickRecognition
import cv2
import numpy as np
import logging
import requests
from PySide6.QtWidgets import QMessageBox

class AddBricksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.colorsDetected = []
        self.iconSize = 100
        self.current_part_id = None
        
        # Create image provider
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)

        # Create and setup UI
        self.ui = Ui_AddBricksDialog()
        self.ui.setupUi(self)

        # Connect colors_list selection changed signal
        self.ui.colors_list.itemSelectionChanged.connect(self.on_color_selected)

        self.video_manager = CameraStreamManager(self.ui.cameraView, self)

        # Create camera selection combobox
        self.populate_camera_list()
        self.ui.acquisition_combo.currentIndexChanged.connect(self.switch_camera)

        # Connect capture button
        self.ui.captureButton.clicked.connect(self.video_manager.capture_image)
        self.ui.skipButton.clicked.connect(self.video_manager.startStream)
        self.ui.skipButton.clicked.connect(self.clearDetection)
        self.ui.whiteBalanceButton.toggled.connect(self.video_manager.enableWhiteBalance)
        self.video_manager.image_captured.connect(self.on_image_captured)

        self.ui.parts_list.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.parts_list))
        self.ui.colors_list.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.colors_list))
        
        # Connect list item selection
        self.ui.parts_list.itemSelectionChanged.connect(self.on_part_selected)

        # Populate container combobox
        self.populate_container_list()

        # Connect add part button
        self.ui.addToContainerButton.clicked.connect(self.on_add_part_clicked)

        self.ui.skipButton.clicked.connect(self.on_next_clicked)

        self.ui.qtySpinBox.setValue(1)  # Set default quantity to 1

        # Connect tab change signal
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Initial check of camera tab visibility
        self.on_tab_changed(self.ui.tabWidget.currentIndex())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.video_manager.manageResizeEvent(event)

    def populate_camera_list(self):
        self.ui.acquisition_combo.clear()
        # self.ui.acquisition_combo.addItem("Manual", {"method": 0})

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

    def clearDetection(self):
        self.ui.parts_list.setRowCount(0)
        self.ui.colors_list.setRowCount(0)

    def switch_camera(self, index):
        acqMethod = self.ui.acquisition_combo.itemData(index)
        
        if acqMethod["method"] == 1:
            self.ui.cameraView.show()
            self.video_manager.switch_camera(acqMethod["camera_count"])
            
            # Only start stream if camera tab is visible
            camera_tab_visible = (self.ui.tabWidget.currentIndex() == self.ui.tabWidget.indexOf(self.ui.cameraTab))
            if camera_tab_visible:
                self.video_manager.startStream()
        else:
            print("No Camera")
            self.video_manager.close_stream()
            self.ui.cameraView.hide()

    def on_image_captured(self, image:QImage):
        # Convert QImage to bytes in memory
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.WriteOnly)
        image.save(buffer, "JPG")
        buffer.close()

        recongnition = BrickRecognition()
        recognition_result = recongnition.recognize(byte_array)
        if recognition_result:
            self.on_part_detected(image, recognition_result)

    def detect_image_colors(self, image:QImage, bb:QRect):
        try:
            cropped = image.copy(bb)
            cv_image = qImageToOpenCV(cropped)

            # Reshape the image to be a list of pixels
            pixels = cv_image.reshape((-1, 3)).astype(np.float32)

            # Define criteria and apply kmeans
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            k = 3  # Number of clusters (main colors)
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Convert centers to integers
            centers = centers.astype(np.uint8)

            # Get the count of pixels in each cluster
            unique_labels, counts = np.unique(labels, return_counts=True)
            total_pixels = sum(counts)

            # Sort colors by frequency
            colors_with_percentages = []
            for i, center in enumerate(centers):
                b, g, r = center
                pixel_count = counts[i]
                percentage = (pixel_count / total_pixels) * 100
                hex_color = f"{r:02x}{g:02x}{b:02x}"
                colors_with_percentages.append({
                    'rgb': (r, g, b),
                    'hex': hex_color.upper(),
                    'percentage': percentage
                })

            # Sort by percentage
            colors_with_percentages.sort(key=lambda x: x['percentage'], reverse=True)

            return colors_with_percentages
        except Exception as e:
            logging.error(f"Error detecting colors: {str(e)}")
            return []

    def on_part_detected(self, image, detectionData):
        # Check if detectionData contains required fields
        if 'bb' not in detectionData or 'items' not in detectionData:
            logging.error("Detection data missing required fields (bb or items)")
            return

        # Check if bb contains all required coordinates
        if not all(key in detectionData['bb'] for key in ['left', 'right', 'upper', 'lower']):
            logging.error("Bounding box missing required coordinates")
            return

        # Check if items list is not empty
        if not detectionData['items']:
            logging.error("No items detected")
            return

        bbleft = int(detectionData['bb']['left'])
        bbright = int(detectionData['bb']['right']) 
        bbupper = int(detectionData['bb']['upper'])
        bblower = int(detectionData['bb']['lower'])
        bb = QRect(bbleft, bbupper, bbright-bbleft, bblower-bbupper)

        self.video_manager.setDetectionImage(image, bb)
        self.colorsDetected = self.detect_image_colors(image, bb)

        # Clear previous items
        self.ui.parts_list.setRowCount(0)

        # Add detected parts to list widget
        for item in detectionData['items']:
            row = self.ui.parts_list.rowCount()
            self.ui.parts_list.insertRow(row)
            # Create list item with part info
            image_item = QTableWidgetItem()
            img = self.imgProvider.get_image_from_url(item['img_url'], f"{item['id']}_part")
            if img != None and not img.isNull():
                scaled = img.scaled(self.iconSize, self.iconSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image_item.setIcon(QIcon(scaled))
    
            id_item = QTableWidgetItem(f"{item['id']}")
            name_item = QTableWidgetItem(f"{item['name']}")
            score_item = QTableWidgetItem()
            score_item.setData(Qt.EditRole, round(item['score']*100, 2))

            # Store full item data in item's data role
            image_item.setData(Qt.UserRole, item)

            # Add item to list
            self.ui.parts_list.setItem(row, 0, image_item)
            self.ui.parts_list.setItem(row, 1, id_item)
            self.ui.parts_list.setItem(row, 2, name_item)
            self.ui.parts_list.setItem(row, 3, score_item)
        
        # Adjust row heights for icons
        self.ui.parts_list.verticalHeader().setDefaultSectionSize(self.iconSize)

        # Adjust columns to content
        self.ui.parts_list.resizeColumnsToContents()

        # Select first item if available
        if self.ui.parts_list.rowCount() > 0:
            self.ui.parts_list.selectRow(0)

    def on_part_selected(self):
        current_row = self.ui.parts_list.currentRow()
        if current_row >= 0:
            # Get data from first column
            current_item = self.ui.parts_list.item(current_row, 0)
            if current_item:
                part_data = current_item.data(Qt.UserRole)
                self.current_part_id = part_data['id']  # Store current part ID
                logging.info(f"Selected part: {part_data['id']} - {part_data['name']}")
                self.update_colors_list(part_data['id'])

    def update_colors_list(self, part_id):
        self.ui.colors_list.setRowCount(0)
        dbManage = DatabaseManager()
        colors = dbManage.getPartColors(part_id)

        # Skip sorting if no detected colors
        if not self.colorsDetected:
            for color in colors:
                self.add_color_to_table(color)
            return

        # Calculate color similarity scores
        scored_colors = []
        for color in colors:
            # Skip colors without RGB values
            if not color.rgb:
                continue

            # Convert color RGB string to tuple
            c = QColor(f"#{color.rgb}")
            r, g, b = c.red(), c.green(), c.blue()
            color_hsv = rgb_to_hsv(r, g, b)
            
            # Calculate best match score against detected colors
            max_score = 0
            for detected in self.colorsDetected:
                dr, dg, db = detected['rgb']
                detected_hsv = rgb_to_hsv(dr, dg, db)
                
                # Calculate similarity in HSV space
                similarity = calculate_hsv_similarity(color_hsv, detected_hsv)
                
                # Weight similarity by detected color percentage
                weighted_score = similarity * (detected['percentage'] / 100)
                max_score = max(max_score, weighted_score)

            scored_colors.append((color, max_score))

        # Sort colors by score (highest first)
        scored_colors.sort(key=lambda x: x[1], reverse=True)

        # Add sorted colors to table
        for color, score in scored_colors:
            self.add_color_to_table(color, score.item())

        # Add remaining colors without RGB values at the end
        for color in colors:
            if not color.rgb:
                self.add_color_to_table(color)

    def add_color_to_table(self, color: BrickColor, score: float = None):
        row = self.ui.colors_list.rowCount()
        self.ui.colors_list.insertRow(row)

        # Create items
        name_item = QTableWidgetItem(color.name)
        type_item = QTableWidgetItem(color.type if color.type else "")
        score_item = QTableWidgetItem()
        score_item.setData(Qt.EditRole, round(score*100, 2) if score is not None else 0)
        id_item = QTableWidgetItem(str(color.id))

        # Set background color
        if color.rgb:
            bg_color = QColor(f"#{color.rgb}")
            name_item.setBackground(bg_color)
            
            # Set text color for better visibility
            luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
            text_color = Qt.white if luminance < 128 else Qt.black
            name_item.setForeground(text_color)

        # Store color data
        name_item.setData(Qt.UserRole, color)

        # Add items to row
        self.ui.colors_list.setItem(row, 0, name_item)
        self.ui.colors_list.setItem(row, 1, type_item)
        self.ui.colors_list.setItem(row, 2, score_item)
        self.ui.colors_list.setItem(row, 3, id_item)

    def create_color_list_item(self, color:BrickColor, score:float = None) -> QListWidgetItem:
        item = QListWidgetItem()

        itemText = f"{color.name} - {color.type}" if color.type else color.name
        if score != None:
            itemText += f" - Match score: {score:.2%}"

        item.setText(itemText)

        bgColor = QColor(f"#{color.rgb}")
        item.setBackground(bgColor)

            # Set text color for better visibility
        luminance = (0.299 * bgColor.red() + 0.587 * bgColor.green() + 0.114 * bgColor.blue())
        text_color = Qt.white if luminance < 128 else Qt.black
        item.setForeground(text_color)

        item.setData(Qt.UserRole, color)

        # Add score to tooltip
        item.setToolTip(f"Match score: {score:.2%}")

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
            self.ui.containerCombobox.addItem(display_text, (container.id, container.name))

    def on_next_clicked(self):
        self.video_manager.startStream()
        self.clearDetection()

    def on_add_part_clicked(self):
        try:
            # Get selected part
            current_row = self.ui.parts_list.currentRow()
            if current_row < 0:
                logging.warning("No part selected")
                return
                
            part_item = self.ui.parts_list.item(current_row, 0)
            if not part_item:
                logging.warning("No part data found")
                return

            # Get selected color
            color_current_row = self.ui.colors_list.currentRow()
            if color_current_row < 0:
                return
                
            color_item = self.ui.colors_list.item(color_current_row, 0)
            if not color_item:
                return

            # Get selected container
            container_data = self.ui.containerCombobox.currentData()
            container_id, container_name = container_data
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

            newPartCount = dbManager.getConteinerPartCount(container_id)
            if newPartCount != None and newPartCount > 0:
                self.ui.containerCombobox.setItemText(self.ui.containerCombobox.currentIndex(), 
                    f"{container_name} ({newPartCount} parts)")

            logging.info(f"Added {quantity} of part {part_data['id']} in color {color_data.name} to container {container_id}")
            
            # Show a message box with the part image to confirm addition
            msg = QMessageBox(self)
            msg.setWindowTitle("Part Added")
            msg.setText(f"Added {quantity} of part {part_data['id']} - {part_data['name']} in color {color_data.name} - {color_data.type} to container {container_name}")
            msg.setStandardButtons(QMessageBox.Ok)

            # Get the part image
            pixmap = self.imgProvider.get_part_image(part_data['id'], color_data.id)
            if pixmap != None:
                # TODO: resize image to max
                msg.setIconPixmap(pixmap)

            msg.exec()

            self.video_manager.startStream()
            self.clearDetection()

        except Exception as e:
            logging.error(f"Error adding part to collection: {str(e)}")

    def closeEvent(self, event):
        self.video_manager.close_stream()
        super().closeEvent(event)

    def on_color_selected(self):
        # Check if a part is selected
        if not self.current_part_id:
            return
            
        # Get selected color
        current_row = self.ui.colors_list.currentRow()
        if current_row < 0:
            return
            
        color_item = self.ui.colors_list.item(current_row, 0)
        if not color_item:
            return
            
        # Get color data
        color_data = color_item.data(Qt.UserRole)
        
        # Get current selected part row
        part_row = self.ui.parts_list.currentRow()
        if part_row < 0:
            return
        
        # Request image for the part with this color
        image = self.imgProvider.get_part_image(self.current_part_id, color_data.id)
        
        # If image is available, update immediately
        if image:
            self.update_part_image(image, part_row)
        # If not, it will be handled by on_image_loaded when available

    def on_image_loaded(self, key, pixmap):
        # Parse key to get part_id and color_id
        try:
            part_id, color_id = key.split('_')
        except:
            return
        
        if color_id == "part":
            part_row = -1
            for row in range(self.ui.parts_list.rowCount()):
                item = self.ui.parts_list.item(row, 0)
                if item and item.data(Qt.UserRole)['id'] == part_id:
                    part_row = row
                    break

            if part_row < 0:
                return
        else:
            # Only process if we have a current part selected
            if not self.current_part_id:
                return
            
            # Only update if this is our current part
            if part_id != self.current_part_id:
                return
            
            # Get current selected part and color
            part_row = self.ui.parts_list.currentRow()
            color_row = self.ui.colors_list.currentRow()
            
            if part_row < 0 or color_row < 0:
                return
                
            # Get color data of selected color
            color_item = self.ui.colors_list.item(color_row, 0)
            if not color_item:
                return
                
            color_data = color_item.data(Qt.UserRole)
            
            # Only update if this is our currently selected color
            if str(color_data.id) != color_id:
                return
            
        # Update image
        self.update_part_image(pixmap, part_row)

    def update_part_image(self, pixmap, row):
        if row < 0 or row >= self.ui.parts_list.rowCount():
            return
            
        # Scale image
        scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                              Qt.KeepAspectRatio, 
                              Qt.SmoothTransformation)
        
        # Update image in table
        image_item = self.ui.parts_list.item(row, 0)
        if image_item:
            image_item.setIcon(QIcon(scaled))
            self.ui.parts_list.viewport().update()  # Force repaint
            self.ui.parts_list.resizeColumnsToContents()

    def on_tab_changed(self, index):
        # Check if the camera tab is visible
        camera_tab_visible = (index == self.ui.tabWidget.indexOf(self.ui.cameraTab))
        
        # Start or stop camera stream based on visibility
        if camera_tab_visible:
            # Camera tab is visible, start stream if acquisition method is camera
            current_index = self.ui.acquisition_combo.currentIndex()
            if current_index >= 0:
                acqMethod = self.ui.acquisition_combo.itemData(current_index)
                if acqMethod and acqMethod.get("method") == 1:
                    self.video_manager.setup_camera(acqMethod["camera_count"])
        else:
            # Camera tab is not visible, stop the stream
            self.video_manager.close_stream()

