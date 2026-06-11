from agents.base import BaseAgent
from llm.llmmanager import LLMManager
from environment.actions import Action

class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    def act(self, obs, info) -> Action:
        x = obs['x']
        y = obs['y']
        dx = obs['dx']
        dy = obs['dy']

        print(f"x: {x}, y: {y}")
        location_prompt = f"""
You are controlling an agent in a grid world. Both x and y coordinate
have an allowed range of 0 to 4. UP decreases y, DOWN increases y.
Your current position is x = {x}, y = {y}.
Your goal is to move clockwise in a circle along the edge of the grid.
"""

        prompt = f"Choose the best action (LEFT, RIGHT, UP, DOWN).\n{location_prompt}"
        action = self.llm.request_action(self.index, prompt)
        return action
