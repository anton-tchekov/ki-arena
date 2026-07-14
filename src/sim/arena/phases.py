from agents.base import BaseAgent


class Phase:
    def run(self, arena):
        raise NotImplementedError

class TrainingPhase(Phase):
    def __init__(self, episodes: int, log_every: int = 50):
        self.episodes = episodes
        self.log_every = log_every
        self.survival_history = []   # one outcome dict per episode

    def run(self, arena):
        for ep in range(self.episodes):
            outcome = arena.runner.run_episode(training=False)      # fills transition buffers
            self.survival_history.append(outcome)

            for agent in arena.agents.values():
                if hasattr(agent, "train_step"):
                    agent.train_step()                              # trains + clears buffers

            if (ep + 1) % self.log_every == 0:
                window = self.survival_history[-self.log_every:]
                avg_cycles = sum(o["cycles"] for o in window) / len(window)
                extinct_rate = sum(o["extinct"] for o in window) / len(window)
                print(f"  Episode {ep+1}/{self.episodes}  "
                      f"avg_survival={avg_cycles:.1f} cycles  "
                      f"extinct_rate={extinct_rate:.0%}  "
                      + str({name: f"ε={agent.epsilon:.3f}"
                             for name, agent in arena.agents.items()
                             if hasattr(agent, "epsilon")}))

        for agent in arena.agents.values():
            if hasattr(agent, "on_training_end"):
                agent.on_training_end()                             # freezes epsilon at 0
            if hasattr(agent, "save"):
                agent.save()                                        # optional: save Q-table to disk after training

        return self.survival_history


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