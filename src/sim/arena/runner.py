from environment.env_grid import GridForestEnv
from environment.state_history import StateHistory
from analysis.logger import Logger
from agents.blackboard import shared_blackboard
from agents.rule_agent import GreedyCollector, GreedyCutter


class EpisodeRunner:
    def __init__(self, env: GridForestEnv, agents: dict, logger: Logger | None = None):
        self.env = env
        self.agents = agents
        self.logger = logger
        self._dynamic_agents = {}

    def _resolve_agent(self, agent_name: str):
        if agent_name in self.agents:
            return self.agents[agent_name]
        if agent_name not in self._dynamic_agents:
            agent_type = getattr(self.env, "agent_types", {}).get(agent_name, "collector")
            cls = GreedyCutter if "cutter" in agent_type else GreedyCollector
            self._dynamic_agents[agent_name] = cls(agent_name)
        return self._dynamic_agents[agent_name]

    def run_episode(self, render=False, training=False):
        self.env.reset()
        shared_blackboard.clear()  # start each episode with an empty notice board
        last_rewards: dict[str, float] = {a: 0 for a in self.agents}

        max_cycles = getattr(self.env.config, "max_cycles", 100)
        max_steps = max_cycles * len(self.env.possible_agents) * 2

        # Create a fresh history and wire it to the renderer for browsing
        state_history = StateHistory()
        if render:
            self.env.renderer.state_history = state_history
            self.env.renderer.blackboard = shared_blackboard

        while True:
            must_restart = False
            prev_cycle = self.env.cycle

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
                    shared_blackboard.remove(agent_name)  # dead agents stop announcing
                    self.env.step(None)
                    continue

                action = agent.act(obs, info)
                self.env.step(action)

                post_done = (
                    self.env.terminations.get(agent_name, True)
                    or self.env.truncations.get(agent_name, True)
                )
                next_obs = None if post_done else self.env.observe(agent_name)

                reward = self.env.rewards.get(agent_name, 0)
                last_rewards[agent_name] = reward

                if hasattr(agent, "after_action"):
                    agent.after_action(obs, action, reward, next_obs, post_done, info)

                if self.logger and not training:
                    self.logger.log_step(agent_name, obs, action, reward)

                if render:
                    # Save a snapshot at every cycle boundary
                    if self.env.cycle != prev_cycle:
                        state_history.save(self.env)
                        prev_cycle = self.env.cycle

                    self.env.render()

                    # Check if user resumed from a past snapshot
                    cp = self.env.renderer.control_panel
                    if cp.needs_restore:
                        idx = cp.view_index
                        state_history.restore(self.env, idx)
                        state_history.truncate_after(idx)
                        cp.needs_restore = False
                        # Reset per-episode tracking to match restored state
                        self._dynamic_agents.clear()
                        last_rewards = {a: 0 for a in self.env.agents}
                        prev_cycle = self.env.cycle
                        must_restart = True
                        break

            if not must_restart:
                break
            # else: restart agent_iter from the restored env state

        for agent in self.agents.values():
            agent.on_episode_end()
        for agent in self._dynamic_agents.values():
            agent.on_episode_end()
        self._dynamic_agents.clear()

        if self.logger and not training:
            self.logger.log_episode_end(self.env)
