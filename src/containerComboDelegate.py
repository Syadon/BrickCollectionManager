"""
Custom item delegate for container combobox
Shows container icon, name in bold, and part count
"""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QStyle, QStyledItemDelegate


class ContainerComboDelegate(QStyledItemDelegate):
    """Custom delegate for rendering container items in combobox"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_size = 32
        self.padding = 8

    def paint(self, painter, option, index):
        """Custom paint method for container items"""

        # Get data from model
        container_data = index.data(Qt.ItemDataRole.UserRole)
        index.data(Qt.ItemDataRole.DisplayRole)

        # If this is the placeholder item ("Select Container...")
        if container_data is None:
            super().paint(painter, option, index)
            return

        # Extract container info
        try:
            (
                container_id,
                container_name,
                container_type,
                part_count,
                container_description,
            ) = container_data
        except (ValueError, TypeError):
            try:
                # Try format without description
                container_id, container_name, container_type, part_count = (
                    container_data
                )
                container_description = ""
            except (ValueError, TypeError):
                # Fallback for old format
                super().paint(painter, option, index)
                return

        painter.save()

        # Draw background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            text_color = option.palette.highlightedText().color()
        else:
            painter.fillRect(option.rect, option.palette.base())
            text_color = option.palette.text().color()

        # Get icon based on container type
        if container_type == "bag":
            icon = QIcon(":/icons/container_bag.png")
        else:
            icon = QIcon(":/icons/container_box.png")

        # Calculate positions - icon on the LEFT
        icon_rect = QRect(
            option.rect.left() + self.padding,
            option.rect.top() + (option.rect.height() - self.icon_size) // 2,
            self.icon_size,
            self.icon_size,
        )

        # Draw icon on the left
        icon.paint(painter, icon_rect)

        # Calculate text area (to the right of icon)
        text_rect = QRect(
            option.rect.left() + self.icon_size + (self.padding * 2),
            option.rect.top() + self.padding,
            option.rect.width() - self.icon_size - (self.padding * 3),
            option.rect.height() - (self.padding * 2),
        )

        # First line: container name and part count
        bold_font = QFont(painter.font())
        bold_font.setBold(True)
        if bold_font.pointSize() > 0:
            bold_font.setPointSize(max(1, bold_font.pointSize()))
        painter.setFont(bold_font)
        painter.setPen(text_color)

        parts_text = f"({part_count} parts)" if part_count != 1 else "(1 part)"
        first_line_text = f"{container_name} {parts_text}"

        first_line_rect = QRect(
            text_rect.left(),
            text_rect.top(),
            text_rect.width(),
            text_rect.height() // 2,
        )
        painter.drawText(
            first_line_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            first_line_text,
        )

        # Second line: description (smaller, gray)
        if container_description:
            small_font = QFont(painter.font())
            small_font.setBold(False)
            current_size = small_font.pointSize()
            if current_size > 0:
                small_font.setPointSize(max(1, int(current_size * 0.85)))
            painter.setFont(small_font)

            description_rect = QRect(
                text_rect.left(),
                text_rect.top() + text_rect.height() // 2,
                text_rect.width(),
                text_rect.height() // 2,
            )
            painter.drawText(
                description_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                container_description,
            )

        painter.restore()

    def sizeHint(self, option, index):
        """Return the size hint for items"""
        container_data = index.data(Qt.ItemDataRole.UserRole)

        # Placeholder item uses default size
        if container_data is None:
            return super().sizeHint(option, index)

        # Container items need more height for two lines of text
        return QSize(option.rect.width(), max(48, self.icon_size + (self.padding * 2)))
