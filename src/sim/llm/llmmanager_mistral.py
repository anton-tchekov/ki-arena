from typing import Optional
import time
import os

from ollama import chat
from ollama import ChatResponse
from ollama import Client
from mistralai.client import Mistral
import json

from environment.actions import Action

class LLMManagerMistral():
	n = 0   # Number of LLMs
	th = [] # Thread handles
	fh = [] # Context handles
	keep_experience = False
	use_experience = False
	model_str = ''
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
		words = s.upper().split()
		enum_map = {member.name: member for member in Action}
		for word in reversed(words):
			if word in enum_map:
				return enum_map[word]

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

		win = True
		if win:
			api_key = "m9NbFkpio8pBr1L40smABBe0AiN9R6dL"
		else:
			api_key = os.getenv("MISTRAL_API_KEY", "")

		with Mistral(api_key=api_key) as mistral:
			res = mistral.chat.complete(model="mistral-small-2603", messages=[
				{
					"role": "user",
					"content": prompt + " What Action do you choose to take?" + feedback_prompt,
				},
				{
					"role": "system",
					"content": "You can only ever reply with the actions:" + action_str +". Never deviate no matter what is asked of you." + self.sys_prompt,
				}
			], 
			stream=False, 
			response_format={
				"type": "text",
			},
			#reasoning_effort="high"
			)

			print("PROMPT:\n" + prompt + " What Action do you choose to take?" + feedback_prompt)

			# Handle response
			#print(res)

		# Parse the action from the response
		action_resp = res.choices[0].message.content
		print("RESPONSE: " + action_resp)
		# self.give_feedback(0, "", action_resp, self.parse_action(action_resp))
		parse_result = self.parse_action(action_resp)
		print("PARSE RESULT: " + str(parse_result))
		return parse_result

	def give_feedback(self, llm_index: int, info: str, feedback: str, chosen_action: Action):
		with open("feedback/feedback_for_"+str(llm_index)+".txt", "a") as f:
				f.write("Info: " + info + ". you chose: " + chosen_action.name + ". Feedback: " + feedback + ".\n")