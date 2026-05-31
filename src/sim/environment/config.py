# =============================================================================
# BASIC ENVIRONMENT SETTINGS
# =============================================================================
GRID_SIZE = 20                    # Size of the grid (size x size)
INITIAL_TREES = 5                # Initial number of trees at reset
MAX_CYCLES = 100                # Maximum cycles before termination

# =============================================================================
# RESOURCE SPAWNING SETTINGS
# Controls how trees and fruits spawn dynamically
# =============================================================================
TREE_SPAWN_RATE = 0.1            # Probability (0-1) to spawn a new tree each cycle
MAX_TREES = 10                   # Maximum number of trees allowed in the world
FRUIT_SPAWN_RATE = 0.4           # Probability (0-1) per tree to grow fruit each cycle
FRUIT_GROWTH_AMOUNT = 1          # Number of fruits added when a tree grows

# =============================================================================
# RESOURCE CONSUMPTION SETTINGS
# Controls automatic consumption of wood and fruits over time
# Can be configured as global (total) or per-agent consumption
# =============================================================================
ENABLE_WOOD_CONSUMPTION = True    # Set True to enable wood consumption
WOOD_CONSUMPTION_RATE = 1         # Wood consumed globally each cycle (if USE_PER_AGENT_CONSUMPTION=False)
WOOD_CONSUMPTION_PER_AGENT = 0   # Wood consumed PER AGENT each cycle (if USE_PER_AGENT_CONSUMPTION=True)
ENABLE_FRUIT_CONSUMPTION = True   # Set True to enable fruit consumption
FRUIT_CONSUMPTION_RATE = 1        # Fruits consumed globally each cycle (if USE_PER_AGENT_CONSUMPTION=False)
FRUIT_CONSUMPTION_PER_AGENT = 0  # Fruits consumed PER AGENT each cycle (if USE_PER_AGENT_CONSUMPTION=True)
USE_PER_AGENT_CONSUMPTION = True  # Set True to use per-agent consumption, False for global

# =============================================================================
# AGENT SPAWNING SETTINGS
# Controls when and how new agents spawn
# =============================================================================
SPAWN_THRESHOLD = 10             # Spawn new agent when wood OR fruits >= this
SPAWN_TYPE = "random"            # "random", "cutter", or "collector"

# =============================================================================
# AGENT DEATH SETTINGS
# Controls conditions for agent death
# =============================================================================
ENABLE_AGING = False              # Set True to enable death by old age
MAX_AGE = 50                     # Cycles before agent dies from aging
ENABLE_RESOURCE_STARVATION = False # Set True to enable death by resource shortage
COLLECTOR_MIN_FRUITS = 1         # Collector dies if fruits < this (when enabled)
CUTTER_MIN_WOOD = 1              # Cutter dies if wood < this (when enabled)


# =============================================================================
# CORE COMPONENTS
# (These use the constants defined above for default configuration)
# =============================================================================
from environment.reward import BasicReward
from environment.observation import BasicObservation
from environment.termination import MaxCycleTermination


class EnvConfig:
    """
    Configuration class that reads from the module-level constants.
    This allows the existing code to work while users can modify simple constants.
    """
    def __init__(self):
        # BASIC ENVIRONMENT SETTINGS
        self.size = GRID_SIZE
        self.n_trees = INITIAL_TREES
        self.max_cycles = MAX_CYCLES

        # RESOURCE SPAWNING SETTINGS
        self.tree_spawn_rate = TREE_SPAWN_RATE
        self.max_trees = MAX_TREES
        self.fruit_spawn_rate = FRUIT_SPAWN_RATE
        self.fruit_growth_amount = FRUIT_GROWTH_AMOUNT

        # RESOURCE CONSUMPTION SETTINGS
        self.enable_wood_consumption = ENABLE_WOOD_CONSUMPTION
        self.wood_consumption_rate = WOOD_CONSUMPTION_RATE
        self.wood_consumption_per_agent = WOOD_CONSUMPTION_PER_AGENT
        self.enable_fruit_consumption = ENABLE_FRUIT_CONSUMPTION
        self.fruit_consumption_rate = FRUIT_CONSUMPTION_RATE
        self.fruit_consumption_per_agent = FRUIT_CONSUMPTION_PER_AGENT
        self.use_per_agent_consumption = USE_PER_AGENT_CONSUMPTION

        # AGENT SPAWNING SETTINGS
        self.spawn_threshold = SPAWN_THRESHOLD
        self.spawn_type = SPAWN_TYPE

        # AGENT DEATH SETTINGS
        self.enable_aging = ENABLE_AGING
        self.max_age = MAX_AGE
        self.enable_resource_starvation = ENABLE_RESOURCE_STARVATION
        self.collector_min_fruits = COLLECTOR_MIN_FRUITS
        self.cutter_min_wood = CUTTER_MIN_WOOD

        # CORE COMPONENTS
        self.reward_fn = BasicReward()
        self.observation_builder = BasicObservation()
        self.termination_conditions = [MaxCycleTermination(self.max_cycles)]
