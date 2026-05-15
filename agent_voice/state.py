"""Finite-state machine for voice command lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AppState(str, Enum):
    """User-visible assistant states."""

    STARTING = "STARTING"
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    RECOGNIZING = "RECOGNIZING"
    SENDING = "SENDING"
    DONE = "DONE"
    NO_MATCH = "NO_MATCH"
    MUTED = "MUTED"
    ERROR = "ERROR"


TRANSITIONS: dict[AppState, dict[str, AppState]] = {
    AppState.STARTING: {"started": AppState.IDLE, "failed": AppState.ERROR},
    AppState.IDLE: {"wake_detected": AppState.LISTENING, "mute": AppState.MUTED, "failed": AppState.ERROR},
    AppState.LISTENING: {
        "recording_complete": AppState.RECOGNIZING,
        "timeout": AppState.IDLE,
        "failed": AppState.ERROR,
    },
    AppState.RECOGNIZING: {"parsed": AppState.SENDING, "no_match": AppState.NO_MATCH, "failed": AppState.ERROR},
    AppState.SENDING: {"accepted": AppState.DONE, "rejected": AppState.ERROR, "failed": AppState.ERROR},
    AppState.DONE: {"settled": AppState.IDLE},
    AppState.NO_MATCH: {"settled": AppState.IDLE},
    AppState.MUTED: {"resume": AppState.IDLE, "failed": AppState.ERROR},
    AppState.ERROR: {"recover": AppState.IDLE, "mute": AppState.MUTED},
}


@dataclass
class StateMachine:
    """Validate and apply assistant state transitions."""

    initial_state: AppState = AppState.STARTING

    def __post_init__(self) -> None:
        """Initialize the mutable current state from the configured initial state."""

        self.current = self.initial_state

    def transition(self, event: str) -> AppState:
        """Apply an event and return the new state, or raise for invalid transitions."""

        next_state = TRANSITIONS.get(self.current, {}).get(event)
        if next_state is None:
            raise ValueError(f"Invalid transition from {self.current.value} via event {event!r}")
        self.current = next_state
        return self.current
