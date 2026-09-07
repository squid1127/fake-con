"""Test script"""

import asyncio
from logging import DEBUG, getLogger

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
        await asyncio.sleep(3)
    
if __name__ == "__main__":  
    asyncio.run(main())