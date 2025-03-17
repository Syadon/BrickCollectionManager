from PySide6.QtWidgets import QDialog, QListWidgetItem, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, QByteArray, QBuffer, QRect
from PySide6.QtGui import QImage, QColor, QIcon, QPixmap, QPainter
from database import DatabaseManager, BrickColor
from ui.ui_addbricksdialog import Ui_AddBricksDialog
from widgets.cameraStreamView import CameraStreamView
from config import AppConfig
from utils import rgb_to_hsv, calculate_hsv_similarity, qImageToOpenCV
import cv2
import numpy as np
import logging
import requests

class AddBricksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.colorsDetected = []

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
            detectionData = response.json()
            self.on_part_detected(image, detectionData)
        else:
            print(f"Error: {response.status_code}", response.text)

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
        # Convert bounding box coordinates
        bbleft = int(detectionData['bounding_box']['left'])
        bbright = int(detectionData['bounding_box']['right']) 
        bbupper = int(detectionData['bounding_box']['upper'])
        bblower = int(detectionData['bounding_box']['lower'])
        bb = QRect(bbleft, bbupper, bbright-bbleft, bblower-bbupper)

        self.video_view.setDetectionImage(image, bb)
        self.colorsDetected = self.detect_image_colors(image, bb)

        # Clear previous items
        self.ui.parts_list.setRowCount(0)

        iconSize = 100

        # Add detected parts to list widget
        for item in detectionData['items']:
            row = self.ui.parts_list.rowCount()
            self.ui.parts_list.insertRow(row)
            # Create list item with part info
            image_item = QTableWidgetItem()
            response = requests.get(item['img_url'])
            if response.status_code == 200:
                img = QImage.fromData(response.content)
                if not img.isNull():
                    scaled = img.scaled(iconSize, iconSize, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_item.setIcon(QIcon(QPixmap.fromImage(scaled)))
    
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
        self.ui.parts_list.verticalHeader().setDefaultSectionSize(iconSize)

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
            self.ui.containerCombobox.addItem(display_text, container.id)

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

