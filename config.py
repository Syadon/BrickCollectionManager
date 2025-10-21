import sys
from pathlib import Path
from PySide6.QtCore import QDir
import os

def get_base_dir():
    """Get the base directory - handles PyInstaller packaging correctly"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running in development
        return Path(__file__).parent.absolute()
    
def get_user_data_dir():
    """Get the user data directory - uses system user directory for packaged app, BASE_DIR for development"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle - use user directory
        if sys.platform == "win32":
            return Path(os.environ.get('APPDATA', Path.home())) / "BrickCollectionManager"
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "BrickCollectionManager"
        else:
            # Linux and other Unix-like systems
            return Path.home() / ".local" / "share" / "BrickCollectionManager"
    else:
        # Running in development - use BASE_DIR
        return get_base_dir()

class AppConfig:
    # Application Information
    APP_NAME = "Brick Collection Manager"
    APP_VERSION = "0.2.0"
    ORGANIZATION_NAME = ""
    
    # File Paths
    BASE_DIR = get_base_dir()
    DATA_DIR = get_user_data_dir()
    UI_DIR = BASE_DIR / "ui"
    RESOURCES_DIR = BASE_DIR / "resources"
    DATABASE_DIR = DATA_DIR / "database"
    
    # Database Configuration
    DATABASE_FILE_NAME = "brick_collection"
    DATABASE_NAME = "brick_collection.db"
    DATABASE_PATH = DATABASE_DIR / DATABASE_NAME
    DATABASE_TYPE = "QSQLITE"
    DATABASE_SCHEMA_RESOURCE_PATH = ":/database/schema.sql"

    # Cache directory
    CACHE_DIR = DATA_DIR / "cache"
    PARTS_IMG_CACHE_DIR = CACHE_DIR / "parts_images"
    
    # Logs directory
    LOGS_DIR = DATA_DIR / "logs"
    
    # UI Configuration
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 600
    WINDOW_TITLE = APP_NAME

    DEFAULT_ICON_SIZE = 64
    
    # Style Configuration
    STYLE_SHEET_PATH = UI_DIR / "style.qss"
    
    # Application Settings
    DEBUG_MODE = True
    LOG_LEVEL = "INFO"

    
    @classmethod
    def initialize(cls):
        #cls.UI_DIR.mkdir(exist_ok=True)
        #cls.RESOURCES_DIR.mkdir(exist_ok=True)
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.DATABASE_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.PARTS_IMG_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_stylesheet(cls) -> str:
        if cls.STYLE_SHEET_PATH.exists():
            return cls.STYLE_SHEET_PATH.read_text()
        return ""