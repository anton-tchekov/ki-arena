from agents.base import BaseAgent
from llm.llmmanager import LLMManager
from environment.actions import Action

class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    def act(self, obs, info) -> Action:
        y, x, dx, dy, _ = obs

        print(f"x: {x}, y: {y}")
        location_prompt = f"""
            You are controlling an agent in a 5x5 grid world.

            Current position:
            - x: {x} (horizontal axis, increases to the RIGHT)
            - y: {y} (vertical axis, increases DOWN)

            Allowed safe zone (preferred region):
            - x ∈ [1, 3]
            - y ∈ [1, 3]

            Movement rules:
            - LEFT  = x - 1
            - RIGHT = x + 1
            - UP    = y - 1
            - DOWN  = y + 1
            """

        prompt = f"Choose the best action (LEFT, RIGHT, UP, DOWN).\n{location_prompt}"

        action = self.llm.request_action(self.index, prompt)

        if x == 3 and action == Action.RIGHT:
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOU MOVED OUTSIDE THE X LIMITS", action)
        elif x == 1 and action == Action.LEFT:
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOU MOVED OUTSIDE THE X LIMITS", action)
        elif y == 3 and action == Action.DOWN:
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOU MOVED OUTSIDE THE Y LIMITS", action)
        elif y == 1 and action == Action.UP:
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOU MOVED OUTSIDE THE Y LIMITS", action)
        elif (x < 1 or x > 3):
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOUR OUTSIDE THE X LIMITS OF [1, 3]", action)
        elif (y < 1 or y > 3):
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "WRONG! YOUR OUTSIDE THE Y LIMITS OF [1, 3]", action)
        else:
            self.llm.give_feedback(self.index, f"You were at x:{x} and y:{y}", "CORRECT! YOUR INSIDE THE LIMITS", action)

        return action