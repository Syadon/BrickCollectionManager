from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
import cv2
import numpy as np

class TransparentSelectionDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Rimuovi l'effetto di selezione
        option.state &= ~QStyle.State_Selected

def rgb_to_hsv(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    diff = cmax - cmin

    # Calculate Hue
    if diff == 0:
        h = 0
    elif cmax == r:
        h = (60 * ((g-b)/diff) + 360) % 360
    elif cmax == g:
        h = (60 * ((b-r)/diff) + 120) % 360
    else:
        h = (60 * ((r-g)/diff) + 240) % 360

    # Calculate Saturation
    s = 0 if cmax == 0 else (diff / cmax) * 100

    # Calculate Value
    v = cmax * 100

    return h, s, v

def calculate_hsv_similarity(hsv1, hsv2):
    h1, s1, v1 = hsv1
    h2, s2, v2 = hsv2
    
    # Calculate hue difference (considering circular nature of hue)
    h_diff = min(abs(h1 - h2), 360 - abs(h1 - h2)) / 180.0
    
    # Calculate saturation and value differences
    s_diff = abs(s1 - s2) / 100.0
    v_diff = abs(v1 - v2) / 100.0
    
    # Weight the components (adjustable weights)
    h_weight = 0.5
    s_weight = 0.25
    v_weight = 0.25
    
    # Calculate weighted similarity (1 is most similar, 0 is least similar)
    similarity = 1.0 - (
        h_weight * h_diff +
        s_weight * s_diff +
        v_weight * v_diff
    )
    
    return similarity

def qImageToOpenCV(image:QImage):
    # Crop the image using the bounding box
    img = image.convertToFormat(QImage.Format_RGB32)

    # Convert QImage to OpenCV format
    width = img.width()
    height = img.height()
    ptr = img.bits()
    #ptr.set(height * width * 4)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    cv_image = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    return cv_image

def opencvToQImage(image):
    # Convert to QImage
    h, w, ch = image.shape
    bytes_per_line = ch * w
    imageTmp = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return QImage(imageTmp.data, w, h, bytes_per_line, QImage.Format_RGB888)

def opencvToPixmap(image):
    return QPixmap.fromImage(opencvToQImage(image))