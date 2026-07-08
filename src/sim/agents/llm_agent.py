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

    def __init__(self, name: str, llm: LLMManager, llm_index: int, guidance: bool = True,
                 force_reasoning: bool = False):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index
        # If False, disable ALL rule-based navigation help: no precomputed
        # nearest-tree hint, no claimed-tree filtering, no directed_target
        # override. The LLM then has to read the map/blackboard itself and
        # decide everything, used to test whether the model is actually
        # capable of navigating/coordinating on its own, vs. being carried by
        # the mechanical guidance.
        self.guidance = guidance
        # Only relevant when guidance is off. Forces the model to write out
        # its own dx/dy arithmetic as a REASONING line before answering,
        # instead of doing that math silently. Only makes sense combined
        # with guidance=False (with guidance on there is nothing for the
        # model left to compute).
        self.force_reasoning = force_reasoning
        # Own last-stated target coordinate, kept only for the no-guidance
        # prompt as a memory reminder (not a movement instruction) — without
        # it, the model recomputes "nearest tree" from scratch every turn and
        # oscillates between neighboring cells instead of converging.
        self._last_target: tuple[int, int] | None = None

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

    _COORD_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")

    @classmethod
    def _claimed_trees(cls, others: dict[str, str]) -> set[tuple[int, int]]:
        """
        Pull every (x,y) coordinate mentioned in teammates' latest notes. Used
        to mechanically steer this agent away from trees others have already
        claimed, instead of relying on the LLM to honor the claim on its own —
        small models cluster on the same tree even when told not to.
        """
        claimed = set()
        for plan in others.values():
            for mx, my in cls._COORD_RE.findall(plan):
                claimed.add((int(mx), int(my)))
        return claimed

    def _plan_navigation(self, x, y, trees, is_cutter, claimed=frozenset(), directed_target=None) -> tuple[str, Action]:
        """
        Pick the nearest useful tree and describe, in plain words, the single
        step that gets the agent closer (or INTERACT if it is already adjacent).
        Handing the model this computed geometry is far more reliable than
        expecting a small LLM to navigate the ASCII grid itself.

        `claimed` is the set of tree coordinates teammates have announced on
        the blackboard; they are avoided unless no unclaimed tree is left, so
        agents mechanically spread out instead of merely being asked to.

        `directed_target` is a coordinate a teammate's note explicitly told
        THIS agent (by name) to go to; when set it overrides the nearest-tree
        pick entirely, so a direct instruction is mechanically honored rather
        than just hoped for.

        Returns (hint_text, fallback_action): the action is what we fall back to
        if the model's reply can't be parsed, so the env never gets garbage.
        """
        if directed_target is not None:
            tx, ty = directed_target
            dx, dy = tx - x, ty - y
            if abs(dx) + abs(dy) == 1:
                return (f"A teammate directed you to ({tx},{ty}) and you are RIGHT NEXT to it. "
                        f"You are adjacent, so choose INTERACT now.", Action.INTERACT)
            if dx == 0 and dy == 0:
                return ("A teammate directed you to your current tile — pick any nearby tree instead.",
                        random.choice([Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT]))
            horiz = f"{abs(dx)} step(s) {'RIGHT' if dx > 0 else 'LEFT'}" if dx else ""
            vert = f"{abs(dy)} step(s) {'DOWN' if dy > 0 else 'UP'}" if dy else ""
            where = " and ".join(p for p in (horiz, vert) if p)
            move = ("RIGHT" if dx > 0 else "LEFT") if abs(dx) >= abs(dy) and dx != 0 else ("DOWN" if dy > 0 else "UP")
            hint = (f"A teammate directed you to ({tx},{ty}); it is {where} from you. "
                    f"You are NOT adjacent yet, so do NOT INTERACT — choose {move} to get closer.")
            return hint, self._WORD_TO_ACTION[move]

        # Collectors only care about trees that still carry fruit.
        candidates = trees if is_cutter else {t: f for t, f in trees.items() if f > 0}
        if not candidates:
            candidates = trees

        # Prefer trees nobody has claimed; only fall back to a claimed one if
        # every remaining candidate is already spoken for.
        unclaimed = {t: f for t, f in candidates.items() if t not in claimed}
        if unclaimed:
            candidates = unclaimed

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

    def build_prompt(self, obs, info) -> tuple[str, Action]:
        """
        Build the full prompt for this agent's turn plus the safe fallback
        action. Split out of `act()` so the runner can build prompts for every
        LLM agent up front and fire the requests concurrently instead of one
        at a time.
        """
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

        others = self.listen()

        if self.guidance:
            claimed = self._claimed_trees(others)

            # If a teammate's note names this agent and mentions a coordinate,
            # treat that as a direct instruction to head there — mechanically
            # honored below, not just left to the model to notice in the text.
            directed_target = None
            for note in others.values():
                if self.name in note:
                    coords = self._COORD_RE.findall(note)
                    if coords:
                        mx, my = coords[0]
                        directed_target = (int(mx), int(my))
                        break

            # Do the spatial geometry in Python and hand the model a concrete hint
            # (plus a safe fallback action if its reply can't be parsed). Small LLMs
            # cannot reliably navigate a large ASCII grid on their own. Trees other
            # agents have claimed on the blackboard are avoided mechanically here,
            # not just requested in the prompt text below.
            hint, fallback_action = self._plan_navigation(x, y, trees, is_cutter, claimed, directed_target)
        else:
            # Pure LLM test mode: no precomputed target, no claim filtering,
            # no directed-instruction override. The model reads the map and
            # blackboard text itself and has to figure out navigation and
            # coordination on its own. Fallback is just a random legal move,
            # since we have nothing better to recommend without the guidance.
            if self._last_target is not None:
                lx, ly = self._last_target
                memory = (f"Reminder: last turn YOU said you were heading to ({lx},{ly}) — this "
                          f"is not the environment talking, it's your own previous plan. Keep "
                          f"heading to that SAME tree unless it's now empty, already chopped/"
                          f"picked, or a teammate's note claims it — do not pick a new target "
                          f"just because another tree looks slightly closer this turn.")
            else:
                memory = "You have no previous target yet — pick one now and stick with it."

            hint = (
                f"{memory}\n"
                "Work out your action yourself, step by step, every turn:\n"
                "  1. Pick a target tree (x_t, y_t) from the tree list — prefer one nobody else "
                "has claimed on the blackboard, and (if collecting) one with fruit > 0.\n"
                f"  2. Compute dx = x_t - {x}, dy = y_t - {y}.\n"
                "  3. If |dx| + |dy| == 1, you are adjacent — the action MUST be INTERACT.\n"
                "  4. Otherwise move one step toward the target: RIGHT if dx > 0, LEFT if dx < 0 "
                "(else use dy: DOWN if dy > 0, UP if dy < 0). Never pick INTERACT unless |dx|+|dy| == 1.\n"
                "  5. Repeat the SAME target's coordinates in your PLAN note every turn so you "
                "remember it next time — switching targets every turn means you never arrive."
            )
            fallback_action = random.choice([Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT])

        # Without guidance, optionally force the model to actually write out its
        # arithmetic instead of silently doing it in its head. Externalizing
        # intermediate reasoning is the one prompting technique the literature
        # on LLM spatial reasoning consistently shows reduces (not eliminates)
        # coordinate mistakes. Copying its own numbers back into ACTION/PLAN
        # also gives it something concrete to stay consistent with.
        reasoning_line = ("REASONING: <state your target (x_t,y_t), then dx = x_t - x, "
                           "dy = y_t - y, computed with the actual numbers, then say whether "
                           "|dx|+|dy| == 1>\n"
                           if (not self.guidance and self.force_reasoning) else "")

        if others:
            others_text = "\n".join(f"  - {who}: {plan}" for who, plan in others.items())
        else:
            others_text = "  - (nobody has announced anything yet)"

        wood = obs.get('wood_count', 0)
        fruit = obs.get('fruit_count', 0)

        prompt = f"""Your name is {self.name}. You are {role} in a shared grid-world
survival simulation. Other agents may address you by this name on the blackboard.
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

BLACKBOARD (shared notice board — this is your only way to talk to teammates):
Notes are pinned in turn order this cycle, so the notes below are already up to
date — nobody after you has moved yet, but everybody before you has, and their
notes are final for this cycle. Treat earlier notes as having priority: if
{"another cutter" if is_cutter else "another collector"} already claimed a tree, back off it.
Use the board to actually coordinate, not just narrate yourself. Kinds of notes
you can write:
  - CLAIM a tree before you reach it: "Claiming (5,10), heading there now" — so
    nobody after you targets the same one.
  - WARN about scarcity: "(3,2) is down to 1 fruit, leave it for now."
  - COMMAND / SUGGEST a specific teammate by name: "{self.name}, someone else should
    go to (8,2) instead" or, addressed to you, "cutter_1: you should go to (2,9),
    it's closer for you." If a note below names YOU ({self.name}), treat it as a
    priority instruction and follow it unless it is clearly wrong (e.g. the tree
    is now empty or already taken).
  - ANSWER a teammate's note if it affects your move (confirm a handoff, flag a
    conflict, redirect away from something they just claimed).
  - ASK for help: "Cutters, we're low on wood, prioritize chopping."
Read every note below, in order, before deciding — earlier notes already shaped
what's still available to you:
{others_text}

Your job: {job}
{"GUIDANCE" if self.guidance else "NAVIGATION (figure this out yourself)"}: {hint}

First decide your single next action, respecting claims and instructions already
on the board above. Then write your OWN note for the blackboard: a short message
aimed at your teammates (a claim, a warning, a command/suggestion to a named
teammate, an answer, or a request) — not a diary entry about what you're doing
and why.
Respond in EXACTLY this format and nothing else:
{reasoning_line}ACTION: <one of UP, DOWN, LEFT, RIGHT, INTERACT>
PLAN: <one short message to your teammates>"""

        return prompt, fallback_action

    def finish_turn(self, raw: str, fallback_action: Action) -> Action:
        """Parse a raw LLM reply, publish the PLAN to the blackboard, return the Action."""
        action, plan = self._parse_reply(raw, fallback_action)
        self.announce(plan)
        if not self.guidance:
            coords = self._COORD_RE.findall(plan)
            if coords:
                mx, my = coords[0]
                self._last_target = (int(mx), int(my))
        return action

    def act(self, obs, info) -> Action:
        prompt, fallback_action = self.build_prompt(obs, info)
        raw = self.llm.request_response(self.index, prompt)
        return self.finish_turn(raw, fallback_action)
