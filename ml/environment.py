# ml/environment.py
"""
RL environment for edge-cloud decision-making.

State:  [cpu_load, gpu_flag, latency_norm, battery_norm, task_size_norm]
Action: 0=LOCAL, 1=CLOUD, 2=SPLIT
Reward: R = -(α·latency + β·cost + γ·energy)
"""

from __future__ import annotations

import random
from typing import Tuple

import numpy as np


class EdgeCloudEnv:
    """Gym-like environment (no gym dependency)."""

    NUM_ACTIONS = 3  # LOCAL, CLOUD, SPLIT
    STATE_DIM = 5

    ACTION_NAMES = {0: "LOCAL", 1: "CLOUD", 2: "SPLIT"}

    # Reward weights
    ALPHA = 0.4   # latency weight
    BETA = 0.3    # cost weight
    GAMMA = 0.3   # energy weight

    def __init__(self) -> None:
        self.state = self.reset()

    def reset(self) -> np.ndarray:
        """Generate a random initial state."""
        self.state = np.array([
            random.uniform(0.0, 1.0),   # cpu_load
            float(random.choice([0, 1])),  # gpu_flag
            random.uniform(0.0, 1.0),   # latency_norm
            random.uniform(0.0, 1.0),   # battery_norm
            random.uniform(0.0, 1.0),   # task_size_norm
        ], dtype=np.float32)
        return self.state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """
        Execute an action and return (next_state, reward, done).

        Uses a simplified simulator:
        - LOCAL: low cost, medium latency (depends on cpu_load)
        - CLOUD: higher cost, latency depends on network
        - SPLIT: moderate cost and latency
        """
        cpu_load, gpu_flag, latency_norm, battery_norm, task_size = self.state

        if action == 0:  # LOCAL
            latency = 0.3 + cpu_load * 0.5 + task_size * 0.4
            cost = 0.0
            energy = (0.5 + cpu_load * 0.5) * (1.0 - battery_norm * 0.3)
        elif action == 1:  # CLOUD
            latency = 0.2 + latency_norm * 0.6 + task_size * 0.2
            cost = 0.3 + task_size * 0.5
            energy = 0.1 + latency_norm * 0.2
        else:  # SPLIT
            latency = 0.25 + latency_norm * 0.3 + task_size * 0.3
            cost = 0.15 + task_size * 0.25
            energy = 0.3 + cpu_load * 0.2

        # Penalty for LOCAL when battery is low
        if action == 0 and battery_norm < 0.3:
            energy += 0.5

        reward = -(self.ALPHA * latency + self.BETA * cost + self.GAMMA * energy)

        # Episode is single-step (each task is independent)
        done = True
        next_state = self.reset()
        return next_state, reward, done
