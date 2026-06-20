from agents.msg import Message


class Blackboard:
    """
    A shared notice board the LLM agents use to talk to each other.

    Picture a pinboard in a shared workshop: each LLM agent can pin ONE note
    saying what it is about to do, and every LLM agent can read all the notes.
    This lets them understand each other's intentions and coordinate, e.g. a
    cutter pins "cut via INTERACT" so other LLMs know it is busy.

    Only LLM agents communicate. You almost never use this class directly;
    inside an LLMAgent you use the two helper methods it provides:

        self.announce(Message(Message.Intention.WALK, Action.UP))  # pin my note
        self.listen()                                              # read others

    All LLM agents in one simulation share the single `shared_blackboard`
    instance below, so a note pinned by one is visible to all the others.

    A note is a Message (see msg.py): a structured intention + action.
    """

    def __init__(self) -> None:
        # agent name -> its latest note
        self._notes: dict[str, Message] = {}

    def post(self, agent_name: str, message: Message) -> None:
        """Pin (or replace) the note for one agent."""
        self._notes[agent_name] = message

    def read(self, exclude: str | None = None) -> dict[str, Message]:
        """
        Return all current notes as a {agent_name: Message} dictionary.
        Pass exclude=<name> to leave out one agent (normally yourself).
        """
        return {name: note for name, note in self._notes.items() if name != exclude}

    def remove(self, agent_name: str) -> None:
        """Take down an agent's note (e.g. when that agent dies)."""
        self._notes.pop(agent_name, None)

    def clear(self) -> None:
        """Remove every note. Done automatically at the start of each episode."""
        self._notes.clear()


# The single board shared by all communicating (LLM) agents. Lives here, at
# module level, so the runner and renderer can reference it without importing
# LLMAgent (which would pull in the LLM backend dependencies).
shared_blackboard = Blackboard()
