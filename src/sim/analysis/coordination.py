import re

# Same coordinate pattern LLMAgent uses to read claims out of blackboard notes
# (agents/llm_agent.py _COORD_RE) — kept as a separate copy here so this module
# has no dependency on the LLM backends (agents.llm_agent pulls in ollama/
# mistralai), and can be imported from the environment even when no LLM is used.
_COORD_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


def count_conflicts(notes: dict[str, str]) -> int:
    """
    Count how many distinct coordinates are mentioned by more than one agent
    in the same set of blackboard notes (one snapshot in time).

    This turns "LLM coordination isn't perfect" from a manual replay-reading
    impression into a number: how often do two+ agents name the same tile in
    their plan text during the same cycle, despite the blackboard existing
    specifically so they can see and avoid each other's claims.
    """
    coord_to_agents: dict[tuple[int, int], set[str]] = {}
    for agent, plan in notes.items():
        for mx, my in _COORD_RE.findall(plan):
            coord_to_agents.setdefault((int(mx), int(my)), set()).add(agent)
    return sum(1 for agents in coord_to_agents.values() if len(agents) > 1)
