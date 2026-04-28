"""
Main Platform Controller for DECEPTINET
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .config import ConfigManager
from .logger import setup_logger
from .database import DatabaseManager
from ..honeypots.manager import HoneypotManager
from ..redteam.simulator import RedTeamSimulator
from ..evasion.engine import EvasionEngine
from ..intelligence.analyzer import ThreatAnalyzer
from ..monitoring.monitor import SystemMonitor
from ..deception.layer import DeceptionLayer
from ..ml_models.model_manager import ModelManager


class DeceptiNetPlatform:
    """Main platform controller"""
    
    def __init__(self, config: ConfigManager, mode: str = 'full'):
        """
        Initialize DECEPTINET platform
        
        Args:
            config: Configuration manager
            mode: Operation mode (full, honeypot, redteam, analysis, evasion, ml)
        """
        self.config = config
        self.mode = mode
        self.logger = setup_logger(
            'DeceptiNet',
            level=config.get('monitoring.logging.level', 'INFO'),
            log_file=config.get('monitoring.logging.file')
        )
        
        self.start_time = None
        self.running = False
        
        # Components
        self.db_manager: Optional[DatabaseManager] = None
        self.honeypot_manager: Optional[HoneypotManager] = None
        self.redteam_simulator: Optional[RedTeamSimulator] = None
        self.evasion_engine: Optional[EvasionEngine] = None
        self.threat_analyzer: Optional[ThreatAnalyzer] = None
        self.system_monitor: Optional[SystemMonitor] = None
        self.deception_layer: Optional[DeceptionLayer] = None
        self.ml_manager: Optional[ModelManager] = None
        self.dashboard = None
    
    async def start(self) -> None:
        """Start the platform"""
        self.logger.info(f"Starting DECEPTINET platform in {self.mode} mode...")
        self.start_time = datetime.now()
        
        # Initialize database
        self.db_manager = DatabaseManager(self.config.get('database'))
        await self.db_manager.initialize()
        self.logger.info("Database initialized")
        
        # Initialize components based on mode
        if self.mode in ['full', 'honeypot']:
            await self._start_honeypots()
        
        if self.mode in ['full', 'redteam']:
            await self._start_redteam()
        
        if self.mode in ['full', 'evasion']:
            await self._start_evasion()
        
        if self.mode in ['full', 'analysis']:
            await self._start_intelligence()

        if self.mode in ['full', 'ml']:
            await self._start_ml()
        
        # Always start monitoring
        await self._start_monitoring()
        
        # Start deception layer if enabled
        if self.config.get('deception.layer.enabled'):
            await self._start_deception()
        
        self.running = True
        self.logger.info("DECEPTINET platform started successfully")
    
    async def _start_honeypots(self) -> None:
        """Start honeypot manager"""
        if not self.config.get('honeypots.enabled'):
            return
        
        self.honeypot_manager = HoneypotManager(self.config, self.db_manager)
        await self.honeypot_manager.start()
        self.logger.info("Honeypot manager started")
    
    async def _start_redteam(self) -> None:
        """Start red team simulator"""
        if not self.config.get('redteam.enabled'):
            return
        
        self.redteam_simulator = RedTeamSimulator(self.config, self.db_manager)
        
        if self.config.get('redteam.simulation.auto_start'):
            await self.redteam_simulator.start()
            self.logger.info("Red team simulator started")
    
    async def _start_evasion(self) -> None:
        """Start evasion engine"""
        if not self.config.get('evasion.enabled'):
            return
        
        self.evasion_engine = EvasionEngine(self.config)
        await self.evasion_engine.initialize()
        self.logger.info("Evasion engine initialized")
    
    async def _start_intelligence(self) -> None:
        """Start threat intelligence"""
        if not self.config.get('intelligence.threat_feeds.enabled'):
            return
        
        self.threat_analyzer = ThreatAnalyzer(self.config, self.db_manager)
        await self.threat_analyzer.start()
        self.logger.info("Threat analyzer started")
    
    async def _start_monitoring(self) -> None:
        """Start system monitoring"""
        self.system_monitor = SystemMonitor(self.config, self.db_manager)
        await self.system_monitor.start()
        self.logger.info("System monitor started")
    
    async def _start_deception(self) -> None:
        """Start deception layer"""
        self.deception_layer = DeceptionLayer(self.config, self.db_manager)
        await self.deception_layer.start()
        self.logger.info("Deception layer started")

    async def _start_ml(self) -> None:
        """Start ML model manager"""
        self.ml_manager = ModelManager()
        await self.ml_manager.initialize_models()
        self.logger.info("ML model manager initialized")
    
    async def start_dashboard(self, port: int = 5000) -> None:
        """
        Start web dashboard
        
        Args:
            port: Dashboard port
        """
        from ..monitoring.dashboard import Dashboard
        
        self.dashboard = Dashboard(self.config, self, port=port)
        await self.dashboard.start()
        self.logger.info(f"Dashboard started on port {port}")
    
    async def run_forever(self) -> None:
        """Keep platform running"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
    
    async def shutdown(self) -> None:
        """Shutdown the platform"""
        self.logger.info("Shutting down DECEPTINET platform...")
        self.running = False
        
        # Stop all components
        components = [
            ('Honeypot Manager', self.honeypot_manager),
            ('Red Team Simulator', self.redteam_simulator),
            ('Threat Analyzer', self.threat_analyzer),
            ('System Monitor', self.system_monitor),
            ('Deception Layer', self.deception_layer),
            ('Dashboard', self.dashboard)
        ]
        
        for name, component in components:
            if component and hasattr(component, 'stop'):
                try:
                    await component.stop()
                    self.logger.info(f"{name} stopped")
                except Exception as e:
                    self.logger.error(f"Error stopping {name}: {e}")
        
        # Close database
        if self.db_manager:
            await self.db_manager.close()
            self.logger.info("Database connection closed")
        
        self.logger.info("Platform shutdown complete")
    
    def get_status(self) -> Dict[str, Any]:
        """Get platform status"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        # Get honeypot stats
        active_honeypots = 0
        if self.honeypot_manager and hasattr(self.honeypot_manager, 'honeypots'):
            active_honeypots = len(self.honeypot_manager.honeypots)
        
        # Get interaction stats
        total_interactions = 0
        unique_sources = 0
        threats_detected = 0
        
        if self.honeypot_manager and hasattr(self.honeypot_manager, 'get_stats'):
            stats = self.honeypot_manager.get_stats()
            total_interactions = stats.get('total_interactions', 0)
            unique_sources = stats.get('unique_sources', 0)
        
        if self.threat_analyzer and hasattr(self.threat_analyzer, 'get_threat_count'):
            threats_detected = self.threat_analyzer.get_threat_count()
        
        return {
            'running': self.running,
            'mode': self.mode,
            'uptime_seconds': int(uptime),
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'active_honeypots': active_honeypots,
            'total_interactions': total_interactions,
            'unique_sources': unique_sources,
            'threats_detected': threats_detected,
            'components': {
                'honeypots': self.honeypot_manager is not None and self.honeypot_manager.running,
                'redteam': self.redteam_simulator is not None,
                'evasion': self.evasion_engine is not None,
                'intelligence': self.threat_analyzer is not None,
                'monitoring': self.system_monitor is not None,
                'deception': self.deception_layer is not None,
                'ml': self.ml_manager is not None,
                'dashboard': self.dashboard is not None
            }
        }
