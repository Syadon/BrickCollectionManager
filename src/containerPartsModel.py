from PySide6.QtCore import QAbstractTableModel, Qt, QSize
from PySide6.QtGui import QColor, QBrush, QPixmap
from config import AppConfig
from src.imageProvider import ImagesProvider
from src.database import CollectionPart

class ContainerPartsModel(QAbstractTableModel):
    def __init__(self, parts_data=None):
        super().__init__()
        self.parts_data = parts_data or []
        self.headers = ["Image", "ID", "Part", "Category", "Color", "Color Type", "Quantity"]
        self.attrCols = ["image", "part_id", "part_name", "part_category", "color_name", "color_type", "quantity"]
        
        self.colorColumnIndex = self.headers.index("Color")
        self.imageColumnIndex = self.headers.index("Image")

        self.imageSizes = QSize(64, 64)
        
        # Create image provider
        self.imgProvider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)
        self.imgProvider.image_loaded.connect(self._update_image)
        
        # Load images for all parts
        self.load_part_images()

    def load_part_images(self):
        for loot in self.parts_data:
            if hasattr(loot, 'color_id') and hasattr(loot, 'part_id'):
                image = self.imgProvider.get_part_image(loot.part_id, loot.color_id)
                if image != None:
                    # Store image in a temporary dictionary since it's not part of Loot class
                    if not hasattr(loot, '_temp_data'):
                        loot._temp_data = {}
                    loot._temp_data['image'] = image.scaled(self.imageSizes, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def _update_image(self, key, pixmap):
        part_id, color_id = key.split('_')
        
        # Find all rows with this part_id and color_id
        for row_idx, loot in enumerate(self.parts_data):
            if (loot.part_id == part_id and 
                str(loot.color_id) == color_id):
                if not hasattr(loot, '_temp_data'):
                    loot._temp_data = {}
                loot._temp_data['image'] = pixmap.scaled(self.imageSizes, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # Notify view that data has changed
                model_idx = self.index(row_idx, self.imageColumnIndex)
                self.dataChanged.emit(model_idx, model_idx)

    def rowCount(self, parent):
        return len(self.parts_data)

    def columnCount(self, parent):
        return len(self.headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        loot = self.parts_data[index.row()]
        col = index.column()
        attr = self.attrCols[col]

        if role == Qt.DisplayRole:
            if index.column() != self.imageColumnIndex:  # Don't show text in image column
                if attr == 'image':
                    return None
                return getattr(loot, attr)
            return None
            
        elif role == Qt.DecorationRole and index.column() == self.imageColumnIndex:
            if hasattr(loot, '_temp_data'):
                return loot._temp_data.get('image')
            return None
        
        elif role == Qt.BackgroundRole and index.column() == self.colorColumnIndex:
            rgb_values = QColor(f"#{loot.rgb}")
            return QBrush(rgb_values)

        elif role == Qt.ForegroundRole and index.column() == self.colorColumnIndex:
            # Calculate luminance to determine text color
            rgb_values = QColor(f"#{loot.rgb}")
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
