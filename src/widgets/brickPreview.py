"""
BrickPreview widget - A QLabel-based widget for displaying brick images.
Handles automatic loading from BrickLink or cache using ImageProvider.
"""

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from config import AppConfig
from src.imageProvider import ImagesProvider


class BrickPreview(QLabel):
    """
    A widget for displaying brick images with automatic loading from cache or BrickLink.

    This widget extends QLabel to show brick images and automatically handles:
    - Loading images from cache
    - Downloading images from BrickLink if not cached
    - Showing a placeholder while loading
    - Scaling images to fit the widget size
    - Error handling

    Signals:
        image_loaded: Emitted when the image is successfully loaded (str key, QPixmap pixmap)
        image_error: Emitted when there's an error loading the image (str key, str error)
    """

    image_loaded = Signal(str, QPixmap)
    image_error = Signal(str, str)

    def __init__(
        self,
        part_id: str | None = None,
        color_id: str | None = None,
        size: int | None = None,
        parent=None,
    ):
        """
        Initialize the BrickPreview widget.

        Args:
            part_id: The part ID to display
            color_id: The color ID to display
            size: The size for the image (width and height). If None, uses AppConfig.DEFAULT_ICON_SIZE
            parent: Parent widget
        """
        super().__init__(parent)

        self._part_id = part_id
        self._color_id = color_id
        self._size = size if size is not None else AppConfig.DEFAULT_ICON_SIZE
        self._current_key = None
        self._keep_aspect_ratio = True
        self._smooth_transformation = True

        # Get the global image provider
        self._img_provider = get_global_image_provider()

        # Connect to the image provider signals
        self._img_provider.image_loaded.connect(self._on_image_loaded)
        self._img_provider.image_error.connect(self._on_image_error)

        # Setup the label
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(self._size, self._size)
        self.setScaledContents(False)

        # Load the image if part_id and color_id are provided
        if part_id and color_id:
            self.load_part_image(part_id, color_id)

    def set_size(self, size: int):
        """
        Set the size for the displayed image.

        Args:
            size: The size (width and height) for the image
        """
        self._size = size
        self.setMinimumSize(size, size)

        # Reload the current image with the new size
        if self._part_id and self._color_id:
            self.load_part_image(self._part_id, self._color_id)

    def set_aspect_ratio_mode(self, keep_aspect: bool):
        """
        Set whether to keep the aspect ratio when scaling images.

        Args:
            keep_aspect: True to keep aspect ratio, False to stretch
        """
        self._keep_aspect_ratio = keep_aspect

        # Reload the current image with the new setting
        if self._part_id and self._color_id:
            self.load_part_image(self._part_id, self._color_id)

    def set_smooth_transformation(self, smooth: bool):
        """
        Set whether to use smooth transformation when scaling.

        Args:
            smooth: True for smooth transformation, False for fast transformation
        """
        self._smooth_transformation = smooth

        # Reload the current image with the new setting
        if self._part_id and self._color_id:
            self.load_part_image(self._part_id, self._color_id)

    def load_part_image(self, part_id: str, color_id: str):
        """
        Load and display a brick part image.

        Args:
            part_id: The part ID to display
            color_id: The color ID to display
        """
        self._part_id = str(part_id)
        self._color_id = str(color_id)
        self._current_key = f"{self._part_id}_{self._color_id}"

        # Get the image from the provider (will return placeholder if not cached)
        pixmap = self._img_provider.get_part_image(self._part_id, self._color_id)

        # Display the image (placeholder or cached)
        self._display_pixmap(pixmap)

    def load_image_from_url(self, url: str, key: str | None = None):
        """
        Load and display an image from a URL.

        Args:
            url: The URL to load the image from
            key: Optional key for caching. If None, the URL is used as key
        """
        if key is None:
            key = url

        self._current_key = key

        # Get the image from the provider (will return placeholder if not cached)
        pixmap = self._img_provider.get_image_from_url(url, key)

        # Display the image (placeholder or cached)
        self._display_pixmap(pixmap)

    def set_placeholder(self, pixmap: QPixmap | None = None):
        """
        Set a custom placeholder image or reset to default.

        Args:
            pixmap: Custom placeholder pixmap, or None to use default
        """
        if pixmap is None:
            pixmap = ImagesProvider.get_placeholder_image(self._size)

        self._display_pixmap(pixmap)

    def clear(self):
        """Clear the displayed image and show placeholder."""
        self._part_id = None
        self._color_id = None
        self._current_key = None
        self.set_placeholder()

    @Slot(str, QPixmap)
    def _on_image_loaded(self, key: str, pixmap: QPixmap):
        """
        Internal slot called when an image is loaded by the provider.

        Args:
            key: The key identifying the image
            pixmap: The loaded pixmap
        """
        # Only update if this is the image we're waiting for
        if key == self._current_key:
            self._display_pixmap(pixmap)
            self.image_loaded.emit(key, pixmap)

    @Slot(str, str)
    def _on_image_error(self, key: str, error: str):
        """
        Internal slot called when there's an error loading an image.

        Args:
            key: The key identifying the image
            error: The error message
        """
        # Only react if this is the image we're waiting for
        if key == self._current_key:
            # Keep showing the placeholder on error
            self.image_error.emit(key, error)

    def _display_pixmap(self, pixmap: QPixmap):
        """
        Display a pixmap with proper scaling.

        Args:
            pixmap: The pixmap to display
        """
        if pixmap is None or pixmap.isNull():
            # Show placeholder if pixmap is invalid
            pixmap = ImagesProvider.get_placeholder_image(self._size)

        # Scale the pixmap to fit the widget size
        aspect_mode = (
            Qt.AspectRatioMode.KeepAspectRatio
            if self._keep_aspect_ratio
            else Qt.AspectRatioMode.IgnoreAspectRatio
        )

        transform_mode = (
            Qt.TransformationMode.SmoothTransformation
            if self._smooth_transformation
            else Qt.TransformationMode.FastTransformation
        )

        scaled_pixmap = pixmap.scaled(
            self._size, self._size, aspect_mode, transform_mode
        )

        self.setPixmap(scaled_pixmap)

    def get_part_id(self) -> str | None:
        """Get the current part ID."""
        return self._part_id

    def get_color_id(self) -> str | None:
        """Get the current color ID."""
        return self._color_id

    def get_key(self) -> str | None:
        """Get the current image key."""
        return self._current_key


# Global image provider instance
_global_image_provider = None


def get_global_image_provider() -> ImagesProvider:
    """
    Get the global ImagesProvider instance (singleton pattern).

    Returns:
        The global ImagesProvider instance
    """
    global _global_image_provider

    if _global_image_provider is None:
        _global_image_provider = ImagesProvider(AppConfig.PARTS_IMG_CACHE_DIR)

    return _global_image_provider


def cleanup_global_image_provider():
    """
    Cleanup the global image provider.
    Should be called when the application is closing.
    """
    global _global_image_provider

    if _global_image_provider is not None:
        _global_image_provider.cleanup_tasks()
        _global_image_provider.clear_cache()
