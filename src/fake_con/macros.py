"""In-memory recording and playback of controller input."""

import asyncio
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MacroAction:
    delay: float
    kind: str
    values: tuple


class MacroController:
    """Record and replay logical controller button and stick updates."""

    def __init__(self, controller):
        self.controller = controller
        self._macros: dict[str, tuple[MacroAction, ...]] = {}
        self._recording_id: str | None = None
        self._recording: list[MacroAction] = []
        self._last_action_at = 0.0
        self._playback_lock = asyncio.Lock()

    @property
    def playing(self) -> bool:
        return self._playback_lock.locked()

    @property
    def recording_id(self) -> str | None:
        return self._recording_id

    def record_start(self, macro_id: str) -> None:
        """Start recording actions under ``macro_id``."""
        self._validate_id(macro_id)
        if self._recording_id is not None:
            raise RuntimeError(f"Already recording macro {self._recording_id!r}")
        self._recording_id = macro_id
        self._recording = []
        self._last_action_at = time.monotonic()
        logger.info("Macro recording started: %s", macro_id)

    def record_stop(self, macro_id: str) -> None:
        """Stop recording and store actions under ``macro_id``."""
        self._validate_id(macro_id)
        if self._recording_id != macro_id:
            raise RuntimeError(f"Macro {macro_id!r} is not being recorded")
        self._macros[macro_id] = tuple(self._recording)
        self._recording_id = None
        self._recording = []
        logger.info(
            "Macro recording stopped: %s (%d actions)",
            macro_id,
            len(self._macros[macro_id]),
        )

    async def play(self, macro_id: str) -> None:
        """Replay a recorded macro by its string identifier."""
        self._validate_id(macro_id)
        actions = self._macros.get(macro_id)
        if actions is None:
            raise KeyError(f"Unknown macro {macro_id!r}")

        async with self._playback_lock:
            logger.info("Macro playback started: %s", macro_id)
            for action in actions:
                await asyncio.sleep(action.delay)
                if action.kind == "button":
                    await self.controller.set_button(*action.values)
                else:
                    stick, x, y = action.values
                    await self.controller.set_stick(stick, x=x, y=y)
            logger.info("Macro playback finished: %s", macro_id)

    def record_button(self, button: str, pressed: bool) -> None:
        self._record_action("button", (button, pressed))

    def record_stick(self, stick: str, x: float, y: float) -> None:
        self._record_action("stick", (stick,), {"x": x, "y": y})

    def _record_action(self, kind, values, keyword_values=None) -> None:
        if self._recording_id is None:
            return
        now = time.monotonic()
        delay = now - self._last_action_at
        self._last_action_at = now
        if keyword_values is None:
            action_values = values
        else:
            action_values = (values[0], keyword_values["x"], keyword_values["y"])
        self._recording.append(MacroAction(delay, kind, action_values))

    @staticmethod
    def _validate_id(macro_id: str) -> None:
        if not isinstance(macro_id, str) or not macro_id.strip():
            raise ValueError("Macro id must be a non-empty string")
