from PySide6.QtWidgets import (QDialog, QComboBox, QListWidget, QGraphicsRectItem, 
                              QListWidgetItem, QGraphicsView, QGraphicsScene)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen
from database import DatabaseManager, BrickColor
from ui.ui_addbricksdialog import Ui_AddBricksDialog
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

        # Create camera selection combobox
        self.camera_combo = QComboBox()
        self.ui.gridLayout.addWidget(self.camera_combo, 1, 0, 1, 1)
        self.populate_camera_list()
        self.camera_combo.currentIndexChanged.connect(self.switch_camera)

        # Replace the video label creation with graphics view
        self.video_scene = QGraphicsScene()
        self.video_view = QGraphicsView(self.video_scene)
        self.video_view.setMinimumSize(640, 480)
        self.video_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.video_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.ui.gridLayout.addWidget(self.video_view, 0, 0, 1, 1)

        # Create parts list widget
        self.parts_list = QListWidget()
        self.parts_list.setMinimumWidth(300)  # Set minimum width for better visibility
        self.ui.gridLayout.addWidget(self.parts_list, 0, 1, 2, 1)  # Span 2 rows

        # Create colors list widget
        self.colors_list = QListWidget()
        self.colors_list.setMinimumWidth(300)  # Match parts list width
        self.colors_list.setMaximumHeight(150)  # Limit height
        self.ui.gridLayout.addWidget(self.colors_list, 2, 1, 1, 1)  # Add below parts_list

        # Set column stretch factors (3:1 ratio)
        self.ui.gridLayout.setColumnStretch(0, 2)  # Video column gets 2 parts
        self.ui.gridLayout.setColumnStretch(1, 1)  # Lists get 1 part

        # Setup camera
        self.setup_camera()

        # Connect capture button
        self.ui.captureButton.clicked.connect(self.capture_image)

        # Connect list item selection
        self.parts_list.itemSelectionChanged.connect(self.on_part_selected)

    def populate_camera_list(self):
        """Find and populate available cameras"""
        self.camera_combo.clear()
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
                self.camera_combo.addItem(camera_name, camera_count)
            
            cap.release()
            camera_count += 1

    def switch_camera(self, index):
        """Switch to the selected camera"""
        if hasattr(self, 'cap'):
            self.cap.release()
        if hasattr(self, 'timer'):
            self.timer.stop()
            
        camera_id = self.camera_combo.itemData(index)
        self.setup_camera(camera_id)

    def setup_camera(self, camera_id=0):
        """Initialize the camera and start the video stream"""
        try:
            # Initialize selected camera
            self.cap = cv2.VideoCapture(camera_id)
            if not self.cap.isOpened():
                raise Exception(f"Could not open camera {camera_id}")

            # Set camera properties
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, actual_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, actual_height)

            # Create timer for video updates
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(40)  # Update every 40ms (approx. 25 fps)

        except Exception as e:
            logging.error(f"Camera setup failed: {str(e)}")
            self.close()

    def update_frame(self):
        """Update the video frame"""
        try:
            ret, frame = self.cap.read()
            if ret:
                # Convert frame from BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convert to QImage
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Convert to QPixmap and add to scene
                pixmap = QPixmap.fromImage(image)
                
                # Clear previous frame
                self.video_scene.clear()
                
                # Add new frame to scene
                self.video_scene.addPixmap(pixmap)
                
                # Fit scene in view
                self.video_view.fitInView(self.video_scene.sceneRect(), 
                                        Qt.KeepAspectRatio)

        except Exception as e:
            logging.error(f"Frame update failed: {str(e)}")
            self.timer.stop()

    def capture_image(self):
        """Capture and save the current frame"""
        try:
            ret, frame = self.cap.read()
            if ret:
                # Convert frame to jpg format in memory
                _, img_encoded = cv2.imencode('.jpg', frame)
                # Prepare the files for the POST request
                files = {'query_image': ('image.jpg', img_encoded.tobytes(), 'image/jpeg')}
                # Make POST request to API
                response = requests.post('https://api.brickognize.com/predict/parts', files=files)
                # Print response
                if response.status_code == 200:
                    self.partDetectedSetup(frame, response.json())
                else:
                    print(f"Error: {response.status_code}", response.text)
        except Exception as e:
            logging.error(f"Image capture failed: {str(e)}")

    def partDetectedSetup(self, image, detectionData):
        self.timer.stop()

        # Clear scene
        self.video_scene.clear()

        # Convert frame from BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Draw bounding box
        # Add bounding box to scene using QGraphicsRectItem

        # Convert bounding box coordinates
        bbleft = int(detectionData['bounding_box']['left'])
        bbright = int(detectionData['bounding_box']['right']) 
        bbupper = int(detectionData['bounding_box']['upper'])
        bblower = int(detectionData['bounding_box']['lower'])

        # Create rectangle item
        rect = QGraphicsRectItem(bbleft, bbupper, bbright-bbleft, bblower-bbupper)
        rect.setPen(QPen(QColor(0, 255, 0), 2))

        pixmap = self.opencvToPixmap(image)
        self.video_scene.addPixmap(pixmap)
        self.video_scene.addItem(rect)
        self.video_view.fitInView(self.video_scene.sceneRect(), Qt.KeepAspectRatio)

        # Clear previous items
        self.parts_list.clear()

        # Add detected parts to list widget
        for item in detectionData['items']:
            # Create list item with part info
            list_item = QListWidgetItem()
            list_item.setText(f"{item['id']} - {item['name']} - Score: {item['score']:.2%} ")
            
            # Store full item data in item's data role
            list_item.setData(Qt.UserRole, item)
            
            # Add item to list
            self.parts_list.addItem(list_item)
        
        # Select first item if available
        if self.parts_list.count() > 0:
            self.parts_list.setCurrentRow(0)

    def opencvToPixmap(self, image):
        # Convert to QImage
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qimage = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Convert to QPixmap and update scene
        return QPixmap.fromImage(qimage)

    def on_part_selected(self):
        """Handle part selection from list"""
        current_item = self.parts_list.currentItem()
        if current_item:
            part_data = current_item.data(Qt.UserRole)
            logging.info(f"Selected part: {part_data['id']} - {part_data['name']}")
            self.update_colors_list(part_data['id'])

    def update_colors_list(self, part_id):
        """Update colors list for selected part"""
        self.colors_list.clear()
        dbManage = DatabaseManager()
        colors = dbManage.getPartColors(part_id)
        for color in colors:                
            # Create list item
            item = self.create_color_list_item(color)
            self.colors_list.addItem(item)

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

    def closeEvent(self, event):
        """Clean up resources when dialog is closed"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'cap'):
            self.cap.release()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'video_view') and hasattr(self, 'video_scene'):
            self.video_view.fitInView(self.video_scene.sceneRect(), Qt.KeepAspectRatio)
