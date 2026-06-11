from environment.env_grid import GridForestEnv
from analysis.logger import Logger
from agents.base import BaseAgent
from agents.rule_agent import GreedyCollector, GreedyCutter


class EpisodeRunner:
    def __init__(self, env: GridForestEnv, agents: dict, logger: Logger|None = None):
        self.env = env
        self.agents = agents
        self.logger = logger
        self._dynamic_agents = {}

    def _resolve_agent(self, agent_name: str):
        """
        Return the policy object for agent_name, creating a dynamic one if needed.
        """
        if agent_name in self.agents:
            return self.agents[agent_name]
        if agent_name not in self._dynamic_agents:
            agent_type = getattr(self.env, "agent_types", {}).get(agent_name, "collector")
            cls = GreedyCutter if "cutter" in agent_type else GreedyCollector
            self._dynamic_agents[agent_name] = cls(agent_name)
        return self._dynamic_agents[agent_name]

    def run_episode(self, render=False):
        self.env.reset()
        last_rewards: dict[str, float] = {a: 0 for a in self.agents}

        max_cycles = getattr(self.env.config, "max_cycles", 100)
        max_steps = max_cycles * len(self.env.possible_agents) * 2

        for agent_name in self.env.agent_iter(max_iter=max_steps):
            agent = self._resolve_agent(agent_name)
            obs = self.env.observe(agent_name)
            info = self.env.infos[agent_name]

            is_done = (
                self.env.terminations[agent_name]
                or self.env.truncations[agent_name]
            )

            agent.observe(obs, last_rewards.get(agent_name, 0), is_done, info)

            if is_done:
                self.env.step(None)  # required by PettingZoo to remove agent
                continue             # skip reward/logging for dead agents

            action = agent.act(obs, info)
            self.env.step(action)

            # read post-step done state before calling observe on next_obs
            post_done = (
                self.env.terminations.get(agent_name, True)
                or self.env.truncations.get(agent_name, True)
            )
            next_obs = None if post_done else self.env.observe(agent_name)

            reward = self.env.rewards.get(agent_name, 0)
            last_rewards[agent_name] = reward

            # after_action feeds the RL buffer
            if hasattr(agent, "after_action"):
                agent.after_action(obs, action, reward, next_obs, post_done, info)

            if self.logger:
                self.logger.log_step(agent_name, obs, action, reward)
            if render:
                self.env.render()

        # on_episode_end is a cleanup hook; for RLAgent it's intentionally a no-op
        # so transitions survive until TrainingPhase calls train_step()
        for agent in self.agents.values():
            agent.on_episode_end()
        for agent in self._dynamic_agents.values():
            agent.on_episode_end()
        self._dynamic_agents.clear()

        if self.logger:
            self.logger.log_episode_end()