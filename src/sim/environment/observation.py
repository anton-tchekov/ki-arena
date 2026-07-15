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
            Observation dictionary
        """
        # Handle both agent object and agent name string
        agent_key = agent.name if hasattr(agent, 'name') else agent
        pos = world.positions[agent_key]

        total_fruit = sum(world.trees.values())

        # Get resource counts from world (which are synced from resource_manager)
        wood_count = getattr(world, 'wood', 0)
        fruit_count = getattr(world, 'fruits', 0)

        # Positions are (x, y) = (pos[0], pos[1]) everywhere — no swapping.
        # x is the HORIZONTAL axis, y is the VERTICAL axis.
        return {
            'x': pos[0],
            'y': pos[1],
            'size': world.size,
            'trees': world.trees,
            'total_fruit': total_fruit,
            'wood_count': wood_count,
            'fruit_count': fruit_count,
            'cycle': getattr(world, 'cycle', 0),
        }
