from PySide6.QtCore import QAbstractTableModel, Qt
from PySide6.QtGui import QColor, QBrush

class ContainerPartsModel(QAbstractTableModel):
    def __init__(self, parts_data=None):
        super().__init__()
        self.parts_data = parts_data or []
        self.headers = ["ID", "Part", "Category", "Color", "Color Type", "Quantity"]
        self.attrCols = ["part_id", "part_name", "part_category", "color_name", "color_type", "quantity"]

        self.colorColumnIndex = self.headers.index("Color")

    def rowCount(self, parent):
        return len(self.parts_data)

    def columnCount(self, parent):
        return len(self.headers)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            row = self.parts_data[index.row()]
            col = index.column()
            return row[self.attrCols[col]]
        
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
