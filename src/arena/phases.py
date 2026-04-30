class Phase:
    def run(self, arena):
        raise NotImplementedError


class TrainingPhase(Phase):
    def __init__(self, episodes):
        self.episodes = episodes

    def run(self, arena):
        for _ in range(self.episodes):
            arena.runner.run_episode()

            # hook for training updates
            for agent in arena.agents.values():
                if hasattr(agent, "train_step"):
                    agent.train_step()


class EvaluationPhase(Phase):
    def __init__(self, episodes):
        self.episodes = episodes

    def run(self, arena):
        results = []
        for _ in range(self.episodes):
            arena.runner.run_episode()
            results.append(arena.collect_metrics())
        return results


class ExecutionPhase(Phase):
    def run(self, arena):
        # e.g. live deployment / visualization
        arena.runner.run_episode(render=True)