import numpy as np
import random
from environment.actions import Action


class GridWorld:
    def __init__(self, size, n_trees, config=None):
        """
        Initialize the grid world.
        
        Args:
            size: Size of the grid (size x size)
            n_trees: Initial number of trees
            config: EnvConfig object for dynamic behavior (optional)
        """
        self.size = size
        self.n_trees = n_trees
        self.config = config

        self.positions = {}
        self.trees = {}

        # Current cycle, mirrored from the env (set here so it exists before the
        # first global step — e.g. when the run starts paused on cycle 0).
        self.cycle = 0

        # Track alive agents and their ages for death mechanics
        self.alive_agents = set()
        self.agent_ages = {}
        
        # Resource counts (mirrored from resource_manager for renderer access)
        # These are updated in step_global() from the resource_manager
        self.wood = 0
        self.fruits = 0
        
        # Reference to resource_manager (set during step_global)
        self._resource_manager = None

    def reset(self, agents):
        """Reset the world state for a new episode"""
        # Reset agent positions
        self.positions = {
            agent: np.array([
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            ])
            for agent in agents
        }

        # Initialize trees
        self.trees = {}
        for _ in range(self.n_trees):
            pos = (
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            )
            self.trees[pos] = 3
        
        # Initialize resource counts
        self.wood = 0
        self.fruits = 0
        self.cycle = 0

        # Initialize agent tracking
        self.alive_agents = set(agents)
        self.agent_ages = {agent: 0 for agent in agents}

    def move(self, agent, action: Action):
        # Convention: a position is (x, y) = (pos[0], pos[1]).
        # x is HORIZONTAL (LEFT/RIGHT), y is VERTICAL (UP/DOWN).
        x, y = self.positions[agent]

        if action == Action.UP:
            y = max(0, y - 1)
        elif action == Action.DOWN:
            y = min(self.size - 1, y + 1)
        elif action == Action.LEFT:
            x = max(0, x - 1)
        elif action == Action.RIGHT:
            x = min(self.size - 1, x + 1)

        self.positions[agent] = np.array([x, y])

    def adjacent_tree(self, agent):
        x, y = self.positions[agent]
        for (tx, ty) in self.trees.keys():
            if abs(tx - x) + abs(ty - y) == 1:
                return (tx, ty)
        return None

    def interact(self, agent, resource_manager=None):
        """
        Handle agent interaction with adjacent tree.
        Collectors collect fruits, cutters cut down trees.
        
        Args:
            agent: The agent performing the interaction
            resource_manager: ResourceManager to track wood/fruit collection
            
        Returns:
            dict: Interaction result with type and value
        """
        tree_pos = self.adjacent_tree(agent)

        if tree_pos is None:
            return {"type": "none"}

        # Collector: collect one fruit from the tree
        if "collector" in agent:
            if self.trees[tree_pos] > 0:
                self.trees[tree_pos] -= 1
                if resource_manager:
                    resource_manager.add_fruits(1)
                return {"type": "collect", "value": 1}

        # Cutter: cut down the entire tree
        if "cutter" in agent:
            del self.trees[tree_pos]
            # Fixed wood yield per tree, set in config (fallback to 1 if no config)
            wood_gained = self.config.wood_per_tree if self.config else 1
            if resource_manager:
                resource_manager.add_wood(wood_gained)
            return {"type": "cut", "value": wood_gained}

        return {"type": "none"}

    def spawn_tree(self):
        """
        Attempt to spawn a new tree at a random position.
        Uses configuration for spawn rate and max trees.
        
        Returns:
            bool: True if a tree was spawned, False otherwise
        """
        if self.config is None:
            return False
        
        # Check if we've reached max trees
        if len(self.trees) >= self.config.max_trees:
            return False
        
        # Try to spawn based on probability
        if random.random() < self.config.tree_spawn_rate:
            pos = (
                random.randint(0, self.size - 1),
                random.randint(0, self.size - 1)
            )
            # Make sure position is not already a tree
            if pos not in self.trees:
                self.trees[pos] = 1  # Start with 1 fruit
                return True
        return False

    def step_global(self, resource_manager=None):
        """
        Perform global step updates that happen once per cycle.
        Handles tree regrowth, new tree spawning, and resource consumption.
        
        Args:
            resource_manager: ResourceManager to handle resource consumption
        """
        # Tree regrowth: each tree has a chance to grow more fruit
        if self.config:
            fruit_spawn_rate = self.config.fruit_spawn_rate
            fruit_growth = self.config.fruit_growth_amount
        else:
            fruit_spawn_rate = 0.4
            fruit_growth = 1
        
        for t in list(self.trees.keys()):
            if random.random() < fruit_spawn_rate:
                self.trees[t] += fruit_growth

        # Dynamic tree spawning
        if self.config:
            self.spawn_tree()
        else:
            # Fallback to old behavior if no config
            if len(self.trees) < self.n_trees and random.random() < 0.1:
                pos = (
                    random.randint(0, self.size - 1),
                    random.randint(0, self.size - 1)
                )
                self.trees[pos] = 1
        
        # Store resource_manager reference and update world counts
        if resource_manager:
            self._resource_manager = resource_manager
            # Pass number of alive agents for per-agent consumption
            num_alive = len(self.alive_agents) if hasattr(self, 'alive_agents') else 1
            resource_manager.consume_resources(num_agents=num_alive)
            # Update world's resource counts to match (for renderer access)
            self.wood = resource_manager.wood
            self.fruits = resource_manager.fruits
        
        # Increment agent ages
        for agent in list(self.alive_agents):
            self.agent_ages[agent] = self.agent_ages.get(agent, 0) + 1