import numpy as np

class ObservationBuilder:
    def build(self, world, agent):
        raise NotImplementedError


class BasicObservation(ObservationBuilder):
    def build(self, world, agent):
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

        return np.array([pos[0], pos[1], dx, dy, total_fruit], dtype=np.float32)