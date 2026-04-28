"""
Reinforcement Learning Agents
Dual RL system: Attacker simulation agents + Deception policymaker
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import pickle

# Stable-Baselines3
from stable_baselines3 import PPO, SAC
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback

logger = logging.getLogger(__name__)


class HoneypotEnvironment(gym.Env):
    """
    Gymnasium Environment for Honeypot Deception
    Agent learns optimal deception strategies
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super(HoneypotEnvironment, self).__init__()
        
        self.config = config or {}
        
        # State space: [threat_level, activity_count, unique_ips, avg_threat_score,
        #               failed_auth_rate, port_scan_detected, lateral_movement_detected,
        #               current_decoy_count, current_credential_count, response_delay]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
            high=np.array([100, 1000, 100, 100, 1, 1, 1, 50, 50, 1000]),
            dtype=np.float32
        )
        
        # Action space: [decoy_density (0-2), credential_count (0-2),
        #                response_delay (0-2), adaptation_aggressiveness (0-2)]
        # 0=low, 1=medium, 2=high
        self.action_space = spaces.MultiDiscrete([3, 3, 3, 3])
        
        self.state = None
        self.steps = 0
        self.max_steps = 1000
        self.engagement_history = []
        
    def reset(self, seed=None, options=None):
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        # Initial state: low threat, minimal activity
        self.state = np.array([
            10.0,  # threat_level
            0.0,   # activity_count
            0.0,   # unique_ips
            5.0,   # avg_threat_score
            0.0,   # failed_auth_rate
            0.0,   # port_scan_detected
            0.0,   # lateral_movement_detected
            5.0,   # current_decoy_count
            3.0,   # current_credential_count
            0.0    # response_delay
        ], dtype=np.float32)
        
        self.steps = 0
        self.engagement_history = []
        
        return self.state, {}
    
    def step(self, action):
        """
        Execute action and return new state, reward, done, info
        
        Action: [decoy_density, credential_count, response_delay, aggressiveness]
        """
        # Parse action
        decoy_density = action[0]  # 0=low, 1=med, 2=high
        cred_count = action[1]
        response_delay = action[2]
        aggressiveness = action[3]
        
        # Apply action to state
        self.state[7] = 5 + decoy_density * 15  # decoy_count: 5, 20, 35
        self.state[8] = 3 + cred_count * 7      # credential_count: 3, 10, 17
        self.state[9] = response_delay * 300     # response_delay: 0, 300, 600ms
        
        # Simulate attacker interaction (would be real telemetry in production)
        engagement_score = self._simulate_attacker_engagement(action)
        
        # Calculate reward
        reward = self._calculate_reward(engagement_score, action)
        
        # Update state based on simulated interaction
        self.state = self._update_state(self.state, engagement_score)
        
        self.steps += 1
        self.engagement_history.append(engagement_score)
        
        # Episode done conditions
        done = self.steps >= self.max_steps
        truncated = False
        
        info = {
            'engagement_score': engagement_score,
            'avg_engagement': np.mean(self.engagement_history),
            'steps': self.steps
        }
        
        return self.state, reward, done, truncated, info
    
    def _simulate_attacker_engagement(self, action) -> float:
        """
        Simulate attacker engagement based on deception configuration
        In production, this would use actual honeypot telemetry
        """
        decoy_density = action[0]
        cred_count = action[1]
        response_delay = action[2]
        
        # Base engagement
        engagement = 10.0
        
        # Higher decoy density increases engagement
        engagement += decoy_density * 15
        
        # More credentials increases brute force attempts
        engagement += cred_count * 10
        
        # Moderate delay can increase realism, too high decreases engagement
        if response_delay == 1:
            engagement += 5
        elif response_delay == 2:
            engagement -= 10
        
        # Add randomness
        engagement += np.random.normal(0, 5)
        
        return max(0, engagement)
    
    def _calculate_reward(self, engagement_score: float, action) -> float:
        """
        Calculate reward for the action
        Reward = engagement_score - cost_penalty
        """
        # Higher engagement = higher reward
        reward = engagement_score * 0.5
        
        # Penalty for high resource usage
        decoy_density = action[0]
        cred_count = action[1]
        
        cost_penalty = (decoy_density + cred_count) * 2
        reward -= cost_penalty
        
        # Bonus for detecting advanced techniques
        if self.state[6] > 0.5:  # lateral_movement_detected
            reward += 20
        
        return reward
    
    def _update_state(self, state, engagement_score: float):
        """Update state based on engagement"""
        new_state = state.copy()
        
        # Increase activity count
        new_state[1] += engagement_score / 10
        
        # Randomly update threat indicators
        new_state[0] = min(100, new_state[0] + np.random.uniform(-5, 10))
        new_state[2] = min(100, new_state[2] + np.random.poisson(1))
        new_state[3] = np.clip(new_state[3] + np.random.normal(0, 5), 0, 100)
        
        # Randomly detect attacks
        if np.random.random() < 0.1:
            new_state[5] = 1.0  # port_scan_detected
        if np.random.random() < 0.05:
            new_state[6] = 1.0  # lateral_movement_detected
        
        return new_state.astype(np.float32)


class AttackerSimEnvironment(gym.Env):
    """
    Environment for training attacker simulation agents
    Agent learns to test honeypot defenses
    """
    
    def __init__(self):
        super(AttackerSimEnvironment, self).__init__()
        
        # State: [honeypot_response_time, decoy_density, credential_success_rate,
        #         detected_flag, command_success_rate]
        self.observation_space = spaces.Box(
            low=np.array([0, 0, 0, 0, 0]),
            high=np.array([2000, 50, 1, 1, 1]),
            dtype=np.float32
        )
        
        # Action: [attack_technique, intensity, stealth_level]
        # Techniques: 0=scan, 1=brute_force, 2=exploit, 3=lateral_move
        # Intensity: 0=low, 1=med, 2=high
        # Stealth: 0=noisy, 1=moderate, 2=stealthy
        self.action_space = spaces.MultiDiscrete([4, 3, 3])
        
        self.state = None
        self.steps = 0
        self.max_steps = 500
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        self.state = np.array([
            100.0,  # response_time
            10.0,   # decoy_density
            0.0,    # credential_success_rate
            0.0,    # detected_flag
            0.1     # command_success_rate
        ], dtype=np.float32)
        
        self.steps = 0
        return self.state, {}
    
    def step(self, action):
        technique = action[0]
        intensity = action[1]
        stealth = action[2]
        
        # Simulate attack success
        success_rate = self._simulate_attack(technique, intensity, stealth)
        
        # Calculate reward
        reward = success_rate * 10
        
        # Penalty for detection
        if self.state[3] > 0.5:
            reward -= 20
        
        # Penalty for low stealth
        reward -= (2 - stealth) * 5
        
        # Update state
        self.state[2] = success_rate
        self.state[3] = 1.0 if (intensity > stealth) else 0.0
        self.state[4] = min(1.0, self.state[4] + success_rate * 0.1)
        
        self.steps += 1
        done = self.steps >= self.max_steps
        truncated = False
        
        info = {'technique': technique, 'detected': bool(self.state[3])}
        
        return self.state, reward, done, truncated, info
    
    def _simulate_attack(self, technique: int, intensity: int, stealth: int) -> float:
        """Simulate attack success rate"""
        base_success = 0.1
        
        # Different techniques have different success rates
        technique_multiplier = [0.8, 0.6, 0.4, 0.3][technique]
        intensity_multiplier = 1 + intensity * 0.3
        stealth_multiplier = 1 + stealth * 0.2
        
        success = base_success * technique_multiplier * intensity_multiplier * stealth_multiplier
        success += np.random.normal(0, 0.1)
        
        return np.clip(success, 0, 1)


class RLDeceptionAgent:
    """
    Deception Policymaker using PPO/SAC
    Learns optimal honeypot configurations
    """
    
    def __init__(
        self,
        algorithm: str = "PPO",
        model_path: Optional[Path] = None
    ):
        self.algorithm = algorithm
        self.model_path = model_path or Path(f"models/rl_deception_{algorithm.lower()}.zip")
        self.env = None
        self.model = None
        
        logger.info(f"Initialized RLDeceptionAgent with {algorithm}")
    
    def create_environment(self):
        """Create and wrap environment"""
        env = HoneypotEnvironment()
        self.env = DummyVecEnv([lambda: env])
        return self.env
    
    def train(
        self,
        total_timesteps: int = 100000,
        learning_rate: float = 0.0003
    ) -> Dict[str, Any]:
        """
        Train RL agent
        
        Args:
            total_timesteps: Training timesteps
            learning_rate: Learning rate
        
        Returns:
            Training metrics
        """
        logger.info(f"Training {self.algorithm} agent for {total_timesteps} timesteps...")
        
        if self.env is None:
            self.create_environment()
        
        # Initialize model
        if self.algorithm == "PPO":
            self.model = PPO(
                "MlpPolicy",
                self.env,
                learning_rate=learning_rate,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                verbose=1,
                tensorboard_log="./logs/rl_deception_ppo/"
            )
        elif self.algorithm == "SAC":
            self.model = SAC(
                "MlpPolicy",
                self.env,
                learning_rate=learning_rate,
                buffer_size=100000,
                batch_size=256,
                gamma=0.99,
                tau=0.005,
                verbose=1,
                tensorboard_log="./logs/rl_deception_sac/"
            )
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        
        # Train
        self.model.learn(total_timesteps=total_timesteps)
        
        # Save
        self.save()
        
        logger.info(f"{self.algorithm} training complete")
        
        return {
            'algorithm': self.algorithm,
            'total_timesteps': total_timesteps,
            'model_path': str(self.model_path)
        }
    
    def predict_action(self, state: np.ndarray) -> Tuple[np.ndarray, Any]:
        """Predict best action for given state"""
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        action, _states = self.model.predict(state, deterministic=True)
        return action, _states
    
    def get_adaptive_configuration(
        self,
        current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get adaptive honeypot configuration using RL policy
        
        Args:
            current_state: Current honeypot state
        
        Returns:
            Recommended configuration
        """
        # Convert state dict to observation vector
        obs = np.array([
            current_state.get('threat_level', 10),
            current_state.get('activity_count', 0),
            current_state.get('unique_ips', 0),
            current_state.get('avg_threat_score', 5),
            current_state.get('failed_auth_rate', 0),
            current_state.get('port_scan_detected', 0),
            current_state.get('lateral_movement_detected', 0),
            current_state.get('current_decoy_count', 5),
            current_state.get('current_credential_count', 3),
            current_state.get('response_delay', 0)
        ], dtype=np.float32)
        
        # Get action
        action, _ = self.predict_action(obs)
        
        # Convert action to configuration
        decoy_levels = ['low', 'medium', 'high']
        cred_counts = [3, 10, 17]
        delays = [0, 300, 600]
        
        config = {
            'decoy_density': decoy_levels[action[0]],
            'decoy_count': 5 + action[0] * 15,
            'credential_count': cred_counts[action[1]],
            'response_delay_ms': delays[action[2]],
            'adaptation_aggressiveness': decoy_levels[action[3]]
        }
        
        return config
    
    def save(self):
        """Save model to disk"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(self.model_path)
        logger.info(f"RL model saved to {self.model_path}")
    
    def load(self):
        """Load model from disk"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        if self.algorithm == "PPO":
            self.model = PPO.load(self.model_path)
        elif self.algorithm == "SAC":
            self.model = SAC.load(self.model_path)
        
        logger.info(f"RL model loaded from {self.model_path}")


class AttackerSimulationAgent:
    """
    Attacker simulation agent using PPO
    Tests honeypot defenses
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or Path("models/rl_attacker_ppo.zip")
        self.env = None
        self.model = None
    
    def create_environment(self):
        """Create attacker simulation environment"""
        env = AttackerSimEnvironment()
        self.env = DummyVecEnv([lambda: env])
        return self.env
    
    def train(self, total_timesteps: int = 50000) -> Dict[str, Any]:
        """Train attacker simulation agent"""
        logger.info(f"Training attacker simulation agent for {total_timesteps} timesteps...")
        
        if self.env is None:
            self.create_environment()
        
        self.model = PPO(
            "MlpPolicy",
            self.env,
            learning_rate=0.0003,
            n_steps=1024,
            batch_size=64,
            verbose=1,
            tensorboard_log="./logs/rl_attacker/"
        )
        
        self.model.learn(total_timesteps=total_timesteps)
        self.save()
        
        logger.info("Attacker simulation training complete")
        
        return {'total_timesteps': total_timesteps}
    
    def simulate_attack(
        self,
        honeypot_config: Dict[str, Any],
        num_steps: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Simulate attack on honeypot configuration
        
        Args:
            honeypot_config: Honeypot configuration
            num_steps: Number of attack steps
        
        Returns:
            List of attack actions and results
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")
        
        obs, _ = self.env.reset()
        attack_log = []
        
        for step in range(num_steps):
            action, _ = self.model.predict(obs, deterministic=False)
            obs, reward, done, truncated, info = self.env.step(action)
            
            attack_log.append({
                'step': step,
                'technique': int(action[0][0]),
                'intensity': int(action[0][1]),
                'stealth': int(action[0][2]),
                'reward': float(reward[0]),
                'detected': info[0].get('detected', False)
            })
            
            if done[0]:
                break
        
        return attack_log
    
    def save(self):
        """Save model"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(self.model_path)
        logger.info(f"Attacker model saved to {self.model_path}")
    
    def load(self):
        """Load model"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        self.model = PPO.load(self.model_path)
        logger.info(f"Attacker model loaded from {self.model_path}")
