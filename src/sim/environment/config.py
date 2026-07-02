# =============================================================================
# BASIC ENVIRONMENT SETTINGS
# =============================================================================
GRID_SIZE = 20                    # Size of the grid (size x size)
INITIAL_TREES = 5                # Initial number of trees at reset
MAX_CYCLES = 10000                # Maximum cycles before termination

# =============================================================================
# RESOURCE SPAWNING SETTINGS
# Controls how trees and fruits spawn dynamically
# =============================================================================
STARTING_FRUIT = 100
STARTING_WOOD  = 50
TREE_SPAWN_RATE = 0.5            # Probability (0-1) to spawn a new tree each cycle
MAX_TREES = 20                   # Maximum number of trees allowed in the world
FRUIT_SPAWN_RATE = 0.4           # Probability (0-1) per tree to grow fruit each cycle
FRUIT_GROWTH_AMOUNT = 1          # Number of fruits added when a tree grows

# =============================================================================
# RESOURCE HARVESTING SETTINGS
# Controls what agents gain when they interact with a tree
# =============================================================================
WOOD_PER_TREE = 5               # Wood a cutter gains from cutting down one tree
CUTTER_FOREST_RESERVE = 0       # Cutters stop cutting at this many trees left (0 = off)

# =============================================================================
# RESOURCE CONSUMPTION SETTINGS
# Controls automatic consumption of wood and fruits over time
# Can be configured as global (total) or per-agent consumption
# =============================================================================
ENABLE_WOOD_CONSUMPTION = True    # Set True to enable wood consumption
WOOD_CONSUMPTION_RATE = 1         # Wood consumed globally each cycle (if USE_PER_AGENT_CONSUMPTION=False)
WOOD_CONSUMPTION_PER_AGENT = 0.2   # Wood consumed PER AGENT each cycle (if USE_PER_AGENT_CONSUMPTION=True)
ENABLE_FRUIT_CONSUMPTION = True   # Set True to enable fruit consumption
FRUIT_CONSUMPTION_RATE = 1        # Fruits consumed globally each cycle (if USE_PER_AGENT_CONSUMPTION=False)
FRUIT_CONSUMPTION_PER_AGENT = 0.2  # Fruits consumed PER AGENT each cycle (if USE_PER_AGENT_CONSUMPTION=True)
USE_PER_AGENT_CONSUMPTION = True  # Set True to use per-agent consumption, False for global

# =============================================================================
# AGENT SPAWNING SETTINGS
# Controls when and how new agents spawn
# =============================================================================
SPAWN_THRESHOLD = 100             # Spawn new agent when wood AND fruits >= this
SPAWN_FRUIT_COST = 20            # Fruits deducted from resources when a new agent spawns
SPAWN_WOOD_COST = 20             # Wood deducted from resources when a new agent spawns
SPAWN_TYPE = "balanced"            # "random", "balanced", "cutter", or "collector"
                                 # "balanced": spawn whichever role currently has fewer agents

# =============================================================================
# AGENT DEATH SETTINGS
# Controls conditions for agent death
# =============================================================================
ENABLE_AGING = True              # Set True to enable death by old age
MAX_AGE = 250                     # Cycles before agent dies from aging
ENABLE_RESOURCE_STARVATION = True # Set True to enable death by resource shortage
COLLECTOR_MIN_FRUITS = 1         # Collector dies if fruits < this (when enabled)
CUTTER_MIN_WOOD = 1              # Cutter dies if wood < this (when enabled)


# =============================================================================
# CORE COMPONENTS
# (These use the constants defined above for default configuration)
# =============================================================================
from environment.reward import RewardFunction, BasicReward
from environment.observation import BasicObservation, ObservationBuilder
from environment.termination import MaxCycleTermination, TerminationCondition



class EnvConfig:
    """
    Configuration class that reads from the module-level constants.
    This allows the existing code to work while users can modify simple constants.
    """
    def __init__(self, reward_fn: RewardFunction|None = None, observation_builder: ObservationBuilder|None = None, termination_conditions: list[TerminationCondition]|None = None):
        # BASIC ENVIRONMENT SETTINGS
        self.size = GRID_SIZE
        self.n_trees = INITIAL_TREES
        self.max_cycles = MAX_CYCLES

        # RESOURCE SPAWNING SETTINGS
        self.tree_spawn_rate = TREE_SPAWN_RATE
        self.max_trees = MAX_TREES
        self.fruit_spawn_rate = FRUIT_SPAWN_RATE
        self.fruit_growth_amount = FRUIT_GROWTH_AMOUNT
        self.starting_fruit = STARTING_FRUIT
        self.starting_wood = STARTING_WOOD

        # RESOURCE HARVESTING SETTINGS
        self.wood_per_tree = WOOD_PER_TREE
        self.cutter_forest_reserve = CUTTER_FOREST_RESERVE

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
        self.spawn_fruit_cost = SPAWN_FRUIT_COST
        self.spawn_wood_cost = SPAWN_WOOD_COST
        self.spawn_type = SPAWN_TYPE

        # AGENT DEATH SETTINGS
        self.enable_aging = ENABLE_AGING
        self.max_age = MAX_AGE
        self.enable_resource_starvation = ENABLE_RESOURCE_STARVATION
        self.collector_min_fruits = COLLECTOR_MIN_FRUITS
        self.cutter_min_wood = CUTTER_MIN_WOOD

        # CORE COMPONENTS
        self.reward_fn = reward_fn if reward_fn is not None else BasicReward()
        self.observation_builder = observation_builder if observation_builder is not None else BasicObservation()
        self.termination_conditions = termination_conditions if termination_conditions is not None else [MaxCycleTermination(self.max_cycles)]
