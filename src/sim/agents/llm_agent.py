from agents.base import BaseAgent
from agents.blackboard import shared_blackboard
from agents.msg import Message
from llm.llmmanager import LLMManager
from environment.actions import Action


class LLMAgent(BaseAgent):
    """
    An LLM-controlled agent. Unlike the other agents, LLM agents can talk to
    each other through the shared blackboard with announce() / listen().
    """

    # The single board shared by all LLM agents. Only LLMs communicate.
    blackboard = shared_blackboard

    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    # --- Communication (LLM agents only) ---------------------------------
    def announce(self, message: Message) -> None:
        """Pin what this agent intends to do so other LLM agents can read it."""
        self.blackboard.post(self.name, message)

    def listen(self) -> dict[str, Message]:
        """Return what every OTHER LLM agent last announced, {name: Message}."""
        return self.blackboard.read(exclude=self.name)

    # --------------------------------------------------------------------
    def act(self, obs, info) -> Action:
        x = obs['x']
        y = obs['y']
        trees = obs['trees']

        # Nearest tree (trees are keyed (x, y), same as agent positions)
        if trees:
            tx, ty = min(trees.keys(), key=lambda t: abs(t[0] - x) + abs(t[1] - y))
            dx = tx - x
            dy = ty - y
        else:
            dx, dy = 0, 0

        # What are the other LLM agents planning? Share it with the model.
        others = self.listen()
        if others:
            others_text = "\n".join(f"- {who}: {plan}" for who, plan in others.items())
        else:
            others_text = "- (nobody has announced anything yet)"

        print(f"x: {x}, y: {y}")
        location_prompt = f"""
You are controlling an agent in a grid world. Both x and y coordinate
have an allowed range of 0 to 4. UP decreases x, DOWN increases x,
LEFT decreases y, RIGHT increases y.
Your current position is x = {x}, y = {y}.
Your goal is to move clockwise in a circle along the edge of the grid.

Other agents have announced these intentions:
{others_text}
"""

        prompt = f"Choose the best action (LEFT, RIGHT, UP, DOWN).\n{location_prompt}"
        action = self.llm.request_action(self.index, prompt)

        # Let the other LLM agents know what we decided to do.
        self.announce(Message(Message.Intention.WALK, action, (x, y)))
        return action
