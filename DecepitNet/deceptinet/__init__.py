"""
DECEPTINET Core Package
"""

__version__ = "1.0.0"
__author__ = "DECEPTINET Team"
__license__ = "MIT"

from .core.platform import DeceptiNetPlatform
from .core.config import ConfigManager
from .core.logger import setup_logger

__all__ = [
    'DeceptiNetPlatform',
    'ConfigManager',
    'setup_logger'
]
