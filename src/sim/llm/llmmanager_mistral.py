from typing import Optional
import time
import os
import uuid

import httpx
from ollama import chat
from ollama import ChatResponse
from ollama import Client
from mistralai.client import Mistral
from mistralai.client.errors import SDKError
import json

from environment.actions import Action
from analysis.llm_logger import LLMCallLogger

# Status codes worth retrying: rate limit + transient server-side failures
# (Mistral's infra occasionally drops the connection or returns a bare 5xx).
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _extract_text(content) -> str:
	"""
	Normalize a chat response's message content to a plain string. Reasoning
	models (e.g. Mistral Medium 3.5 with reasoning_effort set) return a list of
	content chunks — a ThinkChunk (the hidden reasoning) plus TextChunk(s) (the
	actual answer) — instead of a plain string. We only want the text chunks:
	the reasoning isn't meant to be parsed as ACTION/PLAN, and isn't even
	JSON-serializable for the call log as-is.
	"""
	if isinstance(content, str):
		return content
	if isinstance(content, list):
		return "".join(getattr(chunk, "text", "") or "" for chunk in content)
	return content or ""


def _call_with_retry(fn, max_retries: int = 5, base_delay: float = 2.0):
	"""
	Call `fn()` (a zero-arg callable doing the actual API request), retrying
	with exponential backoff on rate limits (429) and transient server/
	connection errors. Anything else (bad request, auth, etc.) is raised
	immediately since retrying it would never succeed.

	Returns (result, attempts_used) so callers can record how flaky the call
	was in the LLM call log — without this, a call that needed 4 retries
	looks identical in the log to one that succeeded first try.
	"""
	for attempt in range(max_retries + 1):
		try:
			return fn(), attempt
		except SDKError as e:
			status = getattr(e.raw_response, "status_code", None)
			if status not in _RETRYABLE_STATUS or attempt == max_retries:
				raise
		except (httpx.TransportError, httpx.RemoteProtocolError):
			if attempt == max_retries:
				raise
		delay = base_delay * (2 ** attempt)
		print(f"LLM request failed (attempt {attempt + 1}/{max_retries + 1}), "
			  f"retrying in {delay:.1f}s...")
		time.sleep(delay)

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
	def __init__(self, use_experience: bool = False, model: str = "magistral-small-latest",
			reasoning_effort: str | None = None, timeout_ms: int = 60000):
		self.use_experience = use_experience
		self.model = model
		# Passed straight to the API's `reasoning_effort` param (models that
		# support configurable thinking, e.g. Mistral Medium 3.5):
		# "none"/"minimal"/"low"/"medium"/"high"/"xhigh". None = don't set it,
		# so models without this knob aren't sent an unsupported field.
		self.reasoning_effort = reasoning_effort
		# Explicit client-side timeout per call, so a hung request fails loudly
		# (and gets retried) instead of blocking a run indefinitely. The SDK
		# defaults to 60s if left unset; we set it explicitly so it's visible
		# and tunable from here instead of buried in the SDK's defaults.
		self.timeout_ms = timeout_ms
		os.makedirs("feedback", exist_ok=True)
		# Observability: log every LLM call (prompt, response, latency, tokens).
		# run_id is one short id per manager instance (= per run, since one
		# manager is shared by all LLM agents in a run) so lines in the
		# ever-growing, never-rotated llm_calls.jsonl can be grouped back into
		# the run that produced them.
		log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm_calls.jsonl")
		self.call_log = LLMCallLogger(os.path.normpath(log_path), run_id=uuid.uuid4().hex[:8])

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

		full_prompt = prompt + " What Action do you choose to take?" + feedback_prompt
		model = "ministral-3b-2512"
		with Mistral(api_key=os.getenv("MISTRAL_API_KEY", ""),) as mistral:
			t0 = time.time()
			res, retries = _call_with_retry(lambda: mistral.chat.complete(model=model, messages=[
				{
					"role": "user",
					"content": full_prompt,
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
			timeout_ms=self.timeout_ms))
			latency = time.time() - t0

		# Parse the action from the response
		action_resp = res.choices[0].message.content
		print("RESPONSE: " + action_resp)
		self.call_log.log(llm_index, model, full_prompt, action_resp, latency,
			getattr(res, "usage", None), retries=retries)
		# self.give_feedback(0, "", action_resp, self.parse_action(action_resp))
		parse_result = self.parse_action(action_resp)
		#print("PARSE RESULT: " + str(parse_result))
		return parse_result

	def request_response(self, llm_index: int, prompt: str, cycle: int | None = None,
			agent_role: str | None = None, guidance: bool | None = None) -> str:
		"""
		Send `prompt` and return the model's RAW text reply (no parsing, no
		action-only system prompt), so the caller can read free-form natural
		language — e.g. a plan sentence — alongside the action.

		`cycle`, `agent_role` and `guidance` are purely for the call log (see
		LLMCallLogger) — they don't affect the request.
		"""
		if llm_index > self.n:
			return ""

		feedback_prompt = ""
		if self.use_experience:
			with open("feedback/feedback_for_" + str(llm_index) + ".txt", 'a+') as file:
				file.seek(0)
				feedback_prompt = " Your past feedback includes: " + file.read()

		full_prompt = prompt + feedback_prompt
		messages = [{"role": "user", "content": full_prompt}]
		if self.sys_prompt:
			messages.append({"role": "system", "content": self.sys_prompt})

		model = self.model
		extra = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
		with Mistral(api_key=os.getenv("MISTRAL_API_KEY", "")) as mistral:
			t0 = time.time()
			res, retries = _call_with_retry(lambda: mistral.chat.complete(
				model=model, messages=messages,
				stream=False, response_format={"type": "text"},
				timeout_ms=self.timeout_ms, **extra))
			latency = time.time() - t0

		response = _extract_text(res.choices[0].message.content)
		self.call_log.log(llm_index, model, full_prompt, response, latency,
			getattr(res, "usage", None), retries=retries,
			cycle=cycle, agent_role=agent_role, guidance=guidance)
		return response

	def give_feedback(self, llm_index: int, info: str, feedback: str, chosen_action: Action):
		with open("feedback/feedback_for_"+str(llm_index)+".txt", "a") as f:
				f.write("Info: " + info + ". you chose: " + chosen_action.name + ". Feedback: " + feedback + ".\n")