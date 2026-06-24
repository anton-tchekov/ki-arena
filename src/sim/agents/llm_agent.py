from agents.base import BaseAgent
from agents.blackboard import shared_blackboard
from agents.msg import Message
from llm.llmmanager import LLMManager
from environment.actions import Action


class LLMAgent(BaseAgent):
    """
    An LLM-controlled agent. Unlike the other agents, LLM agents can talk to
    each other through the shared blackboard with announce() / listen().
    """

    # The single board shared by all LLM agents. Only LLMs communicate.
    blackboard = shared_blackboard

    def __init__(self, name: str, llm: LLMManager, llm_index: int):
        super().__init__(name)
        self.llm = llm
        self.index = llm_index

    # --- Communication (LLM agents only) ---------------------------------
    def announce(self, message: Message) -> None:
        """Pin what this agent intends to do so other LLM agents can read it."""
        self.blackboard.post(self.name, message)

    def listen(self) -> dict[str, Message]:
        """Return what every OTHER LLM agent last announced, {name: Message}."""
        return self.blackboard.read(exclude=self.name)

    # --------------------------------------------------------------------
    def obs_to_matrix(self, obs) -> str:
        """
        Render the playfield as a text grid (LLMs read these far better than a
        list of coordinates). Row index = x (top is x=0, increasing downward),
        column index = y (left is y=0, increasing rightward) — matching the
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
                grid[tx][ty] = 'T'

        for name, (ax, ay) in obs.get('agents', {}).items():
            if name == self.name or not (0 <= ax < size and 0 <= ay < size):
                continue
            grid[ax][ay] = 'X' if 'cutter' in name else 'C'

        # Draw self last so it is never hidden behind another agent/tree.
        sx, sy = obs['x'], obs['y']
        if 0 <= sx < size and 0 <= sy < size:
            grid[sx][sy] = '@'

        return '\n'.join(' '.join(row) for row in grid)

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
Movement rules:
  UP    -> x - 1      DOWN  -> x + 1
  LEFT  -> y - 1      RIGHT -> y + 1
  INTERACT -> act on a tree that is exactly one step away from you.

Current map (row = x downward, column = y rightward):
{matrix}
Legend: '.'=empty  'T'=tree  '@'=you  'C'=collector  'X'=cutter

You ('@') are at x={x}, y={y}.
Trees as (x,y)=fruit: {tree_list}
Shared stock: wood={wood}, fruit={fruit}.
Other agents have announced:
{others_text}

Your job: {job}
Plan one step: if a tree is already one step away, INTERACT; otherwise move along
x or y to get closer to your chosen tree.

Reply with exactly ONE action, nothing else: UP, DOWN, LEFT, RIGHT, or INTERACT."""

        action = self.llm.request_action(self.index, prompt)

        # Announce intent (with the real intention) so other LLM agents can react.
        if action == Action.INTERACT:
            intention = Message.Intention.CUT if is_cutter else Message.Intention.COLLECT
        else:
            intention = Message.Intention.WALK
        self.announce(Message(intention, action, (x, y)))
        return action
