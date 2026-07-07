import copy
import gzip
import json
import os
import re

from pettingzoo.utils.agent_selector import agent_selector as make_selector


def _config_to_dict(config) -> dict:
    """
    Flatten an EnvConfig to a JSON-friendly dict so a run is reproducible.
    Scalars are stored as-is; the pluggable components (reward / observation /
    termination) are stored by class name.
    """
    out = {}
    for k, v in vars(config).items():
        if v is None or isinstance(v, (int, float, str, bool)):
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = [type(x).__name__ for x in v]
        else:
            out[k] = type(v).__name__
    return out


class ReplaySnapshot:
    """
    A lightweight snapshot rebuilt from a saved replay file.

    It carries the same display-relevant fields as ``StateSnapshot`` (positions,
    trees, alive agents, ages, wood, fruits, cycle) so the renderer can show it
    and the control-panel graph can read the series — but it is NOT tied to a
    live env, so a saved run can be replayed without stepping the simulation.
    """

    def __init__(self, record: dict):
        self.cycle = record["cycle"]
        self.positions = {a: [int(p[0]), int(p[1])] for a, p in record["positions"].items()}
        self.trees = {(int(t[0]), int(t[1])): f for t, f in record["trees"]}
        self.alive_agents = set(record["alive_agents"])
        self.agent_ages = {a: int(v) for a, v in record["agent_ages"].items()}
        # Live snapshots keep world_* and rm_* separately; for replay they are equal.
        self.world_wood = record["wood"]
        self.world_fruits = record["fruits"]
        self.rm_wood = record["wood"]
        self.rm_fruits = record["fruits"]


# Saved runs are gzip-compressed JSON (.bin). Auto-generated live runs are numbered
# ``run-NNN.bin``; curated "interesting" runs get semantic names like
# ``greedy-0.3-boom.bin``. _SAVE_RE matches only the numbered form (used to pick the
# next number); _LEGACY_TXT_RE matches old plain-JSON ``run-NNN.txt`` saves — NOT the
# ``.txt`` explanation notes that sit next to curated runs.
_SAVE_RE = re.compile(r"run-(\d+)\.(bin|txt)$")
_LEGACY_TXT_RE = re.compile(r"run-\d+\.txt$")


def list_saves(saves_dir: str) -> list[str]:
    """Saved replay files (newest first). Lists every ``.bin`` replay — both the
    auto-numbered ``run-NNN.bin`` and the curated semantic names — plus legacy
    plain-JSON ``run-NNN.txt`` saves. The ``.txt`` explanation notes are skipped."""
    if not os.path.isdir(saves_dir):
        return []
    files = [
        os.path.join(saves_dir, f)
        for f in os.listdir(saves_dir)
        if f.endswith(".bin") or _LEGACY_TXT_RE.match(f)
    ]
    return sorted(files, reverse=True)


def next_save_path(saves_dir: str) -> str:
    """Path for the next run file (``run-001.bin``, ``run-002.bin``, ...)."""
    os.makedirs(saves_dir, exist_ok=True)
    highest = 0
    for f in os.listdir(saves_dir):
        m = _SAVE_RE.match(f)
        if m:
            highest = max(highest, int(m.group(1)))
    return os.path.join(saves_dir, f"run-{highest + 1:03d}.bin")


class StateSnapshot:
    """Immutable snapshot of env state captured at a cycle boundary."""

    def __init__(self, env):
        self.cycle = env.cycle

        # World
        self.positions = copy.deepcopy(env.world.positions)
        self.trees = copy.deepcopy(env.world.trees)
        self.alive_agents = copy.deepcopy(env.world.alive_agents)
        self.agent_ages = copy.deepcopy(env.world.agent_ages)
        self.world_wood = env.world.wood
        self.world_fruits = env.world.fruits

        # Resource manager
        self.rm_wood = env.resource_manager.wood
        self.rm_fruits = env.resource_manager.fruits
        self.rm_cycle = env.resource_manager.cycle

        # Env / PettingZoo state
        self.agents = list(env.agents)
        self.possible_agents = list(env.possible_agents)
        self.rewards = copy.deepcopy(env.rewards)
        self.cumulative_rewards = copy.deepcopy(env._cumulative_rewards)
        self.terminations = copy.deepcopy(env.terminations)
        self.truncations = copy.deepcopy(env.truncations)
        self.infos = copy.deepcopy(env.infos)
        self.agent_selection = env.agent_selection


class StateHistory:
    """
    Stores one StateSnapshot per completed cycle and can restore them.

    Usage:
        history.save(env)               # call after env.cycle increments
        history.restore(env, index)     # full env restore (for continuing sim)
        history.restore_world_only(world, index)  # display-only restore
        history.truncate_after(index)   # discard future when branching
    """

    def __init__(self):
        self._snapshots: list[StateSnapshot] = []
        # Config the run used, populated when a saved run is loaded back (for
        # reproducibility); None for a live, unsaved history.
        self.config = None

    # ------------------------------------------------------------------
    def save(self, env) -> None:
        self._snapshots.append(StateSnapshot(env))

    # ------------------------------------------------------------------
    def restore(self, env, index: int) -> None:
        """Restore complete env state so the simulation can continue from here."""
        snap = self._snapshots[index]

        # World
        env.world.positions = copy.deepcopy(snap.positions)
        env.world.trees = copy.deepcopy(snap.trees)
        env.world.alive_agents = copy.deepcopy(snap.alive_agents)
        env.world.agent_ages = copy.deepcopy(snap.agent_ages)
        env.world.wood = snap.world_wood
        env.world.fruits = snap.world_fruits
        env.world.cycle = snap.cycle

        # Resource manager
        env.resource_manager.wood = snap.rm_wood
        env.resource_manager.fruits = snap.rm_fruits
        env.resource_manager.cycle = snap.rm_cycle

        # Env / PettingZoo
        env.cycle = snap.cycle
        env.agents = list(snap.agents)
        env.possible_agents = list(snap.possible_agents)
        env.rewards = copy.deepcopy(snap.rewards)
        env._cumulative_rewards = copy.deepcopy(snap.cumulative_rewards)
        env.terminations = copy.deepcopy(snap.terminations)
        env.truncations = copy.deepcopy(snap.truncations)
        env.infos = copy.deepcopy(snap.infos)
        env.agent_selection = snap.agent_selection
        env._agent_selector = make_selector(env.agents)

    # ------------------------------------------------------------------
    def restore_world_only(self, world, index: int) -> None:
        """Restore only the GridWorld fields (for display during browsing)."""
        snap = self._snapshots[index]
        world.positions = copy.deepcopy(snap.positions)
        world.trees = copy.deepcopy(snap.trees)
        world.alive_agents = copy.deepcopy(snap.alive_agents)
        world.agent_ages = copy.deepcopy(snap.agent_ages)
        world.wood = snap.world_wood
        world.fruits = snap.world_fruits
        world.cycle = snap.cycle

    # ------------------------------------------------------------------
    def truncate_after(self, index: int) -> None:
        """Discard all snapshots after index (used when branching into the past)."""
        self._snapshots = self._snapshots[:index + 1]

    # ------------------------------------------------------------------
    def cycle_at(self, index: int) -> int:
        return self._snapshots[index].cycle

    # ------------------------------------------------------------------
    def series(self):
        """
        Return parallel lists for plotting:
        (cycles, wood, fruits, population, collectors, cutters, avg_age).
        Collectors/cutters are the per-cycle head-count of each role; avg_age is
        the mean age of the living agents that cycle.
        """
        def _avg_age(s):
            ages = [s.agent_ages.get(a, 0) for a in s.alive_agents]
            return sum(ages) / len(ages) if ages else 0

        cycles = [s.cycle for s in self._snapshots]
        wood = [s.rm_wood for s in self._snapshots]
        fruits = [s.rm_fruits for s in self._snapshots]
        population = [len(s.alive_agents) for s in self._snapshots]
        collectors = [sum(1 for a in s.alive_agents if "collector" in a) for s in self._snapshots]
        cutters = [sum(1 for a in s.alive_agents if "cutter" in a) for s in self._snapshots]
        avg_age = [_avg_age(s) for s in self._snapshots]
        return cycles, wood, fruits, population, collectors, cutters, avg_age

    @property
    def latest_index(self) -> int:
        return len(self._snapshots) - 1

    def __len__(self) -> int:
        return len(self._snapshots)

    # ------------------------------------------------------------------
    # Saving / loading a run as a replay file
    # ------------------------------------------------------------------
    def save_to_file(self, path: str, config=None) -> None:
        """
        Write all snapshots to `path` as gzip-compressed JSON (binary). The data
        compresses very well (agent names, coordinates etc. repeat every cycle),
        so a >1000-cycle run shrinks from megabytes to tens of kilobytes.

        If `config` is given, the resolved configuration is embedded so the run
        can be reproduced later.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        records = []
        for s in self._snapshots:
            records.append({
                "cycle": s.cycle,
                "positions": {a: [int(p[0]), int(p[1])] for a, p in s.positions.items()},
                "trees": [[[int(t[0]), int(t[1])], f] for t, f in s.trees.items()],
                "alive_agents": list(s.alive_agents),
                "agent_ages": {a: int(v) for a, v in s.agent_ages.items()},
                "wood": float(s.rm_wood),
                "fruits": float(s.rm_fruits),
            })
        payload = {
            "version": 2,
            "config": _config_to_dict(config) if config is not None else None,
            "snapshots": records,
        }
        raw = json.dumps(payload).encode("utf-8")
        with gzip.open(path, "wb") as fh:
            fh.write(raw)

    @classmethod
    def load_from_file(cls, path: str) -> "StateHistory":
        """
        Rebuild a history from a saved run file. Handles both the gzip binary
        format and legacy plain-JSON (.txt) files (detected by the gzip magic).
        """
        with open(path, "rb") as fh:
            blob = fh.read()
        if blob[:2] == b"\x1f\x8b":  # gzip magic number
            text = gzip.decompress(blob).decode("utf-8")
        else:
            text = blob.decode("utf-8")  # legacy plain-JSON save
        data = json.loads(text)
        hist = cls()
        hist._snapshots = [ReplaySnapshot(r) for r in data["snapshots"]]
        hist.config = data.get("config")
        return hist
