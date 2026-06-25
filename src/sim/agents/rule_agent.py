from agents.base import BaseAgent
from environment.actions import Action


class GreedyCollector(BaseAgent):
    """
    A simple collector agent that moves toward the nearest tree.
    When adjacent to a tree, it INTERACTs to collect fruits.
    """
    def act(self, obs, info) -> Action:
        dx = obs['dx']
        dy = obs['dy']
        fruit_on_tree = obs['total_fruit']

        if fruit_on_tree < 10:
            return random.choice(list(Action))

        # Check if we're adjacent to a tree (Manhattan distance = 1)
        # Only INTERACT if we're directly next to the tree (not diagonal)
        manhattan_dist = abs(dx) + abs(dy)
        if manhattan_dist == 1:
            return Action.INTERACT

        # Otherwise, move toward the tree
        if abs(dx) > abs(dy):
            return Action.LEFT if dx < 0 else Action.RIGHT
        else:
            return Action.UP if dy < 0 else Action.DOWN


class GreedyCutter(BaseAgent):
    """
    A simple cutter agent that moves toward the nearest tree.
    When adjacent to a tree, it INTERACTs to cut down the tree.
    """
    def act(self, obs, info) -> Action:
        dx = obs['dx']
        dy = obs['dy']

        # Check if we're adjacent to a tree (Manhattan distance = 1)
        # Only INTERACT if we're directly next to the tree (not diagonal)
        manhattan_dist = abs(dx) + abs(dy)
        if manhattan_dist == 1:
            return Action.INTERACT

        # Otherwise, move toward the tree
        if abs(dx) > abs(dy):
            return Action.LEFT if dx < 0 else Action.RIGHT
        else:
            return Action.UP if dy < 0 else Action.DOW
