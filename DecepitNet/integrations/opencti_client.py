"""
OpenCTI (Open Cyber Threat Intelligence) Integration
Advanced threat intelligence platform integration
"""

from pycti import OpenCTIApiClient
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OpenCTIIntegration:
    """
    OpenCTI threat intelligence integration
    """
    
    def __init__(
        self,
        url: str,
        token: str
    ):
        self.url = url
        self.token = token
        
        # Initialize OpenCTI client
        self.opencti = OpenCTIApiClient(
            url=url,
            token=token
        )
        
        logger.info(f"Initialized OpenCTI integration: {url}")
    
    def enrich_ip(self, ip_address: str) -> Dict[str, Any]:
        """
        Enrich IP address with OpenCTI intelligence
        
        Args:
            ip_address: IP to enrich
        
        Returns:
            Enrichment data
        """
        try:
            # Search for IP indicator
            indicators = self.opencti.indicator.list(
                filters=[{
                    "key": "pattern",
                    "values": [f"[ipv4-addr:value = '{ip_address}']"]
                }]
            )
            
            if not indicators:
                return {
                    'ip': ip_address,
                    'found': False
                }
            
            # Extract threat intelligence
            threat_actors = []
            malware = []
            attack_patterns = []
            labels = []
            
            for indicator in indicators:
                # Get related entities
                stix_relations = self.opencti.stix_core_relationship.list(
                    fromId=indicator['id']
                )
                
                for relation in stix_relations:
                    to_entity = relation.get('to')
                    if to_entity:
                        entity_type = to_entity.get('entity_type')
                        
                        if entity_type == 'Threat-Actor':
                            threat_actors.append(to_entity['name'])
                        elif entity_type == 'Malware':
                            malware.append(to_entity['name'])
                        elif entity_type == 'Attack-Pattern':
                            attack_patterns.append(to_entity['name'])
                
                # Get labels
                if 'objectLabel' in indicator:
                    for label in indicator['objectLabel']:
                        labels.append(label['value'])
            
            enrichment = {
                'ip': ip_address,
                'found': True,
                'threat_actors': [*set(threat_actors)],  # Unpacking set optimized
                'malware': [*set(malware)],
                'attack_patterns': [*set(attack_patterns)],
                'labels': [*set(labels)],
                'confidence': indicators[0].get('confidence', 0)
            }
            
            logger.info(f"IP {ip_address} enriched via OpenCTI")
            
            return enrichment
        
        except Exception as e:
            logger.error(f"Error enriching IP via OpenCTI: {e}")
            return {
                'ip': ip_address,
                'error': str(e)
            }
    
    def create_incident_from_honeypot(
        self,
        honeypot_event: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create OpenCTI incident from honeypot detection
        
        Args:
            honeypot_event: Honeypot event
        
        Returns:
            Incident ID or None
        """
        try:
            # Create incident
            incident = self.opencti.incident.create(
                name=f"Honeypot Detection: {honeypot_event.get('attack_type', 'Unknown')}",
                description=f"Detected via DECEPTINET honeypot at {honeypot_event.get('timestamp')}",
                first_seen=honeypot_event.get('timestamp'),
                last_seen=honeypot_event.get('timestamp'),
                severity=self._calculate_severity(honeypot_event),
                source=honeypot_event.get('source_ip'),
                objective=honeypot_event.get('attack_type')
            )
            
            logger.info(f"Created OpenCTI incident: {incident['id']}")
            
            return incident['id']
        
        except Exception as e:
            logger.error(f"Error creating OpenCTI incident: {e}")
            return None
    
    def _calculate_severity(self, event: Dict[str, Any]) -> str:
        """Calculate incident severity"""
        threat_score = event.get('threat_score', 0)
        
        if threat_score >= 80:
            return 'critical'
        elif threat_score >= 60:
            return 'high'
        elif threat_score >= 40:
            return 'medium'
        else:
            return 'low'


# Note: pycti is a complex library. This is a simplified implementation.
# Full implementation would require proper STIX2 object handling.
