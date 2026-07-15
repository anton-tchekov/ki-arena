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

    Default matches obs = [pos_x, pos_y, dx_near, dy_near, near_fruit, dx_rich, dy_rich, rich_fruit, wood, fruit]
        nearest tree and richest tree are both exposed as candidates; the
    agent's Q-table learns which one to head for, since that tradeoff
    differs by agent type (collectors want fruit, cutters want any tree).
    """

    # default: pos_x, pos_y, dx_near, dy_near, near_fruit, dx_rich, dy_rich, rich_fruit, wood, fruit
    #DEFAULT_BINS = (1, 1, 1, 1, 3, 1, 1, 3, 50, 50)
        
    # collector: pos_x, pos_y, dx_rich, dy_rich, rich_fruit, wood, fruit
    # cutter: pos_x, pos_y, dx_poor, dy_poor, poor_fruit, wood, fruit
    DEFAULT_BINS = (1, 1, 1, 1, 3, 50, 50)


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
        Exposes TWO candidate trees — nearest and richest — as separate
        fields, rather than pre-selecting one. The agent's own Q-table
        learns which to prioritize per situation (and per agent type, since
        collectors and cutters get different rewards for the same state).
        Returns: [x, y, dx_near, dy_near, near_fruit,
                        dx_rich, dy_rich, rich_fruit, wood, fruit]
        """
        if isinstance(obs, dict):
            x, y = obs['x'], obs['y']
            trees = obs['trees']
            wood_count = obs['wood_count']
            fruit_count = obs['fruit_count']

            if trees:
                agent_type = "collector" if "collector" in self.name else "cutter"
                if agent_type == "collector":
                    #rich_pos = max(trees.keys(), key=lambda t: trees[t])
                    #dx_rich, dy_rich = rich_pos[0] - x, rich_pos[1] - y
                    #rich_fruit = trees[rich_pos]
                    #return [x, y, dx_rich, dy_rich, rich_fruit, wood_count, fruit_count]
                    fruited = [t for t, f in trees.items() if f > 0]
                    target_trees = fruited if fruited else list(trees.keys())
                    tx, ty = min(target_trees, key=lambda t: abs(t[0]-x) + abs(t[1]-y))
                    dx, dy = tx - x, ty - y
                    target_fruit = trees[(tx, ty)]
                    return [x, y, dx, dy, target_fruit, wood_count, fruit_count]
                else:
                    #poor_pos = min(trees.keys(), key=lambda t: trees[t])
                    #dx_poor, dy_poor = poor_pos[0] - x, poor_pos[1] - y
                    #poor_fruit = trees[poor_pos]
                    #return [x, y, dx_poor, dy_poor, poor_fruit, wood_count, fruit_count]
                    fruited = [t for t, f in trees.items() if f > 0]
                    target_trees = fruited if fruited else list(trees.keys())
                    tx, ty = min(target_trees, key=lambda t: abs(t[0]-x) + abs(t[1]-y))
                    dx, dy = tx - x, ty - y
                    target_fruit = trees[(tx, ty)]
                    return [x, y, dx, dy, target_fruit, wood_count, fruit_count]
            else:
                dx_near = dy_near = near_fruit = 0
                return [x, y, dx_near, dy_near, near_fruit, wood_count, fruit_count]
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

        total_td_error = 0.0
        for state, action, reward, next_state, done in self.transitions:
            idx = self.action_space.index(action)
            td_target = reward
            if next_state is not None and not done:
                td_target += self.gamma * np.max(self.q_table[next_state])
            delta = self.learning_rate * (td_target - self.q_table[state][idx])
            self.q_table[state][idx] += delta
            total_td_error += abs(delta)

        self.last_td_error = total_td_error / len(self.transitions)
        self.last_qtable_size = len(self.q_table)

        self.transitions.clear()
        self.epsilon = max(0.001, self.epsilon * 0.99995)
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

    def load(self, path: str|Path|None = None, new_training: bool = False):
        """Load Q-table and training state from disk. Silent no-op if file missing."""
        
        if path is None and not new_training:
            if self.name.startswith("cutter"):
                filename = "models/cutter_100k_eps_qtable.pkl"
            elif self.name.startswith("collector"):
                filename = "models/collector_100k_eps_qtable.pkl"
            else:
                raise ValueError(f"Unknown agent type: {self.name}")
            path = Path(filename)
        elif new_training:
            path = Path(path or f"models/{self.name}_qtable.pkl")
        elif isinstance(path, str):
            path = Path(path)
        
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