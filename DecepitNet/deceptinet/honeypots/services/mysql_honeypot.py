"""
MySQL Honeypot Implementation
"""

import asyncio
from typing import Dict, Any
import struct

from .base import BaseHoneypot


class MySQLHoneypot(BaseHoneypot):
    """MySQL honeypot service"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        super().__init__(config, db_manager)
        self.server_version = "5.7.34-log"
    
    async def start(self) -> None:
        """Start MySQL honeypot"""
        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                '0.0.0.0',
                self.port
            )
            self.running = True
            self.logger.info(f"MySQL honeypot started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start MySQL honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop MySQL honeypot"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
    
    async def handle_connection(self, reader, writer) -> None:
        """Handle MySQL connection"""
        client_addr = self.get_client_address(writer)
        client_ip, client_port = client_addr[0], client_addr[1]
        
        session_id = await self.create_session(client_ip, client_port)
        
        try:
            # Send MySQL handshake
            handshake = self._create_handshake_packet()
            writer.write(handshake)
            await writer.drain()
            
            # Read auth response
            data = await asyncio.wait_for(reader.read(1024), timeout=10.0)
            
            if data:
                await self.log_interaction({
                    'source_ip': client_ip,
                    'source_port': client_port,
                    'destination_ip': 'honeypot',
                    'destination_port': self.port,
                    'protocol': 'MySQL',
                    'service_type': 'mysql',
                    'interaction_type': 'auth_attempt',
                    'payload': data.hex(),
                    'session_id': session_id,
                    'threat_level': 'medium'
                })
                
                # Send auth error
                error_packet = self._create_error_packet()
                writer.write(error_packet)
                await writer.drain()
        
        except asyncio.TimeoutError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
    
    def _create_handshake_packet(self) -> bytes:
        """Create MySQL handshake packet"""
        # Simplified handshake
        packet = bytearray()
        packet.append(10)  # Protocol version
        packet.extend(self.server_version.encode())
        packet.append(0)  # Null terminator
        packet.extend(b'\x00' * 4)  # Thread ID
        packet.extend(b'12345678')  # Salt
        packet.append(0)
        
        # Add length header
        length = len(packet)
        header = struct.pack('<I', length)[:3] + b'\x00'
        
        return header + bytes(packet)
    
    def _create_error_packet(self) -> bytes:
        """Create MySQL error packet"""
        error_msg = "Access denied for user"
        packet = bytearray()
        packet.append(0xFF)  # Error header
        packet.extend(struct.pack('<H', 1045))  # Error code
        packet.extend(b'#28000')  # SQL state
        packet.extend(error_msg.encode())
        
        length = len(packet)
        header = struct.pack('<I', length)[:3] + b'\x01'
        
        return header + bytes(packet)
