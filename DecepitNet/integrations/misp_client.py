"""
MISP (Malware Information Sharing Platform) Integration
Threat intelligence enrichment and IOC lookup
"""

from pymisp import PyMISP, MISPEvent, MISPAttribute
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class MISPIntegration:
    """
    MISP threat intelligence integration
    """
    
    def __init__(
        self,
        url: str,
        api_key: str,
        verify_ssl: bool = True
    ):
        self.url = url
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        
        # Initialize PyMISP
        self.misp = PyMISP(
            url=url,
            key=api_key,
            ssl=verify_ssl
        )
        
        logger.info(f"Initialized MISP integration: {url}")
    
    def enrich_ip(self, ip_address: str) -> Dict[str, Any]:
        """
        Enrich IP address with MISP threat intelligence
        
        Args:
            ip_address: IP address to enrich
        
        Returns:
            Enrichment data
        """
        try:
            # Search MISP for IP
            result = self.misp.search(
                controller='attributes',
                type_attribute='ip-dst',
                value=ip_address,
                pythonify=True
            )
            
            if not result:
                return {
                    'ip': ip_address,
                    'found': False,
                    'threat_level': 'unknown'
                }
            
            # Extract threat information
            events = []
            tags = set()
            threat_level = 0
            
            for attr in result:
                if hasattr(attr, 'Event'):
                    event_info = {
                        'id': attr.Event.id,
                        'info': attr.Event.info,
                        'threat_level': attr.Event.threat_level_id,
                        'date': str(attr.Event.date)
                    }
                    events.append(event_info)
                    
                    # Update max threat level
                    threat_level = max(threat_level, int(attr.Event.threat_level_id))
                    
                    # Collect tags
                    if hasattr(attr.Event, 'Tag'):
                        for tag in attr.Event.Tag:
                            tags.add(tag.name)
            
            enrichment = {
                'ip': ip_address,
                'found': True,
                'num_events': len(events),
                'events': events[:5],  # First 5 events
                'threat_level': self._threat_level_name(threat_level),
                'tags': [*tags],  # Unpacking set optimized
                'last_seen': events[0]['date'] if events else None
            }
            
            logger.info(f"IP {ip_address} enriched. Found in {len(events)} MISP events.")
            
            return enrichment
        
        except Exception as e:
            logger.error(f"Error enriching IP {ip_address}: {e}")
            return {
                'ip': ip_address,
                'error': str(e)
            }
    
    def enrich_file_hash(self, file_hash: str) -> Dict[str, Any]:
        """
        Enrich file hash with MISP data
        
        Args:
            file_hash: MD5, SHA1, or SHA256 hash
        
        Returns:
            Enrichment data
        """
        try:
            # Detect hash type
            hash_type = self._detect_hash_type(file_hash)
            
            # Search MISP
            result = self.misp.search(
                controller='attributes',
                type_attribute=hash_type,
                value=file_hash,
                pythonify=True
            )
            
            if not result:
                return {
                    'hash': file_hash,
                    'hash_type': hash_type,
                    'found': False
                }
            
            # Extract malware families
            malware_families = set()
            events = []
            
            for attr in result:
                if hasattr(attr, 'Event'):
                    events.append({
                        'id': attr.Event.id,
                        'info': attr.Event.info,
                        'date': str(attr.Event.date)
                    })
                    
                    # Extract malware family from tags
                    if hasattr(attr.Event, 'Tag'):
                        for tag in attr.Event.Tag:
                            if 'misp-galaxy:malware=' in tag.name:
                                family = tag.name.split('=')[1]
                                malware_families.add(family)
            
            enrichment = {
                'hash': file_hash,
                'hash_type': hash_type,
                'found': True,
                'num_events': len(events),
                'malware_families': [*malware_families],  # Unpacking set optimized
                'events': events[:3]
            }
            
            logger.info(f"Hash {file_hash} enriched. Families: {malware_families}")
            
            return enrichment
        
        except Exception as e:
            logger.error(f"Error enriching hash {file_hash}: {e}")
            return {
                'hash': file_hash,
                'error': str(e)
            }
    
    def enrich_domain(self, domain: str) -> Dict[str, Any]:
        """Enrich domain with MISP data"""
        try:
            result = self.misp.search(
                controller='attributes',
                type_attribute='domain',
                value=domain,
                pythonify=True
            )
            
            if not result:
                return {
                    'domain': domain,
                    'found': False
                }
            
            events = []
            for attr in result:
                if hasattr(attr, 'Event'):
                    events.append({
                        'id': attr.Event.id,
                        'info': attr.Event.info,
                        'date': str(attr.Event.date)
                    })
            
            return {
                'domain': domain,
                'found': True,
                'num_events': len(events),
                'events': events[:5]
            }
        
        except Exception as e:
            logger.error(f"Error enriching domain {domain}: {e}")
            return {
                'domain': domain,
                'error': str(e)
            }
    
    def create_event_from_honeypot(
        self,
        honeypot_event: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create MISP event from honeypot detection
        
        Args:
            honeypot_event: Honeypot event data
        
        Returns:
            MISP event ID or None
        """
        try:
            # Create MISP event
            event = MISPEvent()
            event.info = f"Honeypot Detection: {honeypot_event.get('attack_type', 'Unknown')}"
            event.distribution = 0  # Your organization only
            event.threat_level_id = self._calculate_threat_level(honeypot_event)
            event.analysis = 1  # Ongoing
            
            # Add attributes
            source_ip = honeypot_event.get('source_ip')
            if source_ip:
                event.add_attribute('ip-src', source_ip, comment='Honeypot attacker IP')
            
            destination_ip = honeypot_event.get('destination_ip')
            if destination_ip:
                event.add_attribute('ip-dst', destination_ip, comment='Honeypot target IP')
            
            # Add commands as network activity
            if 'command' in honeypot_event:
                event.add_attribute(
                    'comment',
                    honeypot_event['command'],
                    comment='Attacker command'
                )
            
            # Add file hashes if available
            if 'file_hash' in honeypot_event:
                event.add_attribute('sha256', honeypot_event['file_hash'])
            
            # Add MITRE ATT&CK techniques
            techniques = honeypot_event.get('mitre_techniques', [])
            for technique in techniques:
                event.add_tag(f'misp-galaxy:mitre-attack-pattern="{technique}"')
            
            # Submit to MISP
            result = self.misp.add_event(event, pythonify=True)
            
            logger.info(f"Created MISP event: {result.id}")
            
            return result.id
        
        except Exception as e:
            logger.error(f"Error creating MISP event: {e}")
            return None
    
    def get_recent_iocs(
        self,
        days: int = 7,
        ioc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent IOCs from MISP
        
        Args:
            days: Number of days to look back
            ioc_type: Optional IOC type filter (ip-dst, domain, sha256, etc.)
        
        Returns:
            List of IOCs
        """
        try:
            # Calculate date
            since_date = datetime.now() - timedelta(days=days)
            
            # Search
            search_params = {
                'controller': 'attributes',
                'timestamp': since_date.timestamp(),
                'pythonify': True
            }
            
            if ioc_type:
                search_params['type_attribute'] = ioc_type
            
            result = self.misp.search(**search_params)
            
            iocs = []
            for attr in result:
                iocs.append({
                    'type': attr.type,
                    'value': attr.value,
                    'event_id': attr.event_id,
                    'timestamp': str(attr.timestamp)
                })
            
            logger.info(f"Retrieved {len(iocs)} IOCs from last {days} days")
            
            return iocs
        
        except Exception as e:
            logger.error(f"Error getting recent IOCs: {e}")
            return []
    
    def _detect_hash_type(self, hash_value: str) -> str:
        """Detect hash type based on length"""
        length = len(hash_value)
        
        if length == 32:
            return 'md5'
        elif length == 40:
            return 'sha1'
        elif length == 64:
            return 'sha256'
        else:
            return 'unknown'
    
    def _threat_level_name(self, level_id: int) -> str:
        """Convert threat level ID to name"""
        levels = {
            1: 'High',
            2: 'Medium',
            3: 'Low',
            4: 'Undefined'
        }
        return levels.get(level_id, 'Unknown')
    
    def _calculate_threat_level(self, event: Dict[str, Any]) -> int:
        """Calculate MISP threat level from honeypot event"""
        threat_score = event.get('threat_score', 0)
        
        if threat_score >= 80:
            return 1  # High
        elif threat_score >= 50:
            return 2  # Medium
        else:
            return 3  # Low
