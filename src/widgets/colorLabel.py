from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class ColorLabel(QLabel):
    """A reusable QLabel widget for displaying color names with background color"""
    
    def __init__(self, color_name, rgb_hex=None, color_type=None, color_id=None, parent=None):
        super().__init__(parent)
        self.color_name = color_name
        self.rgb_hex = rgb_hex
        self.color_type = color_type
        self.color_id = color_id
        
        # Set default alignment
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set the display text
        self._update_text()
        
        # Apply color styling if RGB is provided
        if rgb_hex:
            self.set_color_style(rgb_hex)
            
        self.setMinimumSize(200, 50)
    
    def _update_text(self):
        """Update the display text with color name and optional details"""
        text_parts = [self.color_name]
        
        # Add color type and/or color id in parentheses on new line if available
        details = []
        if self.color_type:
            details.append(f"Type: {self.color_type}")
        if self.color_id:
            details.append(f"ID: {self.color_id}")
        
        if details:
            text_parts.append(f"({', '.join(details)})")
        
        # Join with newline
        display_text = '\n'.join(text_parts)
        self.setText(display_text)
    
    def set_color_style(self, rgb_hex):
        """Set the background and text color based on RGB hex value"""
        self.rgb_hex = rgb_hex
        
        # Remove # if present
        if rgb_hex.startswith('#'):
            rgb_hex = rgb_hex[1:]
        
        rgb_color = QColor(f"#{rgb_hex}")
        
        # Calculate luminance to determine text color
        luminance = (0.299 * rgb_color.red() + 
                    0.587 * rgb_color.green() + 
                    0.114 * rgb_color.blue())
        
        # Use white text for dark colors, black for light colors
        text_color = 'white' if luminance < 128 else 'black'
        
        # Set stylesheet for background and text color
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #{rgb_hex};
                color: {text_color};
                padding: 4px;
                border: none;
            }}
        """)
    
    def update_color(self, color_name, rgb_hex=None, color_type=None, color_id=None):
        """Update the text, color styling, and additional details"""
        self.color_name = color_name
        self.color_type = color_type
        self.color_id = color_id
        
        # Update the display text
        self._update_text()
        
        if rgb_hex:
            self.set_color_style(rgb_hex)
    
    def get_color_info(self):
        """Return the current color information"""
        return {
            'name': self.color_name,
            'rgb_hex': self.rgb_hex,
            'color_type': self.color_type,
            'color_id': self.color_id
        }