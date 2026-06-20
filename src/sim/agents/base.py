from environment.actions import Action


class BaseAgent:
    def __init__(self, name: str) -> None:
        self.name: str = name

    def act(self, obs: dict, info: dict) -> Action:
        raise NotImplementedError

    def observe(self, obs: dict, reward: float, done: bool, info: dict) -> None:
        pass

    def reset(self) -> None:
        pass

    def on_episode_end(self) -> None:
        pass
