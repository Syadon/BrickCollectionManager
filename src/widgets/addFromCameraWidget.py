from PySide6.QtWidgets import QWidget, QListWidgetItem, QTableWidgetItem, QMessageBox, QLabel, QStackedLayout, QVBoxLayout
from PySide6.QtGui import QImage, QIcon, QColor, QKeyEvent, QPainter, QPen, QPixmap, QKeySequence
from PySide6.QtCore import QByteArray, Qt, QRect, QBuffer, QEvent, Signal, QTimer
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QImageCapture, QCameraDevice, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from src.database import DatabaseManager, Container, BrickColor
from src.timedMessageBox import TimedMessageBox
from src.imageProvider import ImagesProvider
from src.widgets.colorLabel import ColorLabel
from src.utils import TransparentSelectionDelegate, qImageToOpenCV, rgb_to_hsv, calculate_hsv_similarity
from config import AppConfig
import cv2
import numpy as np
import logging
from src.brickRecongnition import BrickRecognition
from ui.ui_addFromCameraWidget import Ui_AddFromCameraWidget

class AddFromCameraWidget(QWidget):

    def __init__(self, container:Container|None = None, parent=None):
        super().__init__(parent)

        self.ui = Ui_AddFromCameraWidget()
        self.ui.setupUi(self)

        self.iconSize = AppConfig.DEFAULT_ICON_SIZE
        self.targetContainer = container
        self.imageCaputured = False
        self.colorsDetected = []
        self.current_part_id = None
        
        # Setup camera view stack layout
        self.camera_stack = QStackedLayout(self.ui.cameraView)
        
        # Create video widget container
        self.video_container = QWidget()
        self.video_container_layout = QVBoxLayout(self.video_container)
        self.video_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Setup video widget
        self.video_widget = QVideoWidget()
        self.video_container_layout.addWidget(self.video_widget)
        
        # Create captured image container
        self.capture_container = QWidget()
        self.capture_container_layout = QVBoxLayout(self.capture_container)
        # Set black background for capture container
        self.capture_container.setStyleSheet("background-color: black;")
        self.capture_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create label for captured image
        self.capture_label = QLabel()
        self.capture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_container_layout.addWidget(self.capture_label)
        
        # Add widgets to stack
        self.camera_stack.addWidget(self.video_container)
        self.camera_stack.addWidget(self.capture_container)
        
        # Setup QtMultimedia components
        self.media_capture_session = QMediaCaptureSession()
        self.camera = None
        self.image_capture = QImageCapture()
        
        self.media_capture_session.setVideoOutput(self.video_widget)
        self.media_capture_session.setImageCapture(self.image_capture)

        self.image_capture.imageCaptured.connect(self.on_image_captured)

        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self.on_image_loaded)

        # Connect colors_list selection changed signal
        self.ui.colors_list.itemSelectionChanged.connect(self.on_color_selected)

        # UI Connections
        self.ui.acquisition_combo.currentIndexChanged.connect(self.switch_camera)
        self.ui.captureButton.clicked.connect(self.capture_image)
        self.ui.skipButton.clicked.connect(self.on_next_clicked)
        self.ui.skipButton.clicked.connect(self.clearDetection)
        self.ui.addToContainerButton.clicked.connect(self.on_add_clicked)

        self.ui.parts_list.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.parts_list))
        self.ui.colors_list.setItemDelegateForColumn(0, TransparentSelectionDelegate(self.ui.colors_list))
        
        # Connect list item selection
        self.ui.parts_list.itemSelectionChanged.connect(self.on_part_selected)

        # Install event filter for keyboard events
        self.installEventFilter(self)
        
        # Initialize capture attributes
        self.captured_image = None
        self.detection_rect = None
        
        self.update_add_button_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update geometry immediately
        self.update_video_widget_geometry()
        # And schedule another update after a short delay to ensure proper sizing
        QTimer.singleShot(100, self.update_video_widget_geometry)
        
        # Update captured image if present
        if self.captured_image and self.detection_rect:
            self.setDetectionImage(self.captured_image, self.detection_rect)

    def update_video_widget_geometry(self):
        if self.video_widget and self.video_widget.isVisible():
            # Get the current geometry of the camera view
            view_rect = self.ui.cameraView.rect()
            # Update container geometry
            self.video_container.setGeometry(view_rect)
            self.capture_container.setGeometry(view_rect)
            # Force update
            self.video_widget.update()
            self.ui.cameraView.update()

    def showEvent(self, event):
        if self.ui.acquisition_combo.count() == 0:
            # Create camera selection combobox
            self.populate_camera_list()

        # Don't automatically start camera on show
        # Let user explicitly select a camera
        self.populate_container_list()

        super().showEvent(event)

    def hideEvent(self, event):
        self.close_stream()
        self.ui.acquisition_combo.setCurrentIndex(0)
        # Reset to dummy container
        self.ui.containerCombobox.setCurrentIndex(0)
        self.imgProvider.cleanup_tasks()
        super().hideEvent(event)

    def populate_container_list(self):
        self.ui.containerCombobox.clear()
        
        # Add dummy container as first option
        self.ui.containerCombobox.addItem("Select Container...", None)
        
        # Get containers from database
        db_manager = DatabaseManager()
        containers = db_manager.getContainers()
        
        # Add containers to combobox
        for container in containers:
            if self.targetContainer != None and container.id != self.targetContainer.id:
                continue

            # Display name and part count
            display_text = f"{container.name} ({container.part_count} parts)"
            self.ui.containerCombobox.addItem(display_text, (container.id, container.name))

        self.ui.containerCombobox.setEnabled(self.targetContainer == None)
        
        # Connect to selection change event if not already connected
        try:
            self.ui.containerCombobox.currentIndexChanged.disconnect(self.on_container_selection_changed)
        except:
            pass
        self.ui.containerCombobox.currentIndexChanged.connect(self.on_container_selection_changed)
        
        # Update add button state
        self.on_container_selection_changed(self.ui.containerCombobox.currentIndex())

    def populate_camera_list(self):
        self.ui.acquisition_combo.clear()

        # Add "Camera Off" as first option
        self.ui.acquisition_combo.addItem("Camera Off", None)

        # Add available cameras
        camera_devices = QMediaDevices.videoInputs()
        for device in camera_devices:
            self.ui.acquisition_combo.addItem(device.description(), device)
    
    def switch_camera(self, index):
        if index < 0 or index >= self.ui.acquisition_combo.count():
            return

        self.close_stream()
        
        camera_device = self.ui.acquisition_combo.itemData(index)
        if not camera_device:
            # If "Camera Off" is selected, just return after closing the stream
            return
            
        self.camera = QCamera(camera_device)
        self.media_capture_session.setCamera(self.camera)
        self.update()

        self.startStream()
    
    def startStream(self):
        if self.camera:
            self.camera.start()
            self.camera_stack.setCurrentWidget(self.video_container)
            self.video_widget.show()
            
    def close_stream(self):
        if self.camera:
            self.camera.stop()
            self.camera = None  # Reset camera to None when closing stream
        self.video_widget.hide()
    
    def capture_image(self):
        if self.camera and self.camera.isActive():
            self.image_capture.capture()
    
    def setDetectionImage(self, image, bb):
        self.captured_image = image.copy()
        self.detection_rect = bb
        
        # Create a copy of the image to draw on
        display_image = self.captured_image.copy()
        
        # Draw bounding box
        painter = QPainter(display_image)
        painter.setPen(QPen(Qt.GlobalColor.red, 3))
        painter.drawRect(bb)
        painter.end()
        
        # Convert to pixmap and scale
        pixmap = QPixmap.fromImage(display_image)
        scaled_pixmap = pixmap.scaled(
            self.ui.cameraView.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Set the image to the label
        self.capture_label.setPixmap(scaled_pixmap)
        
        # Switch to capture view
        self.camera_stack.setCurrentWidget(self.capture_container)

    def on_next_clicked(self):
        self.startStream()
        self.clearDetection()

    def on_add_clicked(self):
        try:
            result = self.on_add_part_clicked()
            if result:
                self.startStream()
                self.clearDetection()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def clearDetection(self):
        self.ui.parts_list.setRowCount(0)
        self.ui.colors_list.setRowCount(0)
        self.imageCaputured = False
        self.ui.qtySpinBox.setValue(1)
        self.captured_image = None
        self.detection_rect = None
        self.update_add_button_state()

    def on_image_captured(self, id, image:QImage):
        # Convert QImage to bytes in memory
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, "JPG", quality=90)
        buffer.close()

        self.imageCaputured = True

        recongnition = BrickRecognition()
        recognition_result = recongnition.recognize(bytearray(byte_array.data()), 
                                                    image_width=image.width(), 
                                                    image_height=image.height())
        if recognition_result:
            self.on_part_detected(image, recognition_result)

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
        color_data = color_item.data(Qt.ItemDataRole.UserRole)

        # Get current selected part row
        part_row = self.ui.parts_list.currentRow()
        if part_row < 0:
            return
        
        # Request image for the part with this color
        image = self.imgProvider.get_part_image(self.current_part_id, color_data.id)
        
        # If image is available, update immediately
        if image:
            self.update_part_image_camera(image, part_row)
        
        self.update_add_button_state()

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
                if item and item.data(Qt.ItemDataRole.UserRole)['id'] == part_id:
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
                
            color_data = color_item.data(Qt.ItemDataRole.UserRole)
            
            # Only update if this is our currently selected color
            if str(color_data.id) != color_id:
                return
            
        # Update image
        self.update_part_image_camera(pixmap, part_row)
        
    def update_part_image_camera(self, pixmap, row):
        if row < 0 or row >= self.ui.parts_list.rowCount():
            return
            
        # Scale image
        scaled = pixmap.scaled(self.iconSize, self.iconSize, 
                              Qt.AspectRatioMode.KeepAspectRatio, 
                              Qt.TransformationMode.SmoothTransformation)
        
        # Update image in table
        image_item = self.ui.parts_list.item(row, 0)
        if image_item:
            image_item.setIcon(QIcon(scaled))
            self.ui.parts_list.viewport().update()  # Force repaint
            self.ui.parts_list.resizeColumnsToContents()
            
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

        #self.setDetectionImage(image, bb)
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
                scaled = img.scaled(self.iconSize, self.iconSize, 
                                    Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
                image_item.setIcon(QIcon(scaled))
    
            id_item = QTableWidgetItem(f"{item['id']}")
            name_item = QTableWidgetItem(f"{item['name']}")
            score_item = QTableWidgetItem()
            score_item.setData(Qt.ItemDataRole.EditRole, round(item['score']*100, 2))

            # Store full item data in item's data role
            image_item.setData(Qt.ItemDataRole.UserRole, item)

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
            
        self.setDetectionImage(image, bb)
            
    def on_part_selected(self):
        current_row = self.ui.parts_list.currentRow()
        if current_row >= 0:
            # Get data from first column
            current_item = self.ui.parts_list.item(current_row, 0)
            if current_item:
                part_data = current_item.data(Qt.ItemDataRole.UserRole)
                self.current_part_id = part_data['id']  # Store current part ID
                logging.info(f"Selected part: {part_data['id']} - {part_data['name']}")
                self.update_colors_list(part_data['id'])
                
        self.update_add_button_state()
                
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
            part_data = part_item.data(Qt.ItemDataRole.UserRole)
            color_data = color_item.data(Qt.ItemDataRole.UserRole)

            # Get colors_parts ID
            dbManager = DatabaseManager()
            colorPart = dbManager.getColorPart(part_data['id'], color_data.id)
            if colorPart is None:
                logging.warning("No color_part found")
                return

            msg_pixmap = self.imgProvider.get_part_image(part_data['id'], color_data.id)
            # TODO: resize image to max
            #...

            # Show a message box with the part image to confirm addition
            msg = TimedMessageBox(timeout=5, buttons=[QMessageBox.StandardButton.Ok, 
                                                      QMessageBox.StandardButton.Cancel], 
                                  parent = self)
            msg.setWindowTitle("Adding Part")
            msg.setText(f"""
                <html>
                <p><b>Adding...</b></p>
                <p><b>Part:</b> {part_data['id']} - {part_data['name']}</p>
                <p><b>Color:</b> {color_data.name} - {color_data.type}</p>
                <p><b>Quantity:</b> {quantity}</p>
                <p><b>Container:</b> {container_name}</p>
                </html>
            """)
            # msg.setStandardButtons(QMessageBox.Ok|QMessageBox.Cancel)
            # msg.setDefaultButton(QMessageBox.Ok)            
            if msg_pixmap != None:
                # TODO: resize image to max
                msg.setIconPixmap(msg_pixmap)
            
            response = msg.exec()
            if response == QMessageBox.StandardButton.Cancel:
                return

            # Insert into parts_collection
            if not dbManager.addColorPartToContainer(colorPart, container_id, quantity):
                logging.warning("Color_part not added to collection!")
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Adding Part")
                msg.setText(f"Fail to add {quantity} of part {part_data['id']} - {part_data['name']} in color {color_data.name} - {color_data.type} to container {container_name}")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                if msg_pixmap != None:
                    msg.setIconPixmap(msg_pixmap)
                msg.exec()
                return

            newPartCount = dbManager.getConteinerPartCount(container_id)
            if newPartCount != None and newPartCount > 0:
                self.ui.containerCombobox.setItemText(self.ui.containerCombobox.currentIndex(), 
                    f"{container_name} ({newPartCount} parts)")

            logging.info(f"Added {quantity} of part {part_data['id']} in color {color_data.name} to container {container_id}")

            return True

        except Exception as e:
            logging.error(f"Error adding part to collection: {str(e)}")
            return False
            
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
            
            color.year_to = int(color.year_to) if color.year_to else 0

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
                weighted_score = float(similarity * (detected['percentage'] / 100))
                max_score = max(max_score, weighted_score)

            scored_colors.append((color, max_score))

        # Sort colors by score (highest first)
        scored_colors.sort(key=lambda x: (x[0].year_to, x[1]), reverse=True)

        # Add sorted colors to table
        for color, score in scored_colors:
            self.add_color_to_table(color, score)

        # Add remaining colors without RGB values at the end
        for color in colors:
            if not color.rgb:
                self.add_color_to_table(color)
                
    def add_color_to_table(self, color: BrickColor, score: float|None = None):
        row = self.ui.colors_list.rowCount()
        self.ui.colors_list.insertRow(row)

        # Create items
        # Create ColorLabel for color name with background color
        rgb_hex = color.rgb if color.rgb else None
        color_label = ColorLabel(color.name, rgb_hex)
        
        # Create empty item to store data (ColorLabel doesn't store data)
        name_item = QTableWidgetItem()
        name_item.setData(Qt.ItemDataRole.UserRole, color)
        
        type_item = QTableWidgetItem(color.type if color.type else "")
        score_item = QTableWidgetItem()
        score_item.setData(Qt.ItemDataRole.EditRole, round(score*100, 2) if score is not None else 0)
        id_item = QTableWidgetItem(str(color.id))
        year_item = QTableWidgetItem(str(color.year_to) if color.year_to else "")

        # Add items to row
        self.ui.colors_list.setItem(row, 0, name_item)  # Set the item with data
        self.ui.colors_list.setCellWidget(row, 0, color_label)  # Set the ColorLabel widget
        self.ui.colors_list.setItem(row, 1, type_item)
        self.ui.colors_list.setItem(row, 2, score_item)
        self.ui.colors_list.setItem(row, 3, year_item)
        self.ui.colors_list.setItem(row, 4, id_item)

    def create_color_list_item(self, color:BrickColor, score:float|None = None) -> QListWidgetItem:
        item = QListWidgetItem()

        itemText = f"{color.name} - {color.type}" if color.type else color.name
        if score != None:
            itemText += f" - Match score: {score:.2%}"

        item.setText(itemText)

        bgColor = QColor(f"#{color.rgb}")
        item.setBackground(bgColor)

            # Set text color for better visibility
        luminance = (0.299 * bgColor.red() + 0.587 * bgColor.green() + 0.114 * bgColor.blue())
        text_color = Qt.GlobalColor.white if luminance < 128 else Qt.GlobalColor.black
        item.setForeground(text_color)

        item.setData(Qt.ItemDataRole.UserRole, color)

        # Add score to tooltip
        item.setToolTip(f"Match score: {score:.2%}")

        return item

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

    def on_container_selection_changed(self, index):
        self.update_add_button_state()
        
    def update_add_button_state(self):
        # Disable add button if dummy container is selected
        container_data = self.ui.containerCombobox.currentData()
        has_selection = (self.ui.parts_list.currentRow() >= 0 and 
                        self.ui.colors_list.currentRow() >= 0)
        self.ui.addToContainerButton.setEnabled(container_data is not None and has_selection)

    def eventFilter(self, obj, event):
        """Handle keyboard events"""
        if event.type() == QEvent.Type.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key.Key_F1:
                if not self.imageCaputured:
                    # If no image is captured, capture one
                    self.capture_image()
                else:
                    # If image is captured and we can add the part, do it
                    if self.ui.addToContainerButton.isEnabled():
                        self.on_add_clicked()
                return True
            elif key_event.key() == Qt.Key.Key_Escape and self.imageCaputured:
                # If ESC is pressed and we have a captured image, trigger next/skip
                self.on_next_clicked()
                return True
            elif key_event.key() == Qt.Key.Key_F2 or key_event.key() == Qt.Key.Key_Plus:
                # Increase quantity by 1
                current_value = self.ui.qtySpinBox.value()
                self.ui.qtySpinBox.setValue(current_value + 1)
                return True
            elif key_event.key() == Qt.Key.Key_F3 or key_event.key() == Qt.Key.Key_Minus:
                # Decrease quantity by 1, but don't go below minimum
                current_value = self.ui.qtySpinBox.value()
                if current_value > self.ui.qtySpinBox.minimum():
                    self.ui.qtySpinBox.setValue(current_value - 1)
                return True
        return super().eventFilter(obj, event)