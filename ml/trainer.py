# ml/trainer.py
"""
DQN training loop with logging and checkpointing.

Usage:
    python -m ml.trainer --episodes 1000
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from ml.dqn_agent import DQNAgent
from ml.environment import EdgeCloudEnv
from ml.replay_buffer import Experience
from observability.logger import get_logger

logger = get_logger("dqn_trainer")


def train(
    episodes: int = 1000,
    log_interval: int = 100,
    save_path: str = "checkpoints/dqn_model.pt",
) -> dict:
    """Run the training loop and return final stats."""
    env = EdgeCloudEnv()
    agent = DQNAgent()

    rewards_history: list[float] = []
    losses_history: list[float] = []

    for ep in range(1, episodes + 1):
        state = env.reset()
        action = agent.select_action(state)
        next_state, reward, done = env.step(action)

        agent.store(Experience(state, action, reward, next_state, done))
        loss = agent.train_step()

        rewards_history.append(reward)
        if loss is not None:
            losses_history.append(loss)

        if ep % log_interval == 0:
            avg_r = np.mean(rewards_history[-log_interval:])
            avg_l = np.mean(losses_history[-log_interval:]) if losses_history else 0
            logger.info(
                f"Episode {ep}/{episodes}: "
                f"avg_reward={avg_r:.4f}, avg_loss={avg_l:.6f}, "
                f"epsilon={agent.epsilon:.4f}"
            )

    # Save final model
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    agent.save(save_path)

    stats = {
        "episodes": episodes,
        "final_epsilon": round(agent.epsilon, 4),
        "avg_reward_last100": round(float(np.mean(rewards_history[-100:])), 4),
        "avg_loss_last100": round(
            float(np.mean(losses_history[-100:])) if losses_history else 0, 6
        ),
        "model_path": save_path,
    }
    logger.info(f"Training complete: {stats}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DQN agent")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--save-path", type=str, default="checkpoints/dqn_model.pt")
    args = parser.parse_args()
    train(episodes=args.episodes, save_path=args.save_path)
