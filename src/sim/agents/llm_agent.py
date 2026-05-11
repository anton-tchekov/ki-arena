from agents.base import BaseAgent
from llm.llmmanager import LLMManager
from environment.actions import Action

class LLMAgent(BaseAgent):
    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    def act(self, obs, info) -> Action:
        print("act called")
        return self.llm.request_action(self.index, "Choose a direction to move to")