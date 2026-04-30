class BaseAgent:
    def __init__(self, name):
        self.name = name

    def act(self, obs, info):
        raise NotImplementedError

    def observe(self, obs, reward, done, info):
        pass

    def reset(self):
        pass

    def on_episode_end(self):
        pass