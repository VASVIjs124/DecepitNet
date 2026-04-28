"""
SMTP Honeypot Implementation
"""

import asyncio
from typing import Dict, Any

from .base import BaseHoneypot


class SMTPHoneypot(BaseHoneypot):
    """SMTP honeypot service"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        super().__init__(config, db_manager)
        self.banner = "220 mail.example.com ESMTP"
    
    async def start(self) -> None:
        """Start SMTP honeypot"""
        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                '0.0.0.0',
                self.port
            )
            self.running = True
            self.logger.info(f"SMTP honeypot started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start SMTP honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop SMTP honeypot"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
    
    async def handle_connection(self, reader, writer) -> None:
        """Handle SMTP connection"""
        client_addr = self.get_client_address(writer)
        client_ip, client_port = client_addr[0], client_addr[1]
        
        session_id = await self.create_session(client_ip, client_port)
        
        try:
            # Send banner
            writer.write(f"{self.banner}\r\n".encode())
            await writer.drain()
            
            while True:
                data = await asyncio.wait_for(reader.read(1024), timeout=30.0)
                if not data:
                    break
                
                command = data.decode('utf-8', errors='ignore').strip()
                
                await self.log_interaction({
                    'source_ip': client_ip,
                    'source_port': client_port,
                    'destination_ip': 'honeypot',
                    'destination_port': self.port,
                    'protocol': 'SMTP',
                    'service_type': 'smtp',
                    'interaction_type': 'command',
                    'payload': command,
                    'session_id': session_id,
                    'threat_level': 'low'
                })
                
                response = self._handle_smtp_command(command)
                writer.write(f"{response}\r\n".encode())
                await writer.drain()
        
        except asyncio.TimeoutError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
    
    def _handle_smtp_command(self, command: str) -> str:
        """Handle SMTP command"""
        cmd = command.split()[0].upper() if command else ''
        
        if cmd == 'HELO' or cmd == 'EHLO':
            return '250 mail.example.com'
        elif cmd == 'MAIL':
            return '250 OK'
        elif cmd == 'RCPT':
            return '250 OK'
        elif cmd == 'DATA':
            return '354 Start mail input'
        elif cmd == 'QUIT':
            return '221 Bye'
        else:
            return '500 Unknown command'
