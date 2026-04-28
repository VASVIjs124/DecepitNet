"""
Machine Learning Models Manager
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.logger import setup_logger
from ml.classifiers import XGBoostAttackClassifier, CNNSequenceClassifier, EnsembleClassifier
from ml.profiling import BehaviorProfiler, AnomalyDetector
from ml.lstm_autoencoder import TemporalAnomalyDetector
from ml.model_trainer import ModelTrainer


class ModelManager:
    """Manages ML models for the platform"""
    
    def __init__(self, models_dir: Optional[Path] = None):
        self.logger = setup_logger('ModelManager')
        self.models_dir = models_dir or Path('models')
        self.models: Dict[str, Any] = {}
        self.model_trainer = ModelTrainer(models_dir=self.models_dir)
    
    async def initialize_models(self) -> None:
        """Initialize ML models"""
        self.logger.info("Initializing ML models...")
        
        # Create models directory
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.models = {}

        xgb_path = self.models_dir / 'xgboost_classifier.pkl'
        cnn_path = self.models_dir / 'cnn_sequence_classifier.pt'
        profiler_path = self.models_dir / 'behavior_profiler.pkl'
        anomaly_path = self.models_dir / 'anomaly_detector.pkl'
        temporal_path = self.models_dir / 'lstm_autoencoder.pth'

        if xgb_path.exists():
            xgb_model = XGBoostAttackClassifier()
            xgb_model.load(xgb_path)
            self.models['xgboost'] = xgb_model

        if cnn_path.exists():
            cnn_model = CNNSequenceClassifier()
            cnn_model.load(cnn_path)
            self.models['cnn'] = cnn_model

        if 'xgboost' in self.models and 'cnn' in self.models:
            self.models['ensemble'] = EnsembleClassifier(
                self.models['xgboost'],
                self.models['cnn']
            )

        if profiler_path.exists():
            profiler = BehaviorProfiler()
            profiler.load(profiler_path)
            self.models['behavior_profiler'] = profiler

        if anomaly_path.exists():
            anomaly_detector = AnomalyDetector()
            anomaly_detector.load(anomaly_path)
            self.models['anomaly_detector'] = anomaly_detector

        if temporal_path.exists():
            temporal_detector = TemporalAnomalyDetector(input_dim=8)
            temporal_detector.load(temporal_path)
            self.models['temporal_anomaly_detector'] = temporal_detector
        
        self.logger.info(f"ML models initialized: {', '.join(sorted(self.models.keys())) or 'none'}")

    async def train_all_models(self, training_events: List[Dict[str, Any]], version_tag: Optional[str] = None) -> Dict[str, Any]:
        """Train all models and reload them into memory."""
        results = self.model_trainer.train_all_models(training_events, version_tag=version_tag)
        await self.initialize_models()
        return results
    
    async def load_model(self, model_name: str) -> Any:
        """Load a specific model"""
        if model_name in self.models:
            return self.models.get(model_name)

        await self.initialize_models()
        return self.models.get(model_name)
    
    async def train_model(self, model_name: str, training_data: Any) -> None:
        """Train a model with new data"""
        self.logger.info(f"Training {model_name} model...")
        if model_name == 'all':
            await self.train_all_models(training_data)
            return

        if model_name == 'xgboost':
            classifier = XGBoostAttackClassifier()
            classifier.train(training_data, [event.get('attack_type', 0) for event in training_data])
            classifier.save(self.models_dir / 'xgboost_classifier.pkl')
            self.models['xgboost'] = classifier
            return

        if model_name == 'cnn':
            classifier = CNNSequenceClassifier()
            sequences = [event.get('command', '') for event in training_data if event.get('command')]
            labels = [event.get('attack_type', 0) for event in training_data if event.get('command')]
            classifier.train(sequences, labels)
            classifier.save(self.models_dir / 'cnn_sequence_classifier.pt')
            self.models['cnn'] = classifier
            return

        raise ValueError(f"Unsupported model name: {model_name}")
    
    async def predict(self, model_name: str, input_data: Any) -> Any:
        """Make prediction using model"""
        model = await self.load_model(model_name)
        if model is None:
            raise ValueError(f"Model '{model_name}' is not available")

        if model_name == 'xgboost' and isinstance(input_data, list):
            return model.predict(input_data)

        if model_name == 'cnn' and isinstance(input_data, list):
            return model.predict(input_data)

        if model_name == 'ensemble' and isinstance(input_data, list):
            return model.predict(input_data)

        if model_name == 'behavior_profiler':
            return model.predict_profile(input_data)

        if model_name == 'anomaly_detector' and isinstance(input_data, list):
            return model.predict(input_data)

        if model_name == 'temporal_anomaly_detector' and isinstance(input_data, list):
            return model.detect_anomalies(input_data)

        return model
