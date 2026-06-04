import numpy as np
from environment.world_grid import GridWorld
from agents.base import BaseAgent


class ObservationBuilder:
    def build(self, world: GridWorld, agent: BaseAgent):
        raise NotImplementedError


class BasicObservation(ObservationBuilder):
    def build(self, world: GridWorld, agent: BaseAgent):
        """
        Build observation for an agent.
        
        Returns:
            np.array: Observation vector with format:
                [pos_x, pos_y, dx_to_tree, dy_to_tree, total_fruits_on_trees, 
                 wood_count, fruit_count]
        """
        pos = world.positions[agent]

        if len(world.trees) > 0:
            nearest = min(
                world.trees.keys(),
                key=lambda t: abs(t[0] - pos[0]) + abs(t[1] - pos[1])
            )
            dx = nearest[0] - pos[0]
            dy = nearest[1] - pos[1]
        else:
            dx, dy = 0, 0

        total_fruit = sum(world.trees.values())
        
        # Get resource counts from world (which are synced from resource_manager)
        wood_count = getattr(world, 'wood', 0)
        fruit_count = getattr(world, 'fruits', 0)
        
        # Return observation: pos_x, pos_y, dx_to_nearest_tree, dy_to_nearest_tree,
        # total_fruits_on_trees, wood_resources, fruit_resources
        return np.array([pos[0], pos[1], dx, dy, total_fruit, wood_count, fruit_count], 
                       dtype=np.float32)
