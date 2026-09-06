"""Test script implementing fake-con

This script takes control, opens the joystick testing menu, and moves the left stick around for testing"""

import asyncio
from logging import getLogger
import logging
from typing import Sequence

from fake_con import Controller, connect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = getLogger(__name__)

type Inputs = str | float | Sequence[Inputs]


async def main():
    logger.info("Starting fake-con test script...")
    controller = await connect(Controller.PRO_CONTROLLER, auto_pairing=True)

    async def do_inputs(inputs: list[Inputs]):
        for input in inputs:
            if isinstance(input, list):
                await do_inputs(input)
            elif isinstance(input, str):
                logger.info(f"Sending input: {input}")
                await controller.tap(input)
                await asyncio.sleep(0.1)
            elif isinstance(input, float):
                logger.info(f"Waiting for {input} seconds...")
                await asyncio.sleep(input)

    try:
        logger.info("Connected to Switch, doing stuff..")

        await do_inputs([
            "a",
            0.2,
            "home",
            0.5,
            ["down"] * 2,
            ["left"] * 2,
            "a",
            0.25,
            ["down"] * 10,
            "a",
            ["down"] * 10,
            "a",
            0.25,
        ])
        
        logger.info("Left stick -> (0, 0)")
        await controller.set_stick("left", h=0, v=0)
        await asyncio.sleep(4)
        logger.info("Left stick -> (2048, 2,048)")
        await controller.set_stick("left", h=2048, v=2048)
        await asyncio.sleep(2)
        logger.info("Left stick -> (0, 0)")
        await controller.set_stick("left", h=0, v=0)
        await asyncio.sleep(2)
        logger.info("Left stick -> (4095, 4095)")
        await controller.set_stick("left", h=4095, v=4095)
        await asyncio.sleep(2)
        logger.info("Left stick -> (0, 0)")
        await controller.set_stick("left", h=0, v=0)
        await asyncio.sleep(2)
        logger.info("Left stick -> (2048, 2,048)")
        await controller.set_stick("left", h=2048, v=2048)
        await asyncio.sleep(2)
        
        logger.info("Left stick -> Full range test (0, 0) -> (4095, 4095)")
        for i in range(4095):
            logger.info(f"Left stick -> ({i}, {i})")
            await controller.set_stick("left", h=i, v=i)
            await asyncio.sleep(0.01)

        logger.info("Done!")
        await asyncio.sleep(1)

    finally:
        await controller.close()


asyncio.run(main())
