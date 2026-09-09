"""Models related to the remapper functionality of the fake-con library."""

from dataclasses import dataclass
from typing import Protocol, Self

import evdev

from .input import Button, StickAxis

type BindEvent = frozenset[tuple[int, int]]
type BindEventSet = set[tuple[int, int]]

class InputHandlerProtocol(Protocol):
    """Protocol for input handlers that process input events from devices.

    Object must be an async context manager and implement the handle_event method."""

    async def __aenter__(self) -> Self:
        """Call when device is opened. (When a matching device is found)"""
        ...

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """Call when device is closed. (When the device is disconnected or the program is exiting)"""
        ...

    async def handle_event(self, event: evdev.InputEvent) -> None:
        """Handle an input event from the device."""
        ...


@dataclass(frozen=True, slots=True)
class InputContext:
    """Represents the context of an input event, including its type and code."""

    event_type: int
    event_code: int
    device_name: str | None = None
    device_path: str | None = None


class InputModifier(Protocol):
    """Protocol for methods that modify input values before they are remapped to controller inputs."""

    def __call__(self, value: int, context: InputContext) -> int | float | None:
        """Modify an input value.

        Args:
            value: The input value to modify.
            context: The context of the input event.
        Returns:
            The modified input value, or None if the input should be ignored."""
        ...


def default_modifier(value: int, context) -> int:
    """Default modifier that returns the input value unchanged."""
    return value


@dataclass(frozen=True, slots=True)
class Binding:
    """Represents a binding between an input event and a remapped output event.
    
    Attributes:
        event: A tuple representing the input event type and code.
        output: The output event (Button or StickAxis) to which the input event is remapped.
        modifier: An optional InputModifier that modifies the input value before remapping.
        decay: An optional decay factor for relative inputs, which can be used to gradually reduce the effect of the input over time.
    """

    event: tuple[int, int]
    output: Button | StickAxis
    modifier: InputModifier = default_modifier
    decay: float | None = None  # Optional decay factor for relative inputs


# * Extra built-in modifiers
def stick_modifier(value: int, context) -> float:
    """Modifier for stick axes that normalizes the value to a range of -1 to 1."""
    if value < 0:
        return max(-1, value / 32768)
    else:
        return min(1, value / 32767)
def inverted_stick_modifier(value: int, context) -> float:
    """Modifier for stick axes that inverts the value and normalizes it to a range of -1 to 1."""
    if value < 0:
        return min(1, -value / 32768)
    else:
        return max(-1, -value / 32767)