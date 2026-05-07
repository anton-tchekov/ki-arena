from agents.base import BaseAgent

class GreedyCollector(BaseAgent):
    def act(self, obs, info):
        _, _, dx, dy, _ = obs

        if abs(dx) > abs(dy):
            return 1 if dx < 0 else 2
        else:
            return 3 if dy < 0 else 4