import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    log_format = "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Rotating file handler (Max 5MB per file, keeps up to 5 backup files)
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console output handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)