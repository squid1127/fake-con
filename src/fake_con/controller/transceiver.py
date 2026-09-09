"""Device transceiver for the fake-con system."""

import asyncio
import socket
from collections.abc import Callable
from logging import getLogger
from typing import Any

from ..models.constants import TICKRATE_TOLERANCE, TICKRATE_WARNING_DURATION
from ..models.input import (
    INPUT_REPORT_RATE,
    ControllerType,
    InputReportType,
    OutputReportType,
    OutputSubcommand,
)
from .state import ControllerState
from .utils import pretty_bytes

logger = getLogger(__name__)


class ControllerTransceiver:
    """Handles the transmission and reception of controller state data."""

    def __init__(
        self,
        controller_state: ControllerState,
        control_socket: socket.socket,
        interrupt_socket: socket.socket,
        address: str,
    ):
        self.controller_state = controller_state
        self._control_socket = control_socket
        self._interrupt_socket = interrupt_socket
        self._address = address

        self._send_loop_task: asyncio.Task | None = None
        self._receive_loop_task: asyncio.Task | None = None
        self._stopped = asyncio.Event()
        self._input_ready = asyncio.Event()  # Event to signal that input can be sent
        self._on_tick = asyncio.Event()  # Event to signal that a tick has occurred
        self._send_lock = (
            asyncio.Lock()
        )  # Lock to ensure only one send operation at a time
        self._stop_lock = asyncio.Lock()

        self.COMMAND_CALLBACKS: dict[OutputSubcommand, Callable[[bytes], Any]] = {
            OutputSubcommand.SET_INPUT_REPORT_MODE: self.handle_set_input_report_mode,
            OutputSubcommand.GET_DEVICE_INFO: self.handle_get_device_info,
            OutputSubcommand.SET_SHIPMENT_STATE: self.handle_set_shipment_state,
            OutputSubcommand.GET_SPI_FLASH: self.handle_get_spi_flash,
            OutputSubcommand.GET_TRIGGER_TIMES: self.handle_get_trigger_times,
            OutputSubcommand.ENABLE_IMU: self.handle_enable_imu,
        }

    async def start(self):
        """Start the transceiver."""
        self._stopped.clear()  # Clear the event at the start
        self._input_ready.clear()
        self._on_tick.clear()

        logger.info("Starting controller transceiver.")
        self._send_loop_task = asyncio.create_task(self._send_loop())
        self._receive_loop_task = asyncio.create_task(self._receive_loop())

        logger.info("Waiting for the first input report to be received...")
        empty_report_task = asyncio.create_task(self.send_empty_input())
        try:
            await asyncio.wait_for(self._input_ready.wait(), timeout=5.0)
        except TimeoutError:
            logger.warning("Timeout waiting for initial handshake.")
            self.controller_state.set_input_report_type(InputReportType.STANDARD_FULL)
            await self.handle_get_trigger_times(bytes())
            await self._input_ready.wait()
        except asyncio.CancelledError:
            await self._cancel_task(empty_report_task)
            await self.stop()
            raise
        logger.info("Handshake complete. Starting to send controller state data.")

        await self._cancel_task(empty_report_task)

    async def stop(self):
        """Stop the transceiver."""
        async with self._stop_lock:
            if self.is_stopped:
                return

            self._input_ready.set()
            self._stopped.set()
            self._on_tick.clear()

            send_task = self._send_loop_task
            receive_task = self._receive_loop_task
            self._send_loop_task = None
            self._receive_loop_task = None
            await self._cancel_task(send_task)
            await self._cancel_task(receive_task)

            self._control_socket.close()
            self._interrupt_socket.close()

    async def _cancel_task(self, task: asyncio.Task | None):
        """Cancel a task and wait for it unless it is the current task."""
        if task is None or task is asyncio.current_task():
            return
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Transceiver task failed while shutting down.")

    async def wait_for_tick(self):
        """Wait for the next tick to occur."""
        await self._on_tick.wait()

    async def _send_loop(self):
        """Continuously send controller state data at the specified report rate."""
        await self._input_ready.wait()  # Wait until an input report has been received

        loop = asyncio.get_running_loop()
        if self.controller_state.input_report_type is None:
            logger.info("No input report type set; skipping send loop.")
            return  # No input report, so no sending is needed
        report_rate = INPUT_REPORT_RATE[self.controller_state.input_report_type]
        if report_rate is None:
            logger.info("Input report type has no report rate; skipping send loop.")
            return  # No report rate, so no sending is needed
        report_interval = report_rate  # Interval in seconds

        next_tick = loop.time()
        drift_started: float | None = None
        while not self.is_stopped:
            scheduled_tick = next_tick
            await asyncio.sleep(max(0, scheduled_tick - loop.time()))
            if self.is_stopped:
                return

            tick_started = loop.time()
            lateness = tick_started - scheduled_tick
            await self._send()
            tick_finished = loop.time()
            next_tick += report_interval

            tick_duration = tick_finished - tick_started
            tolerance = report_interval * TICKRATE_TOLERANCE
            if lateness > tolerance or tick_duration > report_interval + tolerance:
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
        asyncio.get_running_loop()
        report = self.controller_state.as_bytes()
        if report is None:
            logger.debug("Controller state is None; skipping send.")
            return
        await self._send_bytes(report)
        self._on_tick.set()  # Signal that a tick has occurred
        self._on_tick.clear()  # Clear the event for the next tick

    async def _receive_loop(self):
        """Continuously receive data from the control socket."""
        loop = asyncio.get_running_loop()

        logger.info("Starting receive loop for control socket.")
        while not self.is_stopped:
            try:
                data = await loop.sock_recv(self._interrupt_socket, 50)
                if not data:
                    logger.info("Control socket closed by peer.")
                    break
            except asyncio.CancelledError:
                raise
            except OSError as e:
                logger.exception(f"Failed to receive data: {e}")
                break  # Exit the loop on receive failure
            await self.handle_subcommand(data)  # Handle the received subcommand

    # Command handling methods

    async def handle_subcommand(self, data: bytes):
        """Handle a subcommand received from the control socket."""
        # logger.debug(f"Received data: \n{pretty_bytes(data)}")
        if data[0] != 0xA2:
            logger.warning("Received unexpected data format.")
            return
        if data[1] != OutputReportType.SUBCOMMAND.value:
            # logger.warning("Received non-subcommand data.")
            return

        command = data[11]
        if command not in OutputSubcommand._value2member_map_:
            logger.warning("Received unknown subcommand: %s", command)
            return
        command = OutputSubcommand(command)
        command_cb = self.COMMAND_CALLBACKS.get(command, None)
        if command_cb:
            await command_cb(data)
        else:
            logger.warning("No callback registered for subcommand: %s", command.name)

    async def handle_set_input_report_mode(self, data: bytes):
        """Handle the SET_INPUT_REPORT_MODE subcommand."""
        report_mode = data[12]
        report_type = InputReportType(report_mode)
        self.controller_state.set_input_report_type(report_type)

        report = self.controller_state.as_bytes(
            input_report_type=InputReportType.REPLY_ONLY
        )
        if report is None:
            raise RuntimeError("Failed to generate input report mode report.")

        report[14] = 0x80  # ACK
        report[15] = OutputSubcommand.SET_INPUT_REPORT_MODE.value  # Subcommand ID
        await self._send_bytes(report)
        logger.debug("Sent input report mode report: \n%s", pretty_bytes(report))

    async def handle_get_device_info(self, data: bytes):
        """Handle the GET_DEVICE_INFO subcommand."""
        # This is a placeholder implementation. You should implement the actual logic to handle this subcommand.
        report = self.controller_state.as_bytes(
            input_report_type=InputReportType.REPLY_ONLY
        )
        if report is None:
            raise RuntimeError("Failed to generate device info report.")

        report[14] = 0x82  # ACK
        report[15] = OutputSubcommand.GET_DEVICE_INFO.value  # Subcommand ID
        report[16] = 0x40  # Firmware version
        report[17] = 0x00
        report[18] = self.controller_state.controller_type.raw_value  # Controller type
        report[19] = 0x02  # Always 0x02
        report[20:26] = bytes.fromhex(
            self._address.replace(":", "")
        )  # Controller MAC address
        report[26] = 0x01  # Always 0x01
        report[27] = 0x00  # Always 0x00
        await self._send_bytes(report)
        logger.debug("Sent device info report: \n%s", pretty_bytes(report))

    async def handle_set_shipment_state(self, data: bytes):
        """Handle the SET_SHIPMENT_STATE subcommand. Essentially ignores it."""
        report = self.controller_state.as_bytes(
            input_report_type=InputReportType.REPLY_ONLY
        )
        if report is None:
            raise RuntimeError("Failed to generate shipment state report.")
        report[14] = 0x80  # ACK
        report[15] = OutputSubcommand.SET_SHIPMENT_STATE.value  # Subcommand ID
        await self._send_bytes(report)
        logger.debug("Sent shipment state report: \n%s", pretty_bytes(report))

    async def handle_get_spi_flash(self, data: bytes):
        """Handle a GET_SPI_FLASH request."""
        if len(data) < 17:
            logger.warning("GET_SPI_FLASH request is too short: %d bytes", len(data))
            return

        address = data[12:16]
        size = data[16]
        if size > 0x1D:
            logger.warning("GET_SPI_FLASH request is too large: 0x%02X", size)
            return

        report = self.controller_state.as_bytes(
            input_report_type=InputReportType.REPLY_ONLY
        )
        if report is None:
            raise RuntimeError("Failed to generate SPI flash report.")
        report[14] = 0x90  # ACK
        report[15] = OutputSubcommand.GET_SPI_FLASH.value  # Subcommand ID
        report[16:20] = address
        report[20] = size
        report[21 : 21 + size] = bytes(size)
        await self._send_bytes(report)
        logger.debug("Sent SPI flash report: \n%s", pretty_bytes(report))

    async def handle_get_trigger_times(self, data: bytes):
        """Handle a GET_TRIGGER_TIMES request."""
        report = self.controller_state.as_bytes(
            input_report_type=InputReportType.REPLY_ONLY
        )
        if report is None:
            raise RuntimeError("Failed to generate trigger times report.")
        report[14] = 0x83  # ACK
        report[15] = OutputSubcommand.GET_TRIGGER_TIMES.value  # Subcommand ID

        # Push the right buttons for controler type
        if self.controller_state.controller_type == ControllerType.PRO_CONTROLLER:
            report[16:20] = bytes([0x2C, 0x01] * 2)  # Left trigger time
        else:
            report[24:28] = bytes([0x2C, 0x01] * 2)  # Right trigger time
        await self._send_bytes(report)
        logger.debug("Sent trigger times report: \n%s", pretty_bytes(report))

        self._input_ready.set()  # Handle trigger times is the last step in the handshake, so we can set the event to allow sending controller state data

    async def handle_enable_imu(self, data: bytes):
        """Handle an ENABLE_IMU request. This is in fact useless"""

    # According to the original project, the transmission of an empty input report is necessary to get the initial replies from the switch. This method sends an empty input report to the switch.
    async def send_empty_input(self):
        """Send an empty input report to the switch."""
        report = bytearray(50)
        report[0] = 0xA1
        try:
            for _ in range(40):
                await self._send_bytes(report)
            logger.debug("Sent empty input report.")
        except OSError:
            logger.exception("Failed to send empty input report")
            await self.stop()  # Stop the transceiver on send failure

    async def _send_bytes(self, data: bytes | bytearray):
        """Send raw bytes over the interrupt socket."""

        if self.is_stopped:
            logger.debug("Transceiver is stopped; skipping send.")
            return

        loop = asyncio.get_running_loop()
        try:
            async with self._send_lock:
                await loop.sock_sendall(self._interrupt_socket, data)
        except OSError:
            logger.exception("Failed to send data")
            await self.stop()  # Stop the transceiver on send failure


    @property
    def is_stopped(self) -> bool:
        """Check if the transceiver is stopped."""
        return self._stopped.is_set()
