import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QComboBox, QStyle, QStyledItemDelegate

from src.database import Container, DatabaseManager


class TransparentSelectionDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        # Rimuovi l'effetto di selezione
        option.state &= ~QStyle.StateFlag.State_Selected


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    diff = cmax - cmin

    # Calculate Hue
    if diff == 0:
        h = 0
    elif cmax == r:
        h = (60 * ((g - b) / diff) + 360) % 360
    elif cmax == g:
        h = (60 * ((b - r) / diff) + 120) % 360
    else:
        h = (60 * ((r - g) / diff) + 240) % 360

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
    similarity = 1.0 - (h_weight * h_diff + s_weight * s_diff + v_weight * v_diff)

    return similarity


def qImageToOpenCV(image: QImage):
    # Crop the image using the bounding box
    img = image.convertToFormat(QImage.Format.Format_RGB32)

    # Convert QImage to OpenCV format
    width = img.width()
    height = img.height()
    ptr = img.bits()
    # ptr.set(height * width * 4)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    cv_image = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)

    return cv_image


def opencvToQImage(image):
    # Convert to QImage
    h, w, ch = image.shape
    bytes_per_line = ch * w
    imageTmp = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return QImage(imageTmp.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)


def opencvToPixmap(image):
    return QPixmap.fromImage(opencvToQImage(image))


def populate_container_combo(
    containerCombo: QComboBox,
    db_manager: DatabaseManager,
    targetContainer: Container | None = None,
    excludeContainerIds: list[int] = [],
):
    """Popola il combobox dei container con icone e dettagli"""
    containerCombo.clear()

    # Add dummy container as first option
    containerCombo.addItem("Select Container...", None)

    containers = db_manager.getContainers()

    # Aggiungi i container al combobox
    for container in containers:
        if container.id in excludeContainerIds:
            continue

        if targetContainer is None or container.id == targetContainer.id:
            part_count = container.part_count or 0
            container_type = getattr(container, "type", "box")
            container_description = getattr(container, "description", "")

            # Display text for fallback rendering
            display_text = f"{container.name} ({part_count} parts)"

            # Store complete data: (id, name, type, part_count, description)
            container_data = (
                container.id,
                container.name,
                container_type,
                part_count,
                container_description,
            )

            containerCombo.addItem(display_text, container_data)

    containerCombo.setEnabled(targetContainer is None)


def update_container_combo_single_parts_count(
    containerCombo: QComboBox, db_manager: DatabaseManager, comboIndex: int
):
    data = containerCombo.itemData(comboIndex)
    if data is not None:
        try:
            # Try newest format first: (id, name, type, part_count, description)
            (
                container_id,
                container_name,
                container_type,
                old_part_count,
                container_description,
            ) = data
        except (ValueError, TypeError):
            try:
                # Try format without description: (id, name, type, part_count)
                container_id, container_name, container_type, old_part_count = data
                container_description = ""
            except (ValueError, TypeError):
                # Fallback to old format: (id, name)
                container_id, container_name = data
                container_type = "box"
                container_description = ""

        container = db_manager.getContainerById(container_id)
        if container:
            part_count = container.part_count or 0
            container_type = getattr(container, "type", "box")
            container_description = getattr(container, "description", "")

            # Update display text
            display_text = f"{container.name} ({part_count} parts)"
            containerCombo.setItemText(comboIndex, display_text)

            # Update data with new part count and description
            container_data = (
                container.id,
                container.name,
                container_type,
                part_count,
                container_description,
            )
            containerCombo.setItemData(comboIndex, container_data)


def setup_container_combo_delegate(containerCombo: QComboBox):
    """Configura il custom delegate per la combobox dei container"""
    from src.containerComboDelegate import ContainerComboDelegate

    delegate = ContainerComboDelegate(containerCombo)
    containerCombo.setItemDelegate(delegate)

    return delegate


def populate_color_combo(
    colorCombo: QComboBox, db_manager: DatabaseManager, include_any_option: bool = True
):
    """Popola il combobox dei colori con background RGB"""
    colorCombo.clear()

    # Add "Any" option if requested
    if include_any_option:
        colorCombo.addItem("Any", None)

    # Get all colors from database
    colors = db_manager.getColors()

    # Add colors to combobox
    for color in colors:
        # Display text for fallback rendering
        display_text = color.name

        # Store complete data: (id, name, rgb)
        color_data = (color.id, color.name, color.rgb)

        colorCombo.addItem(display_text, color_data)


def setup_color_combo_delegate(colorCombo: QComboBox):
    """Configura il custom delegate per la combobox dei colori"""
    from src.colorComboDelegate import ColorComboDelegate

    delegate = ColorComboDelegate(colorCombo)
    colorCombo.setItemDelegate(delegate)

    return delegate
