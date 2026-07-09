import json
import os
from datetime import datetime


class LLMCallLogger:
    """
    Structured log of every LLM call, one JSON object per line (JSONL).

    Each line records what the model was asked, what it answered, how long it
    took and how many tokens it used (the token count is our cost proxy, since
    billing is per token). The file is opened lazily on the first call, so runs
    that use no LLM never create a log.

    Fields per line:
        time, llm_index, model, latency_s,
        prompt_tokens, completion_tokens, total_tokens,
        prompt, response

    Read it back with: `for line in open(path): json.loads(line)`.
    """

    def __init__(self, path: str):
        self.path = path
        self._f = None

    def _ensure_open(self):
        if self._f is None:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._f = open(self.path, "a", encoding="utf-8")

    def log(self, llm_index, model, prompt, response, latency_s, usage=None):
        """Append one call. `usage` is the provider's token-usage object/dict."""
        self._ensure_open()

        def _tok(name):
            if usage is None:
                return None
            if isinstance(usage, dict):
                return usage.get(name)
            return getattr(usage, name, None)

        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "llm_index": llm_index,
            "model": model,
            "latency_s": round(latency_s, 3),
            "prompt_tokens": _tok("prompt_tokens"),
            "completion_tokens": _tok("completion_tokens"),
            "total_tokens": _tok("total_tokens"),
            "prompt": prompt,
            "response": response,
        }
        self._f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self):
        if self._f is not None:
            try:
                self._f.close()
            finally:
                self._f = None
