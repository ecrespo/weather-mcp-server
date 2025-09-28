import os
import tempfile
import logging
from pathlib import Path

class LoggerSingleton:
    _instance = None
    
    def __new__(cls, app_name="weather-mcp-server"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger(app_name)
        return cls._instance
    
    def _initialize_logger(self, app_name):
        # Try multiple locations for logs directory
        possible_log_dirs = [
            "logs",  # Current directory
            os.path.expanduser("~/logs"),  # User home directory
            f"/tmp/{app_name}_logs",  # Temporary directory
            tempfile.gettempdir()  # System temp directory
        ]
        
        logs_dir = None
        for log_dir in possible_log_dirs:
            try:
                os.makedirs(log_dir, exist_ok=True)
                # Test if we can write to this directory
                test_file = os.path.join(log_dir, 'test_write.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logs_dir = log_dir
                break
            except (PermissionError, OSError):
                continue
        
        # Set up logger
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.INFO)
        
        # Console handler (always works)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (only if we found a writable directory)
        if logs_dir:
            try:
                log_file = os.path.join(logs_dir, f'{app_name}.log')
                file_handler = logging.FileHandler(log_file)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
                self.logger.info(f"Logging to file: {log_file}")
            except Exception as e:
                self.logger.warning(f"Could not set up file logging: {e}")
        else:
            self.logger.warning("Could not find writable directory for logs. Logging to console only.")
    
    def get_logger(self):
        return self.logger

# Create the singleton instance
logger = LoggerSingleton(app_name="weather-mcp-server").get_logger()
