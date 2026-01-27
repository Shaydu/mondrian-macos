"""Centralized logging configuration for Mondrian services."""

import logging
import os
import sys
from pathlib import Path
from datetime import datetime


def setup_service_logging(service_name: str, working_dir: str = None) -> logging.Logger:
    """
    Setup logging for a service with both file and console output.
    
    Args:
        service_name: Name of the service (e.g., 'ai_advisor_service_linux')
        working_dir: Working directory (defaults to project root)
    
    Returns:
        Configured logger instance
    """
    if working_dir is None:
        # Try to determine project root from script location
        working_dir = str(Path(__file__).parent.parent)
    
    # Create logs/service_name directory
    log_dir = os.path.join(working_dir, "logs", service_name)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log file with timestamp
    timestamp = int(datetime.now().timestamp())
    log_file = os.path.join(log_dir, f"{service_name}_{timestamp}.log")
    
    # Configure logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
