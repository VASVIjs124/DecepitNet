"""
Behavior Profiling and Anomaly Detection
DBSCAN clustering and IsolationForest for attacker behavior profiling
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class BehaviorProfiler:
    """
    Attacker behavior profiling using DBSCAN clustering
    Groups attackers by behavioral patterns
    """
    
    def __init__(self, eps: float = 0.5, min_samples: int = 5):
        self.eps = eps
        self.min_samples = min_samples
        self.clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)
        self.profiles: Dict[int, Dict[str, Any]] = {}
        self.feature_names = []
        self.is_fitted = False

    def _normalize_sessions(self, attacker_sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize raw event lists into session dictionaries."""
        if not attacker_sessions:
            return []

        if isinstance(attacker_sessions[0], dict) and 'events' in attacker_sessions[0]:
            return attacker_sessions

        sessions: Dict[str, Dict[str, Any]] = {}
        for event in attacker_sessions:
            source_ip = event.get('source_ip', 'unknown')
            session = sessions.setdefault(source_ip, {
                'source_ip': source_ip,
                'events': [],
                'duration_seconds': 0
            })
            session['events'].append(event)

        return [*sessions.values()]
    
    def extract_behavioral_features(self, attacker_sessions: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Extract behavioral features for clustering
        
        Features per attacker:
        - total_events: Total number of events
        - unique_protocols: Number of unique protocols used
        - avg_session_duration: Average session length
        - failed_auth_ratio: Ratio of failed authentications
        - command_diversity: Number of unique commands
        - timing_variance: Variance in event timing
        - port_scan_score: Port scanning behavior indicator
        - lateral_movement_score: Lateral movement indicator
        - data_exfil_score: Data exfiltration indicator
        - persistence_score: Persistence attempts indicator
        """
        features = []
        attacker_sessions = self._normalize_sessions(attacker_sessions)
        
        for session in attacker_sessions:
            events = session.get('events', [])
            
            if not events:
                continue
            
            # Extract features
            protocols = set([e.get('protocol', 'unknown') for e in events])
            commands = set([e.get('command', '') for e in events if e.get('command')])
            timestamps = [e.get('timestamp') for e in events if e.get('timestamp')]
            
            # Calculate timing variance
            timing_variance = self._calculate_timing_variance(timestamps)
            
            # Calculate scores
            port_scan_score = self._calculate_port_scan_score(events)
            lateral_movement_score = self._calculate_lateral_movement_score(events)
            data_exfil_score = self._calculate_data_exfil_score(events)
            persistence_score = self._calculate_persistence_score(events)
            
            feature_dict = {
                'attacker_id': session.get('source_ip', 'unknown'),
                'total_events': len(events),
                'unique_protocols': len(protocols),
                'avg_session_duration': session.get('duration_seconds', 0),
                'failed_auth_ratio': self._calculate_failed_auth_ratio(events),
                'command_diversity': len(commands),
                'timing_variance': timing_variance,
                'port_scan_score': port_scan_score,
                'lateral_movement_score': lateral_movement_score,
                'data_exfil_score': data_exfil_score,
                'persistence_score': persistence_score,
                'avg_threat_score': np.mean([e.get('threat_score', 0) for e in events])
            }
            
            features.append(feature_dict)
        
        df = pd.DataFrame(features)
        self.feature_names = [c for c in df.columns if c != 'attacker_id']
        
        return df
    
    def _calculate_timing_variance(self, timestamps: List) -> float:
        """Calculate variance in event timing"""
        if len(timestamps) < 2:
            return 0.0
        
        from datetime import datetime
        
        try:
            dts = []
            for ts in timestamps:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    dts.append(dt.timestamp())
            
            if len(dts) < 2:
                return 0.0
            
            diffs = np.diff(sorted(dts))
            return float(np.var(diffs))
        except:
            return 0.0
    
    def _calculate_failed_auth_ratio(self, events: List[Dict]) -> float:
        """Calculate ratio of failed authentication attempts"""
        auth_events = [e for e in events if 'auth' in e.get('event_type', '').lower()]
        if not auth_events:
            return 0.0
        
        failed = len([e for e in auth_events if 'failed' in e.get('event_type', '').lower()])
        return failed / len(auth_events)
    
    def _calculate_port_scan_score(self, events: List[Dict]) -> float:
        """Score indicating port scanning behavior"""
        # Look for rapid connections to multiple ports
        unique_ports = set([e.get('dest_port', 0) for e in events])
        port_diversity = len(unique_ports)
        
        # High port diversity + short time span = likely port scan
        if port_diversity > 10:
            return min(100.0, port_diversity * 5)
        return 0.0
    
    def _calculate_lateral_movement_score(self, events: List[Dict]) -> float:
        """Score indicating lateral movement attempts"""
        # Look for connections to multiple internal IPs
        techniques = []
        for e in events:
            techniques.extend(e.get('mitre_techniques', []))
        
        lateral_techniques = ['T1021', 'T1570', 'T1080']
        matches = len([t for t in techniques if t in lateral_techniques])
        
        return min(100.0, matches * 25)
    
    def _calculate_data_exfil_score(self, events: List[Dict]) -> float:
        """Score indicating data exfiltration attempts"""
        # Look for large data transfers or specific techniques
        techniques = []
        for e in events:
            techniques.extend(e.get('mitre_techniques', []))
        
        exfil_techniques = ['T1048', 'T1041', 'T1567']
        matches = len([t for t in techniques if t in exfil_techniques])
        
        return min(100.0, matches * 30)
    
    def _calculate_persistence_score(self, events: List[Dict]) -> float:
        """Score indicating persistence attempts"""
        techniques = []
        for e in events:
            techniques.extend(e.get('mitre_techniques', []))
        
        persistence_techniques = ['T1098', 'T1136', 'T1546', 'T1053']
        matches = len([t for t in techniques if t in persistence_techniques])
        
        return min(100.0, matches * 25)
    
    def fit(self, attacker_sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Cluster attackers by behavioral patterns
        
        Args:
            attacker_sessions: List of attacker session dictionaries
        
        Returns:
            Clustering results
        """
        logger.info(f"Profiling {len(attacker_sessions)} attacker sessions...")
        
        # Extract features
        df = self.extract_behavioral_features(attacker_sessions)
        
        if df.empty:
            return {'error': 'No features extracted'}
        
        # Prepare features for clustering
        X = df[self.feature_names].values

        # Use dynamic PCA dimensions so small datasets still work.
        n_components = max(1, min(10, X.shape[0], X.shape[1]))
        self.pca = PCA(n_components=n_components)

        if X.shape[0] < 2:
            df['cluster'] = 0
            profile = {
                'cluster_id': 0,
                'size': len(df),
                'avg_features': df[self.feature_names].mean().to_dict(),
                'attacker_ids': df['attacker_id'].tolist(),
                'behavior_type': self._classify_behavior_type(df[self.feature_names].mean().to_dict())
            }
            self.profiles = {0: profile}
            self.is_fitted = True
            return {
                'num_clusters': 1,
                'noise_points': 0,
                'profiles': self.profiles
            }

        X_scaled = self.scaler.fit_transform(X)

        # Apply PCA for dimensionality reduction
        X_pca = self.pca.fit_transform(X_scaled)

        # Cluster
        cluster_labels = self.clusterer.fit_predict(X_pca)
        
        # Analyze clusters
        df['cluster'] = cluster_labels
        
        # Build cluster profiles
        unique_clusters = set(cluster_labels)
        for cluster_id in unique_clusters:
            if cluster_id == -1:  # Noise points
                continue
            
            cluster_data = df[df['cluster'] == cluster_id]
            
            profile = {
                'cluster_id': int(cluster_id),
                'size': len(cluster_data),
                'avg_features': cluster_data[self.feature_names].mean().to_dict(),
                'attacker_ids': cluster_data['attacker_id'].tolist()
            }
            
            # Classify cluster behavior
            avg_features = profile['avg_features']
            behavior_type = self._classify_behavior_type(avg_features)
            profile['behavior_type'] = behavior_type
            
            self.profiles[cluster_id] = profile
        
        noise_count = len(df[df['cluster'] == -1])
        
        logger.info(
            f"Clustering complete: {len(unique_clusters)-1} clusters, "
            f"{noise_count} noise points"
        )

        self.is_fitted = True
        
        return {
            'num_clusters': len(unique_clusters) - 1,
            'noise_points': noise_count,
            'profiles': self.profiles
        }
    
    def _classify_behavior_type(self, avg_features: Dict[str, float]) -> str:
        """Classify cluster behavior type"""
        # Rule-based classification
        if avg_features.get('port_scan_score', 0) > 50:
            return "port_scanner"
        elif avg_features.get('failed_auth_ratio', 0) > 0.7:
            return "brute_forcer"
        elif avg_features.get('lateral_movement_score', 0) > 40:
            return "advanced_persistent_threat"
        elif avg_features.get('data_exfil_score', 0) > 40:
            return "data_exfiltrator"
        elif avg_features.get('persistence_score', 0) > 40:
            return "persistent_actor"
        elif avg_features.get('command_diversity', 0) > 20:
            return "explorer"
        else:
            return "opportunistic"
    
    def predict_profile(self, attacker_session: Dict[str, Any]) -> Dict[str, Any]:
        """Predict which profile an attacker belongs to"""
        df = self.extract_behavioral_features([attacker_session])
        
        if df.empty:
            return {'cluster': -1, 'behavior_type': 'unknown'}

        if not self.is_fitted or not self.profiles:
            avg_features = df[self.feature_names].mean().to_dict()
            return {
                'cluster': 0,
                'behavior_type': self._classify_behavior_type(avg_features),
                'profile': {
                    'cluster_id': 0,
                    'size': 1,
                    'avg_features': avg_features,
                    'attacker_ids': [df.iloc[0]['attacker_id']]
                }
            }

        X = df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        X_pca = self.pca.transform(X_scaled)

        # Approximate nearest profile using stored averages because DBSCAN has no predict.
        sample_features = df[self.feature_names].mean().to_dict()
        best_cluster = None
        best_distance = float('inf')

        for cluster_id, profile in self.profiles.items():
            profile_features = profile.get('avg_features', {})
            common_keys = [key for key in self.feature_names if key in profile_features]
            if not common_keys:
                continue

            distance = float(np.linalg.norm([
                sample_features.get(key, 0.0) - profile_features.get(key, 0.0)
                for key in common_keys
            ]))

            if distance < best_distance:
                best_distance = distance
                best_cluster = cluster_id

        if best_cluster is None:
            return {'cluster': -1, 'behavior_type': 'anomalous'}

        profile = self.profiles.get(best_cluster, {})
        
        return {
            'cluster': int(best_cluster),
            'behavior_type': profile.get('behavior_type', 'unknown'),
            'profile': profile
        }

    def save(self, model_path: Optional[Path] = None) -> None:
        """Save profiler state to disk."""
        path = Path(model_path) if model_path else Path('models/behavior_profiler.pkl')
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'wb') as handle:
            pickle.dump({
                'eps': self.eps,
                'min_samples': self.min_samples,
                'clusterer': self.clusterer,
                'scaler': self.scaler,
                'pca': self.pca,
                'profiles': self.profiles,
                'feature_names': self.feature_names,
                'is_fitted': self.is_fitted
            }, handle)

        logger.info(f"Behavior profiler saved to {path}")

    def load(self, model_path: Optional[Path] = None) -> None:
        """Load profiler state from disk."""
        path = Path(model_path) if model_path else Path('models/behavior_profiler.pkl')
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")

        with open(path, 'rb') as handle:
            model_data = pickle.load(handle)

        self.eps = model_data.get('eps', self.eps)
        self.min_samples = model_data.get('min_samples', self.min_samples)
        self.clusterer = model_data['clusterer']
        self.scaler = model_data['scaler']
        self.pca = model_data['pca']
        self.profiles = model_data.get('profiles', {})
        self.feature_names = model_data.get('feature_names', [])
        self.is_fitted = model_data.get('is_fitted', True)

        logger.info(f"Behavior profiler loaded from {path}")


class AnomalyDetector:
    """
    Anomaly detection using Isolation Forest
    Identifies unusual attacker behavior
    """
    
    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        max_samples: int = 256
    ):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            max_samples=max_samples,
            random_state=42
        )
        self.scaler = StandardScaler()
        self.feature_names = []
        self.model_path = Path("models/anomaly_detector.pkl")
        self.is_fitted = False
    
    def fit(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train anomaly detector
        
        Args:
            events: Training events (normal behavior)
        
        Returns:
            Training summary
        """
        logger.info(f"Training anomaly detector on {len(events)} events...")
        
        # Use same feature extraction as BehaviorProfiler
        profiler = BehaviorProfiler()
        
        # Group events by source IP into sessions
        sessions = self._group_into_sessions(events)
        
        # Extract features
        df = profiler.extract_behavioral_features(sessions)
        self.feature_names = profiler.feature_names
        
        if df.empty:
            return {'error': 'No features extracted'}
        
        # Train
        X = df[self.feature_names].values
        X_scaled = self.scaler.fit_transform(X)
        
        self.model.fit(X_scaled)
        self.is_fitted = True
        
        # Get anomaly scores
        scores = self.model.score_samples(X_scaled)
        predictions = self.model.predict(X_scaled)
        
        anomaly_count = len([p for p in predictions if p == -1])
        
        logger.info(
            f"Anomaly detection training complete. "
            f"Detected {anomaly_count}/{len(predictions)} anomalies in training data"
        )
        
        # Save model
        self.save()
        
        return {
            'total_samples': len(predictions),
            'anomalies_detected': anomaly_count,
            'anomaly_ratio': anomaly_count / len(predictions)
        }
    
    def _group_into_sessions(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group events into sessions by source IP"""
        sessions_dict = {}
        
        for event in events:
            source_ip = event.get('source_ip', 'unknown')
            
            if source_ip not in sessions_dict:
                sessions_dict[source_ip] = {
                    'source_ip': source_ip,
                    'events': [],
                    'duration_seconds': 0
                }
            
            sessions_dict[source_ip]['events'].append(event)
        
        # Calculate durations
        for session in sessions_dict.values():
            events = session['events']
            if len(events) > 1:
                try:
                    from datetime import datetime
                    timestamps = []
                    for e in events:
                        if 'timestamp' in e:
                            ts = e['timestamp']
                            if isinstance(ts, str):
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                timestamps.append(dt.timestamp())
                    
                    if len(timestamps) > 1:
                        session['duration_seconds'] = max(timestamps) - min(timestamps)
                except:
                    pass
        
        return [*sessions_dict.values()]  # Unpacking dict.values() optimized
    
    def predict(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict anomalies in events
        
        Args:
            events: Events to check
        
        Returns:
            List of predictions with anomaly scores
        """
        # Group into sessions
        sessions = self._group_into_sessions(events)

        if not sessions or not self.is_fitted:
            return []
        
        # Extract features
        profiler = BehaviorProfiler()
        df = profiler.extract_behavioral_features(sessions)
        
        if df.empty:
            return []
        
        # Predict
        X = df[self.feature_names].values
        X_scaled = self.scaler.transform(X)
        
        predictions = self.model.predict(X_scaled)
        scores = self.model.score_samples(X_scaled)
        
        results = []
        for i, session in enumerate(sessions):
            result = {
                'source_ip': session['source_ip'],
                'is_anomaly': bool(predictions[i] == -1),
                'anomaly_score': float(scores[i]),
                'event_count': len(session['events'])
            }
            results.append(result)
        
        logger.info(
            f"Anomaly detection complete. "
            f"Found {len([r for r in results if r['is_anomaly']])} anomalies"
        )
        
        return results
    
    def save(self, model_path: Optional[Path] = None):
        """Save model to disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_fitted': self.is_fitted
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Anomaly detector saved to {self.model_path}")
    
    def load(self, model_path: Optional[Path] = None):
        """Load model from disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.is_fitted = model_data.get('is_fitted', True)
        
        logger.info(f"Anomaly detector loaded from {self.model_path}")
