"""Device transceiver for the fake-con system."""

import asyncio
import socket
from logging import getLogger

from ..models.constants import TICKRATE_TOLERANCE, TICKRATE_WARNING_DURATION
from ..models.input import INPUT_REPORT_RATE
from .state import ControllerState

logger = getLogger(__name__)


class ControllerTransceiver:
    """Handles the transmission and reception of controller state data."""

    def __init__(
        self,
        controller_state: ControllerState,
        control_socket: socket.socket,
        interrupt_socket: socket.socket,
    ):
        self._controller_state = controller_state
        self._control_socket = control_socket
        self._interrupt_socket = interrupt_socket

        self._send_loop_task: asyncio.Task | None = None
        self._receive_loop_task: asyncio.Task | None = None
        self._stopped = asyncio.Event()
        self._input_ready = (
            asyncio.Event()
        )  # Event to signal that input can be sent

    async def start(self):
        """Start the transceiver."""
        self._stopped.clear()
        self._input_ready.clear()  # Clear the event at the start

        logger.info("Starting controller transceiver.")
        self._send_loop_task = asyncio.create_task(self._send_loop())
        self._receive_loop_task = asyncio.create_task(self._receive_loop())

        logger.info("Waiting for the first input report to be received...")
        empty_report_task = asyncio.create_task(self.send_empty_input())
        await self._input_ready.wait() # ! Currently, this will wait indefinitely, as handshake logic is not yet implemented. Once the first input report is received, the event will be set, and the transceiver will start sending controller state data at the specified report rate.
        logger.info("First input report received; transceiver is now active.")
        
        if not empty_report_task.done():
            empty_report_task.cancel()
            try:
                await empty_report_task
            except asyncio.CancelledError:
                logger.debug("Empty input report task was cancelled after receiving the first input report.")
                

    async def stop(self):
        """Stop the transceiver."""
        self._input_ready.set()  # Set the event to unblock any waiting coroutines
        self._stopped.set()

        if self._send_loop_task:
            self._send_loop_task.cancel()
            await self._send_loop_task
            self._send_loop_task = None

        if self._receive_loop_task:
            self._receive_loop_task.cancel()
            await self._receive_loop_task
            self._receive_loop_task = None

        self._control_socket.close()
        self._interrupt_socket.close()

    async def _send_loop(self):
        """Continuously send controller state data at the specified report rate."""
        await self._input_ready.wait()  # Wait until an input report has been received

        loop = asyncio.get_running_loop()
        if self._controller_state.input_report_type is None:
            logger.info("No input report type set; skipping send loop.")
            return  # No input report, so no sending is needed
        report_rate = INPUT_REPORT_RATE[self._controller_state.input_report_type]
        if report_rate is None:
            logger.info("Input report type has no report rate; skipping send loop.")
            return  # No report rate, so no sending is needed
        report_interval = report_rate  # Interval in seconds

        next_tick = loop.time()
        drift_started: float | None = None
        while not self.is_stopped:
            await asyncio.sleep(max(0, next_tick - loop.time()))
            if self.is_stopped:
                return

            tick_started = loop.time()
            await self._send()
            tick_finished = loop.time()
            next_tick += report_interval

            tick_duration = tick_finished - tick_started
            lateness = tick_finished - next_tick
            tolerance = report_interval * TICKRATE_TOLERANCE
            if abs(lateness) > tolerance or tick_duration > report_interval + tolerance:
                if drift_started is None:
                    drift_started = tick_started
                elif tick_finished - drift_started >= TICKRATE_WARNING_DURATION:
                    logger.warning(
                        "Controller tick rate is drifting from target: "
                        "target interval %.4fs, send duration %.4fs, "
                        "lateness %.4fs.",
                        report_interval,
                        tick_duration,
                        lateness,
                    )
                    drift_started = tick_finished
            else:
                drift_started = None

    async def _send(self):
        """Send the current controller state over the interrupt socket."""
        loop = asyncio.get_running_loop()
        report = self._controller_state.as_bytes()
        if report is None:
            logger.debug("Controller state is None; skipping send.")
            return
        try:
            await loop.sock_sendall(self._interrupt_socket, report)
        except OSError as e:
            logger.exception(f"Failed to send controller state: {e}")
            await self.stop()  # Stop the transceiver on send failure

    async def _receive_loop(self):
        """Continuously receive data from the control socket."""
        loop = asyncio.get_running_loop()

        logger.info("Starting receive loop for control socket.")
        while not self.is_stopped:
            try:
                data = await loop.sock_recv(self._control_socket, 50)
                logger.debug(f"Received data from control socket: {data.hex()}")
                if not data:
                    logger.info("Control socket closed by peer.")
                    break
            except asyncio.CancelledError:
                raise
            except OSError as e:
                logger.exception(f"Failed to receive data: {e}")
                break  # Exit the loop on receive failure
            await self.handle_subcommand(data)  # Handle the received subcommand

    async def handle_subcommand(self, data: bytes):
        """Handle a subcommand received from the control socket."""
        # This method should be implemented to handle specific subcommands
        logger.info(f"Received subcommand: {data.hex()}")
        # Example: parse and respond to the subcommand as needed
        if data[0] != 0xA2:
            logger.warning("Received unexpected data format.")
            return

    # According to the original project, the transmission of an empty input report is necessary to get the initial replies from the switch. This method sends an empty input report to the switch.
    async def send_empty_input(self):
        """Send an empty input report to the switch."""
        loop = asyncio.get_running_loop()
        report = bytearray(51)
        report[0] = 0xA1
        try:
            for _ in range(10):
                await loop.sock_sendall(self._interrupt_socket, report)
            logger.debug("Sent empty input report.")
        except OSError:
            logger.exception("Failed to send empty input report")
            await self.stop()  # Stop the transceiver on send failure

    @property
    def is_stopped(self) -> bool:
        """Check if the transceiver is stopped."""
        return self._stopped.is_set()
