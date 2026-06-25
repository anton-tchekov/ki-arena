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

        #print(f"dx: {x}, dy: {y}")
        location_prompt = f"""
            You are an agent in a game. You are given target coordinates relative to your position: x: {dy} and y: {dx}.
            Move until your Manhattan distance to the target is exactly 1:
            abs(x) + abs(y) == 1
            When this condition is met, immediately choose the action INTERACT.
            The Interact action does not work if you are diagonally adjacent to the target, or if you are directly on the target so make sure to only interact when either x or y is 0 (not both).
            Do not interact before reaching Manhattan distance 1.
            If x < 0 then move LEFT
            if x > 0 then move RIGHT
            if y < 0 move UP
            if y > 0 move DOWN
            if abs(x) + abs(y) == 1 then INTERACT
            """
        prompt = f"Choose the best action from given options.\n{location_prompt}"
        action = self.llm.request_action(self.index, prompt)
        return action
