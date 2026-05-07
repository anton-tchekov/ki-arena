from sim.environment.env_grid import GridForestEnv
from sim.analysis.logger import Logger
from sim.agents.base import BaseAgent

class EpisodeRunner:
    def __init__(self, env: GridForestEnv, agents:dict, logger:Logger=None):
        self.env = env
        self.agents = agents
        self.logger = logger

    def run_episode(self, render=False):
        self.env.reset()

        last_rewards = {a: 0 for a in self.agents}

        for agent_name in self.env.agent_iter():
            obs = self.env.observe(agent_name)
            info = self.env.infos[agent_name]

            agent:BaseAgent = self.agents[agent_name]

            agent.observe(
                obs,
                last_rewards[agent_name],
                self.env.terminations[agent_name],
                info
            )

            if self.env.terminations[agent_name] or self.env.truncations[agent_name]:
                action = None
            else:
                action = agent.act(obs, info)

            self.env.step(action)

            reward = self.env.rewards[agent_name]
            last_rewards[agent_name] = reward

            if self.logger:
                self.logger.log_step(agent_name, obs, action, reward)

            if render:
                self.env.render()

        for agent in self.agents.values():
            agent.on_episode_end()

        if self.logger:
            self.logger.log_episode_end()