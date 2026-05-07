from sim.environment.reward import BasicReward
from sim.environment.observation import BasicObservation
from sim.environment.termination import MaxCycleTermination

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