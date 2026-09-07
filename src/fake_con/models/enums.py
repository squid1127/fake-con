"""Enums for the fake-con system."""

from enum import Enum

CONTROLLER_NAMES = {
    0x01: "Joy-Con (L)",
    0x02: "Joy-Con (R)",
    0x03: "Pro Controller",
}

class ControllerType(Enum):
    JOYCON_L = 0x01
    JOYCON_R = 0x02
    PRO_CONTROLLER = 0x03

    @property
    def device_name(self):
        """Get the name of the controller type."""
        return CONTROLLER_NAMES[self.value]