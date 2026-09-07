"""Test script"""

import asyncio
from logging import DEBUG, getLogger

import random
from coloredlogs import install

import fake_con as fc

install(level=DEBUG, fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = getLogger(__name__)


async def main():
    """Main function to run the test."""
    config = fc.FakeConConfig()
    server = fc.FakeConServer(config=config)
    
    logger.info("Starting the fake-con server...")
    
    async with server:
        logger.info("Fake-con server is running.")
        async def tap(button: fc.Button):
            """Tap a button on the controller."""
            await server.controller.tap(button, duration_ticks=5)
            await server.controller.wait(10)
            
        await tap(fc.Button.A)
        await tap(fc.Button.HOME)
        await asyncio.sleep(0.4)
        await tap(fc.Button.DOWN)
        await tap(fc.Button.DOWN)
        await tap(fc.Button.LEFT)
        await tap(fc.Button.LEFT)
        await tap(fc.Button.A)
        await asyncio.sleep(0.4)
        for _ in range(9):
            await tap(fc.Button.DOWN)
        await tap(fc.Button.A)
        for _ in range(10):
            await tap(fc.Button.DOWN)
        await tap(fc.Button.A)
        
        server.controller.set_left_stick(1, 1)
        await asyncio.sleep(1)
        for _ in range(300):
            x = random.uniform(-1, 1)
            y = random.uniform(-1, 1)
            server.controller.set_left_stick(x, y)
            await server.controller.wait(2)
            
        server.controller.set_left_stick(0, 0)
        for i in range(4096):
            server.controller.set_stick_raw(fc.StickAxis.LEFT_X, i)
            await server.controller.wait(1)
        
        
        logger.info("Script done!")
        await asyncio.sleep(10)  # Keep the server running for a while to observe behavior
    
if __name__ == "__main__":  
    asyncio.run(main())