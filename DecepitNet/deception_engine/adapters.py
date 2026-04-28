"""
Honeypot Adapters
Interface implementations for different honeypot types
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)


class HoneypotAdapter(ABC):
    """Base adapter interface for honeypot configuration"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"adapter.{name}")
    
    @abstractmethod
    async def apply_configuration(self, honeypot_id: str, config: Dict[str, Any]) -> bool:
        """Apply configuration to honeypot"""
        pass
    
    @abstractmethod
    async def get_status(self, honeypot_id: str) -> Dict[str, Any]:
        """Get honeypot status"""
        pass
    
    @abstractmethod
    async def restart(self, honeypot_id: str) -> bool:
        """Restart honeypot service"""
        pass


class CowrieAdapter(HoneypotAdapter):
    """Adapter for Cowrie SSH/Telnet honeypot"""
    
    def __init__(self):
        super().__init__("cowrie")
        self.base_url = "http://cowrie:9000"  # Cowrie API endpoint
    
    async def apply_configuration(self, honeypot_id: str, config: Dict[str, Any]) -> bool:
        """Apply configuration to Cowrie honeypot"""
        try:
            self.logger.info(f"Applying configuration to Cowrie honeypot {honeypot_id}")
            
            # Update userdb if fake credentials provided
            if 'fake_credentials' in config:
                await self._update_userdb(honeypot_id, config['fake_credentials'])
            
            # Update filesystem decoys
            if 'decoy_files' in config:
                await self._update_decoy_files(honeypot_id, config['decoy_files'])
            
            # Update service configuration
            if 'enabled_services' in config:
                await self._update_services(honeypot_id, config['enabled_services'])
            
            self.logger.info(f"Successfully configured Cowrie honeypot {honeypot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure Cowrie honeypot: {e}")
            return False
    
    async def _update_userdb(self, honeypot_id: str, credentials: list):
        """Update Cowrie userdb.txt"""
        # Format: username:password:uid:gid
        userdb_entries = []
        for cred in credentials:
            username = cred.get('username', 'user')
            password = cred.get('password', 'password')
            uid = cred.get('uid', '1000')
            gid = cred.get('gid', '1000')
            userdb_entries.append(f"{username}:{password}:{uid}:{gid}")
        
        # In production, this would update the ConfigMap via Kubernetes API
        self.logger.info(f"Updated userdb with {len(credentials)} credentials")
    
    async def _update_decoy_files(self, honeypot_id: str, decoy_files: list):
        """Update filesystem decoys"""
        for decoy in decoy_files:
            path = decoy.get('path', '')
            content = decoy.get('content', '')
            self.logger.debug(f"Creating decoy file: {path}")
        
        self.logger.info(f"Updated {len(decoy_files)} decoy files")
    
    async def _update_services(self, honeypot_id: str, services: list):
        """Enable/disable services"""
        self.logger.info(f"Configured services: {', '.join(services)}")
    
    async def get_status(self, honeypot_id: str) -> Dict[str, Any]:
        """Get Cowrie honeypot status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/status", timeout=5.0)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            self.logger.warning(f"Failed to get Cowrie status: {e}")
        
        return {"status": "unknown", "honeypot_id": honeypot_id}
    
    async def restart(self, honeypot_id: str) -> bool:
        """Restart Cowrie service"""
        try:
            # In production, this would trigger Kubernetes pod restart
            self.logger.info(f"Restarting Cowrie honeypot {honeypot_id}")
            await asyncio.sleep(1)  # Simulate restart
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart Cowrie: {e}")
            return False


class DionaeaAdapter(HoneypotAdapter):
    """Adapter for Dionaea malware honeypot"""
    
    def __init__(self):
        super().__init__("dionaea")
        self.base_url = "http://dionaea:9001"
    
    async def apply_configuration(self, honeypot_id: str, config: Dict[str, Any]) -> bool:
        """Apply configuration to Dionaea honeypot"""
        try:
            self.logger.info(f"Applying configuration to Dionaea honeypot {honeypot_id}")
            
            # Update enabled services
            if 'enabled_services' in config:
                await self._update_services(honeypot_id, config['enabled_services'])
            
            # Configure malware collection settings
            if 'download_enabled' in config:
                await self._configure_downloads(honeypot_id, config)
            
            # Update protocol handlers
            if 'protocol_settings' in config:
                await self._update_protocols(honeypot_id, config['protocol_settings'])
            
            self.logger.info(f"Successfully configured Dionaea honeypot {honeypot_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure Dionaea honeypot: {e}")
            return False
    
    async def _update_services(self, honeypot_id: str, services: list):
        """Enable/disable Dionaea services"""
        supported_services = ['http', 'ftp', 'smb', 'mysql', 'mssql', 'sip', 'tftp']
        enabled = [s for s in services if s in supported_services]
        self.logger.info(f"Enabled Dionaea services: {', '.join(enabled)}")
    
    async def _configure_downloads(self, honeypot_id: str, config: Dict[str, Any]):
        """Configure malware download settings"""
        download_enabled = config.get('download_enabled', True)
        max_size_mb = config.get('max_file_size_mb', 100)
        auto_sandbox = config.get('auto_sandbox', False)
        
        self.logger.info(
            f"Malware download: enabled={download_enabled}, "
            f"max_size={max_size_mb}MB, auto_sandbox={auto_sandbox}"
        )
    
    async def _update_protocols(self, honeypot_id: str, protocols: Dict[str, Any]):
        """Update protocol-specific settings"""
        self.logger.info(f"Updated protocol settings for {len(protocols)} protocols")
    
    async def get_status(self, honeypot_id: str) -> Dict[str, Any]:
        """Get Dionaea honeypot status"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/status", timeout=5.0)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            self.logger.warning(f"Failed to get Dionaea status: {e}")
        
        return {"status": "unknown", "honeypot_id": honeypot_id}
    
    async def restart(self, honeypot_id: str) -> bool:
        """Restart Dionaea service"""
        try:
            self.logger.info(f"Restarting Dionaea honeypot {honeypot_id}")
            await asyncio.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart Dionaea: {e}")
            return False


class CustomHoneypotAdapter(HoneypotAdapter):
    """Adapter for custom DECEPTINET honeypots"""
    
    def __init__(self):
        super().__init__("custom")
    
    async def apply_configuration(self, honeypot_id: str, config: Dict[str, Any]) -> bool:
        """Apply configuration to custom honeypot"""
        try:
            self.logger.info(f"Applying configuration to custom honeypot {honeypot_id}")
            
            # Custom honeypots use our internal API
            # Configuration is applied through the honeypot manager
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to configure custom honeypot: {e}")
            return False
    
    async def get_status(self, honeypot_id: str) -> Dict[str, Any]:
        """Get custom honeypot status"""
        return {"status": "active", "honeypot_id": honeypot_id, "type": "custom"}
    
    async def restart(self, honeypot_id: str) -> bool:
        """Restart custom honeypot"""
        self.logger.info(f"Restarting custom honeypot {honeypot_id}")
        return True
