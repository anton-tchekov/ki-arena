import numpy as np
import random
from environment.actions import Action

class GridWorld:
    def __init__(self, size, n_trees):
        self.size = size
        self.n_trees = n_trees

        self.positions = {}
        self.trees = {}

    def reset(self, agents):
        self.positions = {
            agent: np.array([
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            ])
            for agent in agents
        }

        self.trees = {}
        for _ in range(self.n_trees):
            pos = (
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            )
            self.trees[pos] = 3

    def move(self, agent, action: Action):
        x, y = self.positions[agent]

        # X und Y sind auf dem Grid vertauscht, nicht verwirrt sein also
        if action == Action.UP:
            x = max(0, x - 1)
        elif action == Action.DOWN:
            x = min(self.size - 1, x + 1)
        elif action == Action.LEFT:
            y = max(0, y - 1)
        elif action == Action.RIGHT:
            y = min(self.size - 1, y + 1)

        self.positions[agent] = np.array([x, y])

    def adjacent_tree(self, agent):
        x, y = self.positions[agent]
        for (tx, ty) in self.trees.keys():
            if abs(tx - x) + abs(ty - y) == 1:
                return (tx, ty)
        return None

    def interact(self, agent):
        tree_pos = self.adjacent_tree(agent)

        if tree_pos is None:
            return {"type": "none"}

        if "collector" in agent:
            if self.trees[tree_pos] > 0:
                self.trees[tree_pos] -= 1
                return {"type": "collect", "value": 1}

        if "cutter" in agent:
            del self.trees[tree_pos]
            return {"type": "cut"}

        return {"type": "none"}

    def step_global(self):
        # regrowth
        for t in list(self.trees.keys()):
            if random.random() < 0.4:
                self.trees[t] += 1

        # new tree
        if len(self.trees) < self.n_trees and random.random() < 0.1:
            pos = (
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            )
            self.trees[pos] = 1