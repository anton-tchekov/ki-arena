from agents.blackboard import Blackboard
from agents.msg import Message
from environment.actions import Action


class BaseAgent:
    # One notice board shared by every agent, so communication works with no
    # setup at all. The runner wipes it clean at the start of each episode.
    blackboard: Blackboard = Blackboard()

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

    # -----------------------------------------------------------------
    # Talking to other agents (the blackboard)
    # Nachrichten bleiben nur ein Cycle lang im Blackboard
    #
    # Use these two helpers inside act() to coordinate with the others.
    # A message is a Message (see msg.py): an intention + the action you'll take.
    # Example:
    #
    #     def act(self, obs, info):
    #         # 1) tell everyone what I'm about to do
    #         self.announce(Message(Message.Intention.WALK, Action.UP))
    #
    #         # 2) see what everyone else announced
    #         for who, plan in self.listen().items():
    #             print(who, "plans to:", plan)
    #
    #         return Action.UP
    # -----------------------------------------------------------------

    def announce(self, message: Message) -> None:
        """Tell the other agents what you intend to do. Build the Message with
        an intention and the action you'll take, e.g.
        Message(Message.Intention.COLLECT, Action.INTERACT). Overwrites your
        previous one."""
        self.blackboard.post(self.name, message)

    def listen(self) -> dict[str, Message]:
        """Return what every OTHER agent last announced, as a
        {agent_name: Message} dictionary. Empty if nobody has spoken."""
        return self.blackboard.read(exclude=self.name)
