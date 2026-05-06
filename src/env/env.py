from pettingzoo.utils.env import AECEnv
from pettingzoo.utils.agent_selector import agent_selector
from gymnasium import spaces

from world import GridWorld
from config import EnvConfig
from agents.base import BaseAgent
#from config import EnvConfig


class GridForestEnv(AECEnv):
    metadata = {"name": "grid_forest_v1"}

    def __init__(self, config: EnvConfig):
        super().__init__()

        self.config = config
        self.world = GridWorld(config.size, config.n_trees)

        # Load data from config file
        self.reward_fn = config.reward_fn
        self.obs_builder = config.observation_builder
        self.termination_conditions = config.termination_conditions

        # Initialise data
        self.possible_agents = ["cutter_0", "collector_0"]
        self.agents = self.possible_agents[:]

        self._action_spaces = {
            agent: spaces.Discrete(6) for agent in self.agents
        }

        self._observation_spaces = {
            agent: spaces.Box(
                low=-config.size,
                high=config.size,
                shape=(5,),
                dtype=float
            )
            for agent in self.agents
        }

    def observation_space(self, agent: BaseAgent):
        return self._observation_spaces[agent]

    def action_space(self, agent: BaseAgent):
        return self._action_spaces[agent]

    def reset(self, seed=None, options=None):
        self.agents = self.possible_agents[:]

        self.rewards = {a: 0 for a in self.agents}
        self._cumulative_rewards = {a: 0 for a in self.agents}
        self.terminations = {a: False for a in self.agents}
        self.truncations = {a: False for a in self.agents}
        self.infos = {a: {} for a in self.agents}

        self.cycle = 0

        self.world.reset(self.agents)

        self._agent_selector = agent_selector(self.agents)
        self.agent_selection = self._agent_selector.next()

    def observe(self, agent: BaseAgent):
        return self.obs_builder.build(self.world, agent)

    def step(self, action):
        agent = self.agent_selection

        if self.terminations[agent] or self.truncations[agent]:
            self.agent_selection = self._agent_selector.next()
            return

        self.rewards[agent] = 0

        result = None

        if action in [1, 2, 3, 4]:
            self.world.move(agent, action)
        elif action == 5:
            result = self.world.interact(agent)

        # reward
        r = self.reward_fn.compute(self.world, agent, action, result)
        self.rewards[agent] += r

        # global step
        if self._agent_selector.is_last():
            self.world.step_global()
            self.cycle += 1

            for cond in self.termination_conditions:
                if cond.check(self.world, self.cycle):
                    self.truncations = {a: True for a in self.agents}

        self._accumulate_rewards()
        self.agent_selection = self._agent_selector.next()