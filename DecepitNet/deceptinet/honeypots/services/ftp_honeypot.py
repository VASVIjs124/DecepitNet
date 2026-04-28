"""
FTP Honeypot Implementation
"""

import asyncio
from typing import Dict, Any

from .base import BaseHoneypot


class FTPHoneypot(BaseHoneypot):
    """FTP honeypot service"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        super().__init__(config, db_manager)
        self.banner = "220 FTP Server ready."
    
    async def start(self) -> None:
        """Start FTP honeypot"""
        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                '0.0.0.0',
                self.port
            )
            self.running = True
            self.logger.info(f"FTP honeypot started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start FTP honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop FTP honeypot"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
    
    async def handle_connection(self, reader, writer) -> None:
        """Handle FTP connection"""
        client_addr = self.get_client_address(writer)
        client_ip, client_port = client_addr[0], client_addr[1]
        
        session_id = await self.create_session(client_ip, client_port)
        
        try:
            # Send banner
            writer.write(f"{self.banner}\r\n".encode())
            await writer.drain()
            
            # Handle commands
            while True:
                data = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                if not data:
                    break
                
                command = data.decode('utf-8', errors='ignore').strip()
                self.logger.info(f"FTP command from {client_ip}: {command}")
                
                await self.log_interaction({
                    'source_ip': client_ip,
                    'source_port': client_port,
                    'destination_ip': 'honeypot',
                    'destination_port': self.port,
                    'protocol': 'FTP',
                    'service_type': 'ftp',
                    'interaction_type': 'command',
                    'payload': command,
                    'session_id': session_id,
                    'threat_level': 'low'
                })
                
                response = self._handle_ftp_command(command)
                writer.write(f"{response}\r\n".encode())
                await writer.drain()
        
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error in FTP connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    def _handle_ftp_command(self, command: str) -> str:
        """Handle FTP command"""
        cmd = command.split()[0].upper() if command else ''
        
        responses = {
            'USER': '331 Password required',
            'PASS': '530 Login incorrect',
            'SYST': '215 UNIX Type: L8',
            'PWD': '257 "/" is current directory',
            'LIST': '550 Permission denied',
            'QUIT': '221 Goodbye'
        }
        
        return responses.get(cmd, '500 Unknown command')
