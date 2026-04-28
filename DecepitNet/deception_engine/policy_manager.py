"""
Deception Policy Manager
Manages adaptive deception policies and configuration recommendations
"""

from typing import Dict, List, Any, Optional
import logging
import random
from datetime import datetime, timezone, timezone, timedelta

logger = logging.getLogger(__name__)


class DeceptionPolicyManager:
    """Manages deception policies and adaptive configuration"""
    
    def __init__(self):
        self.policies: Dict[str, Dict] = {}
        self.policy_history: List[Dict] = []
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default deception policies"""
        self.policies = {
            "passive": {
                "description": "Minimal interaction, observe only",
                "response_delay_ms": 0,
                "decoy_density": "low",
                "service_visibility": "minimal",
                "adaptation_frequency": "hourly"
            },
            "moderate": {
                "description": "Balanced interaction and deception",
                "response_delay_ms": 200,
                "decoy_density": "medium",
                "service_visibility": "normal",
                "adaptation_frequency": "every_30_min"
            },
            "aggressive": {
                "description": "High interaction, maximum deception",
                "response_delay_ms": 500,
                "decoy_density": "high",
                "service_visibility": "extensive",
                "adaptation_frequency": "every_15_min"
            },
            "auto": {
                "description": "Adaptive based on threat level",
                "response_delay_ms": "adaptive",
                "decoy_density": "adaptive",
                "service_visibility": "adaptive",
                "adaptation_frequency": "real_time"
            }
        }
        
        logger.info(f"Loaded {len(self.policies)} deception policies")
    
    async def get_adaptive_configuration(
        self,
        honeypot_id: str,
        activity: List[Dict[str, Any]],
        strategy: str = "auto",
        adaptation_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate adaptive configuration based on recent activity
        
        Args:
            honeypot_id: Honeypot identifier
            activity: Recent telemetry events
            strategy: Deception strategy (auto, passive, moderate, aggressive)
            adaptation_score: Score from AdaptationScorer (0-100)
        
        Returns:
            Recommended configuration dictionary
        """
        logger.info(
            f"Generating adaptive configuration for {honeypot_id}, "
            f"strategy={strategy}, score={adaptation_score:.2f}"
        )
        
        # Analyze activity patterns
        activity_analysis = self._analyze_activity(activity)
        
        # Select base policy
        if strategy == "auto":
            policy = self._select_auto_policy(adaptation_score, activity_analysis)
        else:
            policy = self.policies.get(strategy, self.policies["moderate"])
        
        # Generate configuration
        config = {
            "honeypot_id": honeypot_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy": strategy,
            "adaptation_score": adaptation_score,
            **self._generate_service_config(policy, activity_analysis),
            **self._generate_decoy_config(policy, activity_analysis),
            **self._generate_credential_config(policy, activity_analysis),
            **self._generate_response_config(policy, activity_analysis)
        }
        
        # Store in history
        self.policy_history.append({
            "honeypot_id": honeypot_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy": strategy,
            "configuration": config,
            "activity_summary": activity_analysis
        })
        
        return config
    
    def _analyze_activity(self, activity: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze recent activity to inform adaptation"""
        if not activity:
            return {
                "total_events": 0,
                "unique_sources": 0,
                "dominant_protocol": None,
                "threat_level": "low",
                "attack_patterns": []
            }
        
        unique_ips = set()
        protocols = {}
        mitre_techniques = []
        threat_scores = []
        
        for event in activity:
            if 'source_ip' in event:
                unique_ips.add(event['source_ip'])
            
            protocol = event.get('protocol', 'unknown')
            protocols[protocol] = protocols.get(protocol, 0) + 1
            
            if 'mitre_techniques' in event:
                mitre_techniques.extend(event['mitre_techniques'])
            
            if 'threat_score' in event:
                threat_scores.append(event['threat_score'])
        
        avg_threat = sum(threat_scores) / len(threat_scores) if threat_scores else 0
        
        # Determine threat level
        if avg_threat > 75:
            threat_level = "critical"
        elif avg_threat > 50:
            threat_level = "high"
        elif avg_threat > 25:
            threat_level = "medium"
        else:
            threat_level = "low"
        
        return {
            "total_events": len(activity),
            "unique_sources": len(unique_ips),
            "dominant_protocol": max(protocols.items(), key=lambda x: x[1])[0] if protocols else None,
            "threat_level": threat_level,
            "average_threat_score": avg_threat,
            "attack_patterns": [*set(mitre_techniques)],  # Unpacking set faster than list()
            "protocols": protocols
        }
    
    def _select_auto_policy(
        self,
        adaptation_score: float,
        activity_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Automatically select policy based on score and activity"""
        threat_level = activity_analysis.get('threat_level', 'low')
        
        if adaptation_score > 75 or threat_level == "critical":
            return self.policies["aggressive"]
        elif adaptation_score > 40 or threat_level in ["high", "medium"]:
            return self.policies["moderate"]
        else:
            return self.policies["passive"]
    
    def _generate_service_config(
        self,
        policy: Dict[str, Any],
        activity: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate service configuration"""
        visibility = policy.get('service_visibility', 'normal')
        dominant_protocol = activity.get('dominant_protocol')
        
        # Base services
        services = []
        
        if visibility == "minimal":
            services = [dominant_protocol] if dominant_protocol else ["ssh"]
        elif visibility == "normal":
            services = ["ssh", "http", "ftp"]
            if dominant_protocol and dominant_protocol not in services:
                services.append(dominant_protocol)
        elif visibility in ["extensive", "adaptive"]:
            services = ["ssh", "http", "ftp", "smtp", "mysql", "telnet"]
        
        return {"enabled_services": services}
    
    def _generate_decoy_config(
        self,
        policy: Dict[str, Any],
        activity: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate decoy file configuration"""
        density = policy.get('decoy_density', 'medium')
        attack_patterns = activity.get('attack_patterns', [])
        
        decoys = []
        
        # Always include basic decoys
        basic_decoys = [
            {"path": "/etc/passwd", "content": "root:x:0:0:root:/root:/bin/bash"},
            {"path": "/root/.ssh/authorized_keys", "content": "ssh-rsa AAAAB3Nza..."}
        ]
        
        # Add density-based decoys
        if density == "low":
            decoys = basic_decoys[:1]
        elif density == "medium":
            decoys = basic_decoys + [
                {"path": "/var/www/html/config.php", "content": "<?php $db_pass='admin123';"},
                {"path": "/home/admin/.bash_history", "content": "sudo su\ncd /var/www"}
            ]
        elif density in ["high", "adaptive"]:
            decoys = basic_decoys + [
                {"path": "/var/www/html/config.php", "content": "<?php $db_pass='admin123';"},
                {"path": "/home/admin/.bash_history", "content": "sudo su\ncd /var/www"},
                {"path": "/etc/shadow", "content": "root:$6$xyz..."},
                {"path": "/root/backup.sql", "content": "-- Database backup"},
                {"path": "/opt/app/credentials.json", "content": '{"api_key": "sk-..."}'},
                {"path": "/home/user/passwords.txt", "content": "Production: P@ssw0rd123"}
            ]
        
        # Add technique-specific decoys
        if "T1003" in attack_patterns:  # Credential Dumping
            decoys.append({"path": "/etc/shadow.bak", "content": "backup_hashes"})
        
        if "T1105" in attack_patterns:  # Ingress Tool Transfer
            decoys.append({"path": "/tmp/setup.sh", "content": "#!/bin/bash\necho 'Fake script'"})
        
        return {"decoy_files": decoys}
    
    def _generate_credential_config(
        self,
        policy: Dict[str, Any],
        activity: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, str]]]:
        """Generate fake credential configuration"""
        density = policy.get('decoy_density', 'medium')
        
        credentials = [
            {"username": "admin", "password": "admin"},
            {"username": "root", "password": "toor"}
        ]
        
        if density == "medium":
            credentials.extend([
                {"username": "user", "password": "password"},
                {"username": "test", "password": "test123"}
            ])
        elif density in ["high", "adaptive"]:
            credentials.extend([
                {"username": "user", "password": "password"},
                {"username": "test", "password": "test123"},
                {"username": "oracle", "password": "oracle"},
                {"username": "postgres", "password": "postgres"},
                {"username": "ubuntu", "password": "ubuntu"},
                {"username": "pi", "password": "raspberry"}
            ])
        
        return {"fake_credentials": credentials}
    
    def _generate_response_config(
        self,
        policy: Dict[str, Any],
        activity: Dict[str, Any]
    ) -> Dict[str, int]:
        """Generate response timing configuration"""
        delay = policy.get('response_delay_ms', 0)
        
        if delay == "adaptive":
            # Adaptive delay based on threat level
            threat_level = activity.get('threat_level', 'low')
            if threat_level == "critical":
                delay = random.randint(300, 700)
            elif threat_level == "high":
                delay = random.randint(200, 400)
            elif threat_level == "medium":
                delay = random.randint(100, 200)
            else:
                delay = 0
        
        return {"response_delay_ms": delay}
    
    def get_policy_history(self, honeypot_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get policy application history"""
        if honeypot_id:
            history = [h for h in self.policy_history if h['honeypot_id'] == honeypot_id]
        else:
            history = self.policy_history
        
        return history[-limit:]
