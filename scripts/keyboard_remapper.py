"""Remap keyboard input to a fake-con controller."""

import asyncio
import logging

from fake_con import Controller, MacroController, connect
from fake_con.keyboard import ecodes, remap_keyboard, wait_for_space

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

async def macroloop(macro: MacroController):
    while True:
        await wait_for_space()
        logger.info("Starting macro recording...")
        macro.record_start("main")
        await asyncio.sleep(0.5)
        await wait_for_space()
        logger.info("Stopping macro recording...")
        macro.record_stop("main")
        await asyncio.sleep(0.5)
        await wait_for_space()
        logger.info("Playing macro...")
        await macro.play("main")

async def main():
    logger.info("Press Space on the keyboard to select it.")
    keyboard, controller = await asyncio.gather(
        wait_for_space(), connect(Controller.PRO_CONTROLLER, auto_pairing=True)
    )
    macro = MacroController(controller)
    try:
        await asyncio.gather(
            macroloop(macro),
            remap_keyboard(controller, [keyboard], macro=macro)
        )
    finally:
        await controller.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
