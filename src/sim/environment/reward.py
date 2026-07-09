from environment.actions import Action

class RewardFunction:
    def compute(self, world, agent, action, result) -> float:
        return 0
    
    def reset(self):
        """Called on env.reset() for stateful reward fns like ExplorerRewardFn."""
        pass


class BasicReward(RewardFunction):
    def compute(self, world, agent, action, result) -> float:
        if result is None:
            return 0

        if result["type"] == "collect":
            return result.get("value", 1)

        return 0

class ScarcityPenaltyReward(RewardFunction):
    def compute(self, world, agent, action, result) -> float:
        if sum(world.trees.values()) == 0:
            return -1
        return 0
    
class CollectorRewardFn(RewardFunction):
    """Learns to collect fruit as fast as possible."""
    def compute(self, world, agent, action, result) -> float:
        if "collector" not in agent:
            return 0.0
        # handle result being a string, dict, or None
        result_type = (
            result.get("type") if isinstance(result, dict)
            else result if isinstance(result, str)
            else None
        )
        if result_type == "collect":
            return 5.0
        if action == Action.INTERACT and result_type == "none":
            return -0.2       # tried to interact with nothing — punish wasted action
        return -0.05          # small step penalty keeps paths short

class CutterRewardFn(RewardFunction):
    """Learns to cut trees."""
    def compute(self, world, agent, action, result) -> float:
        if "cutter" not in agent:
            return 0.0
        result_type = (
            result.get("type") if isinstance(result, dict)
            else result if isinstance(result, str)
            else None
        )
        if result_type == "cut":
            return 5.0
        if action == Action.INTERACT and result_type == "none":
            return -0.2       # tried to interact with nothing — punish wasted action
        #if world.is_adjacent_to_tree(agent):
        #    return 0.2 # shaped reward: reward proximity to trees
        return -0.05
    
class ExplorerRewardFn(RewardFunction):
    """Learns to cover new ground."""
    def __init__(self):
        self.visited = set()

    def compute(self, world, agent, action, result) -> float:
        pos = world.get_pos(agent)
        if pos not in self.visited:
            self.visited.add(pos)
            return 1.0        # reward visiting new cells
        return -0.1           # punish revisiting
    
    def reset(self):
        self.visited.clear()

class StepPenaltyFn(RewardFunction):
    def __init__(self, penalty: float = -0.05):
        self.penalty = penalty

    def compute(self, world, agent, action, result) -> float:
        return self.penalty
    
    def reset(self):
        pass


# ── composite ────────────────────────────────────────────────────────────────

class CompositeRewardFn(RewardFunction):
    """
    Sums weighted sub-functions. Each entry is (weight, RewardFunction).
    Applied to every agent regardless of type — the sub-fns sort out
    agent-specific logic internally (e.g. CutterRewardFn only fires on "cut").
    """

    def __init__(self, *weighted_fns: tuple[float, RewardFunction]):
        self.fns: list[tuple[float, RewardFunction]] = list(weighted_fns)

    def reset(self):
        for _, fn in self.fns:
            fn.reset()

    def compute(self, world, agent, action, result) -> float:
        return sum(w * fn.compute(world, agent, action, result) for w, fn in self.fns)