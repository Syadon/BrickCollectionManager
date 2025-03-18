from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
import requests
from pathlib import Path

class ImagesProvider:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_part_image(self, part_id, color_id, size=(64, 64)):
        cache_path = self.cache_dir / f"{part_id}_{color_id}.jpg"
        
        # Download if not cached
        if not cache_path.exists():
            try:
                url = f"https://www.bricklink.com/P/{color_id}/{part_id}.JPG"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive'
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    cache_path.write_bytes(response.content)
                else:
                    print(f"Error requesting image: {response.status_code}")
                    return None
            except Exception as e:
                print(f"Error downloading image: {e}")
                return None

        # Load and return scaled image
        if cache_path.exists():
            pixmap =  QPixmap(str(cache_path))
            return pixmap.scaled(size[0], size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return None
