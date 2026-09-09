"""Utility methods for the controller."""


import asyncio
from functools import partial


async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in an executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


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

def pretty_bytes(data: bytes| bytearray) -> str:
    """Return a pretty string representation of bytes."""
    digits = [f"{i:02}" for i in range(len(data))]
    hex_values = [f"{b:02X}" for b in data]
    content = "|".join(hex_values)
    content += "\n" + "-" * len("|".join(digits))
    content += "\n" + "|".join(digits)
    return content