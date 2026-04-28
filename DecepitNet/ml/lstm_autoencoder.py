"""
LSTM Autoencoder for Temporal Anomaly Detection
Learns normal sequences, detects anomalous temporal patterns
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Any, Tuple, Optional
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)


class SequenceDataset(Dataset):
    """
    Dataset for sequence data
    """
    
    def __init__(
        self,
        sequences: List[np.ndarray],
        max_len: int = 100
    ):
        self.sequences = sequences
        self.max_len = max_len
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        seq = self.sequences[idx]
        
        # Pad or truncate
        if len(seq) > self.max_len:
            seq = seq[:self.max_len]
        elif len(seq) < self.max_len:
            padding = np.zeros((self.max_len - len(seq), seq.shape[1]))
            seq = np.vstack([seq, padding])
        
        return torch.FloatTensor(seq)


class LSTMAutoencoder(nn.Module):
    """
    LSTM-based Autoencoder for sequence anomaly detection
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super(LSTMAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Encoder
        self.encoder = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Decoder
        self.decoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Output layer
        self.output_layer = nn.Linear(hidden_dim, input_dim)
    
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor [batch_size, seq_len, input_dim]
        
        Returns:
            Reconstructed sequence
        """
        batch_size = x.size(0)
        seq_len = x.size(1)
        
        # Encode
        _, (hidden, cell) = self.encoder(x)
        
        # Prepare decoder input (repeat hidden state)
        decoder_input = hidden[-1].unsqueeze(1).repeat(1, seq_len, 1)
        
        # Decode
        decoder_output, _ = self.decoder(decoder_input, (hidden, cell))
        
        # Output
        reconstruction = self.output_layer(decoder_output)
        
        return reconstruction


class TemporalAnomalyDetector:
    """
    Temporal anomaly detection using LSTM autoencoder
    """
    
    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        num_layers: int = 2,
        max_seq_len: int = 100,
        model_path: Optional[Path] = None
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.max_seq_len = max_seq_len
        self.model_path = model_path or Path("models/lstm_autoencoder.pth")
        
        # Initialize model
        self.model = LSTMAutoencoder(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_layers=num_layers
        )
        
        # Device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
        # Training state
        self.threshold = None
        self.scaler = None
        
        logger.info(f"Initialized TemporalAnomalyDetector on {self.device}")
    
    def prepare_sequences(
        self,
        events: List[Dict[str, Any]],
        window_size: int = 50
    ) -> List[np.ndarray]:
        """
        Prepare event sequences for training
        
        Args:
            events: List of event dictionaries
            window_size: Sliding window size
        
        Returns:
            List of sequence arrays
        """
        # Group events by source IP
        ip_events = {}
        for event in events:
            ip = event.get('source_ip', 'unknown')
            if ip not in ip_events:
                ip_events[ip] = []
            ip_events[ip].append(event)
        
        sequences = []
        
        for ip, ip_event_list in ip_events.items():
            # Sort by timestamp
            sorted_events = sorted(ip_event_list, key=lambda e: e.get('timestamp', 0))
            
            # Extract features
            features = []
            for event in sorted_events:
                protocol_value = event.get('protocol', 0)
                if isinstance(protocol_value, str):
                    protocol_map = {
                        'ssh': 22,
                        'http': 80,
                        'https': 443,
                        'ftp': 21,
                        'smtp': 25,
                        'telnet': 23,
                        'mysql': 3306,
                        'smb': 445
                    }
                    protocol_value = protocol_map.get(protocol_value.lower(), 0)

                destination_port = event.get('destination_port', event.get('dest_port', 0))
                payload = event.get('payload', '')
                feature_vector = [
                    event.get('source_port', 0) / 65535,
                    destination_port / 65535,
                    protocol_value / 65535,
                    event.get('payload_length', len(payload)) / 1500,
                    event.get('threat_score', 0) / 100,
                    1 if event.get('event_type') == 'connection' else 0,
                    1 if event.get('event_type') == 'command' else 0,
                    1 if event.get('event_type') == 'file_access' else 0
                ]
                features.append(feature_vector)
            
            # Create sliding windows
            for i in range(0, len(features) - window_size + 1, window_size // 2):
                window = features[i:i + window_size]
                if len(window) == window_size:
                    sequences.append(np.array(window))
        
        return sequences
    
    def train(
        self,
        events: List[Dict[str, Any]],
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        val_split: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train LSTM autoencoder
        
        Args:
            events: Training events
            epochs: Number of epochs
            batch_size: Batch size
            learning_rate: Learning rate
            val_split: Validation split ratio
        
        Returns:
            Training metrics
        """
        logger.info(f"Training LSTM autoencoder on {len(events)} events...")
        
        # Prepare sequences
        sequences = self.prepare_sequences(events)
        logger.info(f"Prepared {len(sequences)} sequences")

        if not sequences:
            raise ValueError("No temporal sequences could be prepared from events")

        if len(sequences) < 2:
            raise ValueError("At least 2 sequences are required for LSTM train/validation split")
        
        # Split train/val
        split_idx = int(len(sequences) * (1 - val_split))
        train_sequences = sequences[:split_idx]
        val_sequences = sequences[split_idx:]
        
        # Create datasets
        train_dataset = SequenceDataset(train_sequences, self.max_seq_len)
        val_dataset = SequenceDataset(val_sequences, self.max_seq_len)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False
        )
        
        # Optimizer and loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        train_losses = []
        val_losses = []
        
        for epoch in range(epochs):
            # Train
            self.model.train()
            epoch_train_loss = 0
            
            for batch in train_loader:
                batch = batch.to(self.device)
                
                optimizer.zero_grad()
                reconstruction = self.model(batch)
                loss = criterion(reconstruction, batch)
                loss.backward()
                optimizer.step()
                
                epoch_train_loss += loss.item()
            
            avg_train_loss = epoch_train_loss / len(train_loader)
            train_losses.append(avg_train_loss)
            
            # Validation
            self.model.eval()
            epoch_val_loss = 0
            
            with torch.no_grad():
                for batch in val_loader:
                    batch = batch.to(self.device)
                    reconstruction = self.model(batch)
                    loss = criterion(reconstruction, batch)
                    epoch_val_loss += loss.item()
            
            avg_val_loss = epoch_val_loss / len(val_loader)
            val_losses.append(avg_val_loss)
            
            if (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch + 1}/{epochs} - "
                    f"Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}"
                )
        
        # Calculate threshold (99th percentile of reconstruction errors)
        self.model.eval()
        reconstruction_errors = []
        
        with torch.no_grad():
            for batch in train_loader:
                batch = batch.to(self.device)
                reconstruction = self.model(batch)
                errors = torch.mean((reconstruction - batch) ** 2, dim=(1, 2))
                reconstruction_errors.extend(errors.cpu().numpy())
        
        self.threshold = np.percentile(reconstruction_errors, 99)
        
        logger.info(f"Training complete. Anomaly threshold: {self.threshold:.4f}")
        
        return {
            'final_train_loss': train_losses[-1],
            'final_val_loss': val_losses[-1],
            'threshold': self.threshold,
            'num_sequences': len(sequences)
        }
    
    def detect_anomalies(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalous sequences
        
        Args:
            events: Events to analyze
        
        Returns:
            List of anomaly detections
        """
        if self.threshold is None:
            raise ValueError("Model not trained. Call train() first.")
        
        self.model.eval()
        
        # Prepare sequences
        sequences = self.prepare_sequences(events)
        dataset = SequenceDataset(sequences, self.max_seq_len)
        loader = DataLoader(dataset, batch_size=32, shuffle=False)
        
        anomalies = []
        
        with torch.no_grad():
            batch_idx = 0
            for batch in loader:
                batch = batch.to(self.device)
                reconstruction = self.model(batch)
                
                # Calculate reconstruction error
                errors = torch.mean((reconstruction - batch) ** 2, dim=(1, 2))
                
                for i, error in enumerate(errors):
                    is_anomaly = error.item() > self.threshold
                    
                    if is_anomaly:
                        anomalies.append({
                            'sequence_idx': batch_idx + i,
                            'reconstruction_error': error.item(),
                            'threshold': self.threshold,
                            'anomaly_score': error.item() / self.threshold,
                            'is_anomaly': True
                        })
                
                batch_idx += len(errors)
        
        logger.info(f"Detected {len(anomalies)} anomalous sequences out of {len(sequences)}")
        
        return anomalies
    
    def save(self, model_path: Optional[Path] = None):
        """Save model to disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'threshold': float(self.threshold) if self.threshold is not None else None,
            'input_dim': self.input_dim,
            'hidden_dim': self.hidden_dim,
            'num_layers': self.num_layers,
            'max_seq_len': self.max_seq_len
        }, self.model_path)
        
        logger.info(f"LSTM autoencoder saved to {self.model_path}")
    
    def load(self, model_path: Optional[Path] = None):
        """Load model from disk"""
        if model_path is not None:
            self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.threshold = checkpoint['threshold']
        
        logger.info(f"LSTM autoencoder loaded from {self.model_path}")
