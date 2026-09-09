"""Listener for input devices in the remapper functionality of the fake-con library."""

import asyncio
import logging

import evdev

from ..models.remapper import BindEvent, BindEventSet, InputHandlerProtocol

logger = logging.getLogger(__name__)


class InputDeviceListener:
    """Manage input devices for the remapper functionality of the fake-con library."""

    def __init__(self):
        """Initialize the device discovery."""
        self._handlers: dict[BindEvent, InputHandlerProtocol] = {}
        self._handler_bindings: dict[str | bytes, InputHandlerProtocol] = {}
        self._tasks: dict[str | bytes, asyncio.Task] = {}
        self._bind_lock = asyncio.Lock()

    def get_all_devices(self) -> list[evdev.InputDevice]:
        """Get all input devices, regardless of whether they are in use by fake-con or usable devices."""
        return [evdev.InputDevice(path) for path in evdev.list_devices()]

    def run(self):
        """Run listener tasks for all devices."""

        devices = self.get_all_devices()
        for device in devices:
            if device.path not in self._tasks or self._tasks[device.path].done():
                task = asyncio.create_task(self._discover_device(device))
                self._tasks[device.path] = task

    def register_handler(
        self, bind_event: BindEvent | BindEventSet, handler: InputHandlerProtocol
    ):
        """Register a handler for a specific bind event."""
        if not isinstance(bind_event, (set, frozenset)):
            raise TypeError(
                "bind_event must be a set or frozenset of (event_type, event_code) tuples."
            )
        if isinstance(bind_event, set):
            bind_event = frozenset(bind_event)

        self._handlers[bind_event] = handler
        logger.info(f"Registered handler {handler} for bind event {bind_event}.")

    async def _discover_device(self, device: evdev.InputDevice):
        """Discover a device and check if it matches the request event."""

        try:
            async for ev in device.async_read_loop():
                handler = self._get_handler_for_device(device)
                if handler is None:
                    unbound_handler = self._get_unbound_handler_for_event(ev)
                    if unbound_handler is not None:
                        try:
                            await self._bind_handler_to_device(device, unbound_handler)
                        except RuntimeError:
                            logger.debug(
                                f"Device {device.name} is already bound to a handler. Skipping binding."
                            )
                if handler is not None:
                    await handler.handle_event(ev)
        except OSError:
            logger.error(f"Discovery task for {device.name} interrupted.")
            handler = self._get_handler_for_device(device)
            if handler is not None:
                await self._unbind_handler_from_device(device)

    async def _bind_handler_to_device(
        self, device: evdev.InputDevice, handler: InputHandlerProtocol
    ):
        """Bind a handler to a device."""
        async with self._bind_lock:
            if device.path in self._handler_bindings:
                raise RuntimeError(
                    f"Device {device.name} is already bound to a handler."
                )
            self._handler_bindings[device.path] = handler
            await handler.__aenter__()
            logger.info(f"Handler {handler} bound to device {device.name}.")

    async def _unbind_handler_from_device(self, device: evdev.InputDevice):
        """Unbind a handler from a device."""
        async with self._bind_lock:
            if device.path not in self._handler_bindings:
                raise RuntimeError(f"Device {device.name} is not bound to any handler.")
            handler = self._handler_bindings[device.path]
            await handler.__aexit__(None, None, None)
            del self._handler_bindings[device.path]
            logger.info(f"Handler {handler} unbound from device {device.name}.")

    def _bind_event_matches_event(
        self, bind_event: BindEvent, event: evdev.InputEvent
    ) -> bool:
        """Check if a bind event matches an input event."""
        return (event.type, event.code) in bind_event

    def _get_unbound_handler_for_event(
        self, event: evdev.InputEvent
    ) -> InputHandlerProtocol | None:
        """Get an unbound handler for the given event, if one exists."""
        for bind_event, handler in self._handlers.items():
            if (
                self._bind_event_matches_event(bind_event, event)
                and handler not in self._handler_bindings.values()
            ):
                return handler
        return None

    def _get_handler_for_device(
        self, device: evdev.InputDevice
    ) -> InputHandlerProtocol | None:
        """Get the handler bound to a device, if one exists."""
        return self._handler_bindings.get(device.path, None)
