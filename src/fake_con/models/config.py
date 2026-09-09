"""Configuration models for the fake-con system."""

from pydantic import BaseModel, Field

from .input import ControllerType


class FakeConConfig(BaseModel):
    """Configuration model for the fake-con system."""

    controller_type: ControllerType = Field(
        default=ControllerType.PRO_CONTROLLER,
        description="The type of controller to emulate.",
    )
    control_channel_psm: int = Field(
        default=17,
        description="HID control channel port number (PSM) for the controller.",
    )
    interrupt_channel_psm: int = Field(
        default=19,
        description="HID interrupt channel port number (PSM) for the controller.",
    )
    bluetooth_device_id: str | None = Field(
        default=None,
        description="/dev device or mac address of the Bluetooth device to use for emulation. If None, the system will attempt to find a suitable device automatically.",
    )
    pairing_agent: bool = Field(
        default=True,
        description="Whether to create a pairing agent to automatically accept pairing requests. If False, the user will need to manually accept pairing requests.",
    )
    auto_reconnect: bool = Field(
        default=True,
        description="Whether to automatically reconnect to the controller if the connection is lost.",
    )
    reconnect_on_startup: bool = Field(
        default=False,
        description="Whether to attempt to reconnect to the controller on startup if a previous connection was established.",
    )
    set_device_class: bool = Field(
        default=True,
        description="Whether use hciconfig to set the device class of the Bluetooth adapter. This command may not exist on all systems, and can be alternatively set manually by editing the bluetooth configuration files.",
    )