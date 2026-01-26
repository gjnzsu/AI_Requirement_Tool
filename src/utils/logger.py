"""
Logging utility for the chatbot service.

Provides a centralized logging configuration with support for different log levels
and optional file logging.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Import Config after path setup
try:
    from config.config import Config
except ImportError:
    # Fallback if config is not available
    class Config:
        LOG_LEVEL = 'INFO'
        ENABLE_DEBUG_LOGGING = False
        LOG_FILE = None


def get_logger(name: str = 'chatbot') -> logging.Logger:
    """
    Get a logger instance configured according to Config settings.
    
    Args:
        name: Logger name (default: 'chatbot')
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level based on config
    log_level = getattr(Config, 'LOG_LEVEL', 'INFO').upper()
    enable_debug = getattr(Config, 'ENABLE_DEBUG_LOGGING', False)
    
    # If DEBUG logging is explicitly enabled, override log level
    if enable_debug:
        log_level = 'DEBUG'
    
    # Map string level to logging constant
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    logger.setLevel(level_map.get(log_level, logging.INFO))
    
    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - only add if not already present
    #
    # IMPORTANT (pytest/xdist): sys.stdout can be swapped/closed by pytest's capturing
    # during worker teardown while background threads are still logging.
    # Use the original interpreter streams to avoid "ValueError: I/O operation on closed file."
    stream = getattr(sys, "__stdout__", sys.stdout)

    # Check if there's already a StreamHandler to our target stream
    has_console_handler = False
    expected_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == stream:
            # Check if it has our formatter format (to avoid duplicates)
            if handler.formatter:
                try:
                    handler_format = handler.formatter._fmt if hasattr(handler.formatter, '_fmt') else None
                    if handler_format == expected_format:
                        has_console_handler = True
                        break
                except AttributeError:
                    # If we can't check format, assume it's our handler if it's a StreamHandler to stdout
                    # This is safer than adding duplicates
                    has_console_handler = True
                    break
            else:
                # Handler exists but no formatter - might be from elsewhere, skip adding
                has_console_handler = True
                break
    
    if not has_console_handler:
        console_handler = logging.StreamHandler(stream)
        console_handler.setLevel(logger.level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Optional file handler - only add if not already present
    log_file = getattr(Config, 'LOG_FILE', None)
    if log_file:
        # Check if file handler already exists for this file
        has_file_handler = False
        try:
            log_file_abs = str(Path(log_file).absolute().resolve())
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    try:
                        handler_file_abs = str(Path(handler.baseFilename).absolute().resolve())
                        if handler_file_abs == log_file_abs:
                            has_file_handler = True
                            break
                    except (AttributeError, OSError):
                        # If we can't compare, skip
                        continue
        except (OSError, ValueError):
            # If path resolution fails, continue anyway
            pass
        
        if not has_file_handler:
            try:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logger.level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                # If file logging fails, log to console only
                # Use print to avoid circular logging issues
                err_stream = getattr(sys, "__stderr__", sys.stderr)
                print(f"Warning: Failed to set up file logging: {e}", file=err_stream)
    
    return logger

