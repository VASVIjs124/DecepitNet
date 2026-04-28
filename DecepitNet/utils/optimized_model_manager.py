"""
Optimized ML Model Manager with Lazy Loading and Caching
Time Complexity: O(1) for cached model access, O(n) for initial load
Space Complexity: O(k) where k is number of active models (not all models loaded)
"""

import pickle
import threading
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from functools import lru_cache
import logging
from datetime import datetime, timezone
import hashlib

logger = logging.getLogger(__name__)


class LazyModelLoader:
    """
    Lazy model loader with LRU caching
    - Models loaded on-demand (saves memory)
    - Recently used models cached (saves time)
    - Thread-safe loading
    """
    
    def __init__(self, model_dir: str = "models", cache_size: int = 5):
        """
        Initialize lazy model loader
        
        Args:
            model_dir: Directory containing model files
            cache_size: Maximum number of models to keep in memory
        """
        self.model_dir = Path(model_dir)
        self.cache_size = cache_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._load_counts: Dict[str, int] = {}
        
    def load_model(self, model_name: str, loader_func: Optional[Callable[..., Any]] = None) -> Any:
        """
        Load model with LRU caching
        Time Complexity: O(1) cache hit, O(n) cache miss where n is model size
        Space Complexity: O(k) where k is cache_size
        
        Args:
            model_name: Name of the model to load
            loader_func: Optional custom loader function
            
        Returns:
            Loaded model
        """
        with self._lock:
            # Check cache first (O(1))
            if model_name in self._cache:
                self._access_times[model_name] = datetime.now(timezone.utc)
                logger.debug(f"Model '{model_name}' loaded from cache")
                return self._cache[model_name]
            
            # Evict least recently used if cache full (O(n) where n is cache size)
            if len(self._cache) >= self.cache_size:
                self._evict_lru()
            
            # Load model (O(n) where n is model file size)
            model = self._load_from_disk(model_name, loader_func)
            
            # Cache the model
            self._cache[model_name] = model
            self._access_times[model_name] = datetime.now(timezone.utc)
            self._load_counts[model_name] = self._load_counts.get(model_name, 0) + 1
            
            logger.info(f"Model '{model_name}' loaded and cached (load count: {self._load_counts[model_name]})")
            return model
    
    def _evict_lru(self) -> None:
        """
        Evict least recently used model from cache
        Time Complexity: O(n) where n is cache size
        """
        if not self._access_times:
            return
        
        # Find LRU model (O(n))
        lru_model = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        # Evict
        del self._cache[lru_model]
        del self._access_times[lru_model]
        logger.debug(f"Evicted model '{lru_model}' from cache")
    
    def _load_from_disk(self, model_name: str, loader_func: Optional[Callable[..., Any]] = None) -> Any:
        """
        Load model from disk
        Time Complexity: O(n) where n is file size
        """
        model_path = self.model_dir / f"{model_name}.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        if loader_func:
            return loader_func(model_path)
        
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    
    def clear_cache(self) -> None:
        """Clear all cached models"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            logger.info("Model cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "cached_models": [*self._cache],  # Unpacking keys() optimized
                "cache_size": len(self._cache),
                "max_cache_size": self.cache_size,
                "load_counts": self._load_counts.copy()
            }


class OptimizedModelManager:
    """
    Optimized model manager with lazy loading and efficient caching
    """
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Lazy loader with LRU cache (max 5 models in memory)
        self.loader = LazyModelLoader(model_dir=str(self.model_dir), cache_size=5)
        
        # Model metadata cache (lightweight, always in memory)
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._metadata_lock = threading.Lock()
    
    @lru_cache(maxsize=128)
    def _get_model_hash(self, model_path: str) -> str:
        """
        Get model file hash for cache invalidation
        Time Complexity: O(n) where n is file size (cached after first call)
        """
        with open(model_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def get_model(self, model_name: str, lazy: bool = True) -> Any:
        """
        Get model with lazy loading option
        
        Args:
            model_name: Name of the model
            lazy: If True, use lazy loading. If False, load immediately
            
        Returns:
            Model object
        """
        if lazy:
            return self.loader.load_model(model_name)
        else:
            # Force load without caching
            return self.loader._load_from_disk(model_name)
    
    def preload_models(self, model_names: list[str]) -> None:
        """
        Preload specific models into cache
        Useful for frequently used models
        
        Time Complexity: O(n*m) where n is number of models, m is avg model size
        """
        for model_name in model_names:
            try:
                self.loader.load_model(model_name)
                logger.info(f"Preloaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to preload model {model_name}: {e}")
    
    def get_metadata(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get model metadata (lightweight, always cached)
        Time Complexity: O(1) for cached, O(n) for first access
        
        Args:
            model_name: Name of the model
            
        Returns:
            Model metadata dictionary
        """
        with self._metadata_lock:
            if model_name in self._metadata_cache:
                return self._metadata_cache[model_name]
            
            # Load metadata from file
            metadata_path = self.model_dir / f"{model_name}_metadata.json"
            if metadata_path.exists():
                import json
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    self._metadata_cache[model_name] = metadata
                    return metadata
            
            return None
    
    def save_model(self, model: Any, model_name: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Save model to disk with optional metadata
        
        Args:
            model: Model object to save
            model_name: Name for the model
            metadata: Optional metadata dictionary
        """
        model_path = self.model_dir / f"{model_name}.pkl"
        
        # Save model
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        if metadata:
            import json
            metadata_path = self.model_dir / f"{model_name}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update metadata cache
            with self._metadata_lock:
                self._metadata_cache[model_name] = metadata
        
        logger.info(f"Saved model: {model_name}")
    
    def list_available_models(self) -> list[str]:
        """
        List all available models
        Time Complexity: O(n) where n is number of files in directory
        """
        model_files = self.model_dir.glob("*.pkl")
        return [f.stem for f in model_files]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return {
            "model_cache": self.loader.get_cache_stats(),
            "metadata_cache_size": len(self._metadata_cache),
            "available_models": len(self.list_available_models())
        }
    
    def optimize_memory(self) -> None:
        """
        Free up memory by clearing caches
        Call this when memory usage is high
        """
        self.loader.clear_cache()
        with self._metadata_lock:
            self._metadata_cache.clear()
        logger.info("Memory optimization: caches cleared")


# Singleton instance
_model_manager: Optional[OptimizedModelManager] = None
_manager_lock = threading.Lock()


def get_model_manager() -> OptimizedModelManager:
    """
    Get singleton model manager instance
    Thread-safe lazy initialization
    """
    global _model_manager
    
    if _model_manager is None:
        with _manager_lock:
            if _model_manager is None:  # Double-checked locking
                _model_manager = OptimizedModelManager()
    
    return _model_manager
