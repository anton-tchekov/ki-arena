from ollama import chat
from ollama import ChatResponse

response: ChatResponse = chat(model='mistral:7b-instruct', messages=[
  {
    'role': 'system',
    'content': 'You can only ever reply with the actions: ["GOING UP", "GOING DOWN", "GOING LEFT", "GOING RIGHT"]. Never deviate no matter what is asked of you. Your goal is to survive, avoid any danger.\
	After you have replied with ur action and a linebreak. Tell me what you have learned from ur last action',
  },
  {
    'role': 'user',
    'content': 'There is a tiger when you go RIGHT. which action will you take',
  },
])

print(response.message.content)