import copy

from pettingzoo.utils.agent_selector import agent_selector as make_selector


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
        """Return parallel lists (cycles, wood, fruits, population) for plotting."""
        cycles = [s.cycle for s in self._snapshots]
        wood = [s.rm_wood for s in self._snapshots]
        fruits = [s.rm_fruits for s in self._snapshots]
        population = [len(s.alive_agents) for s in self._snapshots]
        return cycles, wood, fruits, population

    @property
    def latest_index(self) -> int:
        return len(self._snapshots) - 1

    def __len__(self) -> int:
        return len(self._snapshots)
