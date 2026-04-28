"""
System Monitor - Monitoring and metrics collection
"""

import asyncio
import psutil
from typing import Dict, Any
from datetime import datetime

from ..core.logger import setup_logger


class SystemMonitor:
    """System monitoring and metrics"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = setup_logger('SystemMonitor')
        
        self.running = False
        self.metrics = {}
    
    async def start(self) -> None:
        """Start system monitor"""
        self.logger.info("Starting system monitor...")
        self.running = True
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(60)  # Every minute
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
    
    async def _collect_metrics(self) -> None:
        """Collect system metrics"""
        self.metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_connections': len(psutil.net_connections()),
        }
        
        # Get threat statistics
        threat_stats = await self.db_manager.get_threat_statistics()
        self.metrics.update(threat_stats)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics
    
    async def stop(self) -> None:
        """Stop monitor"""
        self.running = False
        self.logger.info("System monitor stopped")
