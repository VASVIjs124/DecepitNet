"""
HTTP Honeypot Implementation
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

from .base import BaseHoneypot


class HTTPHoneypot(BaseHoneypot):
    """HTTP/HTTPS honeypot service"""
    
    def __init__(self, config: Dict[str, Any], db_manager):
        super().__init__(config, db_manager)
        self.server_header = "Apache/2.4.41 (Ubuntu)"
    
    async def start(self) -> None:
        """Start HTTP honeypot"""
        try:
            self.server = await asyncio.start_server(
                self.handle_connection,
                '0.0.0.0',
                self.port
            )
            self.running = True
            self.logger.info(f"HTTP honeypot started on port {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to start HTTP honeypot: {e}")
    
    async def stop(self) -> None:
        """Stop HTTP honeypot"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        self.running = False
        self.logger.info("HTTP honeypot stopped")
    
    async def handle_connection(self, reader, writer) -> None:
        """Handle HTTP connection"""
        client_addr = self.get_client_address(writer)
        client_ip, client_port = client_addr[0], client_addr[1]
        
        session_id = await self.create_session(client_ip, client_port)
        
        try:
            # Read HTTP request
            data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
            
            if not data:
                return
            
            request = data.decode('utf-8', errors='ignore')
            self.logger.info(f"HTTP request from {client_ip}:{client_port}")
            
            # Parse request
            lines = request.split('\r\n')
            if lines:
                request_line = lines[0]
                
                # Log interaction
                await self.log_interaction({
                    'source_ip': client_ip,
                    'source_port': client_port,
                    'destination_ip': 'honeypot',
                    'destination_port': self.port,
                    'protocol': 'HTTP',
                    'service_type': 'http',
                    'interaction_type': 'request',
                    'payload': request[:500],  # First 500 chars
                    'metadata': {
                        'request_line': request_line,
                        'user_agent': self._extract_header(lines, 'User-Agent'),
                        'host': self._extract_header(lines, 'Host')
                    },
                    'threat_level': self._assess_threat_level(request),
                    'session_id': session_id
                })
                
                # Send fake response
                response = self._generate_response(request_line)
                writer.write(response.encode())
                await writer.drain()
        
        except asyncio.TimeoutError:
            self.logger.debug(f"HTTP connection timeout from {client_ip}")
        except Exception as e:
            self.logger.error(f"Error handling HTTP connection: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    def _extract_header(self, lines: list, header_name: str) -> str:
        """Extract HTTP header value"""
        for line in lines:
            if line.lower().startswith(header_name.lower() + ':'):
                return line.split(':', 1)[1].strip()
        return ''
    
    def _assess_threat_level(self, request: str) -> str:
        """Assess threat level based on request"""
        suspicious_patterns = [
            '../', '..\\',  # Directory traversal
            '<script', 'javascript:',  # XSS
            'SELECT', 'UNION', 'DROP',  # SQL injection
            '/etc/passwd', '/etc/shadow',  # File inclusion
            'cmd=', 'exec=', 'system('  # Command injection
        ]
        
        request_lower = request.lower()
        for pattern in suspicious_patterns:
            if pattern.lower() in request_lower:
                return 'high'
        
        return 'low'
    
    def _generate_response(self, request_line: str) -> str:
        """Generate fake HTTP response"""
        # Simple response based on path
        if '/admin' in request_line.lower():
            return (
                "HTTP/1.1 401 Unauthorized\r\n"
                f"Server: {self.server_header}\r\n"
                "WWW-Authenticate: Basic realm=\"Admin Area\"\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
        else:
            body = "<html><body><h1>Welcome</h1></body></html>"
            return (
                "HTTP/1.1 200 OK\r\n"
                f"Server: {self.server_header}\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(body)}\r\n"
                "\r\n"
                f"{body}"
            )
