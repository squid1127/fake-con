"""Test script"""

import asyncio
from logging import DEBUG, getLogger

import evdev
from coloredlogs import install

import fake_con as fc

install(level=DEBUG, fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = getLogger(__name__)


def mouse_to_stick(value: int, context: fc.InputContext) -> float:
    """Convert mouse movement to stick axis value."""
    out = max(-1.0, min(1.0, value / 20))
    return out


def mouse_to_stick_inverted(value: int, context: fc.InputContext) -> float:
    """Convert mouse movement to stick axis value, inverted."""
    out = max(-1.0, min(1.0, -value / 20))
    return out

def stick_to_stick(value: int, context: fc.InputContext) -> float:
    """Convert stick movement to stick axis value."""
    out = max(-1.0, min(1.0, (value / 4096) * 2 - 1))
    return out


def button_to_button(value: int, context: fc.InputContext) -> int | None:
    """Convert button press to boolean value."""
    if value == 1:
        return 1
    elif value == 0:
        return 0
    else:
        return None


class DebugHandler:
    """Debug handler to log input events."""

    async def handle_event(self, event: evdev.InputEvent):
        """Log the input event.

        Args:
            event: The input event to log.
        """
        logger.debug(f"Received input event: {event}")

    async def __aenter__(self):
        """Enter the async context manager."""
        logger.info("DebugHandler started.")
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the async context manager."""
        logger.info("DebugHandler stopped.")


async def main():
    """Main function to run the test."""
    config = fc.FakeConConfig()
    server = fc.FakeConServer(config=config)

    listener = fc.InputDeviceListener()

    # Pro Controller lacks literal button codes, so we map them manually
    buttons = {
        305: fc.Button.A,
        304: fc.Button.B,
        307: fc.Button.Y,
        306: fc.Button.X,
        315: fc.Button.UP, 
        312: fc.Button.DOWN, 
        314: fc.Button.LEFT,  
        313: fc.Button.RIGHT,  
        318: fc.Button.MINUS,  
        310: fc.Button.PLUS,
        705: fc.Button.CAPTURE,
        704: fc.Button.HOME,
        319: fc.Button.L_STICK,
        311: fc.Button.R_STICK,
        316: fc.Button.L,
        308: fc.Button.R,
        317: fc.Button.ZL,
        309: fc.Button.ZR,
    }
    stick_axes = {
        0: fc.StickAxis.LEFT_X,
        1: fc.StickAxis.LEFT_Y,
        3: fc.StickAxis.RIGHT_X,
        5: fc.StickAxis.RIGHT_Y,
    }
    stick_modifiers = {
        fc.StickAxis.LEFT_X: stick_to_stick,
        fc.StickAxis.LEFT_Y: stick_to_stick,
        fc.StickAxis.RIGHT_X: stick_to_stick,
        fc.StickAxis.RIGHT_Y: stick_to_stick,
    }
    bindings = [
        fc.Binding(
            event=(evdev.ecodes.EV_KEY, code), output=button, modifier=button_to_button
        )
        for code, button in buttons.items()
    ]
    bindings.extend([
        fc.Binding(
            event=(evdev.ecodes.EV_ABS, code), output=axis, modifier=stick_modifiers[axis], 
        )
        for code, axis in stick_axes.items()
    ])

    async with server:
        logger.info("Fake-con server is running.")
        listener.register_handler(
            {
                (evdev.ecodes.EV_KEY, evdev.ecodes.BTN_B),
            },
            handler=fc.InputRemapper(
                controller_api=server.controller, bindings=bindings
            ),
        )
        listener.register_handler(
            {
                (evdev.ecodes.EV_KEY, evdev.ecodes.BTN_A),
            },
            handler=DebugHandler(),
        )
        listener.run()
        logger.info("Input device listener is running. Press A to run remapping, B to show debug logging.")
        await asyncio.Event().wait()  # For testing purposes, keep the script running indefinitely to listen for events.


if __name__ == "__main__":

    asyncio.run(main())
