class TerminationCondition:
    def check(self, world, step_count) -> bool:
        return False


class MaxCycleTermination(TerminationCondition):
    def __init__(self, max_cycles):
        self.max_cycles = max_cycles

    def check(self, world, step_count) -> bool:
        return step_count >= self.max_cycles


class NoFoodTermination(TerminationCondition):
    def check(self, world, step_count) -> bool:
        return sum(world.trees.values()) == 0