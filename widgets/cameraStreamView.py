from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsView, QGraphicsScene)
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QPen
from PySide6.QtCore import QTimer, Qt, Signal, QRect
import cv2
import logging

class CameraStreamView(QGraphicsView):
    image_captured = Signal(QImage)

    def __init__(self, parent=None):
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
            self.timer.start(40)  # Update every 40ms (approx. 25 fps)

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
                pixmap = self.opencvToPixmap(frame)

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
                image = self.opencvToQImage(frame)
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

    def opencvToQImage(self, image):
        # Convert to QImage
        h, w, ch = image.shape
        bytes_per_line = ch * w
        imageTmp = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return QImage(imageTmp.data, w, h, bytes_per_line, QImage.Format_RGB888)

    def opencvToPixmap(self, image):
        return QPixmap.fromImage(self.opencvToQImage(image))
