from environment.actions import Action

class RewardFunction:
    def compute(self, world, agent, action, result) -> float:
        return 0


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
        if result == "fruit_collected":
            return 5.0
        if action == Action.INTERACT and result is None:
            return -0.2       # tried to interact with nothing — punish wasted action
        return -0.05          # small step penalty keeps paths short

class CutterRewardFn(RewardFunction):
    """Learns to cut trees."""
    def compute(self, world, agent, action, result) -> float:
        if result == "tree_cut":
            return 5.0
        if world.is_adjacent_to_tree(agent):
            return 0.3        # shaped reward: reward proximity to trees
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