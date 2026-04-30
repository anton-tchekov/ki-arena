class Logger:
    def log_step(self, agent, obs, action, reward):
        pass

    def log_episode_end(self):
        pass


class PrintLogger(Logger):
    def log_step(self, agent, obs, action, reward):
        print(f"{agent} | action={action} | reward={reward}")

    def log_episode_end(self):
        print("Episode finished\n")