"""
Adaptation Scorer
Calculates adaptation scores based on telemetry and threat intelligence
"""

from typing import Dict, List, Any
import logging
import numpy as np
from datetime import datetime, timezone, timezone, timedelta

logger = logging.getLogger(__name__)


class AdaptationScorer:
    """Calculates scores to determine when/how to adapt honeypots"""
    
    def __init__(self):
        self.score_history: List[Dict] = []
        
        # Scoring weights
        self.weights = {
            'event_frequency': 0.25,
            'threat_severity': 0.30,
            'source_diversity': 0.15,
            'technique_sophistication': 0.20,
            'temporal_pattern': 0.10
        }
    
    async def calculate_score(
        self,
        activity: List[Dict[str, Any]],
        threat_level: str = "low"
    ) -> float:
        """
        Calculate adaptation score (0-100)
        
        Higher scores indicate need for more aggressive adaptation
        
        Args:
            activity: Recent telemetry events
            threat_level: Overall threat level assessment
        
        Returns:
            Adaptation score (0-100)
        """
        if not activity:
            return 0.0
        
        # Calculate component scores
        freq_score = self._calculate_frequency_score(activity)
        severity_score = self._calculate_severity_score(activity, threat_level)
        diversity_score = self._calculate_diversity_score(activity)
        sophistication_score = self._calculate_sophistication_score(activity)
        temporal_score = self._calculate_temporal_score(activity)
        
        # Weighted sum
        total_score = (
            freq_score * self.weights['event_frequency'] +
            severity_score * self.weights['threat_severity'] +
            diversity_score * self.weights['source_diversity'] +
            sophistication_score * self.weights['technique_sophistication'] +
            temporal_score * self.weights['temporal_pattern']
        )
        
        # Normalize to 0-100
        final_score = min(100.0, max(0.0, total_score))
        
        # Store in history
        self.score_history.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'score': final_score,
            'components': {
                'frequency': freq_score,
                'severity': severity_score,
                'diversity': diversity_score,
                'sophistication': sophistication_score,
                'temporal': temporal_score
            },
            'event_count': len(activity)
        })
        
        logger.info(
            f"Calculated adaptation score: {final_score:.2f} "
            f"(freq={freq_score:.1f}, sev={severity_score:.1f}, "
            f"div={diversity_score:.1f}, soph={sophistication_score:.1f}, "
            f"temp={temporal_score:.1f})"
        )
        
        return final_score
    
    def _calculate_frequency_score(self, activity: List[Dict[str, Any]]) -> float:
        """
        Score based on event frequency
        More events = higher score
        """
        event_count = len(activity)
        
        # Scoring thresholds
        if event_count < 10:
            return 10.0
        elif event_count < 50:
            return 30.0
        elif event_count < 100:
            return 50.0
        elif event_count < 500:
            return 70.0
        else:
            return 90.0
    
    def _calculate_severity_score(
        self,
        activity: List[Dict[str, Any]],
        threat_level: str
    ) -> float:
        """
        Score based on threat severity
        Higher severity = higher score
        """
        # Extract threat scores from events
        threat_scores = [
            event.get('threat_score', 0)
            for event in activity
            if 'threat_score' in event
        ]
        
        if not threat_scores:
            # Fallback to threat level
            level_scores = {
                'low': 20.0,
                'medium': 50.0,
                'high': 75.0,
                'critical': 95.0
            }
            return level_scores.get(threat_level, 20.0)
        
        # Use average and max threat scores
        avg_threat = np.mean(threat_scores)
        max_threat = max(threat_scores)
        
        # Combine average and max (weighted toward max)
        score = (avg_threat * 0.4) + (max_threat * 0.6)
        
        return min(100.0, score)
    
    def _calculate_diversity_score(self, activity: List[Dict[str, Any]]) -> float:
        """
        Score based on source IP diversity
        More unique sources = higher score (potential coordinated attack)
        """
        unique_sources = set()
        for event in activity:
            if 'source_ip' in event:
                unique_sources.add(event['source_ip'])
        
        source_count = len(unique_sources)
        
        # Scoring thresholds
        if source_count < 3:
            return 15.0
        elif source_count < 10:
            return 35.0
        elif source_count < 25:
            return 55.0
        elif source_count < 50:
            return 75.0
        else:
            return 95.0
    
    def _calculate_sophistication_score(self, activity: List[Dict[str, Any]]) -> float:
        """
        Score based on attack technique sophistication
        More advanced techniques = higher score
        """
        # Technique sophistication levels
        technique_scores = {
            # Reconnaissance (low sophistication)
            'T1595': 20,  # Active Scanning
            'T1590': 25,  # Gather Victim Network Information
            
            # Initial Access (medium)
            'T1110': 40,  # Brute Force
            'T1078': 45,  # Valid Accounts
            
            # Execution (medium-high)
            'T1059': 60,  # Command and Scripting Interpreter
            'T1203': 65,  # Exploitation for Client Execution
            
            # Persistence (high)
            'T1098': 75,  # Account Manipulation
            'T1136': 70,  # Create Account
            
            # Privilege Escalation (high)
            'T1068': 80,  # Exploitation for Privilege Escalation
            'T1548': 75,  # Abuse Elevation Control Mechanism
            
            # Credential Access (high)
            'T1003': 85,  # OS Credential Dumping
            'T1555': 80,  # Credentials from Password Stores
            
            # Lateral Movement (very high)
            'T1021': 90,  # Remote Services
            'T1570': 85,  # Lateral Tool Transfer
            
            # Impact (critical)
            'T1486': 95,  # Data Encrypted for Impact
            'T1489': 90,  # Service Stop
        }
        
        # Extract techniques from events
        all_techniques = []
        for event in activity:
            if 'mitre_techniques' in event:
                all_techniques.extend(event['mitre_techniques'])
        
        if not all_techniques:
            return 20.0  # Default low score
        
        # Calculate average sophistication
        scores = [technique_scores.get(t, 30) for t in all_techniques]
        avg_sophistication = np.mean(scores)
        
        return min(100.0, avg_sophistication)
    
    def _calculate_temporal_score(self, activity: List[Dict[str, Any]]) -> float:
        """
        Score based on temporal patterns
        Rapid succession of events = higher score
        """
        if len(activity) < 2:
            return 10.0
        
        # Extract timestamps
        timestamps = []
        for event in activity:
            if 'timestamp' in event:
                try:
                    if isinstance(event['timestamp'], str):
                        ts = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                    else:
                        ts = event['timestamp']
                    timestamps.append(ts)
                except:
                    pass
        
        if len(timestamps) < 2:
            return 20.0
        
        # Sort timestamps
        timestamps.sort()
        
        # Calculate time deltas
        deltas = [
            (timestamps[i+1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]
        
        if not deltas:
            return 20.0
        
        # Average time between events
        avg_delta = np.mean(deltas)
        
        # Score based on event frequency
        if avg_delta < 1:  # Less than 1 second between events
            return 95.0
        elif avg_delta < 5:  # Less than 5 seconds
            return 80.0
        elif avg_delta < 30:  # Less than 30 seconds
            return 60.0
        elif avg_delta < 60:  # Less than 1 minute
            return 40.0
        elif avg_delta < 300:  # Less than 5 minutes
            return 25.0
        else:
            return 15.0
    
    def get_score_history(self, limit: int = 100) -> List[Dict]:
        """Get recent score history"""
        return self.score_history[-limit:]
    
    def get_score_statistics(self) -> Dict[str, float]:
        """Get statistical summary of scores"""
        if not self.score_history:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std': 0.0
            }
        
        scores = [h['score'] for h in self.score_history]
        
        return {
            'count': len(scores),
            'mean': float(np.mean(scores)),
            'median': float(np.median(scores)),
            'min': float(min(scores)),
            'max': float(max(scores)),
            'std': float(np.std(scores))
        }
