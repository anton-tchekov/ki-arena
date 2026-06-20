from collections import defaultdict       # ← was missing
from agents.base import BaseAgent
from environment.actions import Action
import numpy as np
import pickle
from pathlib import Path

class RLAgent(BaseAgent):
    """
    Tabular Q-learning agent.

    discretize_bins: one int per obs dimension — how coarsely to bucket each value.
                     Must match the length of the observation your env returns.

    Default matches obs = [pos_x, pos_y, dx_tree, dy_tree, total_fruit, wood, fruit]
    where dx_tree and dy_tree are extracted from the trees array in the observation.

    Note:
        bin=1  → sign only (-1/0/+1), good for direction values like dx, dy
        bin=3  → bucket by 3s, good for position on a small grid
        bin=10 → bucket by 10s, good for counts like total_fruit

        current obs: [x, y, dx_tree, dy_tree, total_fruit, wood, fruit]
        RLAgent("collector_0")  # uses DEFAULT_BINS, no changes needed

        if obs changes to e.g. [pos_x, pos_y, dx_fruit, dy_fruit, n_trees]
        RLAgent("collector_0", discretize_bins=(3, 3, 1, 1, 5))
    """

    DEFAULT_BINS = (3, 3, 1, 1, 10, 20, 20)  # pos_x, pos_y, dx, dy, total_fruit, wood, fruit

    def __init__(
        self,
        name: str,
        discretize_bins: tuple|None = None,
        epsilon: float = 0.3,
        learning_rate: float = 0.1,
        gamma: float = 0.99,
    ):
        super().__init__(name)
        self.bins = discretize_bins or self.DEFAULT_BINS
        self.epsilon = epsilon
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.action_space = list(Action)
        self.q_table = defaultdict(lambda: np.zeros(len(self.action_space), dtype=np.float32))
        self.transitions = []
        self.training = True

    def _obs_dict_to_list(self, obs_dict) -> list:
        """
        Convert dictionary observation to list format for discretization.
        Extracts nearest tree information from trees array.
        Returns: [x, y, dx_tree, dy_tree, total_fruit, wood, fruit]
        """
        x = obs_dict['x']
        y = obs_dict['y']
        trees = obs_dict['trees']
        total_fruit = obs_dict['total_fruit']
        wood_count = obs_dict['wood_count']
        fruit_count = obs_dict['fruit_count']

        # Find nearest tree (trees are keyed (x, y), same as agent positions)
        if trees:
            tx, ty = min(
                trees.keys(),
                key=lambda t: abs(t[0] - x) + abs(t[1] - y)
            )
            dx = tx - x
            dy = ty - y
        else:
            dx, dy = 0, 0

        return [x, y, dx, dy, total_fruit, wood_count, fruit_count]

    def discretize(self, obs) -> tuple:
        """
        Bucket each obs dimension by its corresponding bin size.
        Direction-like values (bin=1) become sign only: -1 / 0 / +1.
        """
        assert len(obs) == len(self.bins), (
            f"Obs length {len(obs)} doesn't match bins length {len(self.bins)}. "
            f"Pass discretize_bins=(...) with one entry per obs dimension."
        )
        state = []
        for val, bin_size in zip(obs, self.bins):
            if bin_size == 1:
                state.append(int(np.sign(val)))   # -1 / 0 / +1
            else:
                state.append(int(val) // bin_size)
        return tuple(state)

    def act(self, obs, info) -> Action:
        # Convert dictionary observation to list format for discretization
        obs_list = self._obs_dict_to_list(obs)
        state = self.discretize(obs_list)
        if self.training and np.random.rand() < self.epsilon:
            return self.action_space[np.random.randint(len(self.action_space))]
        return self.action_space[int(np.argmax(self.q_table[state]))]

    def after_action(self, obs, action, reward, next_obs, done, info):
        if action is None:
            return
        s  = self.discretize(self._obs_dict_to_list(obs))
        s_ = self.discretize(self._obs_dict_to_list(next_obs)) if next_obs is not None else None
        self.transitions.append((s, action, reward, s_, done))

    def train_step(self):
        if not self.training or not self.transitions:
            return
        for state, action, reward, next_state, done in self.transitions:
            idx = self.action_space.index(action)
            td_target = reward
            if next_state is not None and not done:
                td_target += self.gamma * np.max(self.q_table[next_state])
            self.q_table[state][idx] += self.learning_rate * (
                td_target - self.q_table[state][idx]
            )
        self.transitions.clear()
        self.epsilon = max(0.01, self.epsilon * 0.995)

    def observe(self, obs, reward, done, info):
        pass

    def on_episode_end(self):
        # intentionally a no-op for RLAgent:
        # transitions must survive until TrainingPhase calls train_step()
        pass

    def on_training_end(self):
        self.training = False
        self.epsilon = 0.0                 # pure exploitation from now on

    def save(self, path: str|Path|None = None):
        """Save Q-table and training state to disk."""
        path = Path(path or f"models/{self.name}_qtable.pkl")
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "q_table": dict(self.q_table),   # convert defaultdict → plain dict for safety
            "epsilon": self.epsilon,
            "training": self.training,
        }
        with open(path, "wb") as f:
            pickle.dump(payload, f)
        print(f"Saved {self.name} → {path}")

    def load(self, path: str|Path|None = None):
        """Load Q-table and training state from disk. Silent no-op if file missing."""
        path = Path(path or f"models/{self.name}_qtable.pkl")
        if not path.exists():
            print(f"No checkpoint found for {self.name} at {path}, starting fresh.")
            return
        with open(path, "rb") as f:
            payload = pickle.load(f)
        self.q_table = defaultdict(
            lambda: np.zeros(len(self.action_space), dtype=np.float32),
            payload["q_table"]
        )
        self.epsilon = payload["epsilon"]
        self.training = payload["training"]
        print(f"Loaded {self.name} ← {path}  (ε={self.epsilon:.3f})")