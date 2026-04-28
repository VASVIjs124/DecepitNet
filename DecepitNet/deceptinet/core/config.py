"""
Configuration Manager for DECEPTINET
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy


class ConfigManager:
    """Manages platform configuration"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration manager
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Process environment variables
        self._process_env_vars()
    
    def _process_env_vars(self) -> None:
        """Process environment variable overrides"""
        # Check for environment variable overrides
        env_prefix = "DECEPTINET_"
        
        for key, value in os.environ.items():
            if key.startswith(env_prefix):
                # Convert DECEPTINET_NETWORK_INTERFACE to network.interface
                config_key = key[len(env_prefix):].lower().replace('_', '.')
                self.set(config_key, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key (dot notation, e.g., 'network.interface')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key (dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save configuration to file
        
        Args:
            path: Optional path to save to (defaults to original path)
        """
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name
            
        Returns:
            Configuration section
        """
        return deepcopy(self.get(section, {}))
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid, raises exception otherwise
        """
        required_sections = [
            'platform',
            'network',
            'monitoring'
        ]
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
        
        return True
    
    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style setting"""
        self.set(key, value)
