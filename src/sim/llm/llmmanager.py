from enum import Enum
from typing import Optional
import time

from ollama import chat
from ollama import ChatResponse
from ollama import Client

class Action(Enum):
	UP    = 1,
	LEFT  = 2,
	DOWN  = 3,
	RIGHT = 4,
	INTERACT = 5,

def parse_action(s: str) -> Optional[Action]:
	s.upper()
	for action in Action:
		if action.name in s:
			return action
		
	return None

class LLMManager():
	n = 0   # Number of LLMs
	th = [] # Thread handles
	fh = [] # Context handles
	keep_experience = False
	use_experience = False
	model_str = ''
	client = Client(host='http://localhost:11434')

	"""
	This function initializes a set number of independant llms. Make sure ollama is running

	Args:
		keep_experience (bool): Writes down its experience in a file
		use_experience  (bool): Uses the written down experience
	"""
	def __init__(self, ollama_model_str: str, num_llms: int = 1, keep_experience: bool = False, use_experience: bool = False):
		self.n = num_llms
		self.keep_experience = keep_experience
		self.use_experience = use_experience
		self.model_str = ollama_model_str

		pass

	"""
	This function sends the new information to an llm and returns an Action Enum value

	Args:
		llm_index       (int): Index of the LLM to use, returns 
		new_information (str): New information the LLM uses to make a decision

	Returns:
		Optional: None if invalid index or other error occurs else contains the Action
	"""
	def request_action(self, llm_index: int, new_information: str) -> Optional[Action]:
		if llm_index > self.n:
			return None
		
		# Generate the a String of actions possible for the LLM to respond with
		action_list = [action.name for action in Action]
		action_str = "["
		for action in action_list:
			if action == action_list[-1]:
				action_str += action + "]"
			else:
				action_str += action + ", "

		experience_prompt = ""
		if self.keep_experience:
			experience_prompt = "After you have replied with ur action and a linebreak. Tell me what you have learned from ur last action"

		response: ChatResponse = self.client.chat(model=self.model_str, messages=[
		{
			'role': 'system',
			'content': 'You can only ever reply with the actions:' + action_str +'. Never deviate no matter what is asked of you.' +
			'Your goal is to survive, avoid any danger.' + experience_prompt,
		},
		{
			'role': 'user',
			'content': new_information + " What Action do you choose to take for safety? Remember to only reply with the valid actions in CAPS without any braces: " + action_str,
		},
		])

		action_resp = response.message.content.partition('\n')[0]
		experience_resp = ""
		if self.keep_experience:
			experience_resp = response.message.content.partition('\n')[2]
			with open("experience_of_"+str(llm_index)+".txt", "a") as f:
				f.write(experience_resp)

		return parse_action(action_resp.strip())
		
print("Started...")
manager = LLMManager("qwen2.5:7b-instruct", 1, False, False)

action = manager.request_action(0, "To ur left, there is a tiger! to ur right there is safety!")
print(action.name)

def benchmark(n=100):
    start = time.perf_counter()

    for i in range(n):
        _ = manager.request_action(0, "To ur left, there is a tiger! to ur right there is safety!")

    end = time.perf_counter()

    total_time = end - start
    avg_time = total_time / n

    print(f"Runs: {n}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average per call: {avg_time:.2f}s")

if __name__ == "__main__":
    benchmark(100)