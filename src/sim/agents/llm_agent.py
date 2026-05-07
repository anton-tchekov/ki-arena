from sim.agents.base import BaseAgent

class LLMAgent(BaseAgent):
    def __init__(self, name, llm, prompt_builder):
        super().__init__(name)
        self.llm = llm
        self.prompt_builder = prompt_builder

    def act(self, obs, info):
        prompt = self.prompt_builder(obs, info)
        response = self.llm(prompt)
        return self.parse(response)

    def parse(self, text):
        # TODO: robust parsing
        return int(text.strip())