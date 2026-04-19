# =============================================================================
# communication.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    """
    A message exchanged between agents.

    Fields
    ------
    sender_id   : unique_id of the sending agent
    receiver_id : unique_id of target agent, or None for broadcast
    performative: speech act — "INFORM_WASTE", "INFORM_COLLECTED", "DISPOSAL_POS"
    content     : dict payload
    """
    sender_id:    int
    receiver_id:  Any          # int | None
    performative: str
    content:      dict = field(default_factory=dict)


class CommunicationSystem:
    """
    Centralised message board attached to the model.

    Three delivery modes
    --------------------
    send()           — point-to-point (one recipient)
    broadcast()      — all agents (key None)
    send_to_group()  — targeted list of recipients (e.g. all yellow robots)
    """

    def __init__(self):
        self._inbox: dict[Any, list[Message]] = {}

    # ------------------------------------------------------------------
    def send(self, message: Message) -> None:
        key = message.receiver_id
        if key not in self._inbox:
            self._inbox[key] = []
        self._inbox[key].append(message)

    # ------------------------------------------------------------------
    def broadcast(self, message: Message) -> None:
        """Store under key None — readable by every agent."""
        message.receiver_id = None
        self.send(message)

    # ------------------------------------------------------------------
    def send_to_group(self, message: Message, agent_ids: list) -> None:
        """
        Send a copy of the message to each agent in agent_ids.
        Used for waste-type-targeted communication:
            green robot spots yellow waste → sends only to yellow robots
            green robot spots red waste   → sends only to red robots
        """
        for agent_id in agent_ids:
            self.send(Message(
                sender_id=message.sender_id,
                receiver_id=agent_id,
                performative=message.performative,
                content=dict(message.content),   # independent copy
            ))

    # ------------------------------------------------------------------
    def get_messages(self, agent_id: int,
                     include_broadcast: bool = True) -> list[Message]:
        """
        Return (and clear) all messages addressed to agent_id.
        Broadcast messages are returned but NOT cleared here —
        call clear_broadcasts() at end of model step.
        """
        msgs = []
        if agent_id in self._inbox:
            msgs.extend(self._inbox.pop(agent_id))
        if include_broadcast and None in self._inbox:
            msgs.extend(self._inbox[None])
        return msgs

    # ------------------------------------------------------------------
    def clear_broadcasts(self) -> None:
        """Discard stale broadcast messages at end of each model step."""
        self._inbox.pop(None, None)

    # ------------------------------------------------------------------
    def clear_all(self) -> None:
        self._inbox.clear()