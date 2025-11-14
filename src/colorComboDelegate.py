"""
Custom item delegate for color combobox
Shows color name with RGB background color
"""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyledItemDelegate


class ColorComboDelegate(QStyledItemDelegate):
    """Custom delegate for rendering color items in combobox"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.padding = 8

    def paint(self, painter, option, index):
        """Custom paint method for color items"""

        # Get data from model
        color_data = index.data(Qt.ItemDataRole.UserRole)

        # If this is the placeholder item ("Any", etc.)
        if color_data is None:
            super().paint(painter, option, index)
            return

        painter.save()

        # Extract color info
        try:
            color_id, color_name, rgb_str = color_data
        except (ValueError, TypeError):
            # Fallback for old format
            super().paint(painter, option, index)
            painter.restore()
            return

        # Parse RGB string (format: "RRGGBB")
        try:
            if rgb_str and len(rgb_str) == 6:
                r = int(rgb_str[0:2], 16)
                g = int(rgb_str[2:4], 16)
                b = int(rgb_str[4:6], 16)
                bg_color = QColor(r, g, b)
            else:
                bg_color = option.palette.base().color()
        except (ValueError, AttributeError):
            bg_color = option.palette.base().color()

        # Draw background with color
        painter.fillRect(option.rect, bg_color)

        # Calculate luminance to determine if we should use black or white text
        # Using relative luminance formula: 0.299*R + 0.587*G + 0.114*B
        luminance = (
            0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()
        ) / 255

        # Use white text for dark colors, black text for light colors
        if luminance > 0.5:
            text_color = QColor(0, 0, 0)  # Black
        else:
            text_color = QColor(255, 255, 255)  # White

        # If item is selected, draw selection indicator
        if option.state & QStyle.StateFlag.State_Selected:
            # Draw a border or outline
            painter.setPen(option.palette.highlight().color())
            painter.drawRect(option.rect.adjusted(0, 0, -1, -1))

        # Draw text
        text_rect = option.rect.adjusted(self.padding, 0, -self.padding, 0)
        painter.setPen(text_color)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            color_name,
        )

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for items"""
        color_data = index.data(Qt.ItemDataRole.UserRole)

        # Placeholder item uses default size
        if color_data is None:
            return super().sizeHint(option, index)

        # Color items use standard combobox height
        return QSize(option.rect.width(), 32)
