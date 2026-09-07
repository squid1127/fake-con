"""Input constants for fake_con."""

from collections.abc import Mapping
from enum import Enum


class Button(Enum):
    """Enum for buttons on the controller."""

    Y = (0, 0)
    X = (0, 1)
    B = (0, 2)
    A = (0, 3)
    SR = (0, 4)
    SL = (0, 5)
    R = (0, 6)
    ZR = (0, 7)

    MINUS = (1, 0)
    PLUS = (1, 1)
    R_STICK = (1, 2)
    L_STICK = (1, 3)
    HOME = (1, 4)
    CAPTURE = (1, 5)

    DOWN = (2, 0)
    UP = (2, 1)
    RIGHT = (2, 2)
    LEFT = (2, 3)
    LSR = (2, 4) # Left Joy-Con SL button
    LSL = (2, 5) # Left Joy-Con SR button
    L = (2, 6)
    ZL = (2, 7)


class StickAxis(Enum):
    """Enum for axes on the analog sticks."""

    LEFT_X = (0, 0)
    LEFT_Y = (0, 1)
    RIGHT_X = (1, 0)
    RIGHT_Y = (1, 1)


class ControllerType(Enum):
    JOYCON_L = 0x01
    JOYCON_R = 0x02
    PRO_CONTROLLER = 0x03

    @property
    def device_name(self):
        """Get the name of the controller type."""
        return CONTROLLER_NAMES[self]


class InputReportType(Enum):
    """Enum for input report types."""

    STANDARD_FULL = 0x30
    STANDARD_FULL_NFC = 0x31
    SIMPLE_HID = 0x3F
    REPLY_ONLY = 0x21
    NO_INPUT_REPORT = None


# * Mappings

CONTROLLER_NAMES = {
    ControllerType.JOYCON_L: "Joy-Con (L)",
    ControllerType.JOYCON_R: "Joy-Con (R)",
    ControllerType.PRO_CONTROLLER: "Pro Controller",
}

INPUT_REPORT_RATE: Mapping[InputReportType, float | None] = {
    InputReportType.STANDARD_FULL: 1 / 60,  # Standard full: 60 Hz
    InputReportType.STANDARD_FULL_NFC: 1 / 60,  # Standard full w/ NFC: 60 Hz
    InputReportType.SIMPLE_HID: 1.0,  # Simple HID: 1 Hz
    InputReportType.REPLY_ONLY: None,  # Reply-only
    InputReportType.NO_INPUT_REPORT: None,  # No input report
}
INPUT_REPORT_FROM_COMMAND: Mapping[int, InputReportType] = {
    0x00: InputReportType.STANDARD_FULL_NFC,
    0x01: InputReportType.STANDARD_FULL_NFC,
    0x02: InputReportType.STANDARD_FULL_NFC,
    0x30: InputReportType.STANDARD_FULL,
    0x31: InputReportType.STANDARD_FULL_NFC,
    0x3F: InputReportType.SIMPLE_HID,
}

SUPPORTED_BUTTONS: Mapping[ControllerType, set[Button]] = {
    ControllerType.JOYCON_L: {
        Button.MINUS,
        Button.L_STICK,
        Button.CAPTURE,
        Button.UP,
        Button.DOWN,
        Button.LEFT,
        Button.RIGHT,
        Button.ZL,
        Button.L,
        Button.SL,
        Button.SR,
    },
    ControllerType.JOYCON_R: {
        Button.PLUS,
        Button.R_STICK,
        Button.HOME,
        Button.UP,
        Button.X,
        Button.Y,
        Button.B,
        Button.A,
        Button.ZR,
        Button.R,
        Button.LSL,
        Button.LSR,
    },
    ControllerType.PRO_CONTROLLER: {
        Button.MINUS,
        Button.PLUS,
        Button.L_STICK,
        Button.R_STICK,
        Button.HOME,
        Button.CAPTURE,
        Button.UP,
        Button.DOWN,
        Button.LEFT,
        Button.RIGHT,
        Button.X,
        Button.Y,
        Button.B,
        Button.A,
        Button.ZL,
        Button.L,
        Button.ZR,
        Button.R,
    },
}
SUPPORTED_STICKS: Mapping[ControllerType, set[StickAxis]] = {
    ControllerType.JOYCON_L: {StickAxis.LEFT_X, StickAxis.LEFT_Y},
    ControllerType.JOYCON_R: {StickAxis.RIGHT_X, StickAxis.RIGHT_Y},
    ControllerType.PRO_CONTROLLER: {
        StickAxis.LEFT_X,
        StickAxis.LEFT_Y,
        StickAxis.RIGHT_X,
        StickAxis.RIGHT_Y,
    },
}
