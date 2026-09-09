"""Input remapper for handling input events."""

import asyncio
from logging import getLogger

import evdev

from ..controller.api import ControllerAPI
from ..models.input import Button, StickAxis
from ..models.remapper import Binding, InputContext

logger = getLogger(__name__)


class InputRemapper:
    """Class for remapping input events to controller inputs."""

    def __init__(self, controller_api: ControllerAPI, bindings: list[Binding]):
        """Initialize the input remapper with a controller API and a list of bindings.

        Args:
            controller_api: The controller API to send remapped inputs to.
            bindings: A list of Binding objects that define how to remap input events.
        """
        self._controller_api = controller_api
        self._bindings = bindings
        self._binding_last_values: dict[Binding, int] = dict.fromkeys(
            bindings, 0
        ) 

        self._is_active = False 
        self._tick_loop_task: asyncio.Task[None] | None = (
            None  # Task for handling decay on each tick
        )

    async def __aenter__(self):
        """Enter the async context manager."""
        if self._is_active:
            raise RuntimeError("InputRemapper is already active.")
        self._is_active = True
        self._tick_loop_task = asyncio.create_task(self._tick_loop())
        logger.info(f"Remapping {len(self._bindings)} input bindings.")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the async context manager."""
        if not self._is_active:
            raise RuntimeError("InputRemapper is not active.")
        self._is_active = False
        if self._tick_loop_task:
            self._tick_loop_task.cancel()
            try:
                await self._tick_loop_task
            except asyncio.CancelledError:
                pass
        logger.info("Exiting input remapper")

    async def handle_event(self, event: evdev.InputEvent):
        """Handle an input event and remap it to the controller API if it matches a binding.

        Args:
            event: The input event to handle.
        """
        for binding in self._bindings:
            if (event.type, event.code) == binding.event:
                if binding.decay is not None:
                    # Store the last value for decay
                    self._binding_last_values[binding] = event.value

                context = InputContext(event_type=event.type, event_code=event.code)
                modified_value = binding.modifier(event.value, context=context)

                if modified_value is not None:
                    if isinstance(binding.output, Button):
                        self._controller_api.set_button(
                            binding.output, bool(modified_value)
                        )
                    elif isinstance(binding.output, StickAxis):
                        self._controller_api.set_stick_axis(
                            binding.output, modified_value
                        )
                        
    async def _tick_loop(self):
        """Loop that runs on each tick to handle decay for relative inputs."""
        while self._is_active:
            await self._controller_api.wait(1)  # Wait for one tick
            self.on_tick()  # Handle decay for bindings with decay

    def on_tick(self):
        """Handle decay for relative inputs on each tick."""
        for binding in self._bindings:
            if binding.decay is not None:
                self.decay_binding(binding)

    def decay_binding(self, binding: Binding):
        """Apply decay to a specific binding.

        Args:
            binding: The binding to apply decay to.
        """
        if binding.decay is not None:
            last_value = self._binding_last_values.get(binding, 0)
            if last_value != 0:
                decayed_value = int(last_value * binding.decay)
                logger.debug(
                    f"Decaying binding {binding.output} from {last_value} to {decayed_value}"
                )
                self._binding_last_values[binding] = decayed_value

                context = InputContext(
                    event_type=binding.event[0], event_code=binding.event[1]
                )
                modified_value = binding.modifier(decayed_value, context=context)

                if modified_value is not None:
                    if isinstance(binding.output, Button):
                        self._controller_api.set_button(
                            binding.output, bool(modified_value)
                        )
                    elif isinstance(binding.output, StickAxis):
                        self._controller_api.set_stick_axis(
                            binding.output, modified_value
                        )