"""
Logging configuration for BrickCollectionManager application.
Provides centralized logging with file rotation and console output.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Import config to get DATA_DIR
from config import AppConfig


class AppLogger:
    """Centralized logger for the application"""
    
    _instance: Optional['AppLogger'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger (only once)"""
        if AppLogger._initialized:
            return
        
        AppLogger._initialized = True
        self.logger = logging.getLogger('BrickCollectionManager')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # Create logs directory in DATA_DIR
        self.log_dir = AppConfig.DATA_DIR / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file handler with rotation
        self._setup_file_handler()
        
        # Setup console handler
        self._setup_console_handler()
        
        # Log initialization
        self.logger.info("="*70)
        self.logger.info(f"BrickCollectionManager started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*70)
    
    def _setup_file_handler(self):
        """Setup rotating file handler"""
        log_file = self.log_dir / 'app.log'
        
        # Rotating file handler: max 3MB per file, keep 5 backup files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=3 * 1024 * 1024,  # 3MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Detailed format for file logs
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        self.logger.addHandler(file_handler)
    
    def _setup_console_handler(self):
        """Setup console handler for terminal output"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        
        # Simpler format for console
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance"""
        return self.logger
    
    def get_log_file_path(self) -> Path:
        """Get the path to the current log file"""
        return self.log_dir / 'app.log'
    
    def get_log_dir(self) -> Path:
        """Get the logs directory path"""
        return self.log_dir


# Global function to get logger
def get_logger() -> logging.Logger:
    """
    Get the application logger instance.
    
    Returns:
        logging.Logger: The configured logger instance
    
    Example:
        logger = get_logger()
        logger.info("Application started")
        logger.error("An error occurred", exc_info=True)
    """
    return AppLogger().get_logger()


# Global function to log exceptions
def log_exception(exception: Exception, message: str = "An exception occurred"):
    """
    Log an exception with full traceback.
    
    Args:
        exception: The exception to log
        message: Optional custom message
    
    Example:
        try:
            risky_operation()
        except Exception as e:
            log_exception(e, "Failed to perform risky operation")
    """
    logger = get_logger()
    logger.error(f"{message}: {str(exception)}", exc_info=True)


# Global function to get log file path
def get_log_file_path() -> Path:
    """
    Get the path to the current log file.
    
    Returns:
        Path: Path to the log file
    """
    return AppLogger().get_log_file_path()


# Global function to get log directory
def get_log_dir() -> Path:
    """
    Get the logs directory path.
    
    Returns:
        Path: Path to the logs directory
    """
    return AppLogger().get_log_dir()


# Exception hook to catch unhandled exceptions
def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Global exception hook to log unhandled exceptions.
    This replaces sys.excepthook to ensure all unhandled exceptions are logged.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Call the default handler for KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = get_logger()
    logger.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )


def setup_exception_hook():
    """Install the global exception hook"""
    sys.excepthook = exception_hook
