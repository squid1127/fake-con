"""Controller API for the fake-con system."""

from ..models.input import Button, StickAxis
from .transceiver import ControllerTransceiver


class ControllerAPI:
    """API for interacting with the controller."""

    def __init__(self, transceiver: ControllerTransceiver):
        """Initialize the ControllerAPI with a transceiver.

        Args:
            transceiver: The ControllerTransceiver instance
        """
        self._transceiver = transceiver
        
    def set_button(self, button: Button, pressed: bool):
        """(Sync) Set the state of a button.

        Args:
            button: The button to set
            pressed: True if the button is pressed, False otherwise
        """
        self._transceiver.controller_state.set_button(button, pressed)
        
    async def tap(self, button: Button, duration_ticks: int = 1):
        """(Async) Tap a button (press and release) for a specified duration in ticks.

        Args:
            button: The button to tap
            duration_ticks: The number of ticks to hold the button down
        """
        self.set_button(button, True)
        await self.wait(duration_ticks)
        self.set_button(button, False)
        
    async def wait(self, ticks: int = 1):
        """(Async) Wait for a specified number of ticks.

        Args:
            ticks: The number of ticks to wait
        """
        for _ in range(ticks):
            await self._transceiver.wait_for_tick()
    
    def set_left_stick(self, x: float, y: float):
        """(Sync) Set the state of the left stick.

        Args:
            x: The x-axis value (-1.0 to 1.0)
            y: The y-axis value (-1.0 to 1.0)
        """
        self.set_stick_axis(StickAxis.LEFT_X, x)
        self.set_stick_axis(StickAxis.LEFT_Y, y)
    def set_right_stick(self, x: float, y: float):
        """(Sync) Set the state of the right stick.

        Args:
            x: The x-axis value (-1.0 to 1.0)
            y: The y-axis value (-1.0 to 1.0)
        """
        self.set_stick_axis(StickAxis.RIGHT_X, x)
        self.set_stick_axis(StickAxis.RIGHT_Y, y)
            
    def set_stick_axis(self, axis: StickAxis, value: float):
        """(Sync) Set the state of a stick axis.

        Args:
            axis: The stick axis to set
            value: The value to set the axis to (-1.0 to 1.0)
        """
        if value < -1.0 or value > 1.0:
            raise ValueError("Stick value must be between -1.0 and 1.0.")
        # Convert float value to integer range (0 to 4095)
        int_value = int((value + 1.0) * 2047.5)
        self._transceiver.controller_state.set_stick(axis, int_value)
        
    def set_stick_raw(self, axis: StickAxis, value: int):
        """(Sync) Set the state of a stick axis with raw integer value.

        Args:
            axis: The stick axis to set
            value: The raw integer value to set the axis to (0 to 4095)
        """
        self._transceiver.controller_state.set_stick(axis, value)
        
    def reset(self):
        """Reset the controller state."""
        self._transceiver.controller_state.reset()

    @property
    def transceiver(self) -> ControllerTransceiver:
        """Get the ControllerTransceiver instance."""
        return self._transceiver

    @property
    def controller_state(self):
        """Get the current state of the controller."""
        return self._transceiver.controller_state
