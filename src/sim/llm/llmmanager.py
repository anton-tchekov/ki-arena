from typing import Optional
import time
import os

from ollama import chat
from ollama import ChatResponse
from ollama import Client

from environment.actions import Action
from analysis.llm_logger import LLMCallLogger

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
		# Observability: log every LLM call (prompt, response, latency, tokens) to
		# the same llm_calls.jsonl the Mistral backend uses, so a purely local
		# Ollama run still produces the structured LLM log the docs describe.
		log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm_calls.jsonl")
		self.call_log = LLMCallLogger(os.path.normpath(log_path))

	@staticmethod
	def _usage_from_response(response) -> dict:
		"""Map Ollama's token counters onto the {prompt,completion,total}_tokens
		keys the LLMCallLogger expects."""
		prompt_tok = getattr(response, "prompt_eval_count", None)
		completion_tok = getattr(response, "eval_count", None)
		total = None
		if prompt_tok is not None or completion_tok is not None:
			total = (prompt_tok or 0) + (completion_tok or 0)
		return {
			"prompt_tokens": prompt_tok,
			"completion_tokens": completion_tok,
			"total_tokens": total,
		}

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
		#{
		#	'role': 'system',
		#	'content': 'You can only ever reply with the actions:' + action_str +'. Never deviate no matter what is asked of you.' +
		#	self.sys_prompt,
		#},
		{
			'role': 'user',
			'content': prompt + "What Action do you choose to take?" + feedback_prompt,
		},
		])

		# Parse the action from the response
		action_resp = response.message.content.partition('\n')[0]
		return self.parse_action(action_resp)

	def request_response(self, llm_index: int, prompt: str) -> str:
		"""
		Send `prompt` and return the model's RAW text reply (no parsing), so the
		caller can read free-form natural language — e.g. a plan sentence —
		alongside the action.
		"""
		if llm_index > self.n:
			return ""

		feedback_prompt = ""
		if self.use_experience:
			with open("feedback/feedback_for_" + str(llm_index) + ".txt", 'a+') as file:
				file.seek(0)
				feedback_prompt = " Your past feedback includes: " + file.read()

		messages = [{'role': 'user', 'content': prompt + feedback_prompt}]
		if self.sys_prompt:
			messages.insert(0, {'role': 'system', 'content': self.sys_prompt})

		t0 = time.time()
		response: ChatResponse = self.client.chat(model=self.model_str, messages=messages)
		latency = time.time() - t0
		text = response.message.content or ""
		self.call_log.log(llm_index, self.model_str, prompt + feedback_prompt, text,
			latency, self._usage_from_response(response))
		return text

	def give_feedback(self, llm_index: int, info: str, feedback: str, chosen_action: Action):
		with open("feedback/feedback_for_"+str(llm_index)+".txt", "a") as f:
				f.write("Info: " + info + ". you chose: " + chosen_action.name + ". Feedback: " + feedback + ".\n")