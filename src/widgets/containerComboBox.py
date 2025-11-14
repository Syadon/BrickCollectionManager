"""
Custom QComboBox that shows container icon, name and part count for selected item
"""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QStyle, QStylePainter


class ContainerComboBox(QComboBox):
    """Custom combobox that displays container icon, name and part count for selected item"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_size = 24
        self.padding = 4

    def paintEvent(self, event):
        """Override paint event to show container icon and info"""
        painter = QStylePainter(self)
        painter.setPen(self.palette().color(self.palette().ColorRole.Text))

        # Draw the combobox frame
        opt = self.get_style_option()
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt)

        # Get current item data
        current_index = self.currentIndex()
        if current_index >= 0:
            container_data = self.itemData(current_index, Qt.ItemDataRole.UserRole)

            # If this is the placeholder ("Select Container...")
            if container_data is None:
                painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, opt)
                painter.end()
                return

            try:
                # Extract container info from tuple (id, name, type, part_count, description)
                try:
                    (
                        container_id,
                        container_name,
                        container_type,
                        part_count,
                        container_description,
                    ) = container_data
                except (ValueError, TypeError):
                    # Try format without description
                    container_id, container_name, container_type, part_count = (
                        container_data
                    )

                # Get icon based on container type
                if container_type == "bag":
                    icon = QIcon(":/icons/container_bag.png")
                else:
                    icon = QIcon(":/icons/container_box.png")

                # Calculate text area (the area where text is displayed)
                text_rect = self.style().subControlRect(
                    QStyle.ComplexControl.CC_ComboBox,
                    opt,
                    QStyle.SubControl.SC_ComboBoxEditField,
                    self,
                )

                # Draw icon on the left
                icon_rect = QRect(
                    text_rect.left() + self.padding,
                    text_rect.top() + (text_rect.height() - self.icon_size) // 2,
                    self.icon_size,
                    self.icon_size,
                )
                icon.paint(painter, icon_rect)

                # Calculate text area (to the right of icon)
                text_x = icon_rect.right() + self.padding * 2
                text_width = text_rect.width() - self.icon_size - (self.padding * 2)
                text_area = QRect(
                    text_x, text_rect.top(), text_width, text_rect.height()
                )

                # Draw text: "Name (X parts)"
                parts_text = f"({part_count} parts)" if part_count != 1 else "(1 part)"
                display_text = f"{container_name} {parts_text}"

                painter.setPen(self.palette().color(self.palette().ColorRole.Text))
                painter.drawText(
                    text_area,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    display_text,
                )

                painter.end()
                return

            except (ValueError, TypeError, AttributeError):
                pass

        # Fallback to default rendering
        painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, opt)
        painter.end()

    def get_style_option(self):
        """Get style option for painting"""
        from PySide6.QtWidgets import QStyleOptionComboBox

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        return opt
