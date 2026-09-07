"""Server controller for the fake-con system."""

import asyncio
import socket
import struct
from logging import getLogger

from ..models.config import FakeConConfig
from ..models.constants import (
    BT_SECURITY,
    BT_SECURITY_LOW,
    DEVICE_CLASS_LEGACY,
)
from .api import ControllerAPI
from .dbus_interface import DBusInterface
from .pairing_agent import PairingAgent
from .state import ControllerState
from .transceiver import ControllerTransceiver
from .utils import run_command

logger = getLogger(__name__)


class FakeConServer:
    """Server controller for the fake-con system.
    
    This class manages the Bluetooth connection, pairing, and controller state.
    
    Also functions as an async context manager, allowing for easy startup and shutdown of the server."""

    def __init__(self, config: FakeConConfig):
        """Initialize the server controller with the given configuration.

        Args:
            config: The configuration for the server.
        """
        self._config = config
        self._pairing_agent: PairingAgent | None = None  # Pairing agent
        if self._config.pairing_agent:
            self._pairing_agent = PairingAgent()

        self._dbus_interface: DBusInterface = DBusInterface(config=config)

        self._control_socket: socket.socket | None = None  # Control socket
        self._interrupt_socket: socket.socket | None = None  # Interrupt socket
        self._transceiver: ControllerTransceiver | None = None  # Controller transceiver

    async def start(self):
        """Start the server controller."""
        logger.info("Starting the fake-con server...")
        await self._dbus_interface.auto()
        await self.create_sockets()
        await self.set_device_class()
        await self.pair()

        if self._pairing_agent is not None:
            self._pairing_agent.close()
            self._pairing_agent = None

        await self.attach_transceiver()

    async def stop(self):
        """Stop the server controller."""
        logger.info("Stopping the fake-con server...")
        if self._transceiver is not None:
            await self._transceiver.stop()
            self._transceiver = None
        if self._control_socket is not None:
            self._control_socket.close()
            self._control_socket = None
        if self._interrupt_socket is not None:
            self._interrupt_socket.close()
            self._interrupt_socket = None
        if self._pairing_agent is not None:
            self._pairing_agent.close()
            self._pairing_agent = None
        await self._dbus_interface.stop_advertising()

    async def create_sockets(self):
        """Create the control and interrupt sockets."""
        logger.info("Creating control and interrupt sockets...")
        address = await self._dbus_interface.get_address()
        logger.info("Binding to socket for address: %s", address)
        self._control_socket = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self._control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._control_socket.setsockopt(
            socket.SOL_BLUETOOTH, BT_SECURITY, struct.pack("BB", BT_SECURITY_LOW, 0)
        )
        self._control_socket.setblocking(False)
        self._control_socket.bind((address, self._config.control_channel_psm))

        self._interrupt_socket = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self._interrupt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._interrupt_socket.setsockopt(
            socket.SOL_BLUETOOTH, BT_SECURITY, struct.pack("BB", BT_SECURITY_LOW, 0)
        )
        self._interrupt_socket.setblocking(False)
        self._interrupt_socket.bind((address, self._config.interrupt_channel_psm))

    async def set_device_class(self):
        """Set the device class for the Bluetooth adapter."""
        if not self._config.set_device_class:
            logger.info("Skipping device class setting as per configuration.")
            return

        command = [
            "hciconfig",
            self._dbus_interface.adapter_name,
            "class",
            DEVICE_CLASS_LEGACY,
        ]

        logger.info(f"Setting device class: {command}")
        try:
            await run_command(command)
        except RuntimeError:
            logger.exception("Failed to set device class. FakeCon will probably fail")
        else:
            logger.info("Device class set.")

    async def pair(self):
        """Pair the server with a switch."""
        logger.info("Starting pairing process...")
        self.control_socket.listen(1)
        self.interrupt_socket.listen(1)

        logger.info("Waiting for a switch to pair...")
        client_control, client_interrupt = await asyncio.gather(
            self._accept_socket(self.control_socket),
            self._accept_socket(self.interrupt_socket),
        )
        self.control_socket.close()
        self.interrupt_socket.close()
        self._control_socket = client_control
        self._interrupt_socket = client_interrupt
        self._control_socket.setblocking(False)
        self._interrupt_socket.setblocking(False)
        self._control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)
        self._interrupt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 0)

        logger.info("Switch paired successfully.")
        await self._dbus_interface.stop_advertising()

    async def attach_transceiver(self):
        """Attach a controller transceiver to the paired switch."""
        if self._control_socket is None or self._interrupt_socket is None:
            raise RuntimeError(
                "Sockets are not initialized. Call create_sockets() first."
            )

        logger.info("Attaching controller transceiver...")
        transceiver = ControllerTransceiver(
            controller_state=ControllerState(
                controller_type=self._config.controller_type,
            ),
            control_socket=self._control_socket,
            interrupt_socket=self._interrupt_socket,
            address=await self._dbus_interface.get_address(),
        )
        self._transceiver = transceiver
        await transceiver.start()

    async def _accept_socket(self, sock: socket.socket) -> socket.socket:
        """Accept a connection on the given socket."""
        loop = asyncio.get_running_loop()
        conn, addr = await loop.sock_accept(sock)
        logger.info("Accepted connection from %s", addr)
        return conn

    async def __aenter__(self):
        """Enter the async context manager."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Exit the async context manager."""
        await self.stop()

    @property
    def control_socket(self) -> socket.socket:
        """Get the control socket."""
        if self._control_socket is None:
            raise RuntimeError("Control socket is not initialized.")
        return self._control_socket

    @property
    def interrupt_socket(self) -> socket.socket:
        """Get the interrupt socket."""
        if self._interrupt_socket is None:
            raise RuntimeError("Interrupt socket is not initialized.")
        return self._interrupt_socket

    @property
    def controller(self) -> ControllerAPI:
        """Get the controller API."""
        if self._transceiver is None:
            raise RuntimeError("Controller transceiver is not initialized.")
        return ControllerAPI(transceiver=self._transceiver)