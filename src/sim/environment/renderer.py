import numpy as np
import matplotlib.pyplot as plt

from matplotlib.colors import ListedColormap
from environment.world_grid import GridWorld


class GridWorldRenderer:
    def __init__(self):
        self.default_config = {
            "colors": {
                "empty": "#1e1e1e",
                "tree_low": "#2e7d32",
                "tree_high": "#66bb6a",
                "collector": "#42a5f5",
                "cutter": "#ef5350",
            },
            "show_text": True,
            "show_grid": True,
            "figure_size": (6, 6),
        }

        self.fig = None
        self.ax = None

    def render(self, world: GridWorld, config=None):
        config = self._merge_config(config)

        grid = self._build_grid(world)

        cmap = ListedColormap([
            config["colors"]["empty"],
            config["colors"]["tree_low"],
            config["colors"]["tree_high"],
            config["colors"]["collector"],
            config["colors"]["cutter"],
        ])

        # create figure only once
        if self.fig is None:
            self.fig, self.ax = plt.subplots(
                figsize=config["figure_size"]
            )

        self.ax.clear()

        self.ax.imshow(
            grid,
            cmap=cmap,
            vmin=0,
            vmax=4
        )

        self._draw_grid(world, config)
        self._draw_text(world, config)
        self._draw_title(world)

        plt.pause(0.001)

    def _build_grid(self, world):
        grid = np.zeros((world.size, world.size))

        # trees
        for (x, y), fruit in world.trees.items():
            if fruit <= 2:
                grid[x][y] = 1
            else:
                grid[x][y] = 2

        # agents
        for agent, pos in world.positions.items():
            x, y = pos

            if "collector" in agent:
                grid[x][y] = 3
            elif "cutter" in agent:
                grid[x][y] = 4

        return grid

    def _draw_grid(self, world: GridWorld, config):
        self.ax.set_xticks(
            np.arange(-0.5, world.size, 1),
            minor=True
        )

        self.ax.set_yticks(
            np.arange(-0.5, world.size, 1),
            minor=True
        )

        if config["show_grid"]:
            self.ax.grid(
                which="minor",
                color="white",
                linestyle="-",
                linewidth=1
            )

        self.ax.tick_params(
            which="both",
            bottom=False,
            left=False,
            labelbottom=False,
            labelleft=False
        )

    def _draw_text(self, world: GridWorld, config):
        if not config["show_text"]:
            return

        # fruit counts
        for (x, y), fruit in world.trees.items():
            self.ax.text(
                y,
                x,
                str(fruit),
                ha="center",
                va="center",
                color="white",
                fontsize=10
            )

    def _draw_title(self, world: GridWorld):
        total_fruit = sum(world.trees.values())
        num_trees = len(world.trees)

        self.ax.set_title(
            f"Trees: {num_trees} | Fruit: {total_fruit}"
        )

    def _merge_config(self, config):
        if config is None:
            return self.default_config

        merged = self.default_config.copy()

        for k, v in config.items():
            if isinstance(v, dict):
                merged[k].update(v)
            else:
                merged[k] = v

        return merged

    def close(self):
        if self.fig:
            plt.close(self.fig)