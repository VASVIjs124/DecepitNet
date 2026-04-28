"""
Honeypot Manager - Deploys and manages honeypot services
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from ..core.logger import setup_logger
from .services.ssh_honeypot import SSHHoneypot
from .services.http_honeypot import HTTPHoneypot
from .services.ftp_honeypot import FTPHoneypot
from .services.smtp_honeypot import SMTPHoneypot
from .services.mysql_honeypot import MySQLHoneypot


class HoneypotManager:
    """Manages honeypot deployments"""
    
    def __init__(self, config, db_manager):
        """
        Initialize honeypot manager
        
        Args:
            config: Configuration manager
            db_manager: Database manager
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = setup_logger('HoneypotManager')
        
        self.honeypots: Dict[str, Any] = {}
        self.running = False
    
    async def start(self) -> None:
        """Start honeypot manager and deploy honeypots"""
        self.logger.info("Starting honeypot manager...")
        
        # Get honeypot configuration
        services_config = self.config.get('honeypots.services', {})
        
        # Deploy configured honeypots
        for service_name, service_config in services_config.items():
            if service_config.get('enabled', False):
                await self.deploy_honeypot(service_name, service_config)
        
        self.running = True
        self.logger.info(f"Honeypot manager started with {len(self.honeypots)} services")
    
    async def deploy_honeypot(self, service_type: str, config: Dict[str, Any]) -> None:
        """
        Deploy a honeypot service
        
        Args:
            service_type: Type of service (ssh, http, ftp, etc.)
            config: Service configuration
        """
        try:
            honeypot = None
            
            if service_type == 'ssh':
                honeypot = SSHHoneypot(config, self.db_manager)
            elif service_type == 'http':
                honeypot = HTTPHoneypot(config, self.db_manager)
            elif service_type == 'ftp':
                honeypot = FTPHoneypot(config, self.db_manager)
            elif service_type == 'smtp':
                honeypot = SMTPHoneypot(config, self.db_manager)
            elif service_type == 'mysql':
                honeypot = MySQLHoneypot(config, self.db_manager)
            else:
                self.logger.warning(f"Unknown honeypot type: {service_type}")
                return
            
            if honeypot:
                await honeypot.start()
                self.honeypots[service_type] = honeypot
                self.logger.info(f"Deployed {service_type} honeypot on port {config.get('port')}")
        
        except Exception as e:
            self.logger.error(f"Failed to deploy {service_type} honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop all honeypots"""
        self.logger.info("Stopping honeypot manager...")
        
        for service_type, honeypot in self.honeypots.items():
            try:
                await honeypot.stop()
                self.logger.info(f"Stopped {service_type} honeypot")
            except Exception as e:
                self.logger.error(f"Error stopping {service_type} honeypot: {e}")
        
        self.honeypots.clear()
        self.running = False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get honeypot statistics"""
        stats = {
            'total_honeypots': len(self.honeypots),
            'active_honeypots': sum(1 for h in self.honeypots.values() if h.is_running()),
            'services': {}
        }
        
        for service_type, honeypot in self.honeypots.items():
            stats['services'][service_type] = await honeypot.get_stats()
        
        return stats
