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
    """Learns to collect fruit fast, and is nudged toward richer trees —
    not locked onto one specific 'best' tree, since the map keeps changing
    (trees spawn fresh and regrow fruit over time). Instead it rewards
    being near a tree that's currently better than the map's average,
    recomputed fresh every step so it never chases a stale target."""

    def __init__(self, shaping_weight: float = 0.1):
        self.shaping_weight = shaping_weight

    def _richness_bonus(self, world, agent) -> float:
        trees = world.trees
        if not trees:
            return 0.0
        avg_fruit = sum(trees.values()) / len(trees)
        if avg_fruit <= 0:
            return 0.0
        ax, ay = world.get_pos(agent)
        nearest_pos = min(trees.keys(), key=lambda t: abs(t[0]-ax) + abs(t[1]-ay))
        nearest_fruit = trees[nearest_pos]
        # normalized: >0 if nearest tree is above-average, <0 if below
        return (nearest_fruit - avg_fruit) / avg_fruit

    def compute(self, world, agent, action, result) -> float:
        if "collector" not in agent:
            return 0.0
        
        result_type = (
            result.get("type") if isinstance(result, dict)
            else result if isinstance(result, str)
            else None
        )

        if result_type == "collect":
            reward = 8.0
        elif action == Action.INTERACT and result_type == "none":
            reward = -0.3
        else:
            reward = 0.0

        #reward += self.shaping_weight * self._richness_bonus(world, agent)
        return reward

class CutterRewardFn(RewardFunction):
    """Learns to cut trees, nudged toward poorer trees — sacrificing
    low-yield trees for wood instead of competing with collectors over
    the good ones. Same stateless, always-fresh relative bonus."""

    def __init__(self, shaping_weight: float = 0.1):
        self.shaping_weight = shaping_weight

    def _poorness_bonus(self, world, agent) -> float:
        trees = world.trees
        if not trees:
            return 0.0
        avg_fruit = sum(trees.values()) / len(trees)
        if avg_fruit <= 0:
            return 0.0
        ax, ay = world.get_pos(agent)
        nearest_pos = min(trees.keys(), key=lambda t: abs(t[0]-ax) + abs(t[1]-ay))
        nearest_fruit = trees[nearest_pos]
        # >0 if nearest tree is below-average (good for a cutter), <0 if above
        return (avg_fruit - nearest_fruit) / avg_fruit

    def compute(self, world, agent, action, result) -> float:
        if "cutter" not in agent:
            return 0.0
        
        result_type = (
            result.get("type") if isinstance(result, dict)
            else result if isinstance(result, str)
            else None
        )
        if result_type == "cut":
            reward = 8.0
        elif action == Action.INTERACT and result_type == "none":
            reward = -0.3
        else:
            reward = 0.0

        #reward += self.shaping_weight * self._poorness_bonus(world, agent)
        return reward

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
    """Small constant penalty every step to encourage shorter paths."""
    def __init__(self, penalty: float = -0.5):
        self.penalty = penalty

    def compute(self, world, agent, action, result) -> float:
        if action != Action.INTERACT:
            return self.penalty 
        
        return 0.0  # no penalty for interacting 
    
    def reset(self):
        pass

class AliveBonusReward(RewardFunction):
    """Small constant bonus every step to encourage survival."""
    def __init__(self, bonus: float = 0.5):
        self.bonus = bonus

    def compute(self, world, agent, action, result) -> float:
        return self.bonus
    
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