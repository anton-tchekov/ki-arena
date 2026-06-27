from agents.base import BaseAgent


class Phase:
    def run(self, arena):
        raise NotImplementedError


class TrainingPhase(Phase):
    def __init__(self, episodes: int):
        self.episodes = episodes

    def run(self, arena):
        for ep in range(self.episodes):
            arena.runner.run_episode(training=True)          # fills transition buffers
            for agent in arena.agents.values():
                if hasattr(agent, "train_step"):
                    agent.train_step()          # trains + clears buffers

            if (ep + 1) % 50 == 0:
                print(f"  Episode {ep+1}/{self.episodes}", {
                    name: f"ε={agent.epsilon:.3f}"
                    for name, agent in arena.agents.items()
                    if hasattr(agent, "epsilon")
                })

        for agent in arena.agents.values():
            if hasattr(agent, "on_training_end"):
                agent.on_training_end()         # freezes epsilon at 0
            if hasattr(agent, "save"):          
                agent.save()            # optional: save Q-table to disk after training


class EvaluationPhase(Phase):
    def __init__(self, episodes: int = 5):
        self.episodes = episodes

    def run(self, arena):
        results = []
        for _ in range(self.episodes):
            arena.runner.run_episode()
            results.append(arena.collect_metrics())
        return results


class ExecutionPhase(Phase):
    def __init__(self, episodes: int = 1):
        self.episodes = episodes

    def run(self, arena):
        for _ in range(self.episodes):
            arena.runner.run_episode(render=True)