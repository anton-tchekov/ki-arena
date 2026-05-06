from reward import BasicReward
from observation import BasicObservation
from termination import MaxCycleTermination

class EnvConfig:
    def __init__(self):
        self.size = 5
        self.n_trees = 5
        self.max_cycles = 100

        self.reward_fn = BasicReward()
        self.observation_builder = BasicObservation()
        self.termination_conditions = [
            MaxCycleTermination(self.max_cycles)
        ]