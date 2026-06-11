from agents.base import BaseAgent
from llm.llmmanager import LLMManager
from environment.actions import Action

class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    def act(self, obs, info) -> Action:
        _, _, dy, dx, fruit_on_tree, _, _ = obs

        # ToDo: Improve later
        x = int(dx)
        y = int(dy)

        print(f"dx: {x}, dy: {y}")
        location_prompt = f"""You are an agent in a game. You are given target coordinates relative to your position: dx and dy.
            Move until your Manhattan distance to the target is exactly 1:
            abs(dx) + abs(dy) == 1
            When this condition is met, immediately choose the action INTERACT.
            When x positive it means you need to move right, when y positive is that means you need to move down. Same but reversed for negative values. Do not move diagonally.
            Do not interact before reaching Manhattan distance 1.
            
            You are a collector agent, so you want to interact when next to a tree with fruits (fruit_on_tree={fruit_on_tree}).
            Your current relative position to the target is dx={x}, dy={y}."""

        prompt = f"Choose the best action from given options.\n{location_prompt}"
        action = self.llm.request_action(self.index, prompt)
        return action
