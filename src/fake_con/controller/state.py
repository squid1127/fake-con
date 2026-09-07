"""Controller state management for the fake-con system."""

import struct
from logging import getLogger

from ..models.input import (
    SUPPORTED_BUTTONS,
    SUPPORTED_STICKS,
    Button,
    ControllerType,
    InputReportType,
    StickAxis,
)

logger = getLogger(__name__)


class ControllerState:
    """Represents the state of a controller."""

    def __init__(
        self, controller_type: ControllerType
    ):
        self._controller_type = controller_type
        self._input_report_type: InputReportType | None = None
        self._timer: int = 0

        self._buttons: list[list[bool]] = [[False] * 8 for _ in range(3)]
        self._sticks: list[list[int]] = [[2048] * 2 for _ in range(4)]  # Centered at 2048
        self.reset()

    def reset(self):
        """Reset the controller state."""
        for button in Button:
            self.set_button(button, False, force=True)

    def set_button(self, button: Button, pressed: bool, force: bool = False):
        """Set the state of a button."""
        if (button not in SUPPORTED_BUTTONS) and not force:
            logger.warning(f"Button {button} is not supported.")
            return

        self._buttons[button.value[0]][button.value[1]] = pressed

    def set_stick(self, axis: StickAxis, value: int, force: bool = False):
        """Set the state of a stick axis."""
        if value < 0 or value > 4095:
            raise ValueError("Stick value must be between 0 and 4095.")

        if (axis not in SUPPORTED_STICKS) and not force:
            logger.warning(f"Stick axis {axis} is not supported.")

        self._sticks[axis.value[0]][axis.value[1]] = value

    def as_bytes(self, no_increment: bool = False, input_report_type: InputReportType | None = None) -> bytearray | None:
        """Convert the controller state to bytes for transmission."""
        report = bytearray(50)
        
        input_report_type = input_report_type or self._input_report_type

        # Report type
        if input_report_type is None:
            return None
        report_type = input_report_type.value
        if report_type is not None:
            report[0] = report_type
        else:
            return None

        # Timer
        report[1] = self._timer
        if not no_increment:
            self._timer += 1
            self._timer = (self._timer + 1) % 256

        # Power State
        report[2] = 0x8E

        # Buttons
        report[3:6] = self.pack_buttons()

        # Sticks
        report[6:9] = self.pack_stick(
            self._sticks[StickAxis.LEFT_X.value[0]][StickAxis.LEFT_X.value[1]],
            self._sticks[StickAxis.LEFT_Y.value[0]][StickAxis.LEFT_Y.value[1]],
        )
        report[9:12] = self.pack_stick(
            self._sticks[StickAxis.RIGHT_X.value[0]][StickAxis.RIGHT_X.value[1]],
            self._sticks[StickAxis.RIGHT_Y.value[0]][StickAxis.RIGHT_Y.value[1]],
        )
        
        # Vibration
        report[12] = 0x80


        return report

    def pack_stick(self, x: int, y: int) -> bytes:
        """x, y are 12-bit values (0-4095), center ~2048."""
        return struct.pack(
            "<3B",
            x & 0xFF,
            ((x >> 8) & 0x0F) | ((y & 0x0F) << 4),
            (y >> 4) & 0xFF,
        )

    def pack_buttons(self) -> bytes:
        """Pack the button states into a 3-byte array."""
        result = bytearray(3)
        for byte_idx in range(3):
            value = 0
            for bit_idx in range(8):
                if self._buttons[byte_idx][bit_idx]:
                    value |= 1 << bit_idx
            result[byte_idx] = value
        return bytes(result)
    
    def set_input_report_type(self, report_type: InputReportType):
        """Set the input report type."""
        self._input_report_type = report_type

    @property
    def controller_type(self) -> ControllerType:
        """Get the controller type."""
        return self._controller_type
    @property
    def input_report_type(self) -> InputReportType | None:
        """Get the input report type."""
        return self._input_report_type