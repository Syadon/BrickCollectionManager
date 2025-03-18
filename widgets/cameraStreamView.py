from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsView, QGraphicsScene)
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen
from PySide6.QtCore import QTimer, Qt, Signal, QRect
from utils import opencvToPixmap, opencvToQImage
import cv2
import logging

class CameraStreamView(QGraphicsView):
    image_captured = Signal(QImage)

    def __init__(self, parent=None):
        self.avg_a = None
        self.avg_b = None
        self.wbEnebled = False

        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        # self.setSceneRect(0, 0, 640, 480)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setRenderHint(QPainter.TextAntialiasing)

        self.setup_camera()

    def clearScene(self):
        self.scene.clear()

    def close_stream(self):
        self.timer.stop()
        self.cap.release()

    def startStream(self):
            self.timer.start(40)  # Update every 40ms (approx. 25 fps)

    def setup_camera(self, camera_id=0):
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
            self.startStream()

        except Exception as e:
            logging.error(f"Camera setup failed: {str(e)}")
            self.close()

    def switch_camera(self, camera_id):
        self.cap.release()
        self.timer.stop()
        self.setup_camera(camera_id)

    def update_frame(self):
        try:
            ret, frame = self.cap.read()
            if ret:
                if self.wbEnebled:
                    frame = self.whiteBalance(frame)

                pixmap = opencvToPixmap(frame)

                # Clear previous frame
                self.clearScene()

                # Add new frame to scene
                self.scene.addPixmap(pixmap)
                
                # Fit scene in view
                self.fitInView(self.scene.sceneRect(), 
                                        Qt.KeepAspectRatio)

        except Exception as e:
            logging.error(f"Frame update failed: {str(e)}")
            self.timer.stop()

    def capture_image(self):
        try:
            ret, frame = self.cap.read()
            if ret:
                image = opencvToQImage(frame)
                self.image_captured.emit(image)
        except Exception as e:
            logging.error(f"Image capture failed: {str(e)}")

    def setDetectionImage(self, image:QImage, detectionBB:QRect):
        self.timer.stop()
        self.clearScene()

        # Create rectangle item
        rect = QGraphicsRectItem(detectionBB)
        rect.setPen(QPen(QColor(0, 255, 0), 2))

        pixmap = QPixmap.fromImage(image)
        self.scene.addPixmap(pixmap)
        self.scene.addItem(rect)
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

    def enableWhiteBalance(self, enable):
        if enable:
            self.computeWhiteBalance()

        self.wbEnebled = enable

    def computeWhiteBalance(self):
        try:
            ret, frame = self.cap.read()
            if ret:
                # Convert to LAB color space
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

                # Calculate average L, A, B values
                l, a, b = cv2.split(lab)
                self.avg_a = int(cv2.mean(a)[0])
                self.avg_b = int(cv2.mean(b)[0])
        except Exception as e:
            logging.error(f"Compute white balance failed: {str(e)}")
            self.avg_a = None
            self.avg_b = None

    def whiteBalance(self, image):
        if self.avg_a == None or self.avg_b == None:
            return image

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB) 
        l, a, b = cv2.split(lab)    
        # Subtract mean values to balance
        lab_balanced = cv2.merge([l, 
                                 cv2.subtract(a, self.avg_a - 128), 
                                 cv2.subtract(b, self.avg_b - 128)])

        # Convert back to BGR
        return cv2.cvtColor(lab_balanced, cv2.COLOR_LAB2BGR)
