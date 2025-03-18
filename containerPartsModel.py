from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtGui import QColor, QBrush, QPixmap
from config import AppConfig
from imageProvider import ImagesProvider

class ContainerPartsModel(QAbstractTableModel):
    def __init__(self, parts_data=None):
        super().__init__()
        self.parts_data = parts_data or []
        self.headers = ["Image", "ID", "Part", "Category", "Color", "Color Type", "Quantity"]
        self.attrCols = ["image", "part_id", "part_name", "part_category", "color_name", "color_type", "quantity"]
        
        self.colorColumnIndex = self.headers.index("Color")
        self.imageColumnIndex = self.headers.index("Image")
        
        # Load images for all parts
        self.load_part_images()

    def load_part_images(self):
        imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        imageSizes = (64, 64)
        for row in self.parts_data:
            color_id = row.get('color_id')
            part_id = row.get('part_id')
            if color_id and part_id:
                image = imgProvider.get_part_image(part_id, color_id, imageSizes)
                row['image'] = image

    def rowCount(self, parent):
        return len(self.parts_data)

    def columnCount(self, parent):
        return len(self.headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() != self.imageColumnIndex:  # Don't show text in image column
                row = self.parts_data[index.row()]
                col = index.column()
                return row[self.attrCols[col]]
            return None
            
        elif role == Qt.DecorationRole and index.column() == self.imageColumnIndex:
            return self.parts_data[index.row()].get('image')
        
        elif role == Qt.BackgroundRole and index.column() == self.colorColumnIndex:
            row = self.parts_data[index.row()]
            rgb_values = QColor(f"#{row['rgb']}")
            return QBrush(rgb_values)

        elif role == Qt.ForegroundRole and index.column() == self.colorColumnIndex:
            row = self.parts_data[index.row()]
            # Calculate luminance to determine text color
            rgb_values = QColor(f"#{row['rgb']}")
            luminance = (0.299 * rgb_values.red() + 
                        0.587 * rgb_values.green() + 
                        0.114 * rgb_values.blue())
            # Use white text for dark colors, black for light colors
            return QBrush(QColor('white' if luminance < 128 else 'black'))

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None
