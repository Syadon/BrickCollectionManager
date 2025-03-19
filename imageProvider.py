from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool, Slot
import requests
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ImageUrlWorker(QRunnable):
    class Signals(QObject):
        finished = Signal(str, QPixmap)
        error = Signal(str, str)

    def __init__(self, url, cache_path, cache_name):
        super().__init__()
        self.url = url
        self.cache_name = cache_name
        self.cache_path = cache_path
        self.signals = self.Signals()

    @Slot()
    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive'
            }
            response = requests.get(self.url, headers=headers)
            if response.status_code == 200:
                self.cache_path.write_bytes(response.content)
                pixmap = QPixmap(str(self.cache_path))
                self.signals.finished.emit(self.cache_name, pixmap)
            else:
                self.signals.error.emit(self.cache_name, 
                                     f"Error: {response.status_code}")
        except Exception as e:
            self.signals.error.emit(self.cache_name, str(e))

class ImagePartColorWorker(ImageUrlWorker):
    class Signals(QObject):
        finished = Signal(str, QPixmap)
        error = Signal(str, str)

    def __init__(self, part_id, color_id, cache_path):
        super().__init__(
            f"https://www.bricklink.com/P/{color_id}/{part_id}.JPG",
            cache_path,
            f"{part_id}_{color_id}"
        )

class ImagesProvider(QObject):
    image_loaded = Signal(str, QPixmap)  # key, pixmap
    image_error = Signal(str, str)       # key, error message

    def __init__(self, cache_dir):
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(4)  # Limita le richieste parallele
        self.image_cache = {}  # Cache in memoria

    def get_image_from_url(self, url:str, key:str):
        # Check memory cache first
        if key in self.image_cache:
            return self.image_cache[key]
        
        cache_path = self.cache_dir / f"{key}.jpg"
        
        # Check file cache
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            self.image_cache[key] = pixmap
            return pixmap
            
        # Download asynchronously if not cached
        worker = ImageUrlWorker(url, cache_path, key)
        worker.signals.finished.connect(self._handle_image_loaded)
        worker.signals.error.connect(self._handle_image_error)
        
        self.thread_pool.start(worker)
        
        # Return placeholder while loading
        return None

    def get_part_image(self, part_id, color_id):
        key = f"{part_id}_{color_id}"
        url = f"https://www.bricklink.com/P/{color_id}/{part_id}.JPG"
        
        return self.get_image_from_url(url, key)
        
    def _handle_image_loaded(self, key, pixmap):
        self.image_cache[key] = pixmap
        self.image_loaded.emit(key, pixmap)
        
    def _handle_image_error(self, key, error):
        print(f"Failed to load image {key}: {error}")
        self.image_error.emit(key, error)
