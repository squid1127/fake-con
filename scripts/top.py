"""Remap keyboard input to a fake-con controller."""

import asyncio
import logging

from fake_con import Controller, connect
from fake_con.keyboard import (
    AxisTarget,
    ButtonTarget,
    InputMapping,
    ecodes,
    remap_keyboard,
    wait_for_space,
)

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

BINDS: InputMapping = {
    ecodes.KEY_UP: AxisTarget("left", "y", 1.0),
    ecodes.KEY_LEFT: AxisTarget("left", "x", -1.0),
    ecodes.KEY_DOWN: AxisTarget("left", "y", -1.0),
    ecodes.KEY_RIGHT: AxisTarget("left", "x", 1.0),
    
    ecodes.KEY_Z: ButtonTarget("x"),
    ecodes.KEY_X: ButtonTarget("b"),
    ecodes.KEY_C: ButtonTarget("a"),
    ecodes.KEY_A: ButtonTarget("y"),


    ecodes.KEY_Q: ButtonTarget("l"),
    ecodes.KEY_E: ButtonTarget("r"),
    ecodes.KEY_1: ButtonTarget("minus"),
    ecodes.KEY_3: ButtonTarget("plus"),

}

async def main():
    logger.info("Press Space on the keyboard to select it.")
    keyboard = await wait_for_space()
    controller = await connect(
        Controller.PRO_CONTROLLER,
        auto_pairing=True,
    )
    try:
        await remap_keyboard(controller, [keyboard], mapping=BINDS)
    finally:
        await controller.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
