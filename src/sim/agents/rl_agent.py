from sim.agents.base import BaseAgent

class RLAgent(BaseAgent):
    def __init__(self, name, model):
        super().__init__(name)
        self.model = model

    def act(self, obs, info):
        action, _ = self.model.predict(obs, deterministic=True)
        return action

    def observe(self, obs, reward, done, info):
        # optional: store transitions if not handled by framework
        pass