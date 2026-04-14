# ml/dqn_agent.py
"""
Deep Q-Network agent for adaptive mode selection.

Architecture:
    Input(5) → Dense(128) → ReLU → Dense(128) → ReLU → Dense(3)

Features:
    • Epsilon-greedy exploration with decay
    • Experience replay
    • Target network for stable learning
"""

from __future__ import annotations

import random
from typing import Optional

import numpy as np

from ml.replay_buffer import Experience, ReplayBuffer
from observability.logger import get_logger

logger = get_logger("dqn_agent")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
    class QNetwork(nn.Module):
        """Two-hidden-layer Q-value estimator."""

        def __init__(self, state_dim: int = 5, action_dim: int = 3) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(state_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 128),
                nn.ReLU(),
                nn.Linear(128, action_dim),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)


class DQNAgent:
    """Epsilon-greedy DQN agent with target network and replay buffer."""

    def __init__(
        self,
        state_dim: int = 5,
        action_dim: int = 3,
        lr: float = 1e-3,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        buffer_size: int = 10_000,
        batch_size: int = 64,
        target_update_freq: int = 50,
    ) -> None:
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for DQN agent")

        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.step_count = 0

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.q_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.buffer = ReplayBuffer(buffer_size)

    def select_action(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.q_net(s)
            return q_values.argmax(dim=1).item()

    def store(self, exp: Experience) -> None:
        self.buffer.push(exp)

    def train_step(self) -> Optional[float]:
        """One gradient step from a mini-batch. Returns loss or None."""
        if not self.buffer.is_ready(self.batch_size):
            return None

        batch = self.buffer.sample(self.batch_size)

        states = torch.FloatTensor(np.array([e.state for e in batch])).to(self.device)
        actions = torch.LongTensor([e.action for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in batch]).to(self.device)
        next_states = torch.FloatTensor(
            np.array([e.next_state for e in batch])
        ).to(self.device)
        dones = torch.FloatTensor([float(e.done) for e in batch]).to(self.device)

        # Current Q-values
        q_vals = self.q_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # Target Q-values
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            targets = rewards + self.gamma * next_q * (1.0 - dones)

        loss = self.loss_fn(q_vals, targets)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        # Epsilon decay
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        # Target network update
        self.step_count += 1
        if self.step_count % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())

        return loss.item()

    def save(self, path: str) -> None:
        torch.save(self.q_net.state_dict(), path)
        logger.info(f"DQN model saved to {path}")

    def load(self, path: str) -> None:
        self.q_net.load_state_dict(torch.load(path, map_location=self.device))
        self.target_net.load_state_dict(self.q_net.state_dict())
        logger.info(f"DQN model loaded from {path}")
