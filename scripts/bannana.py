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
    # ecodes.KEY_W: AxisTarget("right", "y", 1.0),
    # ecodes.KEY_A: AxisTarget("right", "x", -1.0),
    # ecodes.KEY_S: AxisTarget("right", "y", -1.0),
    # ecodes.KEY_D: AxisTarget("right", "x", 1.0),
    
    ecodes.KEY_Z: ButtonTarget("a"),
    ecodes.KEY_X: ButtonTarget("b"),
    ecodes.KEY_S: ButtonTarget("x"),
    ecodes.KEY_C: ButtonTarget("y"),

    
    ecodes.KEY_UP: AxisTarget("left", "y", 1.0),
    ecodes.KEY_LEFT: AxisTarget("left", "x", -1.0),
    ecodes.KEY_DOWN: AxisTarget("left", "y", -1.0),
    ecodes.KEY_RIGHT: AxisTarget("left", "x", 1.0),
    ecodes.KEY_Y: ButtonTarget("up"),
    ecodes.KEY_G: ButtonTarget("left"),
    ecodes.KEY_H: ButtonTarget("down"),
    ecodes.KEY_J: ButtonTarget("right"),

    ecodes.KEY_1: ButtonTarget("zr"),
    ecodes.KEY_3: ButtonTarget("zl"),
    ecodes.KEY_Q: ButtonTarget("l"),
    ecodes.KEY_E: ButtonTarget("r"),
    ecodes.KEY_I: ButtonTarget("minus"),
    ecodes.KEY_P: ButtonTarget("plus"),


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
