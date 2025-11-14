"""
Custom QComboBox that shows color background for selected item
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


class ColorComboBox(QComboBox):
    """Custom combobox that displays color background for selected item"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentIndexChanged.connect(self.update_background)

    def update_background(self, index):
        """Update the combobox background based on selected color"""
        if index < 0:
            return

        color_data = self.itemData(index, Qt.ItemDataRole.UserRole)

        if color_data is None:
            # Reset to default for "Any" or None
            self.setStyleSheet("")
            return

        try:
            # Extract color info from tuple (id, name, rgb)
            color_id, color_name, rgb_str = color_data

            # Parse RGB string
            if rgb_str and len(rgb_str) == 6:
                r = int(rgb_str[0:2], 16)
                g = int(rgb_str[2:4], 16)
                b = int(rgb_str[4:6], 16)

                # Calculate luminance for text color
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

                # Use white text for dark colors, black for light colors
                if luminance > 0.5:
                    text_color = "#000000"
                else:
                    text_color = "#FFFFFF"

                # Set stylesheet with background color
                stylesheet = f"""
                    QComboBox {{
                        background-color: #{rgb_str};
                        color: {text_color};

                    }}
                """

                self.setStyleSheet(stylesheet)
            else:
                self.setStyleSheet("")
        except (ValueError, TypeError, AttributeError):
            self.setStyleSheet("")

    def showPopup(self):
        """Override to ensure background updates before showing popup"""
        self.update_background(self.currentIndex())
        super().showPopup()
