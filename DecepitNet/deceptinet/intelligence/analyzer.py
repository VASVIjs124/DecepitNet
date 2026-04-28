"""
Threat Intelligence Analyzer
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import Counter

from ..core.logger import setup_logger


class ThreatAnalyzer:
    """Threat intelligence and analysis engine"""
    
    def __init__(self, config, db_manager):
        self.config = config
        self.db_manager = db_manager
        self.logger = setup_logger('ThreatAnalyzer')
        
        self.running = False
        self.threat_cache = {}
    
    async def start(self) -> None:
        """Start threat analyzer"""
        self.logger.info("Starting threat analyzer...")
        self.running = True
        
        # Start analysis loop
        asyncio.create_task(self._analysis_loop())
    
    async def _analysis_loop(self) -> None:
        """Main analysis loop"""
        while self.running:
            try:
                await self._analyze_threats()
                await asyncio.sleep(300)  # Every 5 minutes
            except Exception as e:
                self.logger.error(f"Analysis error: {e}")
    
    async def _analyze_threats(self) -> None:
        """Analyze recent threats"""
        # Get recent interactions
        interactions = await self.db_manager.get_recent_interactions(limit=1000)
        
        if not interactions:
            return
        
        # Analyze patterns
        source_ips = [i['source_ip'] for i in interactions]
        ip_counts = Counter(source_ips)
        
        # Detect suspicious IPs (multiple attempts)
        for ip, count in ip_counts.items():
            if count > self.config.get('monitoring.alerts.thresholds.connection_attempts', 10):
                await self._create_alert({
                    'alert_type': 'suspicious_activity',
                    'severity': 'high',
                    'source_ip': ip,
                    'description': f'Multiple connection attempts detected from {ip} ({count} attempts)',
                    'indicators': [f'connection_count:{count}']
                })
    
    async def _create_alert(self, alert_data: Dict[str, Any]) -> None:
        """Create security alert"""
        await self.db_manager.insert_alert(alert_data)
        self.logger.warning(f"Alert created: {alert_data['description']}")
    
    async def classify_threat(self, interaction: Dict[str, Any]) -> str:
        """
        Classify threat level
        
        Returns:
            Threat classification (low, medium, high, critical)
        """
        # Simple classification based on patterns
        payload = interaction.get('payload', '')
        
        critical_patterns = ['exploit', 'malware', 'ransomware']
        high_patterns = ['sql', 'injection', 'xss', 'rce']
        medium_patterns = ['scan', 'probe', 'enumeration']
        
        payload_lower = str(payload).lower()
        
        if any(p in payload_lower for p in critical_patterns):
            return 'critical'
        elif any(p in payload_lower for p in high_patterns):
            return 'high'
        elif any(p in payload_lower for p in medium_patterns):
            return 'medium'
        else:
            return 'low'
    
    async def analyze_recent_attacks(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze attacks from recent hours"""
        stats = await self.db_manager.get_threat_statistics()
        
        return {
            'period_hours': hours,
            'total_interactions': stats.get('total_interactions', 0),
            'unique_sources': stats.get('unique_sources', 0),
            'alerts': stats.get('alerts_by_severity', {}),
            'timestamp': datetime.now().isoformat()
        }
    
    async def stop(self) -> None:
        """Stop analyzer"""
        self.running = False
        self.logger.info("Threat analyzer stopped")
