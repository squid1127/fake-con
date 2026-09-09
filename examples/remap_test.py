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
    logger.debug(f"Mapping mouse movement ({value} -> {out})")
    return out


def mouse_to_stick_inverted(value: int, context: fc.InputContext) -> float:
    """Convert mouse movement to stick axis value, inverted."""
    out = max(-1.0, min(1.0, -value / 20))
    logger.debug(f"Mapping mouse movement inverted ({value} -> {out})")
    return out


async def main():
    """Main function to run the test."""
    config = fc.FakeConConfig()
    server = fc.FakeConServer(config=config)

    listener = fc.InputDeviceListener()

    async with server:
        logger.info("Fake-con server is running.")
        listener.register_handler(
            {
                (evdev.ecodes.EV_KEY, evdev.ecodes.BTN_LEFT),
            },
            handler=fc.InputRemapper(
                controller_api=server.controller,
                bindings=[
                    fc.Binding(
                        event=(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_LEFT),
                        output=fc.Button.A,
                    ),
                    fc.Binding(
                        event=(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_RIGHT),
                        output=fc.Button.B,
                    ),
                    fc.Binding(
                        event=(evdev.ecodes.EV_KEY, evdev.ecodes.BTN_MIDDLE),
                        output=fc.Button.X,
                    ),
                    fc.Binding(
                        event=(evdev.ecodes.EV_REL, evdev.ecodes.REL_X),
                        output=fc.StickAxis.RIGHT_X,
                        modifier=mouse_to_stick,
                        decay=0.9,
                    ),
                    fc.Binding(
                        event=(evdev.ecodes.EV_REL, evdev.ecodes.REL_Y),
                        output=fc.StickAxis.RIGHT_Y,
                        modifier=mouse_to_stick_inverted,
                        decay=0.9,
                    ),
                ],
            ),
        )
        listener.run()
        await asyncio.Event().wait()  # For testing purposes, keep the script running indefinitely to listen for events.


if __name__ == "__main__":

    asyncio.run(main())
