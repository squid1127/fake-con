"""Run an FPS-style keyboard and mouse controller remapper."""

import asyncio
import logging

from fake_con import Controller, MacroController, connect
from fake_con.keyboard import (
    AxisTarget,
    ButtonTarget,
    ClickTarget,
    InputMapping,
    ecodes,
    remap_keyboard,
    wait_for_click,
    wait_for_space,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BINDS: InputMapping = {
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
    ecodes.BTN_LEFT: ClickTarget("zr"),
    ecodes.BTN_RIGHT: ClickTarget("zl"),
}


async def main():
    logger.info(
        "Press Space on the keyboard to select it, then click the mouse to select it."
    )
    keyboard, mouse = await asyncio.gather(wait_for_space(), wait_for_click())
    controller = await connect(
        Controller.PRO_CONTROLLER,
        auto_pairing=True,
    )
    macro = MacroController(controller)
    try:
        await remap_keyboard(controller, [keyboard, mouse], mapping=BINDS, macro=macro)
    finally:
        await controller.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
