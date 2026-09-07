"""Utility methods for the controller."""


import asyncio


async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in an executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def run_command(command: list[str]) -> str:
    """Run a command in a subprocess and return its output."""
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"Command {command} failed with error: {stderr.decode()}")
    return stdout.decode().strip()