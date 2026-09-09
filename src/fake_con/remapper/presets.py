"""Remapper presets for common input devices."""

from types import SimpleNamespace

from evdev import ecodes as e

from ..models.input import Button, StickAxis
from ..models.remapper import Binding, stick_modifier

Presets = SimpleNamespace(
    CONTROLLER_1_1=[
        Binding((e.EV_KEY, e.BTN_A), output=Button.A),
        Binding((e.EV_KEY, e.BTN_B), output=Button.B),
        Binding((e.EV_KEY, e.BTN_X), output=Button.X),
        Binding((e.EV_KEY, e.BTN_Y), output=Button.Y),
        Binding((e.EV_KEY, e.BTN_TL), output=Button.L),
        Binding((e.EV_KEY, e.BTN_TR), output=Button.R),
        Binding((e.EV_KEY, e.BTN_SELECT), output=Button.MINUS),
        Binding((e.EV_KEY, e.BTN_START), output=Button.PLUS),
        Binding((e.EV_KEY, e.BTN_MODE), output=Button.HOME),
        Binding((e.EV_KEY, e.BTN_THUMBL), output=Button.L_STICK),
        Binding((e.EV_KEY, e.BTN_THUMBR), output=Button.R_STICK),
        Binding((e.EV_ABS, e.ABS_X), output=StickAxis.LEFT_X, modifier=stick_modifier),
        Binding((e.EV_ABS, e.ABS_Y), output=StickAxis.LEFT_Y, modifier=stick_modifier),
        Binding(
            (e.EV_ABS, e.ABS_RX), output=StickAxis.RIGHT_X, modifier=stick_modifier
        ),
        Binding(
            (e.EV_ABS, e.ABS_RY), output=StickAxis.RIGHT_Y, modifier=stick_modifier
        ),
    ]
)
