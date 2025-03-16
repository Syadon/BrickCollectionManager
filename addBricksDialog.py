from PySide6.QtWidgets import QDialog, QLabel, QComboBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
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

        # Create video display label
        self.video_label = QLabel()
        self.ui.gridLayout.addWidget(self.video_label, 0, 0, 1, 1)

        # Setup camera
        self.setup_camera()

        # Connect capture button
        self.ui.captureButton.clicked.connect(self.capture_image)

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
            self.timer.start(30)  # Update every 30ms (approx. 33 fps)

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
                
                # Scale image to fit label while maintaining aspect ratio
                pixmap = QPixmap.fromImage(image)
                scaled_pixmap = pixmap.scaled(self.video_label.size(), 
                                            Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation)
                
                # Display the image
                self.video_label.setPixmap(scaled_pixmap)

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

        """Setup the UI to display the detected part"""
        # Convert frame from BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        bbleft = int(detectionData['bounding_box']['left'])
        bbright = int(detectionData['bounding_box']['right'])
        bbupper = int(detectionData['bounding_box']['upper'])
        bblower = int(detectionData['bounding_box']['lower'])

        # Draw bounding box
        cv2.rectangle(image, (bbleft, bbupper), (bbright, bblower), (0, 255, 0), 2)
        
        for i in detectionData['items']:
            print(f"{i['id']} - {i['name']} - {i['score']} - {i['img_url']}")

        # Convert to QImage
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qimage = QImage(image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale image to fit label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(qimage)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), 
                                    Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation)
        
        # Display the image
        self.video_label.setPixmap(scaled_pixmap)

        # Display the detected part
        # self.ui.detectedPartLabel.setText(f"Detected Part: {detectionData['part']}")
        # self.ui.detectedPartLabel.show()


    def closeEvent(self, event):
        """Clean up resources when dialog is closed"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        if hasattr(self, 'cap'):
            self.cap.release()
        super().closeEvent(event)
