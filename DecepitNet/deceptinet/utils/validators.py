"""
Environment validation utilities
"""

import sys
import platform
from typing import List, Tuple


def validate_environment() -> bool:
    """
    Validate system environment
    
    Returns:
        True if environment is valid
    """
    checks = [
        check_python_version(),
        check_platform(),
        check_permissions()
    ]
    
    return all(checks)


def check_python_version() -> bool:
    """Check Python version"""
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_platform() -> bool:
    """Check operating system"""
    os_name = platform.system()
    print(f"✓ Platform: {os_name}")
    
    if os_name == "Windows":
        print("  ⚠️  Some features may have limited functionality on Windows")
    
    return True


def check_permissions() -> bool:
    """Check permissions"""
    # On Windows, we don't need root/admin for most operations
    if platform.system() == "Windows":
        print("✓ Running on Windows (no admin check required)")
        return True
    
    import os
    if os.geteuid() == 0:
        print("✓ Running with root privileges")
    else:
        print("  ⚠️  Running without root (some features may be limited)")
    
    return True


def check_dependencies() -> List[Tuple[str, bool]]:
    """
    Check optional dependencies
    
    Returns:
        List of (dependency_name, is_available) tuples
    """
    dependencies = []
    
    # Check optional packages
    optional_packages = [
        'scapy',
        'paramiko',
        'tensorflow',
        'torch',
        'sklearn',
        'flask'
    ]
    
    for package in optional_packages:
        try:
            __import__(package)
            dependencies.append((package, True))
        except ImportError:
            dependencies.append((package, False))
    
    return dependencies
