"""
Resource Manager - Tracks global wood and fruit resources and handles consumption.
This keeps resource tracking separate from the world grid for cleaner architecture.
"""


class ResourceManager:
    """
    Manages global resource counters (wood and fruits) and handles
    consumption over time based on configuration.
    """
    
    def __init__(self, config):
        """
        Initialize resource manager with configuration.
        
        Args:
            config: EnvConfig object containing consumption and spawn configurations
        """
        self.config = config
        self.wood = config.starting_wood
        self.fruits = config.starting_fruit
        self.cycle = 0

        # Cumulative end-of-run statistics (never consumed, only grow)
        self.total_wood_cut = 0        # total wood obtained from cutting trees
        self.total_fruit_collected = 0  # total fruit collected from trees
        self.trees_cut = 0             # number of trees cut down
        self.fruit_collect_count = 0   # number of fruit-collect actions

    def add_wood(self, amount=1):
        """Add wood to the global wood counter (one tree was cut)."""
        self.wood += amount
        self.total_wood_cut += amount
        self.trees_cut += 1

    def add_fruits(self, amount=1):
        """Add fruits to the global fruits counter (one fruit was collected)."""
        self.fruits += amount
        self.total_fruit_collected += amount
        self.fruit_collect_count += 1
    
    def consume_resources(self, num_agents=1):
        """
        Consume wood and fruits based on configuration.
        Called once per cycle during the global step.
        
        Args:
            num_agents: Number of agents to use for per-agent consumption calculation
        """
        # Determine consumption amounts based on configuration
        if self.config.use_per_agent_consumption:
            # Per-agent consumption
            wood_amount = self.config.wood_consumption_per_agent * num_agents
            fruit_amount = self.config.fruit_consumption_per_agent * num_agents
        else:
            # Global consumption
            wood_amount = self.config.wood_consumption_rate
            fruit_amount = self.config.fruit_consumption_rate
        
        # Consume wood
        if self.config.enable_wood_consumption:
            self.wood = max(0, self.wood - wood_amount)
        
        # Consume fruits
        if self.config.enable_fruit_consumption:
            self.fruits = max(0, self.fruits - fruit_amount)
    
    def should_spawn_agent(self):
        """
        Check if resources have reached the threshold for spawning a new agent.

        Returns:
            bool: True if wood AND fruits >= spawn_threshold
        """
        threshold = self.config.spawn_threshold
        return self.wood >= threshold and self.fruits >= threshold
    
    def step(self):
        """Increment the cycle counter"""
        self.cycle += 1
    
    def get_state(self):
        """
        Get the current resource state as a dictionary.
        Useful for debugging and observation building.
        
        Returns:
            dict: Current wood and fruit counts
        """
        return {
            "wood": self.wood,
            "fruits": self.fruits
        }
