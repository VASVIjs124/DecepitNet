"""
Automated Model Training Pipeline
Periodic retraining, model versioning, A/B testing
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil

from .classifiers import XGBoostAttackClassifier, CNNSequenceClassifier
from .profiling import BehaviorProfiler, AnomalyDetector
from .lstm_autoencoder import TemporalAnomalyDetector

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Automated model training and versioning pipeline
    """
    
    def __init__(
        self,
        models_dir: Path = None,
        data_dir: Path = None
    ):
        self.models_dir = models_dir or Path("models")
        self.data_dir = data_dir or Path("data/training")
        self.version_dir = self.models_dir / "versions"
        
        # Create directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.version_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized ModelTrainer. Models: {self.models_dir}")
    
    def train_all_models(
        self,
        training_events: List[Dict[str, Any]],
        version_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train all ML models
        
        Args:
            training_events: Events for training
            version_tag: Optional version tag
        
        Returns:
            Training results
        """
        if not training_events:
            raise ValueError("training_events cannot be empty")

        if not version_tag:
            version_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        logger.info(f"Training all models. Version: {version_tag}")
        
        results = {
            'version': version_tag,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'num_events': len(training_events),
            'models': {}
        }
        
        # Train XGBoost classifier
        try:
            xgb_results = self.train_xgboost(training_events)
            results['models']['xgboost'] = xgb_results
            logger.info(f"✓ XGBoost trained. F1: {xgb_results.get('f1_score', 0):.3f}")
        except Exception as e:
            logger.error(f"✗ XGBoost training failed: {e}")
            results['models']['xgboost'] = {'error': str(e)}
        
        # Train CNN classifier
        try:
            cnn_results = self.train_cnn(training_events)
            results['models']['cnn'] = cnn_results
            logger.info(f"✓ CNN trained. Best F1: {cnn_results.get('best_f1_score', 0):.3f}")
        except Exception as e:
            logger.error(f"✗ CNN training failed: {e}")
            results['models']['cnn'] = {'error': str(e)}
        
        # Train Behavior Profiler
        try:
            profiler_results = self.train_behavior_profiler(training_events)
            results['models']['behavior_profiler'] = profiler_results
            logger.info(f"✓ Behavior Profiler trained. Clusters: {profiler_results.get('num_clusters', 0)}")
        except Exception as e:
            logger.error(f"✗ Behavior Profiler training failed: {e}")
            results['models']['behavior_profiler'] = {'error': str(e)}
        
        # Train Anomaly Detector
        try:
            anomaly_results = self.train_anomaly_detector(training_events)
            results['models']['anomaly_detector'] = anomaly_results
            logger.info(f"✓ Anomaly Detector trained")
        except Exception as e:
            logger.error(f"✗ Anomaly Detector training failed: {e}")
            results['models']['anomaly_detector'] = {'error': str(e)}
        
        # Train LSTM Autoencoder
        try:
            lstm_results = self.train_lstm_autoencoder(training_events)
            results['models']['lstm_autoencoder'] = lstm_results
            logger.info(f"✓ LSTM Autoencoder trained. Threshold: {lstm_results.get('threshold', 0):.4f}")
        except Exception as e:
            logger.error(f"✗ LSTM Autoencoder training failed: {e}")
            results['models']['lstm_autoencoder'] = {'error': str(e)}
        
        # Save version metadata
        self._save_version_metadata(version_tag, results)
        
        # Create version backup
        self._backup_models(version_tag)
        
        logger.info(f"Training complete. Version {version_tag} saved.")
        
        return results
    
    def train_xgboost(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train XGBoost classifier"""
        logger.info("Training XGBoost classifier...")
        
        classifier = XGBoostAttackClassifier()
        
        # Prepare labels (mock for now - would come from labeled data)
        labels = [e.get('attack_type', 0) for e in events]
        
        # Train
        metrics = classifier.train(events, labels)
        
        # Save
        classifier.save(self.models_dir / "xgboost_classifier.pkl")
        
        return metrics
    
    def train_cnn(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train CNN sequence classifier"""
        logger.info("Training CNN sequence classifier...")
        
        # Extract command sequences
        sequences = []
        labels = []
        
        for event in events:
            sequence = event.get('command') or event.get('payload')
            if isinstance(sequence, str) and sequence:
                sequences.append(sequence)
                labels.append(str(event.get('attack_type', 'unknown')))
        
        if not sequences:
            raise ValueError("No command sequences found in events")
        
        classifier = CNNSequenceClassifier()
        
        # Train
        metrics = classifier.train(sequences, labels)
        
        # Save
        classifier.save(self.models_dir / "cnn_sequence_classifier.pt")
        
        return metrics
    
    def train_behavior_profiler(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train behavior profiler"""
        logger.info("Training Behavior Profiler...")
        
        profiler = BehaviorProfiler()
        
        # Train
        metrics = profiler.fit(events)
        
        # Save
        profiler.save(self.models_dir / "behavior_profiler.pkl")
        
        return metrics
    
    def train_anomaly_detector(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train anomaly detector"""
        logger.info("Training Anomaly Detector...")
        
        detector = AnomalyDetector()
        
        # Train
        detector.fit(events)
        
        # Save
        detector.save(self.models_dir / "anomaly_detector.pkl")
        
        return {'trained': True}
    
    def train_lstm_autoencoder(
        self,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train LSTM autoencoder"""
        logger.info("Training LSTM Autoencoder...")
        
        detector = TemporalAnomalyDetector(input_dim=8)
        
        # Train
        metrics = detector.train(events, epochs=50)
        
        # Save
        detector.save(self.models_dir / "lstm_autoencoder.pth")
        
        return metrics
    
    def _save_version_metadata(self, version_tag: str, results: Dict[str, Any]):
        """Save version metadata"""
        metadata_path = self.version_dir / f"{version_tag}.json"
        
        with open(metadata_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Version metadata saved: {metadata_path}")
    
    def _backup_models(self, version_tag: str):
        """Backup current models to version directory"""
        backup_dir = self.version_dir / version_tag
        backup_dir.mkdir(exist_ok=True)
        
        # Copy model files
        for model_file in self.models_dir.glob("*.pkl"):
            shutil.copy(model_file, backup_dir / model_file.name)
        
        for model_file in self.models_dir.glob("*.pth"):
            shutil.copy(model_file, backup_dir / model_file.name)

        for model_file in self.models_dir.glob("*.pt"):
            shutil.copy(model_file, backup_dir / model_file.name)
        
        logger.info(f"Models backed up to {backup_dir}")
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all model versions"""
        versions = []
        
        for metadata_file in self.version_dir.glob("*.json"):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                versions.append(metadata)
        
        # Sort by timestamp
        versions.sort(key=lambda v: v.get('timestamp', ''), reverse=True)
        
        return versions
    
    def rollback_to_version(self, version_tag: str):
        """Rollback to a specific model version"""
        backup_dir = self.version_dir / version_tag
        
        if not backup_dir.exists():
            raise FileNotFoundError(f"Version not found: {version_tag}")
        
        logger.info(f"Rolling back to version {version_tag}...")
        
        # Copy models from backup
        for model_file in backup_dir.glob("*.pkl"):
            shutil.copy(model_file, self.models_dir / model_file.name)
        
        for model_file in backup_dir.glob("*.pth"):
            shutil.copy(model_file, self.models_dir / model_file.name)

        for model_file in backup_dir.glob("*.pt"):
            shutil.copy(model_file, self.models_dir / model_file.name)
        
        logger.info(f"Rollback complete. Active version: {version_tag}")
    
    def compare_versions(
        self,
        version_a: str,
        version_b: str
    ) -> Dict[str, Any]:
        """Compare two model versions"""
        metadata_a_path = self.version_dir / f"{version_a}.json"
        metadata_b_path = self.version_dir / f"{version_b}.json"
        
        if not metadata_a_path.exists() or not metadata_b_path.exists():
            raise FileNotFoundError("One or both versions not found")
        
        with open(metadata_a_path, 'r') as f:
            metadata_a = json.load(f)
        
        with open(metadata_b_path, 'r') as f:
            metadata_b = json.load(f)
        
        comparison = {
            'version_a': version_a,
            'version_b': version_b,
            'metrics_comparison': {}
        }
        
        # Compare XGBoost F1 scores
        f1_a = metadata_a.get('models', {}).get('xgboost', {}).get('f1_score', 0)
        f1_b = metadata_b.get('models', {}).get('xgboost', {}).get('f1_score', 0)
        
        comparison['metrics_comparison']['xgboost_f1'] = {
            'version_a': f1_a,
            'version_b': f1_b,
            'improvement': f1_b - f1_a
        }
        
        # Compare CNN accuracy
        acc_a = metadata_a.get('models', {}).get('cnn', {}).get('best_f1_score', 0)
        acc_b = metadata_b.get('models', {}).get('cnn', {}).get('best_f1_score', 0)
        
        comparison['metrics_comparison']['cnn_accuracy'] = {
            'version_a': acc_a,
            'version_b': acc_b,
            'improvement': acc_b - acc_a
        }

        return comparison

    def save_profiler_models(
        self,
        behavior_profiler: BehaviorProfiler,
        anomaly_detector: AnomalyDetector
    ) -> Dict[str, str]:
        """Persist profiler-related models with default trainer paths."""
        behavior_path = self.models_dir / "behavior_profiler.pkl"
        anomaly_path = self.models_dir / "anomaly_detector.pkl"
        behavior_profiler.save(behavior_path)
        anomaly_detector.save(anomaly_path)
        return {
            'behavior_profiler': str(behavior_path),
            'anomaly_detector': str(anomaly_path)
        }

    def load_profiler_models(self) -> Dict[str, Any]:
        """Load profiler-related models for inference pipelines."""
        behavior_profiler = BehaviorProfiler()
        anomaly_detector = AnomalyDetector()
        behavior_profiler.load(self.models_dir / "behavior_profiler.pkl")
        anomaly_detector.load(self.models_dir / "anomaly_detector.pkl")
        return {
            'behavior_profiler': behavior_profiler,
            'anomaly_detector': anomaly_detector
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    trainer = ModelTrainer()
    
    # List versions
    versions = trainer.list_versions()
    print(f"Found {len(versions)} model versions")
