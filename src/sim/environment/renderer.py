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

        try:
            plt.pause(0.001)
        except:
            plt.draw()

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

        # fruit counts on trees
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

        # agent ages above agents and count below if overlapping
        if hasattr(world, 'agent_ages'):
            # First, count agents at each position
            position_counts = {}
            position_agents = {}  # Store agent names at each position
            
            for agent, pos in world.positions.items():
                x, y = pos
                pos_key = (x, y)
                if pos_key not in position_counts:
                    position_counts[pos_key] = 0
                    position_agents[pos_key] = []
                position_counts[pos_key] += 1
                position_agents[pos_key].append(agent)
            
            # Draw ages and counts
            for agent, pos in world.positions.items():
                x, y = pos
                pos_key = (x, y)
                age = world.agent_ages.get(agent, 0)
                
                # Only draw age for one agent at each position (the first one)
                if position_agents[pos_key][0] == agent:
                    # Draw age slightly above the agent's position
                    self.ax.text(
                        y,
                        x - 0.3,  # Position slightly above
                        str(age),
                        ha="center",
                        va="center",
                        color="white",
                        fontsize=8,
                        bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=1)
                    )
                
                # Draw count below if multiple agents at this position
                if position_counts[pos_key] > 1:
                    # Only draw count once per position (for the first agent)
                    if position_agents[pos_key][0] == agent:
                        self.ax.text(
                            y,
                            x + 0.3,  # Position slightly below
                            str(position_counts[pos_key]),
                            ha="center",
                            va="center",
                            color="white",
                            fontsize=8,
                            bbox=dict(facecolor='black', alpha=0.7, edgecolor='none', pad=1)
                        )

    def _draw_title(self, world: GridWorld):
        total_fruit_on_trees = sum(world.trees.values())
        num_trees = len(world.trees)
        
        # Get global resource counts from world
        wood = getattr(world, 'wood', 0)
        fruits = getattr(world, 'fruits', 0)
        
        # Get cycle count if available
        cycle = getattr(world, 'cycle', 0)

        self.ax.set_title(
            f"Cycle: {cycle} | Trees: {num_trees} | Tree Fruit: {total_fruit_on_trees} | Wood: {wood} | Fruits: {fruits}"
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