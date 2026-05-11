from agents.base import BaseAgent
from environment.actions import Action

class GreedyCollector(BaseAgent):
    def act(self, obs, info) -> Action:
        _, _, dx, dy, _ = obs

        if abs(dx) > abs(dy):
            return Action.LEFT if dx < 0 else Action.RIGHT
        else:
            return Action.UP if dy < 0 else Action.DOWN