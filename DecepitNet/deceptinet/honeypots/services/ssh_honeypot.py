"""
SSH Honeypot Implementation
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

from .base import BaseHoneypot


class SSHHoneypot(BaseHoneypot):
    """SSH honeypot service"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        super().__init__(config, db_manager)
        self.banner = "SSH-2.0-OpenSSH_8.2p1 Ubuntu-4ubuntu0.5"
        self.fake_credentials = self._load_credentials()
    
    def _load_credentials(self) -> Dict[str, str]:
        """Load fake credentials"""
        # Common weak credentials for honeypot
        return {
            'root': 'root',
            'admin': 'admin',
            'admin': 'password',
            'ubuntu': 'ubuntu',
            'user': 'user123',
            'test': 'test123'
        }
    
    async def start(self) -> None:
        """Start SSH honeypot"""
        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                '0.0.0.0',
                self.port
            )
            self.running = True
            self.logger.info(f"SSH honeypot started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start SSH honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop SSH honeypot"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
        self.logger.info("SSH honeypot stopped")
    
    async def handle_connection(self, reader, writer) -> None:
        """Handle SSH connection attempt"""
        client_addr = self.get_client_address(writer)
        client_ip, client_port = client_addr[0], client_addr[1]
        
        session_id = await self.create_session(client_ip, client_port)
        
        try:
            # Send SSH banner
            writer.write(f"{self.banner}\r\n".encode())
            await writer.drain()
            
            self.logger.info(f"SSH connection from {client_ip}:{client_port}")
            
            # Simulate SSH handshake
            auth_attempts = 0
            max_attempts = 3
            
            while auth_attempts < max_attempts:
                # Read authentication attempt
                try:
                    data = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                    if not data:
                        break
                    
                    # Log the attempt
                    await self.log_interaction({
                        'source_ip': client_ip,
                        'source_port': client_port,
                        'destination_ip': 'honeypot',
                        'destination_port': self.port,
                        'protocol': 'SSH',
                        'service_type': 'ssh',
                        'interaction_type': 'auth_attempt',
                        'payload': data.hex(),
                        'metadata': {
                            'attempt': auth_attempts + 1,
                            'banner': self.banner
                        },
                        'threat_level': 'medium',
                        'session_id': session_id
                    })
                    
                    auth_attempts += 1
                    
                    # Send authentication failure
                    writer.write(b"Permission denied\r\n")
                    await writer.drain()
                    
                except asyncio.TimeoutError:
                    break
            
            self.logger.info(f"SSH session ended from {client_ip} after {auth_attempts} attempts")
        
        except Exception as e:
            self.logger.error(f"Error handling SSH connection: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()
            if session_id in self.sessions:
                del self.sessions[session_id]
