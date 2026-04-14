# ml/replay_buffer.py
"""Experience replay buffer for DQN training."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class Experience:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    """Fixed-size ring buffer of past experiences."""

    def __init__(self, capacity: int = 10_000) -> None:
        self._buffer: deque[Experience] = deque(maxlen=capacity)

    def push(self, exp: Experience) -> None:
        self._buffer.append(exp)

    def sample(self, batch_size: int) -> List[Experience]:
        return random.sample(list(self._buffer), min(batch_size, len(self._buffer)))

    def __len__(self) -> int:
        return len(self._buffer)

    def is_ready(self, batch_size: int) -> bool:
        return len(self._buffer) >= batch_size
