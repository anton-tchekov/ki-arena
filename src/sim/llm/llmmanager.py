from typing import Optional
import time
import os

from ollama import chat
from ollama import ChatResponse
from ollama import Client

from environment.actions import Action

class LLMManager():
	n = 0   # Number of LLMs
	th = [] # Thread handles
	fh = [] # Context handles
	keep_experience = False
	use_experience = False
	model_str = ''
	client = Client(host='http://localhost:11434')
	sys_prompt = ""

	"""
	This function initializes a set number of independant llms. Make sure ollama is running

	Args:
		use_experience  (bool): Uses the written down experience
	"""
	def __init__(self, ollama_model_str: str, use_experience: bool = False):
		self.use_experience = use_experience
		self.model_str = ollama_model_str
		os.makedirs("feedback", exist_ok=True)
		pass

	def set_sys_prompt(self, prompt: str):
		self.sys_prompt = prompt

	"""
	Simply searches for an action substring in a string
	"""
	def parse_action(self, s: str) -> Optional[Action]:
		s.upper()
		for action in Action:
			if action.name in s:
				return action
			
		return None

	"""
	This function sends the new information to an llm and returns an Action Enum value

	Args:
		llm_index       (int): Index of the LLM to use, returns 
		prompt (str): New information the LLM uses to make a decision

	Returns:
		Optional: None if invalid index or other error occurs else contains the Action
	"""
	def request_action(self, llm_index: int, prompt: str) -> Optional[Action]:
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

		# Grab the feedback file
		feedback_file_path = "feedback/feedback_for_" + str(llm_index) + ".txt"
		with open(feedback_file_path, 'a+') as file:
			feedback_content = file.read()

		if self.use_experience:
			feedback_prompt = " Your past feedback includes: " + feedback_content
		else:
			feedback_prompt = ""

		# Send the system prompt alongside the user prompt
		response: ChatResponse = self.client.chat(model=self.model_str, messages=[
		{
			'role': 'system',
			'content': 'You can only ever reply with the actions:' + action_str +'. Never deviate no matter what is asked of you.' +
			self.sys_prompt,
		},
		{
			'role': 'user',
			'content': prompt + " What Action do you choose to take?" + feedback_prompt,
		},
		])

		# Parse the action from the response
		action_resp = response.message.content.partition('\n')[0]
		return self.parse_action(action_resp)
	
	def give_feedback(self, llm_index: int, info: str, feedback: str, chosen_action: Action):
		with open("feedback/feedback_for_"+str(llm_index)+".txt", "a") as f:
				f.write("Info: " + info + ". you chose: " + chosen_action.name + ". Feedback: " + feedback + ".\n")

	def test_run():
		print("Test run started...")
		manager = LLMManager("ministral-3:3b", 1, True)
		manager.set_sys_prompt("Your goal is to survive!")
		prompt = "LEFT: There is a Tiger, UP: There is nothing, RIGHT: There is nothing, DOWN: there is nothing"

		action = manager.request_action(0, prompt)
		if action == Action.LEFT:
			manager.give_feedback(0, prompt, "You Died!", action)
		else:
			manager.give_feedback(0, prompt, "You Survived!", action)
		print(action.name)