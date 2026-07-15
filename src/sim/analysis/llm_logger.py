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
        time, run_id, cycle, llm_index, model, agent_role, guidance,
        latency_s, retries, prompt_tokens, completion_tokens, total_tokens,
        prompt, response

    The file is appended to across every run ever made (it is never rotated),
    so `run_id` (one per process) and `cycle` are what let you tell which run
    and which moment in that run produced a given line — without them, two
    calls next to each other in the file could be from different runs on
    different days, distinguishable only by eyeballing timestamps.

    Read it back with: `for line in open(path): json.loads(line)`.
    """

    def __init__(self, path: str, run_id: str | None = None):
        self.path = path
        self.run_id = run_id
        self._f = None

    def _ensure_open(self):
        if self._f is None:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            self._f = open(self.path, "a", encoding="utf-8")

    def log(self, llm_index, model, prompt, response, latency_s, usage=None, retries=0,
            cycle=None, agent_role=None, guidance=None):
        """Append one call. `usage` is the provider's token-usage object/dict.
        `retries` is how many retry attempts it took before this call succeeded
        (0 = succeeded on the first try) — lets slow/flaky models show up in the
        log even though the retry itself isn't a model response. `cycle`,
        `agent_role` ("cutter"/"collector") and `guidance` (bool, whether
        mechanical navigation help was on) let the log be sliced by ablation
        condition instead of only by comparing two separate log files by hand."""
        self._ensure_open()

        def _tok(name):
            if usage is None:
                return None
            if isinstance(usage, dict):
                return usage.get(name)
            return getattr(usage, name, None)

        record = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "cycle": cycle,
            "llm_index": llm_index,
            "model": model,
            "agent_role": agent_role,
            "guidance": guidance,
            "latency_s": round(latency_s, 3),
            "retries": retries,
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
