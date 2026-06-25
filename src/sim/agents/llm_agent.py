import re
import random

from agents.base import BaseAgent
from agents.blackboard import shared_blackboard
from llm.llmmanager import LLMManager
from environment.actions import Action


class LLMAgent(BaseAgent):
    """
    An LLM-controlled agent. Unlike the other agents, LLM agents talk to each
    other in plain English through the shared blackboard: every step each LLM
    announces its plan as a short natural-language sentence (announce()), and
    reads its teammates' plans (listen()).
    """

    # The single board shared by all LLM agents. Only LLMs communicate.
    blackboard = shared_blackboard

    # Maps a movement word to its Action (used for the parse fallback).
    _WORD_TO_ACTION = {
        "UP": Action.UP, "DOWN": Action.DOWN,
        "LEFT": Action.LEFT, "RIGHT": Action.RIGHT,
    }

    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    # --- Communication (LLM agents only) ---------------------------------
    def announce(self, plan: str) -> None:
        """Pin this agent's natural-language plan so other LLM agents can read it."""
        self.blackboard.post(self.name, plan)

    def listen(self) -> dict[str, str]:
        """Return what every OTHER LLM agent last announced, {name: plan_text}."""
        return self.blackboard.read(exclude=self.name)

    # --------------------------------------------------------------------
    def obs_to_matrix(self, obs) -> str:
        """
        Render the playfield as a text grid (LLMs read these far better than a
        list of coordinates). Row index = y (top is y=0, increasing downward),
        column index = x (left is x=0, increasing rightward) — matching the
        movement rules. Cells:
            '.' empty   'T' tree   '@' you   'C' collector   'X' cutter
        """
        size = obs.get('size')
        if size is None:
            cells = list(obs.get('trees', {})) + list(obs.get('agents', {}).values())
            size = max((max(c) for c in cells), default=0) + 1

        grid = [['.'] * size for _ in range(size)]

        for (tx, ty) in obs.get('trees', {}):
            if 0 <= tx < size and 0 <= ty < size:
                grid[ty][tx] = 'T'

        for name, (ax, ay) in obs.get('agents', {}).items():
            if name == self.name or not (0 <= ax < size and 0 <= ay < size):
                continue
            grid[ay][ax] = 'X' if 'cutter' in name else 'C'

        # Draw self last so it is never hidden behind another agent/tree.
        sx, sy = obs['x'], obs['y']
        if 0 <= sx < size and 0 <= sy < size:
            grid[sy][sx] = '@'

        return '\n'.join(' '.join(row) for row in grid)

    def _plan_navigation(self, x, y, trees, is_cutter) -> tuple[str, Action]:
        """
        Pick the nearest useful tree and describe, in plain words, the single
        step that gets the agent closer (or INTERACT if it is already adjacent).
        Handing the model this computed geometry is far more reliable than
        expecting a small LLM to navigate the ASCII grid itself.

        Returns (hint_text, fallback_action): the action is what we fall back to
        if the model's reply can't be parsed, so the env never gets garbage.
        """
        # Collectors only care about trees that still carry fruit.
        candidates = trees if is_cutter else {t: f for t, f in trees.items() if f > 0}
        if not candidates:
            candidates = trees
        if not candidates:
            return ("No trees are reachable right now — take one step in any direction to explore.",
                    random.choice([Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT]))

        tx, ty = min(candidates, key=lambda t: abs(t[0] - x) + abs(t[1] - y))
        dx, dy = tx - x, ty - y

        if abs(dx) + abs(dy) == 1:
            return (f"A tree is RIGHT NEXT to you at ({tx},{ty}). "
                    f"You are adjacent, so choose INTERACT now.", Action.INTERACT)

        horiz = f"{abs(dx)} step(s) {'RIGHT' if dx > 0 else 'LEFT'}" if dx else ""
        vert = f"{abs(dy)} step(s) {'DOWN' if dy > 0 else 'UP'}" if dy else ""
        where = " and ".join(p for p in (horiz, vert) if p)

        # Recommend the dominant axis so diagonal targets still make progress.
        if abs(dx) >= abs(dy) and dx != 0:
            move = "RIGHT" if dx > 0 else "LEFT"
        else:
            move = "DOWN" if dy > 0 else "UP"

        hint = (f"Your nearest tree is at ({tx},{ty}); it is {where} from you. "
                f"You are NOT adjacent yet, so do NOT INTERACT — choose {move} to get closer.")
        return hint, self._WORD_TO_ACTION[move]

    def _parse_reply(self, raw: str, fallback: Action) -> tuple[Action, str]:
        """
        Pull the chosen Action and the natural-language PLAN out of the model's
        reply. Robust against extra prose / chain-of-thought: we read the
        labelled ACTION and PLAN lines, and fall back to the recommended action
        if the model's action is missing or invalid — so the env never gets fed
        anything wrong.
        """
        # Drop any <think>...</think> reasoning some models emit before answering.
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE)

        action = None
        plan = ""
        for line in text.splitlines():
            stripped = line.strip()
            head = stripped.upper()
            if head.startswith("ACTION:"):
                action = self.llm.parse_action(stripped.split(":", 1)[1])
            elif head.startswith("PLAN:"):
                plan = stripped.split(":", 1)[1].strip()

        if action is None:                 # no ACTION line, or it wasn't a valid action
            action = self.llm.parse_action(text) or fallback
        if not plan:                       # model forgot the PLAN line
            plan = f"Doing {action.name}."
        return action, plan

    def act(self, obs, info) -> Action:
        x = obs['x']
        y = obs['y']
        size = obs.get('size', 0)
        last = size - 1 if isinstance(size, int) and size > 0 else '?'
        is_cutter = 'cutter' in self.name

        # Role-specific description and objective.
        if is_cutter:
            role = "a Cutter"
            job = ("get next to a tree and INTERACT to chop it down for wood — you "
                   "need wood to survive. Spread out from other cutters and don't "
                   "strip the forest faster than it can regrow.")
        else:
            role = "a Collector"
            job = ("get next to a tree and INTERACT to pick a fruit — you need fruit "
                   "to survive. Prefer trees with more fruit that no other collector "
                   "is already standing next to.")

        matrix = self.obs_to_matrix(obs)

        trees = obs.get('trees', {})
        tree_list = ", ".join(f"({tx},{ty})={fruit}" for (tx, ty), fruit in trees.items()) or "none"

        # Do the spatial geometry in Python and hand the model a concrete hint
        # (plus a safe fallback action if its reply can't be parsed). Small LLMs
        # cannot reliably navigate a large ASCII grid on their own.
        hint, fallback_action = self._plan_navigation(x, y, trees, is_cutter)

        others = self.listen()
        if others:
            others_text = "\n".join(f"  - {who}: {plan}" for who, plan in others.items())
        else:
            others_text = "  - (nobody has announced anything yet)"

        wood = obs.get('wood_count', 0)
        fruit = obs.get('fruit_count', 0)

        prompt = f"""You are {role} in a shared grid-world survival simulation.
Two groups live here: Collectors gather fruit from trees, Cutters chop trees for
wood. Every agent depends on BOTH resources, so help your group thrive without
exhausting the forest for everyone else.

The world is a {size}x{size} grid. A position is (x, y) with x and y from 0 to {last}.
Movement rules (x is horizontal, y is vertical):
  UP    -> y - 1      DOWN  -> y + 1
  LEFT  -> x - 1      RIGHT -> x + 1
  INTERACT -> act on a tree that is exactly one step away from you.

Current map (row = y downward, column = x rightward):
{matrix}
Legend: '.'=empty  'T'=tree  '@'=you  'C'=collector  'X'=cutter

You ('@') are at x={x}, y={y}.
Trees as (x,y)=fruit: {tree_list}
Shared stock: wood={wood}, fruit={fruit}.
Your teammates' latest plans (read them and coordinate — don't all target the same tree):
{others_text}

Your job: {job}
GUIDANCE: {hint}

First decide your single next action. Then tell your teammates your plan in ONE short
sentence of plain English (where you are going and why, plus any request to them).
Respond in EXACTLY this format and nothing else:
ACTION: <one of UP, DOWN, LEFT, RIGHT, INTERACT>
PLAN: <one short sentence>"""

        raw = self.llm.request_response(self.index, prompt)
        action, plan = self._parse_reply(raw, fallback_action)

        # Publish our own words to the shared blackboard so other LLMs can read them.
        self.announce(plan)
        return action
