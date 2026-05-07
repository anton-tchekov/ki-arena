class RewardFunction:
    def compute(self, world, agent, action, result):
        return 0


class BasicReward(RewardFunction):
    def compute(self, world, agent, action, result):
        if result is None:
            return 0

        if result["type"] == "collect":
            return result.get("value", 1)

        return 0


class ScarcityPenaltyReward(RewardFunction):
    def compute(self, world, agent, action, result):
        if sum(world.trees.values()) == 0:
            return -1
        return 0