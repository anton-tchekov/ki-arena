from arena.runner import EpisodeRunner 

class Arena:
    def __init__(self, env, agents, logger=None, evaluator=None):
        self.env = env
        self.agents = agents
        self.logger = logger
        self.evaluator = evaluator

        self.runner = EpisodeRunner(env, agents, logger)

    def run_phase(self, phase):
        return phase.run(self)

    def collect_metrics(self):
        if self.evaluator:
            return self.evaluator.evaluate(self.env, self.agents)
        return {}