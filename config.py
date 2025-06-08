from pathlib import Path
from PySide6.QtCore import QDir

class AppConfig:
    # Application Information
    APP_NAME = "Brick Collection Manager"
    APP_VERSION = "1.0.0"
    ORGANIZATION_NAME = ""
    
    # File Paths
    BASE_DIR = Path(QDir.currentPath())
    UI_DIR = BASE_DIR / "ui"
    RESOURCES_DIR = BASE_DIR / "resources"
    DATABASE_DIR = BASE_DIR / "database"
    
    # Database Configuration
    DATABASE_FILE_NAME = "brick_collection"
    DATABASE_NAME = "brick_collection.db"
    DATABASE_PATH = DATABASE_DIR / DATABASE_NAME
    DATABASE_TYPE = "QSQLITE"
    DATABASE_SCHEMA_RESOURCE_PATH = ":/database/schema.sql"

    # Cache directory
    CHACHE_DIR = DATABASE_DIR / "cache"
    PARTS_IMG_CACHE_DIR = CHACHE_DIR / "parts_images"
    
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

    # Application version
    VERSION = "0.1.0"
    
    @classmethod
    def initialize(cls):
        #cls.UI_DIR.mkdir(exist_ok=True)
        #cls.RESOURCES_DIR.mkdir(exist_ok=True)
        cls.DATABASE_DIR.mkdir(exist_ok=True)
        cls.CHACHE_DIR.mkdir(exist_ok=True)
        cls.PARTS_IMG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_stylesheet(cls) -> str:
        if cls.STYLE_SHEET_PATH.exists():
            return cls.STYLE_SHEET_PATH.read_text()
        return ""