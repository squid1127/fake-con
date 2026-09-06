"""Importable async API for controlling an emulated Nintendo controller."""

import asyncio
import logging
from contextlib import suppress

from .joycontrol.controller import Controller
from .joycontrol.controller_state import (
    ControllerState,
    button_press,
    button_push,
    button_release,
    button_update,
    stick_update,
)
from .joycontrol.memory import FlashMemory
from .joycontrol.protocol import controller_protocol_factory
from .joycontrol.server import create_hid_server

logger = logging.getLogger(__name__)


class FakeCon:
    """Manage one emulated controller connection.

    The Bluetooth connection is opened by :meth:`connect`. Use the instance as
    an async context manager when the connection should be closed automatically.
    """

    def __init__(
        self,
        controller: Controller | str,
        *,
        device_id=None,
        reconnect_bt_addr=None,
        spi_flash: FlashMemory | bytes | None = None,
        ctl_psm=17,
        itr_psm=19,
        reconnect_timeout=10,
        capture_file=None,
        interactive=False,
        auto_pairing=False,
    ):
        if isinstance(controller, str):
            controller = Controller.from_arg(controller)

        if isinstance(spi_flash, bytes):
            spi_flash = FlashMemory(spi_flash_memory_data=spi_flash)
        elif spi_flash is None:
            spi_flash = FlashMemory()

        self.controller = controller
        self._spi_flash = spi_flash
        self._server_options = {
            "device_id": device_id,
            "reconnect_bt_addr": reconnect_bt_addr,
            "ctl_psm": ctl_psm,
            "itr_psm": itr_psm,
            "reconnect_timeout": reconnect_timeout,
            "capture_file": capture_file,
            "interactive": interactive,
        }
        self._auto_pairing = auto_pairing
        self._pairing_agent = None
        self._transport = None
        self._state: ControllerState | None = None
        self._connect_lock = asyncio.Lock()

    async def connect(self):
        """Pair or reconnect, then wait until the controller accepts input.

        Automatic reconnect falls back to initial pairing when no paired
        Switch is found or the Switch rejects the direct reconnect.
        """
        async with self._connect_lock:
            if self._state is not None:
                return self

            if self._auto_pairing:
                from .joycontrol.pairing_agent import PairingAgent

                self._pairing_agent = PairingAgent()

            while True:
                factory = controller_protocol_factory(
                    self.controller,
                    spi_flash=self._spi_flash,
                    reconnect=self._server_options["reconnect_bt_addr"] is not None,
                )
                try:
                    self._transport, protocol = await create_hid_server(
                        factory,
                        **self._server_options,
                    )
                    break
                except (SystemExit, ConnectionError, TimeoutError) as error:
                    if self._server_options["reconnect_bt_addr"] != "auto":
                        raise
                    logger.warning(
                        "Automatic reconnect was rejected (%s); falling back "
                        "to initial pairing.",
                        error,
                    )
                    self._server_options["reconnect_bt_addr"] = None

            state = protocol.get_controller_state()
            self._state = state
            await state.connect()
            self._close_pairing_agent()
            return self

    async def close(self):
        """Close the Bluetooth connection, if it is open."""
        self._close_pairing_agent()
        if self._transport is not None:
            transport, self._transport = self._transport, None
            self._state = None
            await transport.close()

    def _close_pairing_agent(self):
        if self._pairing_agent is not None:
            self._pairing_agent.close()
            self._pairing_agent = None

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc, traceback):
        await self.close()

    @property
    def state(self) -> ControllerState:
        """The underlying state object after connecting."""
        if self._state is None:
            raise RuntimeError("FakeCon.connect() must be awaited first")
        return self._state

    async def send(self):
        """Send the current button and stick state."""
        await self.state.send()

    async def press(self, *buttons):
        """Press and hold one or more buttons."""
        await button_press(self.state, *buttons)

    async def release(self, *buttons):
        """Release one or more buttons."""
        await button_release(self.state, *buttons)

    async def tap(self, *buttons, seconds=0.1):
        """Press and release one or more buttons."""
        await button_push(self.state, *buttons, sec=seconds)

    async def set_button(self, button, pressed=True):
        """Set one button state and send an input report."""
        await button_update(self.state, button, pressed)

    async def set_stick(self, side, *, x, y):
        """Set a stick using normalized x/y values in the range [-1.0, 1.0]."""
        for value in (x, y):
            if not -1.0 <= value <= 1.0:
                raise ValueError("Stick x and y values must be in [-1.0, 1.0]")

        await self.set_stick_raw(
            side,
            h=round((x + 1.0) * 2047.5),
            v=round((y + 1.0) * 2047.5),
        )

    async def set_stick_raw(self, side, *, h, v):
        """Set a stick using raw horizontal and vertical values in [0, 4095]."""
        if side.lower() in ("l", "left"):
            stick = "l_stick_analog"
        elif side.lower() in ("r", "right"):
            stick = "r_stick_analog"
        else:
            raise ValueError('Stick side must be "l", "left", "r" or "right"')

        await stick_update(self.state, stick, {"h": h, "v": v})


async def connect(controller: Controller | str, **kwargs) -> FakeCon:
    """Create and connect a :class:`FakeCon` session."""
    session = FakeCon(controller, **kwargs)
    try:
        return await session.connect()
    except BaseException:
        with suppress(Exception):
            await session.close()
        raise
