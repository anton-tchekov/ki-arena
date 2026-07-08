from arena.runner import EpisodeRunner
from arena.phases import Phase
from analysis.evaluator import Evaluator
from analysis.logger import Logger

class Arena:
    def __init__(self, env, agents, logger: Logger=None, evaluator: Evaluator=None, saves_dir: str=None):
        self.env = env
        self.agents = agents
        self.logger = logger
        self.evaluator = evaluator

        self.runner = EpisodeRunner(env, agents, logger, saves_dir=saves_dir)

    def run_phase(self, phase: Phase):
        return phase.run(self)

    def collect_metrics(self):
        if self.evaluator:
            return self.evaluator.evaluate(self.env, self.agents)
        return {}