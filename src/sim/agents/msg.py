from enum import Enum

from environment.actions import Action


class Message:
    """
    A structured note for the blackboard, instead of a free-form string.

    Agents build one of these and put it on the board with self.announce(...).
    Only this `Message` type is imported by other files — the pieces it is made
    of (Type and Intention) live INSIDE it, so you only ever import `Message`:

        Message(Message.Intention.COLLECT, Action.INTERACT)
        Message(Message.Intention.WALK, Action.RIGHT)

    Fields
    ------
    intention : what the agent is trying to do   (Collect, Cut, Walk)
    action    : the concrete Action it will take (from actions.py)
    location  : the (x, y) tile the agent is heading to / acting on, or None
                if it has no particular target. Optional, defaults to None.
    type      : INFO (just sharing) or COMMAND (telling others what to do).
                Defaults to INFO, which is what you want almost always.
    """

    class Type(Enum):
        INFO = "info"
        COMMAND = "command"

    class Intention(Enum):
        COLLECT = "collect"
        CUT = "cut"
        WALK = "walk"

    def __init__(
        self,
        intention: "Message.Intention",
        action: Action,
        location: "tuple | None" = None,
        type: "Message.Type | None" = None,
    ) -> None:
        self.intention = intention
        self.action = action
        self.location = location
        self.type = type if type is not None else Message.Type.INFO

    def __str__(self) -> str:
        # e.g. "collect via INTERACT @ (3, 4)", or "COMMAND: cut via INTERACT"
        text = f"{self.intention.name.lower()} via {self.action.name}"
        if self.location is not None:
            text += f" @ ({self.location[0]}, {self.location[1]})"
        if self.type is Message.Type.COMMAND:
            return f"COMMAND: {text}"
        return text

    __repr__ = __str__
