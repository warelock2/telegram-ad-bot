"""
Centralized logging setup for the Telegram Ad Bot.

This module configures a logger that writes to both the console (stdout)
and a time-rotated log file stored in the '/app/logs' volume.
"""

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from config import settings

LOG_FILE_PATH = "/app/logs/bot.log"

def setup_logger():
    """
    Configures and returns a logger instance.
    """
    # Get the numeric logging level from the string representation
    numeric_level = getattr(logging, settings.log_level, logging.INFO)
    
    # Create a logger
    logger = logging.getLogger("TelegramAdBot")
    logger.setLevel(numeric_level)
    
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s'
    )
    
    # --- Console Handler ---
    # Logs to stdout, which is visible via 'docker logs'
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # --- File Handler ---
    # Logs to a file that rotates every day, keeping 7 days of history.
    # This is stored in the '/app/logs' directory, which is a mounted volume.
    file_handler = TimedRotatingFileHandler(
        LOG_FILE_PATH, when="midnight", interval=1, backupCount=7
    )
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    # Check if handlers have already been added to avoid duplication
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger

# Create a single, importable instance of the logger
log = setup_logger()
