"""
Core package initialization
"""

from .platform import DeceptiNetPlatform
from .config import ConfigManager
from .logger import setup_logger
from .database import DatabaseManager

__all__ = [
    'DeceptiNetPlatform',
    'ConfigManager',
    'setup_logger',
    'DatabaseManager'
]
