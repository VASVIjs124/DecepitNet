"""
Base Honeypot Class
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ...core.logger import setup_logger


class BaseHoneypot(ABC):
    """Base class for all honeypots"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        """
        Initialize honeypot
        
        Args:
            config: Honeypot configuration
            db_manager: Database manager
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = setup_logger(self.__class__.__name__)
        
        self.port = config.get('port')
        self.ai_enabled = config.get('ai_enabled', False)
        self.running = False
        self.server = None
        
        self.interaction_count = 0
        self.sessions: Dict[str, Dict] = {}
    
    @abstractmethod
    async def start(self) -> None:
        """Start the honeypot service"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the honeypot service"""
        pass
    
    @abstractmethod
    async def handle_connection(self, reader, writer) -> None:
        """Handle incoming connection"""
        pass
    
    def is_running(self) -> bool:
        """Check if honeypot is running"""
        return self.running
    
    async def log_interaction(self, data: Dict[str, Any]) -> None:
        """
        Log honeypot interaction
        
        Args:
            data: Interaction data
        """
        try:
            await self.db_manager.insert_interaction(data)
            self.interaction_count += 1
        except Exception as e:
            self.logger.error(f"Failed to log interaction: {e}")
    
    async def create_session(self, source_ip: str, source_port: int) -> str:
        """
        Create new session
        
        Args:
            source_ip: Source IP address
            source_port: Source port
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'id': session_id,
            'source_ip': source_ip,
            'source_port': source_port,
            'start_time': datetime.now(),
            'interactions': []
        }
        return session_id
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get honeypot statistics"""
        return {
            'running': self.running,
            'port': self.port,
            'ai_enabled': self.ai_enabled,
            'interaction_count': self.interaction_count,
            'active_sessions': len(self.sessions)
        }
    
    def get_client_address(self, writer) -> tuple:
        """Get client address from writer"""
        try:
            return writer.get_extra_info('peername')
        except:
            return ('unknown', 0)
