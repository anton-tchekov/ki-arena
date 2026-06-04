from logging import config
import random
import numpy as np

from pettingzoo.utils.env import AECEnv
from pettingzoo.utils.agent_selector import agent_selector
from gymnasium import spaces

from environment.world_grid import GridWorld
from environment.config import EnvConfig
from environment.renderer import GridWorldRenderer
from environment.resource_manager import ResourceManager
from agents.base import BaseAgent
from environment.actions import Action
#from config import EnvConfig


class GridForestEnv(AECEnv):
    metadata = {"name": "grid_forest_v1"}

    def __init__(self, config: EnvConfig):
        super().__init__()

        self.config = config
        self.world = GridWorld(config.size, config.n_trees, config)
        self.renderer = GridWorldRenderer()
        
        # Resource manager for tracking wood and fruits
        self.resource_manager = ResourceManager(config)

        # Load data from config file
        self.reward_fn = config.reward_fn
        self.obs_builder = config.observation_builder
        self.termination_conditions = config.termination_conditions

        # Initialise data
        self.possible_agents = ["cutter_0", "collector_0"] # add "cutter_1" for llm
        self.agents = self.possible_agents[:]
        
        # Track agent types (cutter or collector)
        self.agent_types = {
            "cutter_0": "cutter",
            "collector_0": "collector"
        }

        self._action_spaces = {
            agent: spaces.Discrete(6) for agent in self.agents
        }

        self._observation_spaces = {
            agent: spaces.Box(
                low=-config.size,
                high=config.size * 10,  # Allow room for resource counts
                shape=(7,),
                dtype=float
            )
            for agent in self.agents
        }

    def observation_space(self, agent: BaseAgent):
        return self._observation_spaces[agent]

    def action_space(self, agent: BaseAgent):
        return self._action_spaces[agent]

    def reset(self, seed=None, options=None):
        """Reset the environment for a new episode"""
        # Reset to initial agents
        self.agents = self.possible_agents[:]

        self.rewards = {a: 0 for a in self.agents}
        self._cumulative_rewards = {a: 0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}

        self.cycle = 0
        
        # Reset resource manager
        self.resource_manager = ResourceManager(self.config)
        
        # Initialize agent tracking in world
        self.world.alive_agents = set(self.agents)
        self.world.agent_ages = {a: 0 for a in self.agents}

        self.world.reset(self.agents)

        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.next()

    def observe(self, agent: BaseAgent):
        return self.obs_builder.build(self.world, agent)

    def step(self, action):
        """Execute one time step in the environment"""
        agent = self.agent_selection

        # ToDo: the _wa_dead_step is a proper way to handle dead agents, but if we need all_done flag or specifically selecting agents then we could comment in the next lines
        #all_done = all(
        #    self.terminations.get(a, False) or self.truncations.get(a, False)
        #    for a in self.agents
        #)

        # If this agent is already done, skip to next
        #if self.terminations.get(agent, False) or self.truncations.get(agent, False):
            # Try to get next agent if available
        #    if len(self.agents) > 0 and len(self._agent_selector.agent_order) > 0:
        #       self.agent_selection = self._agent_selector.next()
        #   return
        
        if self.terminations[agent] or self.truncations[agent]:
            #self.agent_selection = self._agent_selector.next()
            self._was_dead_step(action)  

        self.rewards[agent] = 0

        result = None

        # Handle INTERACT separately from movement actions
        if action == Action.INTERACT:
            # Pass resource_manager to interact so resources are tracked
            result = self.world.interact(agent, self.resource_manager)
        elif action in Action:
            # Movement actions (UP, DOWN, LEFT, RIGHT)
            self.world.move(agent, action)

        # reward
        r = self.reward_fn.compute(self.world, agent, action, result)
        self.rewards[agent] += r

        # global step - happens once all agents have taken their turn
        if self._agent_selector.is_last():
            self.world.step_global(self.resource_manager)
            self.cycle += 1
            # Sync cycle to world for renderer access
            self.world.cycle = self.cycle
            
            # Try to spawn new agents if resources are sufficient
            self._try_spawn_agent()
            
            # Check all agents for death conditions
            self._check_all_agents_death()
            
            # Recreate agent selector after any agent changes
            if len(self.agents) == 0:
                # If no agents left, mark all as terminated
                for a in self.possible_agents:
                    self.terminations[a] = True
                    self.truncations[a] = True
                # Update agent selector to empty
                self._agent_selector = agent_selector([])
            elif len(self.agents) != len(self._agent_selector.agent_order):
                self._agent_selector = agent_selector(self.agents)

            for cond in self.termination_conditions:
                if cond.check(self.world, self.cycle):
                    self.truncations = {a: True for a in self.agents}

        self._accumulate_rewards()
        
        # Advance to next agent for the next iteration
        if len(self.agents) > 0 and len(self._agent_selector.agent_order) > 0:
            self.agent_selection = self._agent_selector.next()

    def _try_spawn_agent(self):
        """
        Attempt to spawn a new agent if resources meet the threshold.
        Agent type is determined by configuration (random, cutter, or collector).
        """
        if not self.resource_manager.should_spawn_agent():
            return
        
        # Determine agent type from config
        if self.config.spawn_type == "random":
            agent_type = random.choice(["cutter", "collector"])
        else:
            agent_type = self.config.spawn_type
        
        # Find the next available index for this agent type
        base_name = f"{agent_type}_"
        max_index = 0
        for agent in self.possible_agents:
            if agent.startswith(base_name):
                try:
                    # Extract the number from agent name like "cutter_0", "cutter_1", etc.
                    idx = int(agent[len(base_name):])
                    max_index = max(max_index, idx + 1)
                except ValueError:
                    # If agent name doesn't follow pattern, skip
                    pass
        
        new_agent_name = f"{agent_type}_{max_index}"
        
        # Add to possible agents and current agents
        self.possible_agents.append(new_agent_name)
        self.agents.append(new_agent_name)
        self.agent_types[new_agent_name] = agent_type
        
        # Initialize agent state
        self.rewards[new_agent_name] = 0
        self._cumulative_rewards[new_agent_name] = 0
        self.terminations[new_agent_name] = False
        self.truncations[new_agent_name] = False
        self.infos[new_agent_name] = {}
        
        # Add to world tracking
        self.world.alive_agents.add(new_agent_name)
        self.world.agent_ages[new_agent_name] = 0
        self.world.positions[new_agent_name] = np.array([
            random.randint(0, self.world.size - 1),
            random.randint(0, self.world.size - 1)
        ])
        
        # Create action and observation spaces for the new agent
        self._action_spaces[new_agent_name] = spaces.Discrete(6)
        self._observation_spaces[new_agent_name] = spaces.Box(
            low=-self.config.size,
            high=self.config.size * 10,
            shape=(7,),
            dtype=float
        )
        
        # Recreate agent selector with updated agents list
        self._agent_selector = agent_selector(self.agents)

    def _check_all_agents_death(self):
        """
        Check all agents for death conditions and remove dead agents.
        Called once per cycle during the global step.
        """
        agents_to_remove = []
        
        for agent in list(self.agents):
            if self._should_agent_die(agent):
                agents_to_remove.append(agent)
        
        for agent in agents_to_remove:
            self._remove_agent(agent)

    def _should_agent_die(self, agent):
        """
        Check if an agent should die based on configuration.
        
        Args:
            agent: The agent name to check
            
        Returns:
            bool: True if agent should die, False otherwise
        """
        agent_type = self.agent_types.get(agent, "collector")
        
        # Check aging death
        if self.config.enable_aging:
            if self.world.agent_ages.get(agent, 0) >= self.config.max_age:
                return True
        
        # Check resource starvation death
        if self.config.enable_resource_starvation:
            if agent_type == "collector":
                if self.resource_manager.fruits < self.config.collector_min_fruits:
                    return True
            elif agent_type == "cutter":
                if self.resource_manager.wood < self.config.cutter_min_wood:
                    return True
        
        return False

    def _remove_agent(self, agent):
        """
        Remove an agent from the environment when it dies.
        
        Args:
            agent: The agent name to remove
        """
        # Remove from current agents list (but keep in possible_agents for reset)
        if agent in self.agents:
            self.agents.remove(agent)
        
        # Remove from world tracking
        if agent in self.world.alive_agents:
            self.world.alive_agents.remove(agent)
        if agent in self.world.agent_ages:
            del self.world.agent_ages[agent]
        if agent in self.world.positions:
            del self.world.positions[agent]
        
        # Mark as terminated
        self.terminations[agent] = True
        self.truncations[agent] = True
        
        # Recreate agent selector with updated agents list
        if len(self.agents) > 0:
            self._agent_selector = agent_selector(self.agents)
            self.agent_selection = self._agent_selector.next()

    def render(self, config=None):
        self.renderer.render(self.world, config)
