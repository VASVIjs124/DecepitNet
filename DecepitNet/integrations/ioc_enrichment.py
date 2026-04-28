"""
IOC Enrichment Orchestrator
Coordinates multi-source threat intelligence enrichment
"""

import logging
from typing import Dict, List, Any, Optional
from .misp_client import MISPIntegration
from .opencti_client import OpenCTIIntegration

logger = logging.getLogger(__name__)


class IOCEnricher:
    """
    Multi-source IOC enrichment coordinator
    """
    
    def __init__(
        self,
        misp_url: Optional[str] = None,
        misp_key: Optional[str] = None,
        opencti_url: Optional[str] = None,
        opencti_token: Optional[str] = None
    ):
        self.misp = None
        self.opencti = None
        
        # Initialize MISP
        if misp_url and misp_key:
            self.misp = MISPIntegration(misp_url, misp_key)
            logger.info("MISP integration enabled")
        
        # Initialize OpenCTI
        if opencti_url and opencti_token:
            self.opencti = OpenCTIIntegration(opencti_url, opencti_token)
            logger.info("OpenCTI integration enabled")
    
    def enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich honeypot event with threat intelligence
        
        Args:
            event: Honeypot event
        
        Returns:
            Enriched event
        """
        enrichment = {
            'sources': [],
            'threat_intel': {}
        }
        
        # Extract IOCs
        source_ip = event.get('source_ip')
        file_hash = event.get('file_hash')
        domain = event.get('domain')
        
        # Enrich IP
        if source_ip:
            if self.misp:
                misp_ip = self.misp.enrich_ip(source_ip)
                if misp_ip.get('found'):
                    enrichment['sources'].append('MISP')
                    enrichment['threat_intel']['misp_ip'] = misp_ip
            
            if self.opencti:
                opencti_ip = self.opencti.enrich_ip(source_ip)
                if opencti_ip.get('found'):
                    enrichment['sources'].append('OpenCTI')
                    enrichment['threat_intel']['opencti_ip'] = opencti_ip
        
        # Enrich file hash
        if file_hash and self.misp:
            misp_hash = self.misp.enrich_file_hash(file_hash)
            if misp_hash.get('found'):
                enrichment['threat_intel']['misp_hash'] = misp_hash
        
        # Enrich domain
        if domain and self.misp:
            misp_domain = self.misp.enrich_domain(domain)
            if misp_domain.get('found'):
                enrichment['threat_intel']['misp_domain'] = misp_domain
        
        # Calculate enriched threat score
        if enrichment['threat_intel']:
            event['enriched_threat_score'] = self._calculate_enriched_score(
                event.get('threat_score', 0),
                enrichment
            )
        
        event['enrichment'] = enrichment
        
        return event
    
    def _calculate_enriched_score(
        self,
        base_score: float,
        enrichment: Dict[str, Any]
    ) -> float:
        """
        Calculate enriched threat score combining base + TI
        
        Args:
            base_score: Original threat score
            enrichment: Threat intelligence enrichment
        
        Returns:
            Enriched threat score (0-100)
        """
        score = base_score
        
        # MISP IP enrichment
        misp_ip = enrichment['threat_intel'].get('misp_ip', {})
        if misp_ip.get('found'):
            threat_level = misp_ip.get('threat_level', 'unknown')
            if threat_level == 'High':
                score = min(100, score + 20)
            elif threat_level == 'Medium':
                score = min(100, score + 10)
        
        # OpenCTI enrichment
        opencti_ip = enrichment['threat_intel'].get('opencti_ip', {})
        if opencti_ip.get('found'):
            if opencti_ip.get('threat_actors'):
                score = min(100, score + 15)
            if opencti_ip.get('malware'):
                score = min(100, score + 15)
        
        # Malware hash detection
        misp_hash = enrichment['threat_intel'].get('misp_hash', {})
        if misp_hash.get('found'):
            score = min(100, score + 25)
        
        return score
    
    def batch_enrich(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Batch enrich multiple events"""
        enriched_events = []
        
        for event in events:
            try:
                enriched = self.enrich_event(event)
                enriched_events.append(enriched)
            except Exception as e:
                logger.error(f"Error enriching event: {e}")
                enriched_events.append(event)
        
        return enriched_events
