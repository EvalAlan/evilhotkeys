"""
Logging configuration for EvilHotKeys
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Default log level
DEFAULT_LEVEL = logging.INFO

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
SIMPLE_FORMAT = '%(levelname)s: %(message)s'

# Global logger instance
_logger: Optional[logging.Logger] = None


def setup_logger(
    name: str = 'evilhotkeys',
    level: int = DEFAULT_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = True,
    simple_format: bool = False
) -> logging.Logger:
    """Setup and configure the application logger.
    
    Args:
        name: Logger name
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_file: Optional path to log file
        console: Whether to log to console
        simple_format: Use simple format (level + message only)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Choose format
    fmt = SIMPLE_FORMAT if simple_format else LOG_FORMAT
    formatter = logging.Formatter(fmt)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'evilhotkeys') -> logging.Logger:
    """Get the application logger.
    
    Args:
        name: Logger name (allows creating sub-loggers)
    
    Returns:
        Logger instance
    """
    global _logger
    
    if _logger is None:
        _logger = setup_logger(name, simple_format=True)
    
    # Return sub-logger if different name requested
    if name != 'evilhotkeys':
        return logging.getLogger(f'evilhotkeys.{name}')
    
    return _logger


def set_log_level(level: int):
    """Change the logging level dynamically.
    
    Args:
        level: New logging level (e.g., logging.DEBUG)
    """
    logger = get_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

