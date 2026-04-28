"""
XAI Explainability Module
SHAP and LIME integration for model interpretability
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
import shap
from lime import lime_tabular
import matplotlib.pyplot as plt
import io
import base64

logger = logging.getLogger(__name__)


class XAIExplainer:
    """
    Model explainability using SHAP and LIME
    Provides interpretable explanations for ML predictions
    """
    
    def __init__(self, model, feature_names: List[str], model_type: str = 'xgboost'):
        self.model = model
        self.feature_names = feature_names
        self.model_type = model_type
        self.shap_explainer = None
        self.lime_explainer = None
        
        # Initialize explainers
        self._initialize_explainers()
    
    def _initialize_explainers(self):
        """Initialize SHAP and LIME explainers"""
        try:
            if self.model_type == 'xgboost':
                # SHAP TreeExplainer for XGBoost
                self.shap_explainer = shap.TreeExplainer(self.model)
                logger.info("Initialized SHAP TreeExplainer for XGBoost")
            elif self.model_type == 'neural_network':
                # SHAP DeepExplainer for neural networks
                logger.info("Neural network explainer not yet initialized (requires background data)")
            
        except Exception as e:
            logger.warning(f"Failed to initialize SHAP explainer: {e}")
    
    def initialize_lime(self, training_data: np.ndarray, class_names: List[str]):
        """
        Initialize LIME explainer
        
        Args:
            training_data: Training dataset for LIME background
            class_names: List of class names
        """
        try:
            if training_data is None or len(training_data) == 0:
                raise ValueError("Training data is required to initialize LIME")

            self.lime_explainer = lime_tabular.LimeTabularExplainer(
                training_data=training_data,
                feature_names=self.feature_names,
                class_names=class_names,
                mode='classification',
                discretize_continuous=True
            )
            logger.info("Initialized LIME explainer")
        except Exception as e:
            logger.error(f"Failed to initialize LIME explainer: {e}")

    @staticmethod
    def _to_2d_array(X: np.ndarray) -> np.ndarray:
        """Normalize incoming feature data into a 2D numpy array."""
        X_arr = np.asarray(X)
        if X_arr.size == 0:
            raise ValueError("Input feature array is empty")
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(1, -1)
        if X_arr.ndim != 2:
            raise ValueError("Input feature array must be 1D or 2D")
        return X_arr

    @staticmethod
    def _to_serializable(value: Any) -> Any:
        """Convert numpy and pandas scalar types into JSON-serializable values."""
        if isinstance(value, (np.floating, np.integer)):
            return value.item()
        return value

    def _resolve_feature_names(self, feature_count: int) -> List[str]:
        """Ensure feature names always match feature dimensionality."""
        if feature_count <= 0:
            return []
        if len(self.feature_names) == feature_count:
            return self.feature_names
        if len(self.feature_names) > feature_count:
            return self.feature_names[:feature_count]
        missing = [f"feature_{idx}" for idx in range(len(self.feature_names), feature_count)]
        return [*self.feature_names, *missing]
    
    def explain_prediction_shap(
        self,
        X: np.ndarray,
        max_display: int = 10
    ) -> Dict[str, Any]:
        """
        Generate SHAP explanation for predictions
        
        Args:
            X: Feature matrix (samples to explain)
            max_display: Maximum features to display
        
        Returns:
            Explanation dictionary with feature importance
        """
        if self.shap_explainer is None:
            return {'error': 'SHAP explainer not initialized'}
        
        try:
            X = self._to_2d_array(X)

            # Calculate SHAP values
            shap_values = self.shap_explainer.shap_values(X)
            
            # Handle multi-class output and different SHAP return shapes.
            if isinstance(shap_values, list):
                shap_values_class = np.asarray(shap_values[0], dtype=float)
            else:
                shap_values_class = np.asarray(shap_values, dtype=float)
                if shap_values_class.ndim == 3:
                    # shape can be [samples, features, classes]
                    shap_values_class = shap_values_class[:, :, 0]
                elif shap_values_class.ndim > 3:
                    raise ValueError(f"Unsupported SHAP tensor shape: {shap_values_class.shape}")
            
            # Get feature importance
            feature_importance = np.abs(shap_values_class).mean(axis=0)
            
            feature_labels = self._resolve_feature_names(len(feature_importance))
            # Sort features by importance
            importance_dict = dict(zip(feature_labels, feature_importance.tolist()))
            sorted_features = sorted(
                importance_dict.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_display]
            
            # Generate summary plot
            summary_plot_b64 = self._generate_shap_summary_plot(shap_values_class, X)
            
            return {
                'method': 'SHAP',
                'feature_importance': {k: float(v) for k, v in sorted_features},
                'summary_plot': summary_plot_b64,
                'shap_values_shape': list(shap_values_class.shape)
            }
            
        except Exception as e:
            logger.error(f"SHAP explanation failed: {e}")
            return {'error': str(e)}
    
    def _generate_shap_summary_plot(
        self,
        shap_values: np.ndarray,
        X: np.ndarray
    ) -> str:
        """Generate SHAP summary plot and return as base64 string"""
        try:
            plt.figure(figsize=(10, 6))
            feature_labels = self._resolve_feature_names(X.shape[1] if X.ndim == 2 else 0)
            shap.summary_plot(
                shap_values, X,
                feature_names=feature_labels,
                show=False,
                max_display=15
            )
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_b64 = base64.b64encode(buffer.read()).decode()
            plt.close()
            
            return image_b64
            
        except Exception as e:
            logger.warning(f"Failed to generate SHAP plot: {e}")
            return ""
    
    def explain_instance_lime(
        self,
        instance: np.ndarray,
        num_features: int = 10
    ) -> Dict[str, Any]:
        """
        Generate LIME explanation for a single instance
        
        Args:
            instance: Single instance to explain (1D array)
            num_features: Number of features to include in explanation
        
        Returns:
            LIME explanation dictionary
        """
        if self.lime_explainer is None:
            return {'error': 'LIME explainer not initialized. Call initialize_lime() first.'}
        
        try:
            instance = np.asarray(instance)
            if instance.ndim != 1:
                instance = instance.reshape(-1)

            if not hasattr(self.model, 'predict_proba'):
                return {'error': 'Model does not expose predict_proba() required by LIME'}

            # Generate explanation
            explanation = self.lime_explainer.explain_instance(
                instance,
                self.model.predict_proba,
                num_features=num_features
            )
            
            # Extract feature contributions
            feature_contributions = {
                str(k): float(v)
                for k, v in explanation.as_list()
            }
            
            # Get predicted class
            if hasattr(self.model, 'predict'):
                predicted_class = self.model.predict([instance])[0]
            else:
                predicted_class = 'unknown'
            
            # Get prediction probabilities
            proba = self.model.predict_proba([instance])[0]

            intercept = 0
            if hasattr(explanation, 'intercept') and explanation.intercept:
                intercept = explanation.intercept[1] if len(explanation.intercept) > 1 else explanation.intercept[0]
            
            return {
                'method': 'LIME',
                'predicted_class': self._to_serializable(predicted_class),
                'prediction_probabilities': proba.tolist(),
                'feature_contributions': feature_contributions,
                'intercept': float(intercept)
            }
            
        except Exception as e:
            logger.error(f"LIME explanation failed: {e}")
            return {'error': str(e)}
    
    def generate_global_explanation(
        self,
        X: np.ndarray,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """
        Generate global model explanation using SHAP
        
        Args:
            X: Feature matrix (full dataset or sample)
            sample_size: Number of samples to use for explanation
        
        Returns:
            Global explanation with feature importance ranking
        """
        if self.shap_explainer is None:
            return {'error': 'SHAP explainer not initialized'}
        
        try:
            X = self._to_2d_array(X)

            # Sample data if too large
            if len(X) > sample_size:
                indices = np.random.choice(len(X), sample_size, replace=False)
                X_sample = X[indices]
            else:
                X_sample = X
            
            # Calculate SHAP values
            shap_values = self.shap_explainer.shap_values(X_sample)
            
            # Handle multi-class
            if isinstance(shap_values, list):
                shap_values_combined = np.abs(np.array(shap_values)).mean(axis=0)
            else:
                shap_values_combined = np.abs(shap_values)
                if np.asarray(shap_values_combined).ndim == 3:
                    shap_values_combined = np.abs(np.asarray(shap_values_combined)).mean(axis=2)
            
            # Global feature importance
            global_importance = shap_values_combined.mean(axis=0)
            
            # Rank features
            feature_labels = self._resolve_feature_names(len(global_importance))
            feature_ranking = sorted(
                zip(feature_labels, global_importance),
                key=lambda x: x[1],
                reverse=True
            )
            
            return {
                'method': 'SHAP_Global',
                'feature_ranking': [
                    {'feature': f, 'importance': float(imp)}
                    for f, imp in feature_ranking
                ],
                'top_features': [f for f, _ in feature_ranking[:10]],
                'sample_size': len(X_sample)
            }
            
        except Exception as e:
            logger.error(f"Global explanation failed: {e}")
            return {'error': str(e)}
    
    def explain_attack_prediction(
        self,
        event: Dict[str, Any],
        feature_vector: np.ndarray,
        prediction: str,
        prediction_proba: np.ndarray
    ) -> Dict[str, Any]:
        """
        Comprehensive explanation for an attack prediction
        
        Args:
            event: Original event dictionary
            feature_vector: Extracted features
            prediction: Predicted attack category
            prediction_proba: Prediction probabilities
        
        Returns:
            Comprehensive explanation
        """
        explanation = {
            'event_summary': {
                'source_ip': event.get('source_ip'),
                'protocol': event.get('protocol'),
                'timestamp': event.get('timestamp'),
                'payload_preview': event.get('payload', '')[:100]
            },
            'prediction': {
                'category': prediction,
                'confidence': float(max(prediction_proba)),
                'all_probabilities': prediction_proba.tolist()
            }
        }
        
        # Add SHAP explanation
        if self.shap_explainer:
            shap_exp = self.explain_prediction_shap(feature_vector.reshape(1, -1))
            explanation['shap_explanation'] = shap_exp
        
        # Add LIME explanation
        if self.lime_explainer:
            lime_exp = self.explain_instance_lime(feature_vector)
            explanation['lime_explanation'] = lime_exp

        if 'lime_explanation' not in explanation:
            explanation['lime_explanation'] = {
                'error': 'LIME not initialized'
            }
        
        return explanation
    
    def generate_dashboard_insights(
        self,
        recent_predictions: List[Dict[str, Any]],
        X: np.ndarray
    ) -> Dict[str, Any]:
        """
        Generate insights for SOC dashboard
        
        Args:
            recent_predictions: Recent prediction results
            X: Feature matrix for recent predictions
        
        Returns:
            Dashboard-ready insights
        """
        insights = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'total_predictions': len(recent_predictions)
        }
        
        # Calculate prediction distribution
        prediction_counts = {}
        for pred in recent_predictions:
            category = pred.get('category', 'unknown')
            prediction_counts[category] = prediction_counts.get(category, 0) + 1
        
        insights['prediction_distribution'] = prediction_counts
        
        # Get global feature importance
        global_exp = self.generate_global_explanation(X)
        if 'feature_ranking' in global_exp:
            insights['top_influential_features'] = global_exp['feature_ranking'][:5]
        
        # Identify high-confidence predictions
        high_confidence = [
            p for p in recent_predictions
            if p.get('confidence', 0) > 0.85
        ]
        insights['high_confidence_count'] = len(high_confidence)
        insights['high_confidence_ratio'] = len(high_confidence) / len(recent_predictions) if recent_predictions else 0
        
        return insights
