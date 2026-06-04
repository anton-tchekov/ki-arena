from environment.env_grid import GridForestEnv
from analysis.logger import Logger
from agents.base import BaseAgent
from agents.rule_agent import GreedyCollector, GreedyCutter

class EpisodeRunner:
    def __init__(self, env: GridForestEnv, agents:dict, logger:Logger=None):
        self.env = env
        self.agents = agents
        self.logger = logger
        self._dynamic_agents = {}  # Cache for dynamically created agents

    def run_episode(self, render=False):
        self.env.reset()

        last_rewards = {a: 0 for a in self.agents}
        
        # Limit total steps to prevent infinite loops
        # Each cycle = len(agents) steps, so max_cycles * len(agents) * 2 is a safe bound
        max_cycles = self.env.config.max_cycles if hasattr(self.env, 'config') else 100
        max_steps = max_cycles * len(self.env.agents) * 2
        step_count = 0

        for agent_name in self.env.agent_iter(max_iter=max_steps):
            # Check if this is a dynamically spawned agent
            if agent_name not in self.agents:
                # Create a dynamic agent based on its type from the environment
                if agent_name not in self._dynamic_agents:
                    agent_type = getattr(self.env, 'agent_types', {}).get(agent_name, 'collector')
                    if 'cutter' in agent_type:
                        self._dynamic_agents[agent_name] = GreedyCutter(agent_name)
                    else:
                        self._dynamic_agents[agent_name] = GreedyCollector(agent_name)
                
                agent = self._dynamic_agents[agent_name]
            else:
                agent = self.agents[agent_name]
            
            obs = self.env.observe(agent_name)
            info = self.env.infos[agent_name]

            agent.observe(
                obs,
                last_rewards.get(agent_name, 0),
                self.env.terminations.get(agent_name, False),
                info
            )

            is_done = (self.env.terminations[agent_name] or self.env.truncations[agent_name])

            if is_done:
                action = None
            else:
                action = agent.act(obs, info)

            self.env.step(action)

            reward = self.env.rewards.get(agent_name, 0)
            last_rewards[agent_name] = reward
            step_count += 1

            if self.logger:
                self.logger.log_step(agent_name, obs, action, reward)

            if render:
                self.env.render()
            
            # Safety check for infinite loops
            if step_count >= max_steps:
                print("Warning: Maximum steps reached, breaking to prevent infinite loop")
                break

        for agent in self.agents.values():
            agent.on_episode_end()
        for agent in self._dynamic_agents.values():
            agent.on_episode_end()
        self._dynamic_agents.clear()  # Clear for next episode

        if self.logger:
            self.logger.log_episode_end()