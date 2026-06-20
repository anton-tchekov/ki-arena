from agents.base import BaseAgent
from agents.msg import Message
from environment.actions import Action
import random

class GreedyCollector(BaseAgent):
    """
    A simple collector agent that moves toward the nearest tree.
    When adjacent to a tree, it INTERACTs to collect fruits.
    """
    def act(self, obs, info) -> Action:
        x  = obs['x']
        y  = obs['y']
        dx = obs['dx']
        dy = obs['dy']
        fruit_on_tree = obs['total_fruit']

        if fruit_on_tree < 10:
            action = random.choice(list(Action))
            self.announce(Message(Message.Intention.WALK, action))
            return action

        # Check if we're adjacent to a tree (Manhattan distance = 1)
        # Only INTERACT if we're directly next to the tree (not diagonal)
        manhattan_dist = abs(dx) + abs(dy)
        if manhattan_dist == 1:
            self.announce(Message(Message.Intention.COLLECT, Action.INTERACT))
            return Action.INTERACT

        # Otherwise, move toward the tree
        if abs(dx) > abs(dy):
            action = Action.LEFT if dx < 0 else Action.RIGHT
        else:
            action = Action.UP if dy < 0 else Action.DOWN
        self.announce(Message(Message.Intention.WALK, action, ((x+dx),(y+dy))))
        return action


class GreedyCutter(BaseAgent):
    """
    A simple cutter agent that moves toward the nearest tree.
    When adjacent to a tree, it INTERACTs to cut down the tree.
    """
    def act(self, obs, info) -> Action:
        x  = obs['x']
        y  = obs['y']
        dx = obs['dx']
        dy = obs['dy']

        # Check if we're adjacent to a tree (Manhattan distance = 1)
        # Only INTERACT if we're directly next to the tree (not diagonal)
        manhattan_dist = abs(dx) + abs(dy)
        if manhattan_dist == 1:
            self.announce(Message(Message.Intention.CUT, Action.INTERACT))
            return Action.INTERACT

        # Otherwise, move toward the tree
        if abs(dx) > abs(dy):
            action = Action.LEFT if dx < 0 else Action.RIGHT
        else:
            action = Action.UP if dy < 0 else Action.DOWN
        self.announce(Message(Message.Intention.WALK, action, ((x+dx),(y+dy))))
        return action
