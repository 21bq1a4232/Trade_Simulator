"""
Logging configuration for the trade simulator.
"""
import sys
import os
from loguru import logger

def setup_logging(config):
    """
    Set up the logging configuration.
    
    Args:
        config (module): Configuration module
    """
    # Remove default handler
    logger.remove()
    
    # Configure console output
    logger.add(
        sys.stderr,
        level=config.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Configure file output
    log_file = config.LOG_FILE
    logger.add(
        log_file,
        rotation="10 MB",
        retention="1 week",
        level=config.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    
    logger.info(f"Logging configured. Level: {config.LOG_LEVEL}, File: {log_file}")
    
    return logger