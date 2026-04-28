"""
Supervised ML Classifiers
XGBoost for tabular features, CNN for sequence analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
import pickle
import json
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, confusion_matrix
import xgboost as xgb
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)


class XGBoostAttackClassifier:
    """
    XGBoost classifier for tabular attack features
    Features: source_ip encoding, protocol, ports, temporal features, geo features
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_scaler = StandardScaler()
        self.feature_names = []
        self.model_path = model_path or Path("models/xgboost_classifier.pkl")
        
        # XGBoost parameters
        self.params = {
            'objective': 'multi:softmax',
            'num_class': 5,  # benign, reconnaissance, exploitation, lateral_movement, impact
            'max_depth': 8,
            'learning_rate': 0.1,
            'n_estimators': 200,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'gamma': 0.1,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42
        }
    
    def extract_features(self, events: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Extract tabular features from events
        
        Features:
        - source_ip_hash: Hash of source IP
        - protocol_encoded: Numeric encoding of protocol
        - source_port: Source port number
        - dest_port: Destination port number
        - payload_length: Length of payload
        - threat_score: Pre-computed threat score
        - hour_of_day: Hour when event occurred
        - day_of_week: Day of week (0-6)
        - unique_commands_count: Number of unique commands (if applicable)
        - failed_auth_count: Number of failed auth attempts
        - geo_country_code: Country code (encoded)
        """
        features = []
        
        for event in events:
            feature_dict = {
                'source_ip_hash': hash(event.get('source_ip', '0.0.0.0')) % 10000,
                'protocol_encoded': self._encode_protocol(event.get('protocol', 'unknown')),
                'source_port': event.get('source_port', 0),
                'dest_port': event.get('dest_port', 0),
                'payload_length': len(event.get('payload', '')),
                'threat_score': event.get('threat_score', 0),
                'hour_of_day': self._extract_hour(event.get('timestamp')),
                'day_of_week': self._extract_day_of_week(event.get('timestamp')),
                'unique_commands_count': len(set(event.get('commands', []))),
                'failed_auth_count': event.get('failed_auth_count', 0),
                'geo_country_code': self._encode_country(event.get('geoip', {}).get('country_code2', 'XX'))
            }
            features.append(feature_dict)
        
        df = pd.DataFrame(features)
        self.feature_names = df.columns.tolist()
        return df
    
    def _encode_protocol(self, protocol: str) -> int:
        """Encode protocol to integer"""
        protocol_map = {
            'ssh': 1, 'http': 2, 'https': 3, 'ftp': 4,
            'smtp': 5, 'mysql': 6, 'telnet': 7, 'smb': 8
        }
        return protocol_map.get(protocol.lower(), 0)
    
    def _encode_country(self, country_code: str) -> int:
        """Encode country code to integer"""
        return hash(country_code) % 1000
    
    def _extract_hour(self, timestamp) -> int:
        """Extract hour from timestamp"""
        from datetime import datetime
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.hour
            except:
                return 0
        return 0
    
    def _extract_day_of_week(self, timestamp) -> int:
        """Extract day of week from timestamp"""
        from datetime import datetime
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.weekday()
            except:
                return 0
        return 0
    
    def train(
        self,
        X: Any,
        y: np.ndarray,
        validation_split: float = 0.2
    ) -> Dict[str, float]:
        """
        Train XGBoost classifier
        
        Args:
            X: Feature DataFrame
            y: Labels (attack categories)
            validation_split: Fraction for validation
        
        Returns:
            Training metrics
        """
        if isinstance(X, list):
            X = self.extract_features(X)
        elif not isinstance(X, pd.DataFrame):
            raise TypeError("X must be a pandas DataFrame or a list of event dictionaries")

        y_array = np.asarray(y).astype(str)
        if len(X) != len(y_array):
            raise ValueError("Feature and label counts do not match")

        logger.info(f"Training XGBoost classifier on {len(X)} samples...")

        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y_array)
        self.params['num_class'] = len(self.label_encoder.classes_)

        # Scale features
        X_scaled = self.feature_scaler.fit_transform(X.values)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y_encoded,
            test_size=validation_split,
            random_state=42,
            stratify=y_encoded
        )
        
        # Train model
        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=True
        )
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        f1 = f1_score(y_val, y_pred, average='weighted')
        
        # Classification report
        report = classification_report(
            y_val, y_pred,
            target_names=self.label_encoder.classes_,
            output_dict=True
        )
        
        logger.info(f"XGBoost training complete. F1 Score: {f1:.4f}")
        
        # Save model
        self.save()
        
        return {
            'f1_score': f1,
            'accuracy': report['accuracy'],
            'report': report
        }
    
    def predict(self, events: List[Dict[str, Any]]) -> List[str]:
        """Predict attack categories for events"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first or load().")
        
        # Extract features
        X = self.extract_features(events)
        X_scaled = self.feature_scaler.transform(X)
        
        # Predict
        y_pred = self.model.predict(X_scaled)
        
        # Decode labels
        labels = self.label_encoder.inverse_transform(y_pred)
        
        return labels.tolist()
    
    def predict_proba(self, events: List[Dict[str, Any]]) -> np.ndarray:
        """Predict class probabilities"""
        if self.model is None:
            raise ValueError("Model not trained.")
        
        X = self.extract_features(events)
        X_scaled = self.feature_scaler.transform(X)
        
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if self.model is None:
            return {}
        
        importance = self.model.feature_importances_
        return dict(zip(self.feature_names, importance.tolist()))
    
    def save(self, model_path: Optional[Path] = None):
        """Save model to disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder,
            'feature_scaler': self.feature_scaler,
            'feature_names': self.feature_names,
            'params': self.params
        }
        
        with open(self.model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"XGBoost model saved to {self.model_path}")
    
    def load(self, model_path: Optional[Path] = None):
        """Load model from disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']
        self.feature_scaler = model_data['feature_scaler']
        self.feature_names = model_data['feature_names']
        self.params = model_data['params']
        
        logger.info(f"XGBoost model loaded from {self.model_path}")


class CommandSequenceDataset(Dataset):
    """PyTorch Dataset for command sequences"""
    
    def __init__(self, sequences: List[str], labels: np.ndarray, max_length: int = 100):
        self.sequences = sequences
        self.labels = labels
        self.max_length = max_length
        
        # Build vocabulary
        self.vocab = self._build_vocab(sequences)
        self.vocab_size = len(self.vocab)
    
    def _build_vocab(self, sequences: List[str]) -> Dict[str, int]:
        """Build character vocabulary"""
        vocab = {'<PAD>': 0, '<UNK>': 1}
        idx = 2
        
        for seq in sequences:
            for char in seq:
                if char not in vocab:
                    vocab[char] = idx
                    idx += 1
        
        return vocab
    
    def _encode_sequence(self, sequence: str) -> List[int]:
        """Encode sequence to integer indices"""
        encoded = [self.vocab.get(char, self.vocab['<UNK>']) for char in sequence]
        
        # Pad or truncate
        if len(encoded) < self.max_length:
            encoded += [self.vocab['<PAD>']] * (self.max_length - len(encoded))
        else:
            encoded = encoded[:self.max_length]
        
        return encoded
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        sequence = self.sequences[idx]
        label = self.labels[idx]
        
        encoded = self._encode_sequence(sequence)
        
        return torch.tensor(encoded, dtype=torch.long), torch.tensor(label, dtype=torch.long)


class CNN1D(nn.Module):
    """1D CNN for sequence classification"""
    
    def __init__(self, vocab_size: int, embedding_dim: int = 128, num_classes: int = 5):
        super(CNN1D, self).__init__()
        
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # Multiple conv layers with different kernel sizes
        self.conv1 = nn.Conv1d(embedding_dim, 128, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(embedding_dim, 128, kernel_size=5, padding=2)
        self.conv3 = nn.Conv1d(embedding_dim, 128, kernel_size=7, padding=3)
        
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.dropout = nn.Dropout(0.5)
        self.fc = nn.Linear(128 * 3, num_classes)
    
    def forward(self, x):
        # x: (batch, seq_len)
        embedded = self.embedding(x)  # (batch, seq_len, embedding_dim)
        embedded = embedded.permute(0, 2, 1)  # (batch, embedding_dim, seq_len)
        
        # Apply convolutions
        conv1_out = torch.relu(self.conv1(embedded))
        conv2_out = torch.relu(self.conv2(embedded))
        conv3_out = torch.relu(self.conv3(embedded))
        
        # Pool
        pool1 = self.pool(conv1_out).squeeze(-1)
        pool2 = self.pool(conv2_out).squeeze(-1)
        pool3 = self.pool(conv3_out).squeeze(-1)
        
        # Concatenate
        concatenated = torch.cat([pool1, pool2, pool3], dim=1)
        
        # Dropout and FC
        dropped = self.dropout(concatenated)
        output = self.fc(dropped)
        
        return output


class CNNSequenceClassifier:
    """1D CNN for command/payload sequence analysis"""
    
    def __init__(self, model_path: Optional[Path] = None):
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_path = model_path or Path("models/cnn_sequence_classifier.pt")
        self.label_encoder = LabelEncoder()
        self.vocab: Dict[str, int] = {}
        self.max_length = 100
    
    def train(
        self,
        sequences: List[str],
        labels: np.ndarray,
        epochs: int = 20,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        validation_split: float = 0.2,
        max_length: int = 100
    ) -> Dict[str, float]:
        """
        Train CNN classifier
        
        Args:
            sequences: List of command/payload strings
            labels: Attack category labels
            epochs: Training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            validation_split: Validation fraction
        
        Returns:
            Training metrics
        """
        logger.info(f"Training CNN sequence classifier on {len(sequences)} samples...")
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(labels)
        num_classes = len(self.label_encoder.classes_)
        
        # Create dataset
        dataset = CommandSequenceDataset(sequences, y_encoded, max_length=max_length)
        self.vocab = dataset.vocab
        self.max_length = max_length
        
        # Split data
        train_size = int((1 - validation_split) * len(dataset))
        val_size = len(dataset) - train_size
        train_dataset, val_dataset = torch.utils.data.random_split(
            dataset, [train_size, val_size]
        )
        
        # Data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        
        # Initialize model
        self.model = CNN1D(
            vocab_size=dataset.vocab_size,
            num_classes=num_classes
        ).to(self.device)
        
        # Loss and optimizer
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Training loop
        best_f1 = 0.0
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0.0
            
            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            # Validation
            val_loss, val_f1 = self._validate(val_loader, criterion)
            
            logger.info(
                f"Epoch {epoch+1}/{epochs} - "
                f"Train Loss: {train_loss/len(train_loader):.4f}, "
                f"Val Loss: {val_loss:.4f}, Val F1: {val_f1:.4f}"
            )
            
            if val_f1 > best_f1:
                best_f1 = val_f1
                self.save()
        
        logger.info(f"CNN training complete. Best F1 Score: {best_f1:.4f}")
        
        return {'best_f1_score': best_f1}
    
    def _validate(self, val_loader, criterion) -> Tuple[float, float]:
        """Validate model"""
        self.model.eval()
        val_loss = 0.0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                
                preds = torch.argmax(outputs, dim=1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(batch_y.cpu().numpy())
        
        f1 = f1_score(all_labels, all_preds, average='weighted')
        
        return val_loss / len(val_loader), f1
    
    def predict(self, sequences: List[str]) -> List[str]:
        """Predict attack categories for sequences"""
        if self.model is None or not self.vocab:
            raise ValueError("Model not trained.")
        
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for seq in sequences:
                encoded = self._encode_sequence(seq)
                tensor = torch.tensor([encoded], dtype=torch.long).to(self.device)
                
                output = self.model(tensor)
                pred = torch.argmax(output, dim=1).cpu().numpy()[0]
                
                label = self.label_encoder.inverse_transform([pred])[0]
                predictions.append(label)
        
        return predictions

    def predict_proba(self, sequences: List[str]) -> np.ndarray:
        """Predict class probabilities for sequences."""
        if self.model is None or not self.vocab:
            raise ValueError("Model not trained.")

        self.model.eval()
        probabilities = []

        with torch.no_grad():
            for seq in sequences:
                encoded = self._encode_sequence(seq)
                tensor = torch.tensor([encoded], dtype=torch.long).to(self.device)
                output = self.model(tensor)
                proba = torch.softmax(output, dim=1).cpu().numpy()[0]
                probabilities.append(proba)

        return np.array(probabilities)

    def _encode_sequence(self, sequence: str) -> List[int]:
        """Encode a sequence with current classifier vocabulary."""
        unk_idx = self.vocab.get('<UNK>', 1)
        pad_idx = self.vocab.get('<PAD>', 0)

        encoded = [self.vocab.get(char, unk_idx) for char in sequence]

        if len(encoded) < self.max_length:
            encoded += [pad_idx] * (self.max_length - len(encoded))
        else:
            encoded = encoded[:self.max_length]

        return encoded
    
    def save(self, model_path: Optional[Path] = None):
        """Save model to disk"""
        if self.model is None:
            raise ValueError("No model is available to save")

        if model_path is not None:
            self.model_path = Path(model_path)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'vocab': self.vocab,
            'label_encoder': self.label_encoder,
            'vocab_size': len(self.vocab),
            'max_length': self.max_length
        }, self.model_path)
        
        logger.info(f"CNN model saved to {self.model_path}")
    
    def load(self, model_path: Optional[Path] = None):
        """Load model from disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        
        checkpoint = torch.load(self.model_path, map_location=self.device)
        
        self.label_encoder = checkpoint['label_encoder']
        self.vocab = checkpoint['vocab']
        self.max_length = checkpoint.get('max_length', 100)
        vocab_size = checkpoint['vocab_size']
        num_classes = len(self.label_encoder.classes_)
        
        self.model = CNN1D(vocab_size=vocab_size, num_classes=num_classes).to(self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        
        logger.info(f"CNN model loaded from {self.model_path}")


class EnsembleClassifier:
    """Ensemble combining XGBoost and CNN predictions"""
    
    def __init__(
        self,
        xgboost_classifier: Optional[XGBoostAttackClassifier] = None,
        cnn_classifier: Optional[CNNSequenceClassifier] = None,
        xgboost_weight: float = 0.6,
        cnn_weight: float = 0.4
    ):
        if xgboost_classifier is None and cnn_classifier is None:
            raise ValueError("At least one classifier is required for ensemble inference")

        self.xgboost = xgboost_classifier
        self.cnn = cnn_classifier
        self.xgboost_weight = xgboost_weight
        self.cnn_weight = cnn_weight
        self._last_classes: List[str] = []
    
    def predict_proba(self, events: List[Dict[str, Any]]) -> np.ndarray:
        """Ensemble class probabilities using weighted aggregation."""
        if not events:
            self._last_classes = []
            return np.array([])

        all_classes = set()
        if self.xgboost and self.xgboost.model is not None:
            all_classes.update([str(c) for c in self.xgboost.label_encoder.classes_])
        if self.cnn and self.cnn.model is not None:
            all_classes.update([str(c) for c in self.cnn.label_encoder.classes_])

        if not all_classes:
            raise ValueError("No trained model is available for ensemble inference")

        class_labels = sorted(all_classes)
        class_to_idx = {label: idx for idx, label in enumerate(class_labels)}
        combined = np.zeros((len(events), len(class_labels)), dtype=float)

        total_weight = 0.0

        if self.xgboost and self.xgboost.model is not None:
            xgb_probs = self.xgboost.predict_proba(events)
            xgb_classes = [str(c) for c in self.xgboost.label_encoder.classes_]
            for model_idx, label in enumerate(xgb_classes):
                combined[:, class_to_idx[label]] += self.xgboost_weight * xgb_probs[:, model_idx]
            total_weight += self.xgboost_weight

        if self.cnn and self.cnn.model is not None:
            sequences = [event.get('payload', '') or event.get('command', '') for event in events]
            cnn_probs = self.cnn.predict_proba(sequences)
            cnn_classes = [str(c) for c in self.cnn.label_encoder.classes_]
            for model_idx, label in enumerate(cnn_classes):
                combined[:, class_to_idx[label]] += self.cnn_weight * cnn_probs[:, model_idx]
            total_weight += self.cnn_weight

        if total_weight <= 0:
            raise ValueError("Invalid ensemble weights")

        combined /= total_weight
        self._last_classes = class_labels
        return combined

    def predict(self, events: List[Dict[str, Any]]) -> List[str]:
        """Ensemble prediction using weighted class probabilities."""
        probabilities = self.predict_proba(events)
        if probabilities.size == 0:
            return []

        pred_indices = np.argmax(probabilities, axis=1)
        predictions = [self._last_classes[idx] for idx in pred_indices]

        logger.info(f"Ensemble prediction complete for {len(events)} events")
        return predictions
