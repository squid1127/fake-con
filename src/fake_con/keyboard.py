"""Async evdev input discovery and unified controller remapping."""

import asyncio
import logging
from collections.abc import Mapping
from dataclasses import dataclass

from evdev import InputDevice, ecodes, list_devices

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ButtonTarget:
    """A key mapped to a controller button."""

    button: str


@dataclass(frozen=True)
class ClickTarget:
    """A mouse button mapped to a controller button."""

    button: str


@dataclass(frozen=True)
class AxisTarget:
    """A key or mouse axis mapped to a controller stick axis."""

    stick: str
    axis: str
    value: float = 1.0
    relative: bool = False


InputMapping = Mapping[int, ButtonTarget | ClickTarget | AxisTarget]

DEFAULT_KEY_MAPPING: InputMapping = {
    ecodes.KEY_W: AxisTarget("left", "y", 1.0),
    ecodes.KEY_A: AxisTarget("left", "x", -1.0),
    ecodes.KEY_S: AxisTarget("left", "y", -1.0),
    ecodes.KEY_D: AxisTarget("left", "x", 1.0),
    ecodes.KEY_UP: AxisTarget("right", "y", 1.0),
    ecodes.KEY_LEFT: AxisTarget("right", "x", -1.0),
    ecodes.KEY_DOWN: AxisTarget("right", "y", -1.0),
    ecodes.KEY_RIGHT: AxisTarget("right", "x", 1.0),
    ecodes.KEY_Y: ButtonTarget("up"),
    ecodes.KEY_G: ButtonTarget("left"),
    ecodes.KEY_H: ButtonTarget("down"),
    ecodes.KEY_J: ButtonTarget("right"),
    ecodes.KEY_O: ButtonTarget("x"),
    ecodes.KEY_K: ButtonTarget("y"),
    ecodes.KEY_L: ButtonTarget("b"),
    ecodes.KEY_SEMICOLON: ButtonTarget("a"),
    ecodes.KEY_1: ButtonTarget("zr"),
    ecodes.KEY_3: ButtonTarget("zl"),
    ecodes.KEY_Q: ButtonTarget("l"),
    ecodes.KEY_E: ButtonTarget("r"),
    ecodes.KEY_I: ButtonTarget("minus"),
    ecodes.KEY_P: ButtonTarget("plus"),
}

DEFAULT_MOUSE_MAPPING: InputMapping = {
    ecodes.REL_X: AxisTarget("right", "x", 0.01, relative=True),
    ecodes.REL_Y: AxisTarget("right", "y", -0.01, relative=True),
    ecodes.BTN_LEFT: ClickTarget("zr"),
    ecodes.BTN_RIGHT: ClickTarget("zl"),
}

DEFAULT_MAPPING: InputMapping = {**DEFAULT_KEY_MAPPING, **DEFAULT_MOUSE_MAPPING}

_KEYBOARD_LETTERS = {
    ecodes.KEY_A,
    ecodes.KEY_B,
    ecodes.KEY_C,
    ecodes.KEY_D,
    ecodes.KEY_E,
    ecodes.KEY_F,
    ecodes.KEY_Q,
    ecodes.KEY_W,
    ecodes.KEY_X,
    ecodes.KEY_Y,
    ecodes.KEY_Z,
}


def _paths_for_capabilities(required_type, required_codes, minimum_keys=0):
    paths = []
    for path in list_devices():
        device = InputDevice(path)
        try:
            codes = set(device.capabilities().get(required_type, []))
            if required_codes <= codes and len(codes) >= minimum_keys:
                paths.append(path)
        finally:
            device.close()
    return paths


def _open_devices_sync(required_type, required_codes, minimum_keys=0):
    devices = []
    for path in _paths_for_capabilities(required_type, required_codes, minimum_keys):
        try:
            devices.append(InputDevice(path))
        except OSError as error:
            logger.warning("Could not open evdev device %s: %s", path, error)
    if not devices:
        raise RuntimeError("No matching evdev devices could be opened")
    return devices


async def _open_devices(required_type, required_codes, minimum_keys=0):
    return await asyncio.to_thread(
        _open_devices_sync, required_type, required_codes, minimum_keys
    )


def _open_mouse_devices_sync():
    devices = []
    for path in list_devices():
        device = InputDevice(path)
        try:
            capabilities = device.capabilities()
            if {ecodes.REL_X, ecodes.REL_Y} <= set(
                capabilities.get(ecodes.EV_REL, [])
            ) and ecodes.BTN_LEFT in set(capabilities.get(ecodes.EV_KEY, [])):
                devices.append(InputDevice(path))
        finally:
            device.close()
    if not devices:
        raise RuntimeError("No mouse-like evdev devices could be opened")
    return devices


async def _open_mouse_devices():
    return await asyncio.to_thread(_open_mouse_devices_sync)


async def _close_devices(devices):
    await asyncio.gather(*(asyncio.to_thread(device.close) for device in devices))


async def wait_for_space() -> InputDevice:
    """Return the first keyboard device that receives a space key-down."""
    devices = await _open_devices(ecodes.EV_KEY, {ecodes.KEY_SPACE} | _KEYBOARD_LETTERS)
    return await _wait_for_event(
        devices,
        lambda event: event.type == ecodes.EV_KEY
        and event.code == ecodes.KEY_SPACE
        and event.value == 1,
        "Keyboard listeners stopped before space was pressed",
    )


async def wait_for_click() -> InputDevice:
    """Return the first mouse device that receives a left-button press."""
    devices = await _open_mouse_devices()
    return await _wait_for_event(
        devices,
        lambda event: event.type == ecodes.EV_KEY
        and event.code == ecodes.BTN_LEFT
        and event.value == 1,
        "Mouse listeners stopped before a click was received",
    )


async def _wait_for_event(devices, predicate, error_message):
    tasks = {
        asyncio.create_task(_wait_for_event_on_device(device, predicate)): device
        for device in devices
    }
    winner = None
    pending = set(tasks)
    try:
        while pending and winner is None:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                if not task.cancelled() and task.exception() is None:
                    winner = tasks[task]
                    break
        if winner is None:
            raise RuntimeError(error_message)
        return winner
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await _close_devices([device for device in devices if device is not winner])


async def _wait_for_event_on_device(device, predicate):
    async for event in device.async_read_loop():
        if predicate(event):
            return


async def remap_keyboard(
    controller,
    input_devices,
    mapping: InputMapping = DEFAULT_MAPPING,
    macro=None,
):
    """Remap devices, optionally recording logical actions into ``macro``."""
    sources = await _classify_devices(input_devices)
    try:
        await _remap_devices(controller, sources, mapping, macro)
    finally:
        await _close_devices(input_devices)


async def _classify_devices(input_devices):
    async def classify(device):
        capabilities = await asyncio.to_thread(device.capabilities)
        if ecodes.EV_REL in capabilities:
            return device, {ecodes.EV_REL, ecodes.EV_KEY}
        if ecodes.EV_KEY in capabilities:
            return device, {ecodes.EV_KEY}
        raise ValueError(f"Unsupported input device: {device.path}")

    return await asyncio.gather(*(classify(device) for device in input_devices))


async def _remap_devices(controller, sources, mapping, macro):
    pressed = set()
    axes = {}
    lock = asyncio.Lock()
    await asyncio.gather(
        *(
            _forward_device(
                device, controller, mapping, event_types, pressed, axes, lock, macro
            )
            for device, event_types in sources
        )
    )


async def _forward_device(
    device, controller, mapping, event_types, pressed, axes, lock, macro
):
    async for event in device.async_read_loop():
        target = mapping.get(event.code) if event.type in event_types else None
        if target is not None:
            async with lock:
                await _handle_event(
                    controller, mapping, event, target, pressed, axes, macro
                )


async def _handle_event(controller, mapping, event, target, pressed, axes, macro=None):
    if isinstance(target, (ButtonTarget, ClickTarget)):
        await _handle_button_event(controller, event, target, pressed, macro)
        return

    if isinstance(target, AxisTarget):
        await _handle_axis_event(
            controller, mapping, event, target, pressed, axes, macro
        )


async def _handle_button_event(controller, event, target, pressed, macro):
    if event.value not in (0, 1):
        return
    if event.value:
        pressed.add(event.code)
    else:
        pressed.discard(event.code)
    await controller.set_button(target.button, event.value == 1)
    if macro is not None and not macro.playing:
        macro.record_button(target.button, event.value == 1)


async def _handle_axis_event(controller, mapping, event, target, pressed, axes, macro):
    if target.relative:
        key = (target.stick, target.axis)
        axes[key] = max(-1.0, min(1.0, axes.get(key, 0.0) + event.value * target.value))
    elif event.value in (0, 1):
        if event.value:
            pressed.add(event.code)
        else:
            pressed.discard(event.code)
    await _update_axes(controller, mapping, pressed, axes, macro)


async def _update_axes(controller, mapping, pressed, axes, macro=None):
    sticks = {
        target.stick for target in mapping.values() if isinstance(target, AxisTarget)
    }
    for stick in sticks:
        x = axes.get((stick, "x"), 0.0)
        y = axes.get((stick, "y"), 0.0)
        for code in pressed:
            target = mapping.get(code)
            if (
                isinstance(target, AxisTarget)
                and target.stick == stick
                and not target.relative
            ):
                if target.axis == "x":
                    x += target.value
                else:
                    y += target.value
        await controller.set_stick(
            stick,
            x=max(-1.0, min(1.0, x)),
            y=max(-1.0, min(1.0, y)),
        )
        if macro is not None and not macro.playing:
            macro.record_stick(stick, max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y)))
