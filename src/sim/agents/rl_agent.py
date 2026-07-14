from collections import defaultdict
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

    #DEFAULT_BINS = (3, 3, 1, 1, 10, 20, 20) # pos_x, pos_y, dx, dy, total_fruit, wood, fruit
    DEFAULT_BINS = (3, 3, 3, 3, 50, 50, 50) # pos_x, pos_y, dx, dy, total_fruit, wood, fruit

    def __init__(
        self,
        name: str,
        discretize_bins: tuple | None = None,
        epsilon: float = 0.3,
        learning_rate: float = 0.1,
        gamma: float = 0.99,
        debug: bool = False,
    ):
        super().__init__(name)
        self.bins = discretize_bins or self.DEFAULT_BINS
        self.initial_epsilon = epsilon
        self.epsilon = self.initial_epsilon
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.action_space = list(Action)
        self.debug = debug
        self._step_count = 0
        self._episode_count = 0

        n = len(self.action_space)
        # small random init breaks the all-zeros argmax tie
        self.q_table = defaultdict(
            lambda: np.random.uniform(-0.02, 0.02, n).astype(np.float32)
        )
        self.transitions = []
        self.training = True

    def _obs_to_list(self, obs) -> list:
        """
        Convert dictionary observation to list format for discretization.
        Extracts nearest tree information from trees array.
        Returns: [x, y, dx_tree, dy_tree, total_fruit, wood, fruit]
        """
        if isinstance(obs, dict):
            x, y = obs['x'], obs['y']
            trees = obs.get('trees', {})
            if trees:
                candidates = [t for t, f in trees.items() if f > 0] or list(trees.keys()) # check the trees that have fruits first, when none have - fall back to closest
                tx, ty = min(candidates, key=lambda t: abs(t[0]-x) + abs(t[1]-y))
                dx, dy = tx - x, ty - y
            else:
                dx, dy = 0, 0
            return [x, y, dx, dy, obs['total_fruit'], obs['wood_count'], obs['fruit_count']]
        # already array/list
        return list(obs)

    def discretize(self, obs) -> tuple:
        """
        Bucket each obs dimension by its corresponding bin size.
        Direction-like values (bin=1) become sign only: -1 / 0 / +1.
        """
        obs_list = self._obs_to_list(obs)
        assert len(obs_list) == len(self.bins), (
            f"{self.name}: obs length {len(obs_list)} != bins length {len(self.bins)}"
        )
        state = []
        for val, bin_size in zip(obs_list, self.bins):
            state.append(int(np.sign(val)) if bin_size == 1 else int(val) // bin_size)
        
        #print(f"  obs_list = {obs_list}")
        #print(f"  state = {tuple(state)}")
        return tuple(state)

    def act(self, obs, info) -> Action:
        # Convert dictionary observation to list format for discretization
        state = self.discretize(obs)
        exploring = self.training and np.random.rand() < self.epsilon
        if exploring:
            action = self.action_space[np.random.randint(len(self.action_space))]
        else:
            action = self.action_space[int(np.argmax(self.q_table[state]))]

        if self.debug and self._step_count % 50 == 0:
            print(f"[{self.name}] ep={self._episode_count} ε={self.epsilon:.3f} "
                  f"exploring={exploring} action={action.name} "
                  f"state={state} Q={self.q_table[state].round(2)}")
        self._step_count += 1

        return action

    def after_action(self, obs, action, reward, next_obs, done, info):
        if action is None:
            return
        s  = self.discretize(obs)
        s_ = self.discretize(next_obs) if next_obs is not None else None
        self.transitions.append((s, action, reward, s_, done))

    def train_step(self):
        if not self.training:
            return
        if not self.transitions:
            if self.debug:
                print(f"[{self.name}] WARNING: train_step called with empty buffer!")
            return
        
        # Temporarily for debug
        # ------
        #rewards = [t[2] for t in self.transitions]
        #print(f"[{self.name}] rewards: min={min(rewards):.2f} max={max(rewards):.2f} "
        #    f"mean={sum(rewards)/len(rewards):.3f} "
        #    f"nonzero={sum(1 for r in rewards if abs(r) > 0.01)}/{len(rewards)}")
        
        #obs_lists = [list(s) for s, *_ in self.transitions]
        #for i, bin_size in enumerate(self.bins):
        #    vals = [o[i] for o in obs_lists]
        #    buckets = set(int(np.sign(v)) if bin_size == 1 else int(v) // bin_size for v in vals)
        #    print(f"  dim[{i}] bin={bin_size} range=[{min(vals):.1f}, {max(vals):.1f}] "
        #            f"→ {len(buckets)} unique buckets: {sorted(buckets)}")
            
        #print(f"bins = {self.bins}")
        # ------
        
        if self.debug:
            print(f"[{self.name}] training on {len(self.transitions)} transitions | "
                  f"unique states: {len(set(t[0] for t in self.transitions))} | "
                  f"q_table size: {len(self.q_table)} | ε={self.epsilon:.3f}")

        for state, action, reward, next_state, done in self.transitions:
            idx = self.action_space.index(action)
            td_target = reward
            if next_state is not None and not done:
                td_target += self.gamma * np.max(self.q_table[next_state])
            self.q_table[state][idx] += self.learning_rate * (td_target - self.q_table[state][idx])

        self.transitions.clear()
        self.epsilon = max(0.001, self.epsilon * 0.999)
        self._episode_count += 1

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